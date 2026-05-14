---
name: kb
description: 知识库管理规则；用于初始化、同步、审计与上下文读取，确保知识库与代码一致。
---

# 知识库管理（KB）

## 知识库结构

```text
helloagents/
├── CHANGELOG.md
├── CHANGELOG_{YYYY}.md（可选：大型项目按年分片）
├── project.md
├── wiki/
│   ├── overview.md
│   ├── arch.md
│   ├── api.md
│   ├── data.md
│   ├── memories/
│   │   ├── index.md
│   │   └── <module>/<id>.md
│   └── modules/<module>.md
├── plan/YYYYMMDDHHMM_<feature>/
│   ├── why.md
│   ├── how.md
│   └── task.md
└── history/
    ├── index.md
    └── YYYY-MM/YYYYMMDDHHMM_<feature>/
```

## 核心原则

1. 代码是执行事实真相源。
2. 文档必须反映代码真实状态。
3. 只做最小必要更新，避免无关重写。
4. `wiki/modules/` 优先做“索引型文档”，避免复制大段业务细节（详情沉淀在方案包与记忆体）。

## 可选开关：`KB_CREATE_MODE`

> 用途：控制“知识库结构”是否自动创建/补齐，避免在你只想改代码时产生过多文档副作用。

- `0=OFF`：不自动创建/重建知识库结构（仅在用户显式 `~init/~upgrade` 或明确同意时执行）
- `1=ON_DEMAND`（默认）：知识库缺失时只提示 `~init`，不自动创建
- `2=ON_DEMAND_AUTO_FOR_CODING`：在编码/交付类任务中，知识库缺失时允许自动创建
- `3=ALWAYS`：尽量保持知识库结构完整（缺失则创建/补齐）

说明：
- 方案包（`helloagents/plan/`）不受 `KB_CREATE_MODE` 影响：它是交付流程的核心产物。
- 若用户明确要求“不写任何文档/不创建 helloagents/”：必须先说明“知识库同步为交付必做项”；仅当用户二次确认仍要求跳过时才允许跳过，并在最终输出中标注风险。

## 上下文获取策略

1. 先读知识库核心文档（project/overview/arch）。
2. 按模块阅读 `wiki/modules/<module>.md` 定位入口与真相源。
3. 需要“近期变更与回归证据”时优先查 `wiki/memories/index.md` 与对应记忆体文档。
4. 信息不足再扫描代码库补齐。
5. 输出“来源说明”，区分文档结论与代码结论。

补充：知识库的“创建/读取/同步”统一约定见：`references/services/knowledge.md`。

## 同步触发规则

- 代码改动后必须同步知识库。
- API变更更新 `wiki/api.md`。
- 数据模型变更更新 `wiki/data.md`。
- 架构/模块边界变更更新 `wiki/arch.md` 与 `wiki/overview.md`。
- 模块行为变更更新 `wiki/modules/<module>.md`。
- 可追溯回归：涉及关键业务/跨端契约的变更，推荐补充 `wiki/memories/<module>/` 记忆体，并在 `wiki/memories/index.md` 登记（便于检索与回归）。

## 质量门禁（建议）

- `wiki/overview.md` 的“快速链接”建议至少包含：`project/arch/api/data`、`memories/index.md`、`plan/README.md`、`history/index.md`、`CHANGELOG.md`。
- `wiki/modules/` 文档以“入口定位 + 索引链接”为主：单页建议 **≤200 行**；超出则拆分主题页并在模块页保留索引入口。
- `wiki/memories/index.md`：按条登记可追溯证据入口（脚本/接口请求/关键页面路径），避免只有结论没有复现与回归方式。

## 命令

- `~init`：初始化或重建。
- `~upgrade`：模板与结构升级。
- `~validate`：结构完整性与链接一致性检查。

## 脚本与降级（推荐）

> 脚本调用规范、ExecutionReport 与降级接手约定：见 `references/rules/tools.md`。
> 无脚本环境（`SCRIPTS_ENABLED=false`）的手动 init/upgrade/validate：见 `references/rules/noscript.md#9-手动知识库-initupgradevalidate`。

- `~init`（纯文件操作优先脚本）：`scripts/upgradewiki.py --init`（必要时先 `--backup`）。
- `~upgrade`（纯文件操作优先脚本）：`scripts/upgradewiki.py --scan/--backup` 获取现状与备份；涉及批量文件变更可用 `--write` 执行 JSON 计划。
- `~validate`：先用 `scripts/upgradewiki.py --scan` 拿到文件清单，再做结构/链接/索引校验；方案包可用 `scripts/validate_package.py` 一并校验。

## 输出要求

- 使用 `templates/output-format.md`。
- 输出必须包含：知识库状态、变更文件、质量检查结果。
