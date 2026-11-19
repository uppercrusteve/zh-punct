# zh-punct

中文排版体检。查的是机器判得准的那部分：全半角混用、成对符号不闭合、标点连写、省略号和破折号写成 ASCII 形式。

不改内容，只报位置。`--fix` 只落无歧义的那几条。

```
$ zh-punct draft.md
draft.md:3:12 ZP001 x 中文里用了半角 ,，应写 ，
draft.md:7:1  ZP004 x “ 没有闭合
draft.md:9:4  ZP006 ! 省略号写成 ...，应为 ……
```

## 装

```bash
pipx install git+https://github.com/uppercrusteve/zh-punct
# 或者不装，直接跑
uvx --from git+https://github.com/uppercrusteve/zh-punct zh-punct draft.md
```

需要 Python 3.9+，零运行依赖。

## 用

```bash
zh-punct draft.md                  # 单文件
zh-punct docs/                     # 递归目录，只收 .md/.txt/.rst/.tex/.org
zh-punct docs/ --fix               # 落盘修安全项，剩下的照常报，退出码 1
zh-punct - < draft.md              # 读 stdin
zh-punct --format github docs/     # Actions 注解格式
zh-punct --format json docs/       # 给编辑器/脚本
zh-punct --list-rules              # 看全部规则和默认严重度
```

退出码：`0` 干净、`1` 有问题、`2` 用法或编码错误。`--fix` 之后如果仍有剩项，退出码还是 `1`。

## 规则

| 编号 | 查什么 | 默认 | 自动改 |
|---|---|---|---|
| ZP001 | 中文字间夹半角 `, ; : ? ! ( ) .` | error | 是 |
| ZP002 | 整行没汉字却用全角标点 | warn | 否 |
| ZP003 | 汉字与拉丁字母、数字之间缺空格 | off | 是 |
| ZP004 | `“”（）「」《》` 等成对符号不闭合 | error | 否 |
| ZP005 | 标点连写，如 `，，` `！！` | error | 是 |
| ZP006 | 拿 `...` `。。。` `…` 当省略号 | warn | 是 |
| ZP007 | 拿 `--` 当破折号 | warn | 是 |
| ZP009 | 标点落在换行后的行首（避头尾） | warn | 否 |
| ZP010 | 数字区间用半角 `~` | off | 是 |

按需开关：`--rule ZP003=warn`、`--rule ZP001=off`，可逗号连写、可重复。`off` 连自动修复一起关掉。

## 不报什么

误报比漏报更烦人，所以下面这些区域默认整段跳过：

- 围栏代码块、缩进代码块、行内代码
- URL、邮箱、自动链接、`<html 标签>`
- 链接目的地 `[文字](dest)`、引用式定义 `[id]: url`
- YAML front matter、HTML 注释
- 反斜杠转义的字符（`\,`）

行内另有两条逃逸：

```markdown
<!-- zh-punct: off -->
这一整段不查
<!-- zh-punct: on -->

这一行不查 <!-- zh-punct: skip-line -->
```

### 有意为之的豁免

- **小数点、千分位、版本号**：`3.14`、`1,000`、`v0.1.0` 不动。
- **纯 ASCII 的括号内容**：`跑 foo(bar) 看看` 里的括号不改。
- **参考文献行**（`[12] ...` 或表格里的 `| [12] |`）：作者之间用半角逗号是 GB/T 7714 的规定写法，整行的 `, ; :` 不再判。
- **化学式下标**：`(NaPO₃)₆` 视为西文内容。
- **Markdown 图片语法**：`![说明](x.png)` 开头的 `!` 不算半角感叹号。

## 配置

工作目录或任一上级目录放 `.zhpunctignore`，每行一个 glob：

```
draft/**
CHANGELOG.md
```

也能用 `--ignore GLOB` 或环境变量 `ZH_PUNCT_IGNORE`（`;` 分隔）。

`--no-markdown` 把文件当纯文本，代码块也照查——给 `.txt` 语料用。

## 它不干什么

- 判断该不该断句、该用逗号还是分号、语气对不对。
- 查错别字、搭配、语序。那是另一类工具。
- 处理繁体、日文、竖排的专门规则（繁体标点也能跑，但规则没针对性调过）。
- 全角空格、制表符对齐。

## 边界

这是排版卫生的底噪检查，不是排版标准本身。它报了，多半该改；它没报，不代表就对了。规则依据来自 GB/T 15834《标点符号用法》里可机械判定的部分，判断类条文没有实现。

各地出版社、期刊社有自己的细则。有冲突时以对方的投稿规范为准，用 `--rule` 关掉对应的编号。

## 开发

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e . pytest ruff
pytest
ruff check .
```

新增规则：在 `src/zh_punct/rules.py` 的 `RULES` 里登记，写检查函数并挂进 `CHECKS`，然后补测试——**反例测试至少和正例一样多**，覆盖代码块、URL、纯英文行三种语境。

## 许可

MIT。
