# utaagent — 日语歌词学习工具

混合歌词中的英语、法语等拉丁字母词保留原文，不添加注音、中文释义、JLPT 或词语手帖卡片，也不参与语法引用。纯拉丁字母歌词块不调用模型；混合块仍保留完整原文作为日语分析上下文。为兼容现有 0.6.0 结构，这些词使用 `source: "symbol"` 表示仅展示，`gloss` 为空、`jlpt` 为 null。此规则应用于新生成的标注，已有 HTML 需要重新生成。MeCab 未登录词不再读取可能缺失的读音字段。

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

## 输出 0.6.0 与前端关联

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

已完成 0.5.0 或 0.6.0 标注 JSON 可直接导出，不调用模型、不重新分词。
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
导出接受 0.5.0 和 0.6.0 最终标注；不会直接接受未增强的分词 JSON。

PDF 功能暂缓。已提供浏览器打印 CSS（A5 页边距、分页、隐藏工具栏），
可自行通过浏览器打印到 PDF；此阶段不保证跨浏览器分页完全一致，也没有实现独立注音布局引擎。

### 原形与 JLPT 词汇池

词语手帖读取已有 base 字段，在原形不同于表面词形时显示“原形：歩く”，不加原形注音。
原形缺失、为 * 或与表面词形相同时省略此行，不猜测、不重新请求模型。

每首歌的词语手帖提供“全部 / N5 / N4 / N3 / N2 / N1 / 未分级”按钮。
按**精确等级**筛选，N3 不包含 N4、N5；未分级包括 null 或非标准等级，不代表低难度。
选择会同步到书中所有曲目的词语手帖，各曲分别显示匹配数量及空结果提示。
数量按每首歌去重后的词条计数，卡片内保留各次出现位置和不同语境释义。
筛选不影响歌词、语法说明或原始 JSON。点击歌词中的被筛除词时会自动恢复“全部”，保证跳转可见。
无 JavaScript 时默认展示全部词条；筛选控件不显示。刷新后恢复“全部”。
浏览器打印保留当前筛选后的词语手帖，若要打印完整词汇，请先选“全部”。
修改后需要重新运行 HTML 导出；无需重新调用 LLM。


### 去重词条与详细语法讲解（0.6.0）

词语手帖按每首歌的“原形（无有效原形时用词形）＋词性＋JLPT”等级归并。
保留首次出现的顺序和卡片标题，并列出不同词形/读音、不同中文释义及对应原文位置。
相同中文释义只展示一次。不同词性或不同等级不会混为一张卡片，跨歌曲不去重。
正文的每次出现都跳到对应的归并卡片，卡片可返回任意出现位置；
合并只影响 HTML，不删除标注数据，也不修改逐词语法引用。
缺少原形时不同活用词形不会被猜测性归并。同形异义保留不同释义，不强行合并含义。

新语法对象除 pattern/text/meaning/word_refs 外，必须包含：
- connection：接续规则，说明前接词类和所需活用。
- explanation：语法本身的功能、语气、使用情境与必要限制，不是原句翻译。
- context_usage：指出本段实际构成及前后关系，解释为何使用该句型。

HTML 分别展示“核心含义、接续规则、用法说明、歌词中的用例、在本段中的作用”。
模型响应缺少新字段、空白字段或 explanation 完全重复 meaning 时会被拒绝并按配置重试。
结构和字符串检查不能保证讲解在语言学上完全正确，仍应抽样审核。

旧 0.5.0 JSON 仍可导出，缺少讲解时明确显示“接续与用法讲解待补充”，不伪造教学内容。
缓存键包含新提示词和 Schema，旧结果不会被当作完整新讲解使用。
原有歌词若要补齐讲解，重新运行标注并导出（CMD 示例）：

```bat
python main.py samples/user_lyrics.txt --base-url https://api.deepseek.com --model deepseek-flash --api-key-env DEEPSEEK_API_KEY --output-mode json_object > samples/user_lyrics.detailed.json
python export_html.py samples/user_lyrics.detailed.json -o exports/book-detailed.html --theme bunko --title "我的歌词书"
```

上述模型名称以实际服务商支持范围为准。新结果应为 schema_version=0.6.0。
无需重新分词的应用可以调用 Glossifier.enrich 上游输入；不能将最终输出直接当作上游输入。

### 手动管理词语手帖

在每首歌的词语手帖里点击“添加词条”，填写词形、可选读音/原形、词性、JLPT 和中文释义。
点击卡片上的“移除”会将该词放入本曲“已移除”列表，可随时恢复。
操作只改变 HTML 手帖，不改歌词、语法关系或源 JSON。手动词条没有伪造的歌词出处或语法关联。
按原形（缺失时用词形）＋词性＋等级检查重复，已存在时定位原词条，不覆盖原释义。
点击已移除词的歌词链接会提示恢复，不会自动把它重新加入。

同一内容的书使用独立浏览器保存空间，三套主题共享手动修改。
刷新优先读取更新的本地修改；浏览器可能限制 file:// 文件的持久存储，失败时页面会提示。
通过“下载修改后的 HTML”把修改内嵌进单文件，换设备也能保留，不依赖浏览器缓存。
手动输入按文本插入，不能执行 HTML/脚本。下载不会覆写原始 HTML，文件由浏览器保存。
重新标注改变书内容后视作新书，不自动把旧书修改套用到新数据上。
无 JavaScript 时不能增删词条，仍可阅读导出文件当前保留的内容。


## 桌面图形界面（Windows）

双击项目根目录的 `start_gui.bat`，或运行 `python gui.py`。首次安装桌面依赖：`python -m pip install -r requirements-gui.txt`。界面使用 PySide6 / Qt Quick，分词仍需 MeCab。

1. 在“生成手帖”选择 Qwen、DeepSeek 或自定义兼容接口；接口地址和模型名均可修改，模型名以服务商实际提供为准。
2. 填写 API Key，点击“保存密钥到环境变量”。密钥保存到 Windows 当前用户环境变量，后续启动自动读取。Qwen 默认使用 DASHSCOPE_API_KEY，DeepSeek 使用 DEEPSEEK_API_KEY；自定义变量名须以 API_KEY 结尾。更换密钥后再次保存即可。其他已打开的终端可能需要重启。
3. 填写标题、粘贴歌词（也可导入 UTF-8 TXT），选择主题后点击“一键生成 HTML”。生成在后台运行，界面展示处理状态；最终结构经过本地校验。仅词典模式无需密钥。
4. “我的书架”中双击阅读，支持导入 HTML、另存 HTML、修改书架名称、移入回收站及恢复。书架名称不修改原 HTML 封面；导入仅复制文件，用户打开时才在浏览器中运行。

书架及标注 JSON 存在 `data/desktop/books`，回收站在 `data/desktop/.trash`，配置和模型缓存也位于 `data/desktop`；该目录已加入 Git 忽略。每次生成保存为独立手帖，不覆盖已有版本。普通配置不包含密钥；环境变量本身不是加密保险库。

生成结束若有待补充词或失败块，界面会显示数量，可检查配置后重新生成。正在生成时请等待任务结束再关闭窗口。浏览器中修改的词语手帖仍需点击页面“下载修改后的 HTML”，再导入书架保存该版本；书架另存复制的是书架中的文件。


### Qt Quick 单页工作台

主窗口左侧粘贴歌词并生成，右侧直接显示书架，不再切换页面。右上角“设置”打开模型、密钥、输出方式、主题、标题及 MeCab 配置弹窗；标题留空时取歌词首行。输入区的“⋯”提供 TXT 导入与日志查看。书架每张卡片可阅读，其“⋯”菜单提供另存、重命名、移入回收站；书架右上角“⋯”可切换回收站并恢复。

原有 `data/desktop` 书架、配置和用户密钥环境变量直接沿用。密钥若需持久保存，请在设置中勾选“保存密钥到用户环境变量”。
