---
name: cnvd-packager
description: >-
  Post-audit CNVD vulnerability submission packaging pipeline. Consumes findings
  from security-audit and mini-adjudication (or manual audit notes), aligns live
  target URLs and low-privilege test accounts, drives headed-browser (or stepped
  CLI) reproduction and key screenshot capture, renders a unified 3-section Word
  report (报告.docx) plus PoC.md/PoC.sh, enforces an Audio-First zero-overlay
  video standard (复现视频.mp4 with Chinese voiceover), and assembles clean
  per-vulnerability directories with 截图/. Use when the user asks to
  "打包CNVD", "生成CNVD报告", "准备CNVD提交包", "制作漏洞复现视频和Word报告", or
  "package findings for CNVD".
---

# CNVD Packager Pipeline

将代码审计（`security-audit`）与受理裁决（`mini-adjudication`）成果转化为**可直接提交的单洞标准化交付包**（产物规范对齐 `JFlow-精简版`：每洞独立目录含 `报告.docx`、`PoC.md`、`PoC.sh`、`复现视频.mp4`、`截图/`）。本技能定义**输入映射、四阶段流水线、3 段式报告版式、Audio-First 零-Overlay 视频规范与自动化验收门禁**。

---

## 一、 输入源与字段映射

优先读取 `mini-adjudication`（`adjudication-notes.md` 内嵌 JSON / `advisory` 草稿）与 `security-audit`（`findings.json` / `run-metadata.json`）的产物；若仅存在单一产物或手工审计笔记，则按可用字段降级提取，严禁脱离真实源码或实测结果编造内容。

| 目标要素 | 优先取自 `mini-adjudication` (`adjudication-notes.md` / `advisory`) | 回退 / 补充取自 `security-audit` (`findings.json` / `run-metadata.json`) |
| :--- | :--- | :--- |
| **产品 / 版本 / 源码地址** | `target.name`、`claims[].source_ref` | `run-metadata.json` -> `repo` / `target` / `source_ref` |
| **受影响组件与端点** | `claims[].assertions[].anchor` | `findings[].endpoint`、`findings[].trace[0]` |
| **漏洞标题与所需权限** | `claims[].subject`（`accept_after_rewrite` 取重写后标题）、`premise_kind` | `findings[].title`、`findings[].conditions` |
| **一、源码成因** | `claims[].assertions[]` (`anchor`, `statement`)、`acceptance.divergence_sides[]` | `findings[].root_cause`、`trace[]`、`evidence[]` |
| **二、复现步骤与截图** | `advisory` 草稿复现指引 | `findings[].execution` (`payloads`, `instructions`, `observed_result`) |
| **三、修复建议** | `advisory` 修复部分 | `findings[].remediation` (`strategy`, `code_changes[]`) |

---

## 二、 四阶段执行流水线

### Stage 1：筛选与目标对齐
1. **自动筛选可报漏洞**：
   - 若传入 `mini-adjudication` 裁决结果：仅保留 `accept` 与 `accept_after_rewrite`（优先包含 `target` 为 `cnvd` 或适用通用型/开源软件上报的条目）；自动剔除 `decline`、`does_not_hold`、`already_fixed` 与未决阻塞项（除非用户明确点名补充）。
   - 若仅传入 `security-audit` 结果：筛选 `verdict == "confirmed"`。
2. **排序与轨道选定**：
   - 按严重度降序（`critical` > `high` > `medium`）逐洞处理。
   - 为每个漏洞选定视频采集轨道（详见 [视频制作规范](references/video-production.md)）：
     - **`web` 轨道（默认优先）**：所有具备 Web / HTTP 入口的漏洞，优先用真实有头（headed）Chrome 窗口驱动录制（保留完整标签栏与 URL 地址栏、零 Overlay、含控制台界面上下文与负向对照）；
     - **`cli` 轨道（仅降级使用）**：仅当目标完全没有 HTTP/Web 入口时使用分步终端录制。
3. **一次性环境对齐**：开始复现前，一次性向用户确认缺失的运行环境要素（上下文或环境变量已提供则直接复用）：
   - 在线演示地址 / 本地部署服务地址（URL 与端口）；
   - 测试账号与权限视角（优先使用**未登录游客**或**低权限普通账号**；涉及跨用户越权或存储型 XSS 时，确认攻击者账号与受害者/管理员账号）；
   - 是否允许在测试环境/容器内进行文件落盘或结果核验。

### Stage 2：实景复现与单轮同源取证
按 `execution.instructions` / `payloads` 在真实运行环境（优先真实浏览器窗口，辅以接口验证）逐洞实测，并将高清 `.png` 截图保存至交付包的 `截图/` 目录：
1. **单轮同源约束（Single-Run Grounding）**：
   - 涉及可变服务端状态（如登录失败锁定计数、自增文件 ID、一次性验证码）时，验证与录制前必须重置状态或更换全新隔离标识（如新伪造 IP 段），保证实测结果准确（如失败计数从 `1` 开始）。
   - 同一漏洞的 **视频画面、`报告.docx` 内嵌截图、`截图/` 原图、`PoC.md`/`PoC.sh` 实测结果** 必须来自**同一轮干净运行**，禁止跨运行混用动态 Token、验证码或矛盾的失败次数。
   - 截图必须匹配步骤当前的真实鉴权视角（例如「未登录基线对照」步骤禁止贴一张已登录管理员的页面图），且 Web 场景截图须保留真实浏览器标签栏与 URL 地址栏。
2. **必采截图清单**：
   - **执行过程截图**：清晰展示在浏览器（带 URL 地址栏）或代理/终端中构造并发送 Payload 的画面；
   - **确认结果截图**：展示实害闭环的硬证据（如浏览器直出敏感文件内容、页面回显读取结果、跨账号刷新验证篡改、越权查询返回全量记录等）；
   - **对照 / 业务上下文截图**：负向对照画面（如去会话拒绝访问、错误条件返回 `RecCount:0`）或产品控制台对应的真实功能页。

> **合规与安全约束**：所有影响验证尽量使用新建测试数据/测试文件完成，不破坏无关存量业务数据；写入类 PoC 必须在验证后将测试行复位；不在测试过程中调用注销接口导致其他并行会话失效。

### Stage 3：3 段式 `报告.docx` + `PoC.md`/`PoC.sh` + 零-Overlay 视频制作

#### A. Word 报告（`报告.docx`）与 PoC 同步产物
严格按 [报告与 PoC 模板规范](references/report-template.md) 编写 `python-docx` 脚本生成 **`报告.docx`**，并同步输出 **`PoC.md`** 与 **`PoC.sh`**：

1. **`报告.docx` 版式与 3 段式结构**（A4，居中页脚 `第 X 页 / 共 Y 页`）：
   - **标题与 6 行元信息**：主标题（`18pt` `#1F3864`）+ 6 行 `MetaLine`（`源码地址`、`影响版本`、`开发厂商`、`受影响组件`、`受影响端点`、`所需权限`，末行带 `#D0D7DE` 分割线）。
   - **一、源码成因**：1~2 段精炼机理说明 + `• 文件路径:行号 — 说明` 要点列表 + 1×1 细边框（`#D0D7DE`）等宽源码块。
   - **二、复现步骤与关键截图**：按 `1. / 2. / 3.` 分步列出操作描述 → 1×1 细边框可复制命令/`curl`/载荷块 → `结果：` + 实测摘录 → 居中截图（宽 `14.00cm`）+ 居中灰字图注（`图 1  ...`）。
   - **三、修复建议**：可落地的代码/配置整改方案 + `涉及文件：` + 1×1 细边框修复参考代码块。
   - **客观红线**：`报告.docx` 正文**禁止出现** CVSS 评分表、独立 PoC 章节、`严重/高危/中危/低危/Critical/风险等级/定级/严重性` 等定级词，以及内部审计追踪编号（如 `F-01`）。
2. **同步交付 `PoC.md` 与 `PoC.sh`**：
   - `PoC.md`：包含 `# 标题`、4 行元信息、`## 复现步骤`（与 `报告.docx` 完全一致的命令与实测结果）、`## 修复建议`；
   - `PoC.sh`：可执行 Bash 脚本（`chmod +x`、`set -u`、`BASE="${BASE:-...}"`、分 `【步骤 1】...【清理】` 输出，写入类结尾自动复位），通过 `bash -n` 语法校验。

#### B. 复现视频制作（Audio-First + 零-Overlay 规范）
按 [视频制作规范](references/video-production.md) 执行，严禁仅靠纯黑终端一次性跑完 `PoC.sh` 截图定格：

1. **Audio-First 制作顺序（不可逆）**：
   - **先写独立分镜口播稿（`storyboard.json`）**：按「未认证/初始视角 → 触发执行 → 实害落地（展开/格式化关键内容）→ 业务入口对照 → 负向对照」拆成 3~6 步。每支视频**必须独立成篇**，**严禁**出现「第一条」「第 X 项」等批号；发送 TTS 前必须将生僻英文标识符/缩写（如 `ab-inner`、`extractvalue`、`MD5`、`JDBC`）转写为可读中文或加停顿提示。
   - **先合成音频并测时长**：使用清晰自然的中文配音（采样率 `>= 24 kHz`，推荐神经语音 `32 kHz`），测得每步音频精确时长后反驱画面停留：`hold >= audio_dur + 0.35s`。
   - **再分步录制与精确混音**：按音频节拍分步触发真实浏览器交互或分段命令；若使用窗口级异步录屏，采用首尾双色标定帧线性映射时间轴并裁掉标定段与空白过渡。
2. **画面与防作弊硬约束**：
   - **Web/HTTP 漏洞优先有头浏览器录屏**：完整保留浏览器标签栏 + URL 地址栏（`web` 轨道）；仅无任何 HTTP/Web 入口时允许分步终端（`cli` 轨道）。
   - **零 Overlay**：画面仅呈现目标系统浏览器窗口或终端本身，**严禁**烧录字幕条、遮罩框或角标；解说走独立音轨。
   - **禁止「瞬时跑完 + 长定格死图」**：视频帧率必须 **`>= 24 fps`（推荐 `30 fps`）**，严禁 `2 fps` 幻灯片式拼接，禁止脚本前几秒跑完后全程静止定格。
   - **独立清场防串帧**：每条录制前必须退出登录/清空会话/清屏，严禁第 `0.0s` 首帧残留上一条漏洞画面、纯色标定帧或 `about:blank`。
   - **同源一致**：封装为 H.264 + AAC（`abs(video_dur - audio_dur) <= 1.0s`），演示的端点、参数、账号、响应与 `报告.docx` / `PoC.md` / `PoC.sh` 完全一致。

### Stage 4：提交包归档与确定性终审门禁
1. **标准交付目录结构**（每个独立漏洞一个干净目录，命名不带内部审计编号；过程文件 `_work/`、`*.mov`、`*.mp3`、`*.wav`、`.DS_Store` 不得残留）：
   ```text
   {简短漏洞目录}/
     ├── 报告.docx
     ├── PoC.md
     ├── PoC.sh
     ├── 复现视频.mp4        # 仅概率性线程竞态等无法稳定录像时，改放 实测响应.txt 并在报告写明原因
     └── 截图/               # 与 报告.docx 内嵌图片 SHA-256 逐一对应的 .png 原图
   ```
   *(注：默认不强制在根目录生成汇总文件；仅当用户明确要求汇总索引时，再额外生成 `提交清单.csv` 等。)*
2. **交付前自动化门禁（必跑且必须返回 0）**：
   运行内置校验脚本核验目录结构、`报告.docx` 3 段式章节与禁词、`word/media/` 与 `截图/` 1:1 哈希一致、`PoC.md`/`PoC.sh` 规范与可执行位、视频流/动态分布/零-Overlay/地址栏以及跨包首帧串帧：
   ```bash
   python3 "<cnvd-packager技能目录>/scripts/verify_cnvd_package.py" "<交付目录>" --track <web|cli|auto>
   # 批量多个漏洞包时追加跨视频串帧校验：
   python3 "<cnvd-packager技能目录>/scripts/verify_cnvd_package.py" --batch "<交付根目录>"
   ```
3. **人工核验清单（与脚本互为补充）**：
   - [ ] `verify_cnvd_package.py` 全项 `[PASS]`（退出码 `0`）；
   - [ ] 视频内口播无英文生硬吞词误读，实测动态结果与 `报告.docx`、`PoC.md`、`PoC.sh` 完全对齐；
   - [ ] 涉及多漏洞时已按严重度顺序全部完成打包。
