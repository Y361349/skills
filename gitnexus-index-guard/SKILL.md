---
name: gitnexus-index-guard
description: 检查 GitNexus 索引状态（needsInit/isStale/耗时等级）并按需执行 analyze。用于每次会话开始、提交后、或出现“新增文件检索不到/索引过期/stale/analyze”相关问题时。
---

# GitNexus Index Guard

## 何时使用

- 需要判断当前仓库是否已建立 GitNexus 索引
- 怀疑索引落后于代码（`stale`）导致检索结果不一致
- 提交后需要快速确认是否建议重建索引
- 需要统一输出可机读的索引状态 JSON（用于门禁或自动化）

## 何时不要使用

- 只想执行一次裸命令 `gitnexus analyze` 且不需要状态诊断
- 当前目录不是 Git 仓库且也不准备使用 `--skip-git` 场景

## 运行环境

- 支持 Windows PowerShell 5.1（`powershell.exe`）与 PowerShell 7+（`pwsh`）
- 推荐优先使用 PowerShell 7+（兼容性与性能更好）
- 建议执行前先确认版本：`$PSVersionTable.PSVersion`
- `-AutoAnalyze` 需要满足其一：`gitnexus` 在 PATH 中，或可用 `npx`（Node.js/npm 环境）
- `-OnlyCheck` 仅依赖 `git` + `.gitnexus/meta.json`（不要求已安装 `gitnexus`）

## 输入

- `RepoPath`：任意仓库内路径（脚本会自动归一到仓库根目录）
- `AutoAnalyze`：显式开启自动分析
- `DisableAutoAnalyze`：强制关闭自动分析（兼容旧参数）
- `OnlyCheck`：严格仅检测，不执行 analyze
- `WithEmbeddings`：建议分析时附带 `--embeddings`
- `MaxAnalyzeMinutes`：自动分析超时
- `HookManagedNonBlocking`：默认 `true`；当仓库 `.githooks` 已打通时，手动检查走“非阻塞门禁”（不要求当场重建）。如在 hook 内执行自动分析，传 `-HookManagedNonBlocking:$false`

## 输出

- `needsInit`：是否未初始化
- `isStale`：是否落后于当前 `HEAD`（或工作区变更导致落后）
- `estimatedAnalyze`：预计耗时等级（`short/medium/long`）
- `recommendedAnalyzeArgs`：建议执行的 analyze 参数
- `autoAnalyze.*`：自动分析执行细节（执行次数/是否重试/退出码/耗时）
- `hookIntegration.*`：`.githooks` 打通状态（目录、`core.hooksPath`、`post-commit/post-merge`、重建插件是否连通）
- `manualRebuildGate.*`：手动重建门禁状态（是否由 hooks 放行）
- `firstInitConfirmation.*`：首次全局索引初始化确认门禁（`required/question/suggestedAction`）
- `worktreeDirty`：工作区是否存在未提交改动（`git status --porcelain`）
- `worktreeDirtyFileCount`：未提交改动的文件数量
- `worktreeChangedAfterIndex`：工作区改动是否发生在“上次索引”之后（用于识别“未提交但索引落后”的场景）
- `ok`：整体结果是否可视为成功（自动分析失败时为 `false`）

## 工作流

1. 解析仓库根目录（`git rev-parse --show-toplevel`）。
2. 读取 `.gitnexus/meta.json`，判断 `isIndexed/needsInit/isStale`。
3. 估算 analyze 耗时等级并给出建议参数。
4. 若显式开启自动分析，则执行 analyze；失败时可进行一次受控重试。
5. 输出统一 JSON 结果。

## 快速执行

在目标仓库根目录执行（按技能安装位置二选一）：

```powershell
# 全局技能（推荐，PowerShell 7+）
pwsh -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\gitnexus-index-guard\scripts\check_gitnexus_index.ps1"

# 项目内技能（若已放在 <repo>/.codex/skills）
pwsh -NoProfile -ExecutionPolicy Bypass -File ".\.codex\skills\gitnexus-index-guard\scripts\check_gitnexus_index.ps1"

# Windows PowerShell 5.1 兼容调用
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\gitnexus-index-guard\scripts\check_gitnexus_index.ps1"
```

> 根目录定义（重要）：这里的“仓库根目录”指 `git rev-parse --show-toplevel` 返回的目录。  
> 该规则对任何项目通用：都以 Git 仓库顶层目录为准，而不是任意子模块目录。

> 默认行为为“仅检测，不自动 analyze”（安全默认）。

如果要显式指定“自动分析”：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File ./gitnexus-index-guard/scripts/check_gitnexus_index.ps1 -AutoAnalyze
```

如果要关闭自动重建（仅保留首次初始化自动）：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File ./gitnexus-index-guard/scripts/check_gitnexus_index.ps1 -DisableAutoAnalyze
```

如果要严格“仅检测，不执行任何 analyze”（推荐用于守护门禁）：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File ./gitnexus-index-guard/scripts/check_gitnexus_index.ps1 -OnlyCheck
```

## 跨项目自动化（推荐）

如果你希望“**提交/合并后自动刷新 GitNexus 索引**”在不同项目中复用，推荐使用本技能内置的安装脚本：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\gitnexus-index-guard\scripts\install_repo_hooks.ps1" -RepoPath "<repoPath>"
```

它会在仓库根目录创建/更新：

- `<repo>/.githooks/post-commit`
- `<repo>/.githooks/post-merge`
- `<repo>/.githooks/README.md`

并设置本仓库的：`core.hooksPath=.githooks`（该配置是 **clone 级别**，不会被 git 版本化提交）。

“已打通”判定（guard 会据此决定是否放行 non-blocking）：
- `core.hooksPath=.githooks`
- `.githooks/post-commit` 存在且包含 GitNexus 重建逻辑（index-guard 或 `gitnexus analyze`）
- `.githooks/post-merge` 存在且包含 GitNexus 重建逻辑

> 若仓库已设置过 `core.hooksPath` 且不是 `.githooks`，需要加 `-Force` 才会覆盖。

## 新电脑/新 clone 自动启用（可选，全局一次）

> 背景：Git 出于安全原因，不会让仓库“自动启用 hooks 配置”；所以 `.githooks` 目录即使被提交到仓库，新 clone 默认也不会生效，仍需手动执行一次 `git config core.hooksPath .githooks`。

如果你希望在**新电脑**上做到“新 clone 后无需手动启用”，可以在该电脑执行一次全局安装脚本：

```powershell
# 交互式（会提示确认）
pwsh -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\gitnexus-index-guard\scripts\install_global_template_hooks.ps1"

# 无交互（适合脚本/CI）
pwsh -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\gitnexus-index-guard\scripts\install_global_template_hooks.ps1" -Yes
```

它会设置全局 `init.templateDir`，让 Git 在 **新 clone / 新 init** 时自动安装一个极小的 bootstrap hook（`.git/hooks/post-checkout`、`.git/hooks/post-commit`、`.git/hooks/post-merge`）：

- `post-checkout`：若仓库存在 `.githooks`，则自动执行 `git config core.hooksPath .githooks`
- `post-commit/post-merge`：若仓库存在 `.githooks/post-commit|post-merge`，则自动执行 `git config core.hooksPath .githooks` 并转调仓库内的 `.githooks/*`
- 若仓库没有 `.githooks`，则快速 no-op，不影响其他仓库

> 限制：该方案只对“安装后新建/新 clone 的仓库”生效；对已存在的旧仓库仍建议运行 `install_repo_hooks.ps1`（或手动执行一次 `git config core.hooksPath .githooks`）。

关闭方式：

```bash
git config --global --unset init.templateDir
```

如果你之前已启用 embeddings（或本次明确要保留 embeddings）：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File ./gitnexus-index-guard/scripts/check_gitnexus_index.ps1 -AutoAnalyze -WithEmbeddings
```

## 输出解读

- `needsInit=true`：未初始化，需首次 `gitnexus analyze`
- `isStale=true`：索引落后于 `HEAD`，建议重建
- `estimatedAnalyze.level`：
  - `short`：通常可在几分钟内完成
  - `medium`：中等耗时
  - `long`：建议避开高峰时段执行
- `checkDurationMs`：本次检测耗时（检测本身通常很快）
- `autoAnalyze.attempts`：自动分析尝试次数（`1`=仅主路径，`2`=触发了重试）
- `autoAnalyze.retryApplied`：是否触发重试
- `autoAnalyze.firstExitCode`：第一次尝试的退出码（便于定位重试前错误）
- `autoAnalyze.blockedByHookManagedPolicy=true`：检测到已打通 `.githooks`，手动会话按非阻塞策略跳过当场重建
- `hookIntegration.commitRebuildReady=true`：提交后重建插件已实现并打通（`.githooks` + `core.hooksPath` + `post-commit`）
- `manualRebuildGate.bypassedByHooks=true`：已初始化索引的 stale 场景可不阻塞会话，改为提交/合并时自动刷新

## 执行规则

1. 默认仅检测，不自动重建；自动分析必须显式开启（`-AutoAnalyze`）。
2. `isStale=true` 或 `needsInit=true` 时，优先给出建议参数与耗时预估。
3. 当 `needsInit=true` 时必须拦截并要求首次初始化确认：`firstInitConfirmation.required=true`，并提示用户“检测到未初始化，是否现在先执行初始化（yes/no）”。
4. 当仓库 `.githooks` 已打通（`hookIntegration.commitRebuildReady=true`）、索引已初始化且仅处于 `isStale=true` 时，且 `HookManagedNonBlocking=true`，手动检查走非阻塞门禁：可继续会话，不要求当场重建。
5. hook 内触发自动分析时需显式传 `-HookManagedNonBlocking:$false`，避免被“手动非阻塞门禁”误拦截。
6. 护栏：当 `estimatedAnalyze.level=long` 时，自动分析会被跳过（避免在不可控时长下阻塞会话/命令行），需要手动执行。
7. 若历史索引已有 embeddings，后续重建建议带 `--embeddings`，避免丢失向量。
8. 若仓库很大，优先在空闲时段重建，避免影响当前会话响应。
9. 当 `autoAnalyze.exitCode != 0` 时，`ok=false`，应视为分析失败并根据 `autoAnalyze.*` 字段排查。

## 验证

- 最小验证（仅检测）：
  - `pwsh -NoProfile -ExecutionPolicy Bypass -File ./gitnexus-index-guard/scripts/check_gitnexus_index.ps1 -OnlyCheck`
  - 期望：返回 JSON 且包含 `repoRoot/needsInit/isStale/estimatedAnalyze`
- 自动分析验证：
  - `pwsh -NoProfile -ExecutionPolicy Bypass -File ./gitnexus-index-guard/scripts/check_gitnexus_index.ps1 -AutoAnalyze`
  - 期望：`autoAnalyze.executed=true`，成功时 `ok=true` 且 `message=index is up-to-date`

## 安全与护栏

- 安全默认：不显式传 `-AutoAnalyze` 时不执行 analyze
- 失败显式化：自动分析失败返回 `ok=false`，不做静默降级
- 参数兼容：保留 `-DisableAutoAnalyze` 与 `-AutoInitWhenNeedsInit` 以兼容旧调用链

## 参考

- 执行脚本：`scripts/check_gitnexus_index.ps1`
