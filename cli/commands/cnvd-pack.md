---
description: 将审计与裁决确认的漏洞，自动化完成实景复现截图、统一 5 段式 Word (.docx) 报告、中文旁白复现视频 (.mp4) 与 CNVD 提交包归档
argument-hint: "[已有 adjudication-notes.md、findings.json 或目标测试环境信息]"
---

<!-- mini-adjudication managed command v1 -->

# /cnvd-pack — CNVD 漏洞提交包流水线

加载并严格按 `cnvd-packager` 技能执行（技能根目录：
`{{SKILL_DIR}}`，先读其 `SKILL.md`）。

> 本指令区别于 `/adjudicate`（只做漏洞技术有效性裁定与受理判断，不碰活目标、不出 Word/视频）：`/cnvd-pack` 负责**裁决确认之后的实景取证、统一 5 段式 `.docx` 报告生成、中文旁白复现视频验收与标准化 CNVD 提交包归档**。

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

## 第 2 步 — 四阶段打包执行（按 `cnvd-packager/SKILL.md`）

1. **Stage 2 — 实景复现与关键截图**：按已确认载荷与指令在目标环境验证，采集并保存至少包含**「攻击执行过程」**与**「实害闭环确认结果」**的高清 `.png` 截图至 `screenshots/`。
2. **Stage 3A — 统一 5 段式 `.docx` 报告**：现场编写临时 `python-docx` 脚本生成 `{产品名}_{漏洞类型}漏洞报告.docx`，严格包含 `一、漏洞概述 → 二、源码定位 → 三、图文复现 → 四、危害分析 → 五、修复建议`（不写 CVSS 评分表与独立 PoC 章节），内嵌关键截图与完整图注。
3. **Stage 3B — 声明式视频制作与验收**：自主选用本机可用工具或插件录制/合成 `复现视频.mp4`。成片必须可正常播放、包含**执行过程画面 + 确认成功结果画面 + 全程清晰中文语音旁白**，且演示的接口、参数、账号与 `.docx` 完全一致。
4. **Stage 4 — 提交包归档**：按如下目录组织交付物，独立 PoC 或样本放入 `poc/`（无则省略）：
   ```text
   {产品名}_{漏洞类型}_{简短标识}/
     ├── {产品名}_{漏洞类型}漏洞报告.docx
     ├── 复现视频.mp4
     ├── poc/          (可选)
     └── screenshots/
   ```

## 第 3 步 — 交付前门禁

逐项核验：目录命名规范、5 段式结构完整、关键截图已嵌入 Word、视频音画与报告参数一致、存在独立 PoC 时已归档 `poc/`。未全部通过前禁止宣布完成；任何对外平台实际提交动作仍由用户自行操作。
