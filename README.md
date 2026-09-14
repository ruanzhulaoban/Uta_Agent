# utaagent —— 日语歌词学习 agent

输入原始歌词，输出结构化、可校验的标注数据。

当前完成**第一阶段 · 关键任务 1、2、3**：

1. ✅ 接入形态素分析器（MeCab + IPADIC），自动处理上下文相关的汉字读音
2. ✅ 实现分词、词性标注、假名注音（ふりがな）、罗马音生成
3. ✅ 接入 JLPT 词汇表，标注每个词的等级

尚未实现（后续阶段）：LLM 语境化释义与语法点提取、LyricDoc 完整 JSON。

---

## 环境要求

- Python >= 3.8（仅用标准库，无第三方依赖）
- MeCab 及词典已安装（本机位于 `C:\msys64\mingw64\`，会自动探测）

探测顺序：环境变量 `MECAB_PATH` → 常见安装路径 → `PATH`。
词典目录可用 `MECAB_DICDIR` 覆盖，默认 `.../lib/mecab/dic/ipadic`。

## 用法

```bash
# 从文件
python main.py samples/sample.txt

# 从命令行参数
python main.py --text "桜の花が咲く"

# 从标准输入
echo "心に咲いた花よ" | python main.py -

# 紧凑 JSON / 省略罗马音
python main.py --compact samples/sample.txt
python main.py --no-romaji samples/sample.txt

# 指定 mecab 路径
python main.py --mecab C:/msys64/mingw64/bin/mecab.exe lyrics.txt
```

## 输出格式

```jsonc
{
  "schema_version": "0.1.0",
  "analyzer": { "name": "mecab", "dicdir": "...", "dictionary": "ipadic" },
  "lines": [
    {
      "text": "桜の花が咲く",               // 原歌词行
      "reading": "さくらのはながさく",      // 整行平假名读音
      "romaji": "sakura no hana ga saku",  // 整行罗马音
      "words": [
        {
          "surface": "桜",          // 表層形（原文）
          "reading": "さくら",      // 假名注音（平假名）
          "romaji": "sakura",       // 罗马音
          "pos": "名詞",            // 品词
          "pos1": "一般",           // 品词细分类
          "base": "桜",             // 原形
          "conjugation_type": null, // 活用型
          "conjugation_form": null, // 活用形
          "jlpt": "N3"              // JLPT 等级（虚词/未收录为 null）
        }
      ]
    }
  ]
}
```

后续阶段会在 `words` 层追加 `gloss`、`grammar` 字段。

## 关键设计决策

- **假名注音**用 MeCab 的「読み」字段转平假名（如 学校 → がっこう）。
- **罗马音**用「発音」字段生成，能正确反映实际读音：
  助词 は → `wa`、长音 ガッコウ → ガッコー → `gakkō`。
- **罗马音规则**：修订版 Hepburn，支持促音（っ）、长音（ー/おう/おお/うう）、
  拨音（ん，元音前加 `'`）、拗音（きゃ）、外来语音节（ティ/ファ/ヴ）。
  刻意不合并 `ei`（先生 → `sensei`）与 `ii`（新しい → `atarashii`），
  以符合日语学习资料的通行惯例。
- **JLPT 等级**：词表来自 [Bluskyo/JLPT_Vocabulary](https://github.com/Bluskyo/JLPT_Vocabulary)
  （原始数据 tanos.co.uk 的 Jonathan Waller 整理，CC BY 许可，见 `data/jlpt/LICENSE.txt`）。
  匹配按「原形 → 表層形 → 读音」回退，且「词形+读音」精确优先——
  同一词形多读音等级不同时取对的那条（如「人」：じん=N1、ひと=N5）。
  助词/助动词/记号等虚词直接跳过（词表不含功能词）。

## 目录结构

```
utaagent/
├── main.py               # CLI 入口
├── requirements.txt
├── README.md
├── utaagent_core/
│   ├── __init__.py
│   ├── mecab.py          # MeCab 子进程封装
│   ├── kana.py           # 假名 <-> 罗马音
│   ├── jlpt.py           # JLPT 等级查询
│   └── annotator.py      # 标注编排（文本 -> 行/词结构）
├── data/jlpt/            # JLPT 词表 + 许可
│   ├── JLPT_vocab_ALL.json
│   └── LICENSE.txt
├── samples/sample.txt    # 示例歌词
└── tests/
    ├── test_kana.py      # 罗马音单测
    ├── test_jlpt.py      # JLPT 等级单测
    └── test_annotator.py # 端到端测试
```

## 测试

```bash
python tests/test_kana.py
python tests/test_jlpt.py
python tests/test_annotator.py
```

## 已知限制

- 整行罗马音在 MeCab 词边界处用空格分隔，助动词「た」等会与动词分开
  （如 咲いた → `sai ta`）。逐词罗马音不受影响。
- 跨词的拨音 `ん` + 元音不追加撇号（仅在词内部处理）。
- 使用 IPADIC 词典；UniDic / kuromoji 尚未接入（预留扩展点见 `mecab.py`）。
- JLPT 词表为 Tanos 社区整理版，等级判定与官方口径可能有出入
  （官方 JLPT 不公布词表）；复合词（如「日本人」）若未被单独收录则为 `null`。
