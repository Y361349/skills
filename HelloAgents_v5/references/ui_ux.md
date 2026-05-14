# UI/UX 精致化（融合 ui-ux-pro-max 离线素材库）

> 目标：不要求用户提供 UI 参考图，也不依赖联网；基于 `ui-ux-pro-max` 的本地 CSV 素材库，快速产出“可落地”的 UI 视觉规范与交互细节（风格/色板/字体/动效/无障碍/图标/栈指南），并写入 `helloagents/plan/*` 的方案包文件。

## 0) 触发与交互（让你不用记规则）

- 自动触发关键词：`UI|界面|页面|前端|视觉|设计|好看|精美|高级|质感|风格|配色|颜色|字体|排版|动效|动画|组件|图标|表单|表格|列表|详情|dashboard|admin|后台|小程序|H5|uni-app|vben|antdv|ant design|tailwind|shadcn`
- 明确开关：
  - `UI=on` / `UI=off`
  - 选风格：`风格=1|2|3`（或 `风格=minimal|modern|glass`）

## 0.1 默认给出的 3 个风格候选（命中 UI 触发时就给）

1. `minimal`（Minimal/Swiss）：专业、干净、信息密度高，适合后台/表格/表单
2. `modern`（Modern Professional）：更现代、品牌感更强，适合 SaaS/运营后台
3. `glass`（Glassmorphism）：科技质感强，适合少量点缀（卡片/弹窗/顶部导航），注意性能与对比度

## 1) 数据源位置（跨平台）

- Windows：`$env:USERPROFILE\.codex\skills\ui-ux-pro-max\data`
- macOS/Linux：`~/.codex/skills/ui-ux-pro-max/data`

PowerShell 示例（Windows）：

```powershell
$uiuxRoot = Join-Path $env:USERPROFILE '.codex\\skills\\ui-ux-pro-max'
$data = Join-Path $uiuxRoot 'data'
```

## 2) 推荐：一键生成 Design System（Python `search.py --design-system`）

> 适用：本机可用 Python（建议 ≥3.10）。优势：一次输出“风格/色板/字体/动效/无障碍/反例”，可直接粘贴进方案包。

PowerShell 示例（Windows）：

```powershell
$uiuxRoot = Join-Path $env:USERPROFILE '.codex\\skills\\ui-ux-pro-max'
$search = Join-Path $uiuxRoot 'scripts\\search.py'

# 输出为 Markdown（推荐：方便直接粘贴到 why.md 的 UX/UI 章节）
python -X utf8 $search "SaaS 后台 管理端 表格 表单 专业" --design-system -p "项目名" -f markdown

# （可选）落盘保存到项目目录：会创建 design-system/MASTER.md（以及 design-system/pages/ 可选）
# 建议先 cd 到项目根目录，或用 --output-dir 指定目录
python -X utf8 $search "SaaS 后台 管理端 表格 表单 专业" --design-system -p "项目名" -f markdown --persist --output-dir (Get-Location)
```

提示：
- `--persist` 仅在你希望把“设计系统”作为项目文件长期保存时使用；否则直接复制输出内容到方案包即可。
- 若只想补充某一类细节：可用 `--domain` 或 `--stack`（例如 `--domain ux` / `--stack vue`）。

## 3) 离线检索（不依赖 Python，PowerShell 兜底）

> 兼容性：以下命令在 Windows PowerShell 5.1（`powershell.exe`）与 PowerShell 7（`pwsh.exe`）均可运行；**不会自动切换**，若 5.1 执行失败请改用 `pwsh` 重试（主代理也应优先使用 `pwsh`）。  
> 思路：用 `Import-Csv` 读取 CSV 后按关键词筛选，取 Top 1-3 作为“候选”，再在输出里做取舍。

### 3.1 风格（styles.csv）

```powershell
Import-Csv (Join-Path $data 'styles.csv') |
  Where-Object { $_.Keywords -match 'minimal|modern|glass|dashboard|saas|enterprise' -or $_.'Best For' -match 'dashboard|SaaS|Enterprise' } |
  Select-Object -First 3 'Style Category','Type','Primary Colors','Effects & Animation','Best For','Performance','Accessibility','Framework Compatibility','Complexity'
```

### 3.2 色板（colors.csv）

```powershell
Import-Csv (Join-Path $data 'colors.csv') |
  Where-Object { $_.'Product Type' -match 'SaaS|Fintech|Healthcare|Enterprise' -or $_.Keywords -match 'saas|healthcare|enterprise|dashboard|admin' } |
  Select-Object -First 3 'Product Type','Primary (Hex)','Secondary (Hex)','CTA (Hex)','Background (Hex)','Text (Hex)','Border (Hex)','Notes'
```

### 3.3 字体搭配（typography.csv）

```powershell
Import-Csv (Join-Path $data 'typography.csv') |
  Where-Object { $_.'Mood/Style Keywords' -match 'professional|modern|elegant|tech' -or $_.'Best For' -match 'SaaS|dashboard|enterprise' } |
  Select-Object -First 3 'Font Pairing Name','Heading Font','Body Font','Google Fonts URL','CSS Import','Notes'
```

### 3.4 UX 规范（ux-guidelines.csv）

```powershell
Import-Csv (Join-Path $data 'ux-guidelines.csv') |
  Where-Object { $_.Category -match 'Navigation|Animation|Forms|Accessibility' -or $_.Issue -match 'Reduced Motion|Duration|Sticky|Loading' } |
  Select-Object -First 5 Category,Issue,Platform,Do,"Don't",Severity
```

### 3.5 图标（icons.csv，可选）

```powershell
Import-Csv (Join-Path $data 'icons.csv') |
  Where-Object { $_.Keywords -match 'dashboard|table|form|nav|user|settings|search|filter' } |
  Select-Object -First 5 Category,'Icon Name',Library,'Import Code','Usage'
```

### 3.6 栈指南（stacks/<stack>.csv，可选）

> `stack` 可从用户技术栈/项目文件类型推断：`.vue`→`vue`，`.tsx`→`react/nextjs`，不确定→`html-tailwind`。

```powershell
$stack = 'vue' # 示例：vue / react / nextjs / html-tailwind ...
Import-Csv (Join-Path $data "stacks\\$stack.csv") |
  Where-Object { $_.Category -match 'Composition|Styling|Performance|Accessibility' -or $_.Guideline -match 'Accessibility|Theme|Layout' } |
  Select-Object -First 6 Category,Guideline,Do,"Don't",Severity,'Docs URL'
```

## 4) 输出落点（写入方案包）

最小可交付（建议至少包含这些）：

- 产出位置：`helloagents/plan/*/why.md`
  - `#用户体验（UX，可选）`：用户/角色、旅程、关键交互、状态设计（空态/加载/错误/无权限/重复提交）
  - `#视觉与动效（UI，可选）`：风格方向、色板 HEX、字体、布局与组件规范、动效与反馈、无障碍
- 与“前端确认门禁”的关系：
  - 若 `analyze` 判定 `frontendImpact=possible|yes`（或用户显式 `UI=on`），应先完成 `task.md` 的“前端影响面确认 / 前端展示口径确认”，再决定是否做本节的 UI/UX 精致化（视觉规范与动效）。
- 心智负担（前端重点）：
  - UI/UX 优化优先目标之一是降低心智负担：减少步骤与决策点、提供合理默认值、用渐进披露隐藏高级选项、强化防错与反馈。
  - 若交互复杂度主要源于后端契约/约束（需要多接口拼装/缺少汇总字段/状态枚举混乱/错误提示不可用），优先在后端消解，避免把复杂性转嫁到前端。
- 默认策略：命中 UI 触发时先给 3 个风格候选 + 选择方式；用户未选时选择 `minimal` 作为推荐并说明理由
- 禁止事项：不要用 emoji 充当图标；不要只给“好看”形容词而缺少可落地的 token/HEX/规则
