# zh-punct

中文排版体检，命令行工具。只查机器判得准的形态：全半角混用、成对符号不闭合、标点连写、用 `...` 当省略号。改内容的事它不干。

```
$ zh-punct a.md
a.md:1:1 ZP004 x “ 没有闭合
a.md:2:2 ZP006 ! 省略号写成 ...，应为 ……
a.md:3:3 ZP005 x 标点重复 ，，
```

格式是 `文件:行:列 规则号 原始字符 说明`，一行一处。

退出码 `0` 干净、`1` 有问题、`2` 用法或编码错误，`--format github` 直接出 Actions 注解。

## 安装

```bash
pipx install git+https://github.com/uppercrusteve/zh-punct
```

不想装就用 `uvx --from git+https://github.com/uppercrusteve/zh-punct zh-punct draft.md`。需要 Python 3.10+，零运行依赖。

## 用法

```bash
zh-punct draft.md                  # 单文件
zh-punct docs/                     # 递归目录，只收 .md/.markdown/.txt/.rst/.tex/.org
zh-punct docs/ --fix               # 落盘修安全项，剩下的照常报
zh-punct - < draft.md              # 读 stdin
zh-punct --format github docs/     # Actions 注解
zh-punct --format json docs/       # 给编辑器或脚本
zh-punct --ext .txt corpus/        # 临时加后缀
zh-punct --list-rules              # 看全部规则与默认严重度
```

`--fix` 只改无歧义的规则；改完还有剩项，退出码仍是 `1`。

## 规则

| 编号 | 查什么 | 默认 | 可自动改 |
|---|---|---|---|
| ZP001 | 中文字之间夹半角 `, ; : ? ! ( ) .` | error | 是 |
| ZP002 | 整行没有汉字却用全角标点 | warn | 否 |
| ZP003 | 汉字与拉丁字母、数字之间缺空格 | off | 是 |
| ZP004 | `“”（）「」《》` 等成对符号不闭合 | error | 否 |
| ZP005 | 标点连写，如 `，，` `！！` | error | 是 |
| ZP006 | 用 `...` 或 `。` 顶省略号 | warn | 是 |
| ZP007 | 用 `--` 顶破折号 | warn | 是 |
| ZP009 | 标点落在换行后的行首（避头尾） | warn | 否 |
| ZP010 | 数字区间用半角 `~` | off | 是 |

按需开关：`--rule ZP003=warn`、`--rule ZP001=off`，可重复、可逗号连写。`off` 连自动修复一起关。

## 配置

在仓库根或任一上级目录放 `.zhpunctignore`，每行一个 glob：

```
draft/**
CHANGELOG.md
```

也可以用 `--ignore GLOB` 或环境变量 `ZH_PUNCT_IGNORE`（`;` 分隔）。`--no-markdown` 把文件当纯文本，代码块里的内容也照查，给纯语料用。

目录递归时本来就跳过 `.git/`、`node_modules/`、`.venv/`、`dist/`、`build/` 这类目录，要再排除别的用上面三种方式。

## 哪里不查

误报是这类工具的死因，所以下面这些整段跳过，不解析：

- 围栏代码块、缩进代码块、行内代码
- URL、邮箱、自动链接、`<html 标签>`
- 链接目的地 `[文字](dest)`、引用式定义 `[id]: url`
- YAML front matter、HTML 注释
- 反斜杠转义的字符（`\,`）

行级还有两个开关：

```markdown
<!-- zh-punct: off -->
这一段整块不查
<!-- zh-punct: on -->

这一行不查 <!-- zh-punct: skip-line -->
```

识别的写法里另有几条豁免：小数点和千分位（`3.14`、`1,000`）、版本号（`v0.1.0`）、纯 ASCII 括号内容（`foo(bar)`）、化学式下标（`(NaPO₃)₆`）、Markdown 图片语法开头那个 `!`。参考文献行（`[12] ...` 或表格里的 `| [12] |`）整行的 `, ; :` 不判——GB/T 7714 就要求作者之间用半角逗号。

## 边界

- 判的是形态，不是文笔。该不该断句、逗号还是分号、语气对不对，它不知道。
- 错别字、搭配、语序属于另一类工具，这里不碰。
- 繁体、日文能跑，但规则是按简体调的，没针对性验证。竖排不管。
- 规则依据是 GB/T 15834 里可机械判定的部分，判断类条文没实现。

它报了多半该改，它没报不代表写对了。各家出版社、期刊社的细则跟这里打架时，以对方投稿规范为准，用 `--rule` 关掉对应编号。

## 开发

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e . pytest ruff
pytest && ruff check .
```

新增规则：在 `src/zh_punct/rules.py` 的 `RULES` 里登记，写检查函数挂进 `CHECKS`，再补测试。**反例测试至少和正例一样多**，覆盖代码块、URL、纯英文行三种语境。

## 许可

MIT。
