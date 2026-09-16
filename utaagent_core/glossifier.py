"""Dictionary-first enrichment using bounded, overlapping contexts."""
from copy import deepcopy
from .annotator import Annotator
from .gloss_dict import GlossDict
from .blocks import split_blocks
from .text_kind import is_latin_text
from .schemas import INPUT_SCHEMA, FINAL_SCHEMA, validate, validate_result, grammar_key

SCHEMA_VERSION = "0.6.0"
PENDING_GLOSS = "待补充"

class Glossifier:
    def __init__(self, annotator=None, dictionary=None, llm=None, status=None):
        self.annotator = annotator
        self.dictionary = GlossDict() if dictionary is None else (None if dictionary is False else dictionary)
        self.llm = llm
        self.status = status or (lambda message: None)

    def annotate(self, text):
        if self.annotator is None:
            self.annotator = Annotator()
        return self.enrich(self.annotator.annotate(text))

    def enrich(self, document):
        validate(document, INPUT_SCHEMA)
        doc = deepcopy(document)
        failures, last_error, attempts = 0, None, 0
        before_calls = getattr(self.llm, "calls", 0)
        if not isinstance(before_calls, int):
            before_calls = len(before_calls)
        before_hits = getattr(self.llm, "cache_hits", 0)
        for li, line in enumerate(doc["lines"]):
            line["index"] = li
            for wi, word in enumerate(line["words"]):
                word.update(index=wi, grammar_ids=[])
                if is_latin_text(word["surface"]):
                    word.update(reading=word["surface"], jlpt=None, gloss="", source="symbol")
                    continue
                entry = self.dictionary.lookup(surface=word["surface"], reading=word["reading"],
                    pos=word["pos"], base=word.get("base")) if self.dictionary is not None else None
                if entry and entry.get("meaning"):
                    word.update(gloss=entry["meaning"], source="dict")
                elif word["pos"] in ("記号", "フィラー"):
                    word.update(gloss="", source="symbol")
                else:
                    word.update(gloss=PENDING_GLOSS, source="pending")
        groups = split_blocks(doc["lines"])
        doc["blocks"] = []
        seen = set()
        for bid, indices in enumerate(groups):
            self.status("处理分析块 " + str(bid + 1) + "/" + str(len(groups)) +
                        "（原文第 " + str(indices[0] + 1) + "–" + str(indices[-1] + 1) + " 行）")
            block = {"id": bid, "line_indices": indices, "grammar": [],
                     "llm": {"status": "disabled" if self.llm is None else "empty",
                             "output_mode": None, "error": None}}
            doc["blocks"].append(block)
            local = [doc["lines"][i] for i in indices]
            if self.llm is None or not any(w["source"] != "symbol" for line in local for w in line["words"]):
                continue
            payload = {
                "text": "\n".join(line["text"] for line in local),
                "lines": [{"line_index": li, "text": line["text"], "tokens": [
                    {key: w.get(key) for key in ("index", "surface", "reading", "pos", "base", "jlpt")}
                    for w in line["words"]]} for li, line in enumerate(local)],
                "targets": [dict(line_index=li, word_index=wi, **{
                    key: w[key] for key in ("surface", "reading", "pos")})
                    for li, line in enumerate(local) for wi, w in enumerate(line["words"])
                    if w["source"] == "pending"]}
            attempts += 1
            try:
                # gloss_line is retained as a client compatibility alias; payload is now a block.
                call = getattr(self.llm, "gloss_block", None) or self.llm.gloss_line
                result = call(payload)
                validate_result(result, payload)
                points = sorted(result["grammar"], key=lambda g: (
                    tuple(sorted((r["line_index"], r["word_index"]) for r in g["word_refs"])),
                    g["pattern"], g["text"], g["meaning"]))
                for point in points:
                    if any(is_latin_text(local[r["line_index"]]["words"][r["word_index"]]["surface"])
                           for r in point["word_refs"]):
                        continue
                    key = grammar_key(point, indices)
                    if key in seen:
                        continue
                    gid = len(block["grammar"])
                    point = dict(point, id=gid, source="llm",
                                 word_refs=sorted(point["word_refs"], key=lambda r: (r["line_index"], r["word_index"])))
                    block["grammar"].append(point)
                    seen.add(key)
                    for ref in point["word_refs"]:
                        local[ref["line_index"]]["words"][ref["word_index"]]["grammar_ids"].append(
                            "b" + str(bid) + ":g" + str(gid))
                for item in result["words"]:
                    local[item["line_index"]]["words"][item["word_index"]].update(gloss=item["gloss"], source="llm")
                block["llm"]["status"] = "cached" if getattr(self.llm, "last_cached", False) else "ok"
            except Exception as exc:
                failures += 1
                from .llm import LLMError
                last_error = str(exc)[:200] if isinstance(exc, LLMError) else "模型结果处理或本地校验失败"
                block["llm"].update(status="pending", error=last_error)
                self.status("分析块 " + str(bid + 1) + " 待补充：" + last_error + "；可用 --model 更换模型")
            block["llm"]["output_mode"] = getattr(self.llm, "effective_mode", None)
        calls = getattr(self.llm, "calls", 0)
        calls = calls - before_calls if isinstance(calls, int) else attempts
        doc["schema_version"] = SCHEMA_VERSION
        doc["dictionary"] = {"name": self.dictionary.name, "version": self.dictionary.version} if self.dictionary is not None else None
        doc["llm"] = {"enabled": self.llm is not None, "model": getattr(self.llm, "model", None),
                      "requested_mode": getattr(self.llm, "requested_mode", None),
                      "effective_mode": getattr(self.llm, "effective_mode", None),
                      "calls": calls, "cache_hits": getattr(self.llm, "cache_hits", 0) - before_hits,
                      "failures": failures, "last_error": last_error, "validation": "passed"}
        validate(doc, FINAL_SCHEMA)
        return doc
