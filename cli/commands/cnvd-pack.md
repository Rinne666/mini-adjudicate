---
description: 将审计与裁决确认的漏洞，自动化完成实景复现截图、3 段式 Word 报告（报告.docx）、PoC.md/PoC.sh、中文旁白复现视频 (.mp4) 与独立单洞目录归档
argument-hint: "[已有 adjudication-notes.md、findings.json 或目标测试环境信息]"
---

<!-- mini-adjudication managed command v1 -->

# /cnvd-pack — CNVD 单洞交付包流水线

加载并严格按 `cnvd-packager` 技能执行（技能根目录：
`{{SKILL_DIR}}`，先读其 `SKILL.md` 及 `references/report-template.md`、`references/video-production.md`）。

> 本指令区别于 `/adjudicate`（只做漏洞技术有效性裁定与受理判断，不碰活目标、不出 Word/视频）：`/cnvd-pack` 负责**裁决确认之后的实景取证、3 段式 `报告.docx` + `PoC.md`/`PoC.sh` 生成、Audio-First 零-Overlay `复现视频.mp4` 制作与单洞提交包归档**。

## 第 0 步 — 技能完整性检查

命令用于 {{SHELL_NAME}}。Node 启动器自动选择 Python 3.10 或更新版本。

```text
{{CLI_COMMAND}} run check_skill_loaded.py
```

非零退出 = 包内文件与 manifest 不一致，先检查并修复安装，不要继续。

## 第 1 步 — 上游产物与目标环境收单（Intake Gate）

1. **读取上游结果**：
   - `$ARGUMENTS` 指定了 `adjudication-notes.md`、`findings.json`、审计/裁决目录 → 直接读取；
   - 仅给出单个漏洞描述或手工笔记 → 按 `cnvd-packager` 字段映射降级提取；
   - 没有任何漏洞输入 → **停止**，提示用户先运行 `/adjudicate` 或 `security-audit` 确认漏洞后再执行 `/cnvd-pack`。
2. **筛选可打包条目**：
   - 有 `mini-adjudication` 裁决结果时：仅保留 `accept` 与 `accept_after_rewrite`；剔除 `decline`、`does_not_hold`、`already_fixed` 与未决项；
   - 仅有 `security-audit` 结果时：筛选 `verdict == "confirmed"`；
   - 按严重度降序（`critical` → `high` → `medium`）排队。
3. **一次性环境对齐**：在执行实景验证前，向用户一次性确认各目标的演示/部署地址、低权限测试账号（或未登录态）及验证边界。

## 第 2 步 — 四阶段打包执行（对齐 `JFlow-精简版` 标准）

1. **Stage 2 — 单轮同源实景取证与关键截图**：验证前重置可变状态，Web/HTTP 漏洞优先用真实有头 Chrome（保留标签栏与 URL 地址栏）采集高清 `.png` 截图至 `截图/`。截图与响应摘录必须与视频来自同一轮验证，截图鉴权视角须与步骤说明一致。
2. **Stage 3A — 3 段式 `报告.docx` + `PoC.md` + `PoC.sh`**：
   - 按 `references/report-template.md` 编写临时 `python-docx` 脚本生成 `报告.docx`（标题 + 6 行元信息 + `一、源码成因 → 二、复现步骤与关键截图 → 三、修复建议`），**禁用** CVSS 表、独立 PoC 章节及定级词（严重/高危/中危/低危/风险等级），内嵌与 `截图/` SHA-256 一一对应的原图；
   - 同步产出 `PoC.md` 与可执行 `PoC.sh`（`chmod +x`，写入类测试末尾自动复位）。
3. **Stage 3B — Audio-First 零-Overlay 视频制作**：
   - 先写独立分镜口播稿（**严禁**「第一条/第X项」批号，英文/缩写先转写），合成清晰中文语音（采样率 `>= 24 kHz`）；
   - 按语音时长反驱画面停留（`hold >= audio_dur + 0.35s`）：Web/HTTP 漏洞优先有头浏览器窗口级录制（含标签栏、URL 地址栏、控制台 UI 对照、负向对照、零字幕/角标 Overlay）；纯无 Web 入口时才退回分步终端录屏；
   - 视频帧率 **`>= 24 fps`**（推荐 `30 fps`），录前清屏/重置会话防止首帧串帧，严禁前几秒跑完后全程静态定格，封装为 H.264 + AAC（`abs(video_dur - audio_dur) <= 1.0s`）。
4. **Stage 4 — 单洞独立归档**（命名不带内部审计编号，默认不生成顶层汇总文件，无过程中间文件残留）：
   ```text
   {简短漏洞目录}/
     ├── 报告.docx
     ├── PoC.md
     ├── PoC.sh
     ├── 复现视频.mp4
     └── 截图/
   ```

## 第 3 步 — 交付前自动化硬门禁

必须运行校验脚本并通过全部门禁（退出码 `0`）后才可宣布完成；任何对外平台实际提交动作仍由用户自行操作：

```text
python3 "{{SKILL_DIR}}/scripts/verify_cnvd_package.py" "<交付目录>"
python3 "{{SKILL_DIR}}/scripts/verify_cnvd_package.py" --batch "<交付根目录>"
```

补充人工复核：口播无生硬英文误读、动态实测值（验证码/计数/Token/fileId）与 `报告.docx` / `PoC.md` / `PoC.sh` 完全一致。
