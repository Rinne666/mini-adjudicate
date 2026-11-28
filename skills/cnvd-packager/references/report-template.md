# 单洞交付文档与报告排版规范（对齐 `JFlow-精简版` 标准）

每条确认可报的漏洞各自独立成目录，目录内只保留最终交付产物，不残留过程脚本或媒体中间文件：

```text
{简短漏洞目录名}/            # 如 04-流程设计器导出接口未鉴权、WF_MyCC项目字段UPDATE注入（不加 _F01 等内部审计编号）
├── 报告.docx                # 3 段式单洞分析报告（A4，内嵌全部关键截图）
├── PoC.md                   # PoC 纯文本说明（与报告步骤一一对应）
├── PoC.sh                   # 可独立执行的 Bash 验证脚本（含可执行位 +x，写入类末尾自动复位）
├── 复现视频.mp4              # Zero-Overlay Audio-First 实景录屏
└── 截图/                    # 与 报告.docx 内嵌图片 SHA-256 一一对应的 .png 原图
```

> 仅当漏洞触发依赖服务端瞬时状态（如线程复用竞态）导致录屏无法稳定复现时，方可以 `实测响应.txt` + 明确说明替代 `复现视频.mp4`。

---

## 一、`报告.docx` 严格 3 段式结构与排版规范

### 1. 页面与基础样式
- **纸张与页边距**：A4（`21.00cm × 29.70cm`），左/右 `2.50cm`，上/下 `2.26cm`。
- **页眉与页脚**：无页眉；居中页脚 `第 {PAGE} 页 / 共 {NUMPAGES} 页`（字体 `Arial` / `PingFang SC`，`8.5pt` `#595959`）。
- **字体**：西文正文 `Arial`、中文 `PingFang SC`（Windows/Linux 兼容映射时保留 `Arial` + 中文字体 fallback）、代码与路径 `Menlo`（等宽）。
- **配色**：主标题与 H1 `#1F3864`、H2 与路径/链接 `#2F5496`、正文 `#24292F`、图注 `#595959`、边框 `#D0D7DE`。

### 2. 文档内容顺序与禁词红线
1. **顶部标题与 6 行元信息**（无封面表）：
   - `Title`（`18pt` 加粗 `#1F3864`）：`{产品名} {接口/模块} {漏洞类型}漏洞`
   - 紧接 6 行 `MetaLine`（`10pt` 加粗标签 `#24292F` + 值；URL 与端点用 `Menlo 9pt #2F5496`；第 6 行底部加 `#D0D7DE` 细分割线）：
     - `源码地址：`
     - `影响版本：`
     - `开发厂商：`
     - `受影响组件：`
     - `受影响端点：`
     - `所需权限：`
2. **一级章节 1：`一、源码成因`**（H1 `14pt` 加粗 `#1F3864`，带 `#2F5496` 底部细线）
   - 1~2 段机制成因正文（`10.5pt` `#24292F`）；
   - `• {文件路径}:{行号} — {说明}` 定位要点列表（`•` 与路径为 `#2F5496`，路径用 `Menlo 9pt`）；
   - 1×1 单格细边框（`#D0D7DE`，无底纹填充）等宽源码块（`Menlo 8.5pt #24292F`）。
3. **一级章节 2：`二、复现步骤与关键截图`**
   - 按 `1. ...`、`2. ...`、`3. ...` 编号展开 `Heading2`（`11.5pt` 加粗 `#2F5496`）；
   - 每步依次包含：**文字说明** → **1×1 细边框命令/载荷代码块** → **`结果：`（粗体）+ 实测响应摘要** → **居中高清截图（宽 `14.00cm`）** + **居中图注 `图 N  {说明}`（`9pt #595959`）**。
   - 若含权限边界对比或真假对照，一并在对应步骤后附图展示。
4. **一级章节 3：`三、修复建议`**
   - 精准可落地的代码/配置整改方案说明；
   - **`涉及文件：`**（粗体标签 + `Menlo 9.5pt #2F5496` 文件路径）；
   - 1×1 细边框修复后参考代码块。

> **客观表述红线**：`报告.docx` 正文只写客观技术事实，**不得出现** CVSS 评分表、独立 `PoC` 章节标题、`严重`/`高危`/`中危`/`低危`/`Critical`/`风险等级`/`定级`/`严重性` 等评级词，也不得出现内部审计追踪编号（如 `F-01`、`FINDING-09`、`JFLOW-`）。

---

## 二、`python-docx` 参考实现骨架

生成 `报告.docx` 时可直接复用如下样式与辅助函数，确保字号、边框、页脚与间距精确一致：

```python
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

NAVY = RGBColor(0x1F, 0x38, 0x64)
BLUE = RGBColor(0x2F, 0x54, 0x96)
DARK = RGBColor(0x24, 0x29, 0x2F)
GRAY = RGBColor(0x59, 0x59, 0x59)

def init_doc():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin, sec.right_margin = Cm(2.5), Cm(2.5)
    sec.top_margin, sec.bottom_margin = Cm(2.26), Cm(2.26)
    # 居中页脚：第 PAGE 页 / 共 NUMPAGES 页
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for kind, val in [("t", "第 "), ("fld", "PAGE"), ("t", " 页 / 共 "), ("fld", "NUMPAGES"), ("t", " 页")]:
        r = fp.add_run()
        set_run_font(r, size=8.5, color=GRAY)
        if kind == "t":
            r.text = val
        else:
            r._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>'))
            r._r.append(parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> {val} </w:instrText>'))
            r._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="separate"/>'))
            r._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>'))
    return doc

def set_run_font(run, ascii_font="Arial", ea_font="PingFang SC", size=10.5, bold=False, color=DARK):
    run.font.name = ascii_font
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), ascii_font)
    rFonts.set(qn("w:hAnsi"), ascii_font)
    rFonts.set(qn("w:eastAsia"), ea_font)
    rFonts.set(qn("w:cs"), "Arial")
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color

def add_code_box(doc, code_text):
    tbl = doc.add_table(rows=1, cols=1)
    tblPr = tbl._tbl.tblPr
    tblPr.append(parse_xml(
        f'<w:tblW {nsdecls("w")} w:w="9070" w:type="dxa"/>'
    ))
    tblPr.append(parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '<w:top w:val="single" w:color="D0D7DE" w:sz="4"/>'
        '<w:left w:val="single" w:color="D0D7DE" w:sz="4"/>'
        '<w:bottom w:val="single" w:color="D0D7DE" w:sz="4"/>'
        '<w:right w:val="single" w:color="D0D7DE" w:sz="4"/>'
        '<w:insideH w:val="none" w:color="auto" w:sz="0"/>'
        '<w:insideV w:val="none" w:color="auto" w:sz="0"/>'
        '</w:tblBorders>'
    ))
    tblPr.append(parse_xml(
        f'<w:tblCellMar {nsdecls("w")}>'
        '<w:top w:w="90" w:type="dxa"/><w:left w:w="140" w:type="dxa"/>'
        '<w:bottom w:w="90" w:type="dxa"/><w:right w:w="120" w:type="dxa"/>'
        '</w:tblCellMar>'
    ))
    cell = tbl.cell(0, 0)
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:tcW {nsdecls("w")} w:w="9070" w:type="dxa"/>'))
    lines = code_text.rstrip("\n").split("\n")
    for idx, line in enumerate(lines):
        p = cell.paragraphs[0] if idx == 0 else cell.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(line if line else " ")
        set_run_font(r, ascii_font="Menlo", size=8.5, color=DARK)
```

---

## 三、`PoC.md` 与 `PoC.sh` 标准模板

### `PoC.md` 结构
```markdown
# {产品名} {接口/模块} {漏洞类型}漏洞

- **源码地址**：<repo_url>
- **影响版本**：<version_and_commit>
- **受影响端点**：`<METHOD /path>`
- **所需权限**：<无需登录 / 任意已认证用户会话>

## 复现步骤

### 1. <步骤一标题>
<简要说明>
```bash
<可复现命令>
```
**结果**：<实测观察结果>

### 2. <步骤二标题>
...

## 修复建议
<整改说明>
```java
<修复后核心代码>
```
```

### `PoC.sh` 结构
```bash
#!/usr/bin/env bash
# ==============================================================================
# PoC：<漏洞简述>
# 目标：http://localhost:8009
# 前提：<所需权限>
# 用法：bash PoC.sh            （可用 BASE=http://host:port 指定其它目标）
# ==============================================================================
set -u
BASE="${BASE:-http://localhost:8009}"
# 临时文件用 mktemp + trap EXIT 自动清理
# 按 【步骤 1】、【步骤 2】...、【负向对照】、【清理】 分步打印验证结果
```
- 必须具备可执行权限（`chmod +x PoC.sh`）且通过 `bash -n PoC.sh`。
- 写入/修改类 PoC 必须在末尾恢复被测试数据（`【清理】`）。
