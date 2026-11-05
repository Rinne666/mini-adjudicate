---
description: 审计出漏洞后，裁定哪些能报、报给谁（maintainer/CVE/CNVD/SRC），产出可申报总结
argument-hint: "[已有 findings.json、审计运行目录或报告路径]"
---

<!-- mini-adjudication managed command v1 -->

# /adjudicate — 审计后受理裁定

加载并严格按 `mini-adjudication` 技能执行（技能根目录：
`{{SKILL_DIR}}`，先读其 SKILL.md）。

## 第 0 步 — 技能新鲜度检查

命令用于 {{SHELL_NAME}}。Node 启动器自动选择 Python 3.10 或更新版本。
用户提供的 notes、ledger、输出路径应按当前 shell 正确引用。

```text
{{CLI_COMMAND}} run check_skill_loaded.py
```

非零退出 = 技能文件与 manifest 不一致，先检查并修复安装，不要继续。
不要仅刷新哈希以掩盖不一致；该检查验证磁盘文件，不能检查模型上下文。

## 第 1 步 — 收单（Intake Gate）

- `$ARGUMENTS` 给了审计产物路径（findings.json / run 目录 / 报告）→ 用它。
- 没给 → 从当前项目及会话已明确指定的审计目录定位现有产物；多个目标
  无法确定时再询问。不要按全局最近修改时间混用另一个项目的 finding。
- 找不到任何审计产物 → **停止**，告诉用户本技能只在审计出漏洞后触发，
  先运行 security-audit 审计。绝不自己去挖漏洞。

## 第 2 步 — 三阶段裁定（按 SKILL.md 执行）

每一轮都跑驱动器并照它打印的那一条指令做，做完重跑：

```text
{{CLI_COMMAND}} run validate_adjudication.py <adjudication-notes.md> --evidence-ledger <evidence.jsonl> --next
```

阶段门禁：`--phase adjudicate`（拆断言、断言台账、推导 validity）→
`--phase assess`（+三个受理问题、OSS 核验）→ `--phase deliver`（+提交块、
工作队列闭合、渠道）。上一阶段门禁不绿，下一阶段的工作不算数。

1. **Adjudicate**：把每条 finding 登记为 claim，拆断言、做反证尝试，
   用 `runtime/evidence_log.py` 记录证据，产出 validity verdict。
2. **Assess**：对 holds 的 claim 回答三个受理问题；目标是开源项目时
   **必须**完成 OSS 核验（security 政策、commit 时间线、历史相似漏洞、
   开发者受理偏好），对照 `references/submission-targets.md` 的
   SRC/CNA/CNVD/众测平台受理标准。
3. **Deliver**：产出 `templates/submission-summary.md` 可申报总结——
   **按危害等级降序排列的漏洞表格**（critical→high→medium→low，
   每行含：危害等级/核心业务/开发者是否已知/是否需特殊配置/跨安全
   边界/目标平台，目标平台有且仅有一个 primary），报告草稿用
   `templates/advisory.md`。

前提无法确认时保留 `premise.kind = unknown` 和 `acceptability = pending`，
按运行时要求补齐阻塞证据与后续工作，交付阻塞说明，不强行生成报告。
同一任务中所有可报告 claim 的草稿一次完成；等待前一份回复仅是外部投递
顺序的建议，不能阻塞其余已授权草稿的生成。

工作文件写到审计 run 目录旁的 `adjudication/` 子目录（adjudication-notes.md
+ evidence.jsonl + 产物），不要写进技能安装目录。

## 第 3 步 — 交付前硬门禁

```text
{{CLI_COMMAND}} run validate_adjudication.py <adjudication-notes.md> --evidence-ledger <evidence.jsonl> --phase deliver
```

非零退出 → 修复后重跑，不得带病交付。CVSS 向量必须过
`runtime/cvss31.py` 交叉校验。安装器不会注册或验证宿主 hooks；未单独
配置并测试 hooks 时，必须手工运行上述门禁。可选 Stop hook 有有界重试
行为，不能把它视为不可绕过的交付保证。

## 红线

- 本命令/技能只裁定、不提交；任何对外提交动作需用户明确确认。
- 不成立的 claim 写 refutation，不写报告；`needs_more_evidence` 是正式
  结论，不许因为"代码看起来有问题"升级为 holds。
- 交付物最后附：按危害等级降序的可申报漏洞表格（含核心业务/开发者
  是否已知/特殊配置/跨边界/目标平台）+ 每条一个 primary 目标 + 阻塞事实。
