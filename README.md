# utaagent — 日语歌词学习工具

输入原始歌词或已分词、注音和 JLPT 标注的 JSON，输出中文释义与跨行语法关联。
高频词直接使用词典；未命中词和语法点使用 OpenAI 兼容的文本 Chat Completions 接口。

## 安装与运行

Python >= 3.9：

```bat
python -m pip install -r requirements.txt
python main.py samples/annotated.json --input-format json --no-llm
```

原始文本模式需要 MeCab + IPADIC，可用 --mecab 或 MECAB_PATH 指定。
已分词 JSON 模式不需要 MeCab。JLPT 数据来源与许可见 data/jlpt/LICENSE.txt。
输入格式定义在 schemas/input.schema.json；原始行和词序不变，空行保留。
输入只接受上游标注字段，不接受重复增强的输出；未知字段会被拒绝。

默认模型仍为百炼 qwen-plus，密钥环境变量为 DASHSCOPE_API_KEY。
自定义模型示例（CMD；模型 ID 以服务商支持的名称为准）：

```bat
set "MY_LLM_API_KEY=你的密钥"
set "PYTHONIOENCODING=utf-8"
python main.py samples/cross_line.json --input-format json --base-url https://服务商地址/v1 --model 模型名称 --api-key-env MY_LLM_API_KEY --output-mode json_object
```

PowerShell 设置环境变量使用：
```powershell
$env:MY_LLM_API_KEY = "你的密钥"
$env:PYTHONIOENCODING = "utf-8"
```

密钥从指定的环境变量读取，不写入配置文件；程序不自动读取 .env。
--api-key-env 后面填写变量名，不能填写密钥本身。
接口地址自动追加 /chat/completions；不包含 Responses API、工具调用或多模态适配。

## 配置与模型切换

```bat
python main.py samples/annotated.json --input-format json --config config.example.json --model 另一个模型
```

优先级：命令行 > 配置文件 > 默认值。
JSON 配置允许 model、base_url、api_key_env、output_mode、timeout、retries、cache_path、extra_body。
模型名无白名单；程序不会自动更换模型。extra_body 可指定模型专属参数，不能覆盖核心协议字段。
--dict 自定义词典，--cache 自定义缓存文件，--no-cache 禁用缓存，--no-llm 完全离线。
相对缓存路径以运行目录为基准；默认缓存为项目 data/cache/gloss_cache.json。

| output_mode | 行为 |
|---|---|
| auto（默认） | 从 json_schema 开始，明确不支持时依次尝试 json_object、text |
| json_schema | 发送 response_format、Schema、strict: true，不降级模式 |
| json_object | JSON 模式，提示词说明结构，本地校验 |
| text | 普通文本模式，要求单个 JSON 对象，本地校验 |

只有 HTTP 400/422 明确报告输出格式不支持才自动切换。
认证、权限、模型名错误不会触发切换；无法识别服务商文案时可手动指定模式。
超时、限流、部分服务端错误和校验失败有限重试；默认 retries=1，范围 0..5。
每种输出模式最多 retries+1 次请求。JSON 模式不等于服务端严格 Schema。
参考：[百炼结构化输出](https://help.aliyun.com/en/model-studio/qwen-structured-output)、
[DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/)。

## 20 行分析块

换行是歌词排版，不一定是句子边界；同一行可以有多个短句。
每个请求包含最多 **20 个原始行**（包含重叠上下文和空行），不发送全文作为上下文。

- 尚有后续行时，优先在当前窗口最后一个空行或明确句末处结束。
- 若没有自然断点，按 20 行硬切，下一块重叠前块最后 **2 行**。
- 最后不足 20 行的部分整体处理。一个块中可以提取多个独立句型。
- 例如无自然断点的 41 行：第 1–20 行、第 19–38 行、第 37–41 行。
- 20 行是上限，不是必须凑满的长度，也不是可靠的句法边界。

提示词要求模型结合块内上下文分析跨行表达。重叠不保证覆盖所有超长句型，
自然句末判断也是启发式；更长跨度或特殊排版仍可能漏分析。
行数不限制 Token 数：极长单行仍可能超过模型上下文或输出限制。
当前请求串行执行，重叠和重复提示词带来额外 Token；收益是缩小失败重试范围。

## 输出 0.5.0 与前端关联

原始歌词仍在 lines，新增 blocks；没有文档级统一语法表。

- lines[].index：原始行的零基位置。
- lines[].words[].index：词在本行的零基位置。
- words[].gloss/source：中文释义与 dict / llm / pending / symbol 来源。
- words[].grammar_ids：例如 ["b0:g1"]，指向块 0 内的语法点 1；未关联时 []。
- blocks[].id：块的零基编号。
- blocks[].line_indices：块内各行在原始 lines 中的位置，最多 20 项。
- blocks[].grammar[].id：语法点在当前块的零基编号。
- blocks[].grammar[].word_refs：每项为 {"line_index": 0, "word_index": 2}。
  line_index 是**块内**行位置，不是原始文档行号；word_index 是该行词位置。
- blocks[].llm：status、output_mode、error，描述该块调用情况。

前端将引用映射到词：
```javascript
const originalLine = block.line_indices[ref.line_index];
const word = doc.lines[originalLine].words[ref.word_index];
```

重叠区域的词可以同时关联相邻块的语法点，b块号:g语法号避免局部编号歧义。
同样的引用位置和句型在重叠分析中只保留首次成功结果；
释义已成功的词不会在后块再次请求释义，但仍作为上下文参与语法分析。
去重比较精确词位置和 pattern，不合并不同句型；模型把同一概念改写成不同 pattern 时可能留下重复。
若前块失败，重叠词仍可在后块补充；前块失败状态不会因此被隐藏。
语法点按引用位置与内容排序后编号；相同内容在模型改变返回顺序时保持编号。
编号不是跨编辑的永久标识，歌词、分块边界或语法内容改变后可能重排。

0.4.0 迁移：lines[].grammar 和 lines[].llm 移至 blocks；
word_indices 改为 word_refs；词的 grammar_ids 从整数改为块限定字符串。
前端应按新 Schema 更新读取方式。输入格式保持不变。

## 校验、状态与缓存

本地先验证输入，再验证模型响应（包括缓存），最后校验完整输出：
- 释义位置完整、唯一地覆盖 targets。
- 引用的行、词编号是整数、在块内有效且不重复。
- 语法原文来自块内，允许保留或省略换行。
- 分析块不超过 20 行、按原文推进并覆盖所有行。
- 词上的 grammar_ids 与语法 word_refs 双向一致，不留悬空引用。

定义与检查在 utaagent_core/schemas.py。schemas/ 导出 JSON Schema 负责结构，
Python 的 validate(document, FINAL_SCHEMA) 同时检查跨字段引用约束。
validation=passed 只表示结构和引用合规，不保证语义准确或所有调用成功。

进度写 stderr，stdout 只输出 JSON；--quiet 关闭进度提示。
块状态为 ok / cached / pending / disabled / empty。
顶层 llm.calls 是实际 HTTP 请求次数，cache_hits 是缓存命中数，failures 是**失败块数**。
输入或配置错误退出 2；调用失败输出合规待补充结果并退出 0，需检查失败块和 pending 词。

缓存键包含完整分析块、目标词、接口、模型、输出模式、参数、提示词和 Schema。
新协议自动隔离旧缓存，无需删除。只保存校验通过的模型结果。
写缓存失败会提示；缓存使用临时文件原子替换。并行运行应使用不同缓存文件，
避免同时写同一文件丢失部分缓存条目。分块或前块结果变化可能导致相邻块缓存失效。

## Python API

```python
import json
from utaagent_core import CompatibleClient, Glossifier

client = CompatibleClient(
    base_url="https://服务商地址/v1",
    model="模型名称",
    api_key_env="MY_LLM_API_KEY",
    output_mode="json_object",
)
with open("samples/cross_line.json", encoding="utf-8") as f:
    result = Glossifier(llm=client).enrich(json.load(f))
```

原始文本使用 annotate(text)，已标注数据使用 enrich(document)。
客户端新增 gloss_block(payload)；旧方法名 gloss_line 保留，但现在也接收块协议。
QwenClient 仍是 CompatibleClient 的别名。

## 测试

```bat
python -m unittest discover -s tests -p "test_*.py" -v
python tests/test_kana.py
python tests/test_jlpt.py
python tests/test_annotator.py
python tests/test_glossifier.py
```

自动化接口和分块测试模拟 HTTP，不调用真实模型；后两项旧脚本需要 MeCab。
真实服务商的语法质量、耗时和费用需要另行联调。

## 单文件 HTML 歌词书

已完成 0.5.0 标注 JSON 可直接导出，不调用模型、不重新分词。
HTML 包含封面、目录、每首歌、词语手帖及语法说明；CSS 和阅读设置脚本全部内嵌。
文件离线可打开，不请求外部字体、图片或脚本。系统字体会影响不同设备上的实际观感。

CMD 示例：
```bat
python export_html.py samples/user_lyrics.deepseek.json -o exports/lyrics.html --theme bunko --title "我的歌词书"
python export_html.py song1.json song2.json -o exports/collection.html --theme cards
python export_html.py --manifest samples/book.example.json -o exports/book.html --theme lyrics
```

三套主题：
- bunko / 文库本：米色纸面、明朝体、克制的灰绿色注音，适合连续阅读。
- cards / 学习卡片：浅蓝色、无衬线正文、行卡片和词语卡片，适合学习。
- lyrics / 歌词本：暖白与豆沙色、更大的歌词字号与行距，突出歌词节奏。

文件顶部可切换主题、显示/隐藏注音、显示/隐藏释义与语法。
交互仅改变当前页面；要保存指定初始主题，使用 --theme 重新导出。
没有 JavaScript 时默认内容仍全部可读、目录和词语锚点仍可使用。
点击正文词跳到释义；语法说明可返回每个关联词，包含跨块、跨行引用。

出版配置示例见 samples/book.example.json：
title/subtitle 是封面书名、副标题；songs 每项包含 input、title、可选 artist、chorus_ranges。
input 相对于出版配置所在目录解析。chorus_ranges 使用原始歌词的**一基闭区间**，例如 [[8,9]]。
示例中副歌范围只是可编辑的展示配置，不代表程序识别出的歌曲结构；无需副歌强调时删除该字段。
不自动把重复歌词认作副歌，也不把分析块的边界当作歌词段落。

注音使用原生 HTML ruby/rt/rp。按上游词的读音与假名锚点可靠对齐时拆分注音，
例如「歩き」只给「歩」标「ある」，「取り戻す」分别标「取」「戻」。
仅有词级读音时不能可靠推断每个汉字的读法，「今日」「行方不明」等保留汉字组注音，
不机械切分读音。未知读音或假名词不重复加注音。
正文保留原始空格、换行；若词元无法按顺序匹配原文，导出会报错，避免静默丢字。

所有输入文本均转义后插入 HTML，封面、释义和歌词不能注入脚本。
原始标注数据不修改，未补充释义和失败块会有提示。
导出格式只接受当前最终 Schema；不会直接接受未增强的分词 JSON。

PDF 功能暂缓。已提供浏览器打印 CSS（A5 页边距、分页、隐藏工具栏），
可自行通过浏览器打印到 PDF；此阶段不保证跨浏览器分页完全一致，也没有实现独立注音布局引擎。
