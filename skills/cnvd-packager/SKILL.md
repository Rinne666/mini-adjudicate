---
name: cnvd-packager
description: >-
  Post-audit CNVD vulnerability submission packaging pipeline. Consumes findings
  from security-audit and mini-adjudication (or manual audit notes), aligns live
  target URLs and low-privilege test accounts, drives live reproduction and key
  screenshot capture, renders a unified 5-section Word (.docx) report, enforces a
  declarative video acceptance standard (.mp4 with Chinese voiceover), and
  assembles a standardized CNVD submission directory. Use when the user asks to
  "打包CNVD", "生成CNVD报告", "准备CNVD提交包", "制作漏洞复现视频和Word报告", or
  "package findings for CNVD".
---

# CNVD Packager Pipeline

将代码审计（`security-audit`）与受理裁决（`mini-adjudication`）成果转化为**可直接提交 CNVD 的标准化漏洞交付包**。本技能只定义**输入映射、流水线阶段、统一 5 段式文档排版、交付包结构与视频验收契约**；具体浏览器操作、终端执行、录屏/合成与 TTS 配音方式由执行模型根据本机可用工具或插件自主选择。

---

## 一、 输入源与字段映射

优先读取 `mini-adjudication`（`adjudication-notes.md` 内嵌 JSON / `advisory` 草稿）与 `security-audit`（`findings.json` / `run-metadata.json`）的产物；若仅存在单一产物或手工审计笔记，则按可用字段降级提取，严禁脱离真实源码或实测结果编造内容。

| 目标要素 | 优先取自 `mini-adjudication` (`adjudication-notes.md` / `advisory`) | 回退 / 补充取自 `security-audit` (`findings.json` / `run-metadata.json`) |
| :--- | :--- | :--- |
| **产品名称** | `target.name` | `run-metadata.json` -> `repo` / `target` |
| **受影响版本 / 源码版本** | `claims[].source_ref`、`acceptance.oss_verification.commit_timeline.released_in` | `run-metadata.json` -> `source_ref` |
| **漏洞标题与定性** | `claims[].subject`（`accept_after_rewrite` 取重写后标题） | `findings[].title`、`severity.overall_severity` |
| **概述与信任边界** | `claims[].acceptance.boundary_state`、`premise_kind`、`rationale` | `findings[].description`、`intended_behavior`、`conditions` |
| **源码定位与逻辑断层** | `claims[].assertions[]` (`anchor`, `statement`)、`acceptance.divergence_sides[]` | `findings[].root_cause`、`trace[]` (`entrypoint` → `propagation` → `sink`)、`evidence[]` |
| **复现载荷与步骤** | `advisory` 草稿复现指引 | `findings[].execution` (`attacker_perspective`, `payloads`, `instructions`, `observed_result`) |
| **修复建议** | `advisory` 修复部分 | `findings[].remediation` (`strategy`, `code_changes[]`) |

---

## 二、 四阶段执行流水线

### Stage 1：筛选与目标对齐
1. **自动筛选可报漏洞**：
   - 若传入 `mini-adjudication` 裁决结果：仅保留 `accept` 与 `accept_after_rewrite`（优先包含 `target` 为 `cnvd` 或适用通用型/开源软件上报的条目）；自动剔除 `decline`、`does_not_hold`、`already_fixed` 与未决阻塞项（除非用户明确点名补充）。
   - 若仅传入 `security-audit` 结果：筛选 `verdict == "confirmed"`。
2. **排序**：按严重度降序（`critical` > `high` > `medium`）逐洞处理。
3. **一次性环境对齐**：开始复现前，一次性向用户确认缺失的运行环境要素（上下文或环境变量已提供则直接复用）：
   - 在线演示地址 / 本地部署服务地址（URL 与端口）；
   - 测试账号与权限视角（优先使用**未登录游客**或**低权限普通账号**；涉及跨用户越权或存储型 XSS 时，确认攻击者账号与受害者/管理员账号）；
   - 是否允许在测试环境/容器内进行文件落盘或结果核验。

### Stage 2：实景复现与关键截图采集
按 `execution.instructions` / `payloads` 在真实运行环境（Web UI、API、CLI 或本地容器）逐洞验证，并将高清 `.png` 截图保存至交付包的 `screenshots/` 目录：
1. **执行过程截图（必采）**：清晰展示在浏览器、代理工具或终端中构造并发送 Payload / 请求的画面（需能看清接口路径、关键参数、当前低权限/无鉴权状态及响应状态码）。
2. **确认结果截图（必采）**：展示实害闭环的硬证据，按漏洞类型选择最直接的实证画面：
   - **越权 / 未授权**：切换受害者账号刷新页面看到文件被改名/删除，或未带合法凭证直接拿到真实业务数据；
   - **存储型 XSS**：受害者触发页面 + 外带接收端（如 webhook）回传记录 + 解码明文凭据或无痕窗口接管后台界面；
   - **文件上传 / 路径穿越 / 文件读取下载**：容器或服务端内 `find` / `cat` 落盘核验，或打开下载后的敏感文件明文（如 `/etc/passwd`、`.env`、配置文件、数据库文件）。
3. **辅助截图（可选）**：系统首页版本标识、正常拦截基线画面、源码/配置关键行截图。

> **合规与安全约束**：所有影响验证尽量使用新建测试数据/测试文件完成，不破坏无关存量业务数据；不在测试过程中调用注销接口导致已有测试会话失效。

### Stage 3：统一 5 段式 `.docx` 生成 + 声明式视频制作

#### A. Word 报告生成（`.docx`）
由执行模型现场编写一次性 `python-docx` 脚本，将映射后的结构化事实与 `screenshots/*.png` 渲染为统一版式的 `.docx` 文件（**不包含 CVSS 评分表和独立 PoC 章节**）：

1. **排版样式基准**：
   - 正文字体：中文宋体/微软雅黑、英文/代码 Consolas 或等宽字体；一级标题加粗突出，段落间距清晰，无多余空行。
   - **代码块**：使用浅灰底纹单格表格或等宽段落框承载源码片段、Raw HTTP 请求包及 `curl`/Python 命令，禁止与正文混排。
   - **关键信息表格**：统一带细边框与浅色表头，列宽自适应。
   - **内嵌截图**：关键步骤下方直接嵌入高清截图，居中排版并附统一编号图注（如 `图 1：...`）。

2. **统一 5 段式正文结构**：
   - **一、漏洞概述**
     - 顶部附简明基础信息表：`漏洞名称`、`漏洞类型`、`影响产品与版本`、`官网/源码地址`、`利用前提`。
     - 用 1~2 段精炼说明：漏洞入口位置、违背了什么安全边界、无需登录或仅需普通权限即可达成什么结果（禁止空泛科普）。
   - **二、源码定位**
     - 精确给出 `文件路径:行号` 及核心源码片段（标注 `Source` / `Propagation` / `Sink` 或权限校验缺失点）。
     - 若属同类接口校验不一致或过滤绕过，附 1 张简明对比表直观展示差异。
   - **三、图文复现**
     - 简述复现环境地址与测试账号权限表。
     - 按 `1. / 2. / 3.` 分步给出可直接复制复现的**完整请求包 / `curl` / Fetch / 操作步骤**与核心响应摘录，并在对应步骤后**内嵌关键截图**，确保审阅者顺着图文即可完整重放。
   - **四、危害分析**
     - 逐条列出基于**已证实权限面**的真实危害，结合脱敏后的实测证据举例说明（例如：已提取的具体配置键名/凭据类型、已越权操作的对象、已接管的会话角色），不编造未验证的影响。
   - **五、修复建议**
     - 给出精准落地的代码/配置整改方案（附修复前/后核心代码对比）及必要的临时缓解措施。

#### B. 复现视频制作与验收标准（声明式契约）
**不指定具体录屏软件、终端录屏方案或配音引擎**，由执行模型根据当前环境自主选择本地工具/插件（如 Playwright 录屏、桌面录屏、FFmpeg 合成、TTS 配音等）完成制作，但成片必须满足以下全部验收门禁：

1. **必展画面要求**：
   - **攻击执行过程画面**：清晰呈现如何从指定权限视角发起请求或触发载荷（URL/接口、关键参数、请求体或命令清晰可辨）。
   - **确认成功结果画面**：清晰呈现漏洞生效后的真实结果（如返回敏感数据、打开下载文件明文、跨账号验证篡改/触发、回传解码或后台接管画面）。
   - *(可选加分项，不作阻塞)*：开场交代目标版本与测试权限、演示正常拦截基线对照、结尾 10 秒口播总结。
2. **音画与一致性要求**：
   - 格式为可正常播放的 `复现视频.mp4`（推荐 H.264 视频编码 + AAC 音频编码，文字清晰无严重模糊或裁切）。
   - **全程配有清晰中文语音旁白**，实时解释“当前操作”与“返回结果”。
   - 视频中所演示的**接口路径、参数值、测试账号、Payload 必须与 `.docx` 报告完全一致**。
   - *(不作硬性文件大小上限与基线对照阻塞要求)*。

### Stage 4：提交包归档与终审门禁
1. **标准交付目录结构**：
   每个独立漏洞生成如下固定目录（如同一项目有多个漏洞，则各自独立成包）：
   ```text
   {产品名}_{漏洞类型}_{简短标识}/
     ├── {产品名}_{漏洞类型}漏洞报告.docx
     ├── 复现视频.mp4
     ├── poc/                  # 仅当存在独立可运行的 poc.py 或恶意样本（如 .oexe/.svg）时创建；无则省略
     └── screenshots/          # 保留嵌入 Word 的高清原图备用，不要求打入最终上传压缩包
   ```
2. **交付前自检门禁（全部通过才可宣布完成）**：
   - [ ] 目录命名与内部文件名符合规范，无过程垃圾文件散落其中；
   - [ ] `.docx` 包含完整 5 个章节，无 CVSS 表与多余空章，源码行号准确，关键截图已成功嵌入且可见；
   - [ ] 存在独立 PoC 脚本或样本时已归入 `poc/` 且路径/参数与报告一致；
   - [ ] `复现视频.mp4` 可正常解码播放，音视频轨完整（含中文语音旁白），展示内容与报告完全对齐；
   - [ ] 涉及多漏洞时已按严重度顺序全部完成打包。
