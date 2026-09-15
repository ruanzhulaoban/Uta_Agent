"""JSON Schema and cross-field validation for bounded lyric blocks."""
from jsonschema import Draft202012Validator
from .blocks import MAX_LINES

def obj(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required,
            "additionalProperties": False}

S = {"type": "string"}
NS = {"type": ["string", "null"]}
NONEMPTY = {"type": "string", "minLength": 1, "pattern": r"\S"}
INDEX = {"type": "integer", "minimum": 0}
def array(item):
    return {"type": "array", "items": item}

WORD_REF = obj({"line_index": INDEX, "word_index": INDEX})
WORD_REFS = dict(array(WORD_REF), minItems=1)
GLOSS_SCHEMA = obj({
    "words": array(obj({"line_index": INDEX, "word_index": INDEX, "gloss": NONEMPTY})),
    "grammar": array(obj({"text": NONEMPTY, "pattern": NONEMPTY, "meaning": NONEMPTY,
                          "word_refs": WORD_REFS})),
})
WORD_FIELDS = {k: NS for k in ("pos", "pos1", "base", "conjugation_type", "conjugation_form", "jlpt")}
WORD_FIELDS.update(surface={"type": "string", "minLength": 1}, reading=S, romaji=S)
INPUT_WORD = obj(WORD_FIELDS, ["surface", "reading", "pos", "jlpt"])
INPUT_LINE = obj({"text": S, "reading": S, "romaji": S, "words": array(INPUT_WORD)}, ["text", "words"])
INPUT_SCHEMA = obj({"schema_version": S, "analyzer": {"type": "object"}, "lines": array(INPUT_LINE)}, ["lines"])
FINAL_WORD = obj(dict(WORD_FIELDS, index=INDEX,
                      grammar_ids=array({"type": "string", "pattern": r"^b[0-9]+:g[0-9]+$"}),
                      gloss=S, source={"enum": ["dict", "llm", "pending", "symbol"]}),
                 ["surface", "reading", "pos", "jlpt", "gloss", "source", "index", "grammar_ids"])
BLOCK_STATUS = obj({"status": {"enum": ["ok", "cached", "pending", "disabled", "empty"]},
                    "output_mode": NS, "error": NS})
FINAL_SCHEMA = obj({
    "schema_version": {"const": "0.5.0"},
    "analyzer": {"type": "object"},
    "lines": array(obj({"index": INDEX, "text": S, "reading": S, "romaji": S,
                        "words": array(FINAL_WORD)}, ["index", "text", "words"])),
    "blocks": array(obj({
        "id": INDEX,
        "line_indices": dict(array(INDEX), minItems=1, maxItems=MAX_LINES),
        "grammar": array(obj({"id": INDEX, "text": NONEMPTY, "pattern": NONEMPTY,
                              "meaning": NONEMPTY, "word_refs": WORD_REFS, "source": {"const": "llm"}})),
        "llm": BLOCK_STATUS})),
    "dictionary": {"anyOf": [obj({"name": S, "version": S}), {"type": "null"}]},
    "llm": obj({"enabled": {"type": "boolean"}, "model": NS, "requested_mode": NS,
                "effective_mode": NS, "calls": INDEX, "cache_hits": INDEX, "failures": INDEX,
                "last_error": NS, "validation": {"const": "passed"}}),
}, ["schema_version", "lines", "blocks", "dictionary", "llm"])

def validate(value, schema):
    Draft202012Validator(schema).validate(value)
    if schema is FINAL_SCHEMA:
        validate_references(value)

def _pairs(refs, lines, words_key):
    pairs = []
    for ref in refs:
        li, wi = ref["line_index"], ref["word_index"]
        if type(li) is not int or type(wi) is not int or not 0 <= li < len(lines):
            raise ValueError("word_refs 含非法或越界行编号")
        if not 0 <= wi < len(lines[li][words_key]):
            raise ValueError("word_refs 含非法或越界词编号")
        pairs.append((li, wi))
    if len(pairs) != len(set(pairs)):
        raise ValueError("词引用不可重复")
    return pairs

def _check_text(text, lines):
    # Newlines may be retained or omitted by the model, but other content must be original.
    if text.replace("\n", "").replace("\r", "") not in "".join(
            line["text"].replace("\r", "") for line in lines):
        raise ValueError("语法 text 必须是块内原文片段（允许省略换行）")

def validate_result(result, payload):
    validate(result, GLOSS_SCHEMA)
    lines = payload["lines"]
    if not 1 <= len(lines) <= MAX_LINES:
        raise ValueError("分析块必须包含 1..20 行")
    actual = _pairs(result["words"], lines, "tokens")
    expected = _pairs(payload["targets"], lines, "tokens")
    if set(actual) != set(expected):
        raise ValueError("释义必须完整、唯一地覆盖 targets")
    for grammar in result["grammar"]:
        _pairs(grammar["word_refs"], lines, "tokens")
        _check_text(grammar["text"], lines)

def grammar_key(point, line_indices):
    """Deduplicate overlap by exact positions and pattern; keep the first successful analysis."""
    return (tuple(sorted((line_indices[r["line_index"]], r["word_index"])
                         for r in point["word_refs"])), point["pattern"].strip())

def validate_references(document):
    lines = document["lines"]
    expected = [[[] for _ in line["words"]] for line in lines]
    for li, line in enumerate(lines):
        if type(line["index"]) is not int or line["index"] != li:
            raise ValueError("行 index 必须与原始位置一致")
        for wi, word in enumerate(line["words"]):
            if type(word["index"]) is not int or word["index"] != wi:
                raise ValueError("词 index 必须与行内位置一致")
    covered, seen = set(), set()
    previous_start = -1
    for bid, block in enumerate(document["blocks"]):
        indices = block["line_indices"]
        if type(block["id"]) is not int or block["id"] != bid:
            raise ValueError("块 id 必须按顺序编号")
        if any(type(i) is not int or not 0 <= i < len(lines) for i in indices):
            raise ValueError("块含非法行编号")
        if indices != list(range(indices[0], indices[-1] + 1)) or indices[0] <= previous_start:
            raise ValueError("块必须按原文顺序推进且包含连续行")
        previous_start = indices[0]
        covered.update(indices)
        local_lines = [lines[i] for i in indices]
        for gid, point in enumerate(block["grammar"]):
            if type(point["id"]) is not int or point["id"] != gid:
                raise ValueError("语法 id 必须与块内位置一致")
            pairs = _pairs(point["word_refs"], local_lines, "words")
            _check_text(point["text"], local_lines)
            key = grammar_key(point, indices)
            if key in seen:
                raise ValueError("重叠分析块含重复语法点")
            seen.add(key)
            for li, wi in pairs:
                expected[indices[li]][wi].append("b" + str(bid) + ":g" + str(gid))
    if covered != set(range(len(lines))):
        raise ValueError("分析块必须覆盖所有原始行")
    for li, line in enumerate(lines):
        for wi, word in enumerate(line["words"]):
            if word["grammar_ids"] != expected[li][wi]:
                raise ValueError("grammar_ids 与 word_refs 必须双向一致且无重复")
