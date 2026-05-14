# Codex Skills 目录说明

> 路径：`C:\Users\Y3613\.codex\skills`  
> 更新时间：2026-05-14  
> 说明：本文用于说明本目录下各类 skill、agent 配置、设计资料和 MCP 工具的用途，以及图二中 MCP 工具的安装与启用方式。

## 1. 先区分几个概念

`skill`、`agent` 和 `MCP 工具` 不是同一种东西：

| 类型 | 位置示例 | 作用 |
|---|---|---|
| Skill | `HelloAgents_v5/SKILL.md` | 给 Codex 的“专项工作说明书”，用于触发某类任务流程。 |
| Agent 配置 | `agents/ha-explorer.toml` | 给多代理模式使用的角色配置，例如只读探索、风险审查、受控写入。 |
| 资料库 | `design-md/*/README.md` | 不是可触发 skill，而是设计风格、品牌规范、提示词素材。 |
| MCP 工具 | `code-index`、`context7` 等 | Codex 外挂能力：索引代码、查文档、读写文件、规划推理等。 |

判断一个目录是不是 Codex skill，核心看它或其子目录下是否存在 `SKILL.md`，且文件 frontmatter 里包含 `name` 和 `description`。

## 2. 当前目录树概览
```text
skills/
├─ .system/                         # Codex 系统内置技能
│  ├─ imagegen/                     # 图像生成/编辑技能
│  ├─ openai-docs/                  # OpenAI 官方文档查询技能
│  ├─ plugin-creator/               # Codex 插件创建脚手架
│  ├─ skill-creator/                # 创建/维护 Codex skill 的技能
│  └─ skill-installer/              # 从 curated/GitHub 安装 skill
├─ agents/                          # HelloAgents 多代理角色配置
│  ├─ ha-explorer.toml              # 只读探索代理
│  ├─ ha-reviewer.toml              # 只读审查代理
│  ├─ ha-product.toml               # 产品/验收决策代理
│  ├─ ha-ui-designer.toml           # UX/UI 决策代理
│  ├─ ha-writer-backend.toml        # 后端受控写入代理
│  └─ ha-writer-frontend.toml       # 前端受控写入代理
├─ design-md/                       # 品牌/产品设计风格 README 集合
├─ gitnexus/                        # GitNexus 技能组
├─ gitnexus-index-guard/            # GitNexus 索引守护技能
├─ grok-search-codex-proxy/         # GrokSearch MCP 兼容代理技能
├─ HelloAgents_v5/                  # HelloAgents_v5 开发维护流程技能组
├─ prototype-prompt-generator/      # UI/UX 原型提示词生成技能
├─ skills-main/                     # openai/skills 仓库镜像或素材集合
├─ AGENTS.md                        # 本目录级别的工作约束
└─ README.MD                        # 本说明文档
```

## 3. 各目录用途说明
### 3.1 `.system/`：Codex 系统技能

这是 Codex 自带或预置的系统级技能集合，通常不需要你手动改动。

| 子目录 | 作用 | 典型触发场景 |
|---|---|---|
| `.system/imagegen` | 生成或编辑位图图片，例如产品图、海报、UI mockup、透明背景素材。 | “帮我生成一张图”“把这张图改成透明背景”。 |
| `.system/openai-docs` | 查询 OpenAI 产品/API 官方文档。 | “OpenAI API 怎么用”“最新模型如何选择”。 |
| `.system/plugin-creator` | 创建 Codex 插件目录和 `.codex-plugin/plugin.json`。 | “帮我创建一个 Codex 插件”。 |
| `.system/skill-creator` | 创建或更新 Codex skill。 | “帮我写一个新 skill”。 |
| `.system/skill-installer` | 从 OpenAI curated skills 或 GitHub 仓库安装 skill。 | “列出可安装技能”“安装某个 skill”。 |

### 3.2 `agents/`：HelloAgents 子代理角色

这里不是 skill，而是多代理模式的角色配置。它们会被 `HelloAgents_v5` 或主代理按任务需要调用。

| 文件 | 角色 | 权限边界 |
|---|---|---|
| `ha-explorer.toml` | 只读探索，负责定位文件、提取证据锚点。 | 禁止写入，禁止测试/构建。 |
| `ha-reviewer.toml` | 只读审查，关注安全、正确性、测试风险、可维护性。 | 禁止写入，禁止测试/构建。 |
| `ha-product.toml` | 产品决策，补齐范围、验收、成功指标。 | 只读，不能编造字段/接口。 |
| `ha-ui-designer.toml` | UX/UI 决策，补齐交互、状态、视觉建议。 | 只读，不能编造文案/字段。 |
| `ha-writer-backend.toml` | 后端受控写入。 | 只能按主代理写入包改指定文件。 |
| `ha-writer-frontend.toml` | 前端受控写入。 | 只能按主代理写入包改指定文件。 |
### 3.3 `design-md/`：设计风格资料库

`design-md` 下是大量品牌或产品风格说明，例如 `apple`、`figma`、`stripe`、`vercel`、`notion`、`spotify` 等。

它的用途更像“设计参考库”：

- 用于生成 UI 原型提示词时参考具体品牌风格。
- 用于前端视觉设计时提取色彩、排版、组件气质。
- 不属于自动触发 skill，因为这些目录里主要是 `README.md`，不是 `SKILL.md`。

### 3.4 `gitnexus/`：GitNexus 技能组

GitNexus 是代码知识图谱/索引工具，用于理解代码、追踪调用链、做影响面分析和重构辅助。

| 子技能 | 作用 | 典型问题 |
|---|---|---|
| `gitnexus-cli` | 说明 `npx gitnexus analyze/status/clean/wiki/list` 等 CLI。 | “帮我索引这个仓库”。 |
| `gitnexus-exploring` | 探索代码架构、执行流、模块关系。 | “这个认证流程怎么走”。 |
| `gitnexus-debugging` | 调试问题、追踪错误来源。 | “为什么这个接口 500”。 |
| `gitnexus-impact-analysis` | 分析改动影响面。 | “改这个函数会影响哪里”。 |
| `gitnexus-refactoring` | 支持重命名、抽取、移动、拆分等重构。 | “安全地重命名这个方法”。 |
| `gitnexus-guide` | GitNexus 工具、资源、图谱 schema 速查。 | “GitNexus 有哪些工具”。 |

### 3.5 `gitnexus-index-guard/`：GitNexus 索引守护

这个 skill 用来检查当前仓库 GitNexus 索引是否存在、是否过期，以及是否建议重新 analyze。

关键脚本：

```text
gitnexus-index-guard/
└─ scripts/
   ├─ check_gitnexus_index.ps1
   ├─ install_repo_hooks.ps1
   └─ install_global_template_hooks.ps1
```
常用命令：

```powershell
# 仅检测，不自动重建索引
pwsh -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\gitnexus-index-guard\scripts\check_gitnexus_index.ps1" -RepoPath "<repo>" -OnlyCheck

# 为某个仓库安装提交/合并后自动检查 hook
pwsh -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\gitnexus-index-guard\scripts\install_repo_hooks.ps1" -RepoPath "<repo>"
```

### 3.6 `grok-search-codex-proxy/`：GrokSearch MCP 兼容代理

这个 skill 解决 GrokSearch/FastMCP 与 Codex CLI stdio 协议不兼容的问题。

核心原因：

- GrokSearch/FastMCP 使用 NDJSON framing。
- Codex MCP stdio 客户端使用 `Content-Length` framing。
- 直接连接可能在 initialize 阶段失败。

本技能通过 `scripts/stdio-proxy.js` 在中间做协议转换。

关键文件：

```text
grok-search-codex-proxy/
├─ scripts/stdio-proxy.js       # Codex 与 GrokSearch 之间的 stdio 协议转换代理
├─ scripts/mcp-smoke-test.js    # 冒烟测试脚本
└─ assets/GrokSearch/           # 内置 GrokSearch 源码
```

推荐触发方式：

```text
$grok-search-codex-proxy
帮我搜索：你的关键词
```

当显式点名该 skill 时，网页搜索应只使用 `grok-search`，不要自动降级到 `ddg-search`。
```toml
[mcp_servers.desktop_commander]
command = "<你的 npx.cmd 路径>"
args = ["-y", "@wonderwhy-er/desktop-commander", "--transport", "stdio"]

[mcp_servers.sequential_thinking]
command = "<你的 npx.cmd 路径>"
args = ["-y", "@modelcontextprotocol/server-sequential-thinking", "--transport", "stdio"]
```

> 注意：不要把真实 API Key 写进公开仓库或截图里。本文用 `<...>` 占位。

## 5. MCP 工具安装与启用步骤

以下步骤默认 Windows + Codex CLI。配置文件通常在：

```text
C:\Users\Y3613\.codex\config.toml
```

### 5.1 前置依赖

先确认 Node.js、npm/npx、Python、uv 可用：

```powershell
node -v
npm -v
npx -v
python --version
uvx --version
```

如果 `uvx` 不存在，可以安装 `uv`：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 5.2 安装/启用 `code-index`

`code-index` 当前配置来源是：

```toml
[mcp_servers.code-index]
command = "uvx"
args = ["code-index-mcp"]
```
验证：

```powershell
uvx code-index-mcp --help
```

使用要点：

- 每个新会话首次使用前先设置项目根目录。
- 典型顺序：`set_project_path(<项目根目录>)` → `refresh_index`。
- 只有确需符号级分析时才运行深度索引。

### 5.3 安装/启用 `context7`

Context7 用于查询库/框架文档。当前 npm 包信息显示入口为 `context7-mcp`。

推荐配置：

```toml
[mcp_servers.context7]
command = "D:\\java\\Node\\nvm\\v20.19.1\\npx.cmd"
args = ["-y", "@upstash/context7-mcp"]
```

如果你有 Context7 API Key，可以追加：

```toml
args = ["-y", "@upstash/context7-mcp", "--api-key", "<CTX7_API_KEY>"]
```

验证：

```powershell
npx -y @upstash/context7-mcp --help
```

使用要点：

- 先 resolve library id，再 query docs。
- 适合 React、Next.js、Spring、OpenAI SDK 等官方文档查询。

### 5.4 安装/启用 `desktop_commander`

Desktop Commander 用于读写文件、搜索目录、管理本地进程和分析本地数据。

推荐配置：

```toml
[mcp_servers.desktop_commander]
command = "D:\\java\\Node\\nvm\\v20.19.1\\npx.cmd"
args = ["-y", "@wonderwhy-er/desktop-commander", "--transport", "stdio"]
```
验证：

```powershell
npx -y @wonderwhy-er/desktop-commander --help
```

使用要点：

- 适合读写文件、列目录、局部读取大文件。
- 本地 CSV/JSON/PDF/Excel 分析优先用它的进程工具。
- 文件编辑建议用精确替换或分块写入。

### 5.5 安装/启用 `sequential_thinking`

Sequential Thinking 用于复杂问题拆解和计划生成。

推荐配置：

```toml
[mcp_servers.sequential_thinking]
command = "D:\\java\\Node\\nvm\\v20.19.1\\npx.cmd"
args = ["-y", "@modelcontextprotocol/server-sequential-thinking", "--transport", "stdio"]
```

验证：

```powershell
npx -y @modelcontextprotocol/server-sequential-thinking --help
```

使用要点：

- 适合复杂任务规划、方案评估、步骤拆分。
- 输出应转化为可执行计划，不应把冗长推理暴露给最终用户。

### 5.6 安装/启用 `gitnexus`

图二里 `gitnexus` 显示“已停止”。我本机核验到 npm 上存在 `gitnexus` 包，版本为 `1.6.4`，CLI 入口为 `gitnexus`。

先验证 CLI 是否可用：

```powershell
npx gitnexus --help
npx gitnexus status
```
在项目根目录初始化索引：

```powershell
cd <你的项目根目录>
npx gitnexus analyze
```

可选命令：

```powershell
npx gitnexus status      # 查看索引状态
npx gitnexus clean       # 删除当前仓库索引
npx gitnexus list        # 列出已索引仓库
npx gitnexus wiki        # 基于图谱生成文档，通常需要 LLM API Key
```

如果需要保留或生成向量检索能力：

```powershell
npx gitnexus analyze --embeddings
```

`gitnexus` MCP server 的精确配置项要以你安装的 GitNexus 文档或现有 MCP 面板生成项为准。若 Codex 面板里有 `gitnexus` 但停止，优先排查：

1. `config.toml` 里是否存在 `[mcp_servers.gitnexus]`。
2. `command` 指向的可执行文件是否存在。
3. `args` 是否与当前 GitNexus 版本匹配。
4. 是否需要先在目标仓库运行 `npx gitnexus analyze`。
5. 停止后重启 Codex 或重新加载 MCP server。

索引守护检测命令：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\skills\gitnexus-index-guard\scripts\check_gitnexus_index.ps1" -RepoPath "<repo>" -OnlyCheck
```

### 5.7 安装/启用 `grok-search`

图二没有展示 `grok-search`，但当前目录有 `grok-search-codex-proxy` skill。若你要把 GrokSearch 作为 MCP 搜索工具接入 Codex，应通过本技能的 stdio 代理启动。

推荐配置形态：
```toml
[mcp_servers.grok-search]
command = "D:\\java\\Node\\nvm\\v20.19.1\\node.exe"
args = ["C:\\Users\\Y3613\\.codex\\skills\\grok-search-codex-proxy\\scripts\\stdio-proxy.js"]

[mcp_servers.grok-search.env]
GROK_API_URL = "<你的 Grok API URL>"
GROK_API_KEY = "<你的 Grok API Key>"
GROK_WEB_SEARCH_MODE = "grok-only"
GROK_FORCE_MODEL = "grok-4-fast"
```

验证代理握手：

```powershell
node "$env:USERPROFILE\.codex\skills\grok-search-codex-proxy\scripts\mcp-smoke-test.js" --with-config
```

如果要验证搜索能力：

```powershell
node "$env:USERPROFILE\.codex\skills\grok-search-codex-proxy\scripts\mcp-smoke-test.js" --with-config --search "OpenAI Codex MCP"
```

注意：

- 不要把 `GROK_API_KEY` 写进 README 或公开仓库。
- 若用户显式写 `$grok-search-codex-proxy`，应只用 grok-search，不自动降级 DuckDuckGo。
- 如果 initialize 握手失败，优先确认 `stdio-proxy.js` 路径和 Node.js 路径。

## 6. 常见排错

### 6.1 MCP 显示“已停止”

按顺序排查：

1. 打开 `C:\Users\Y3613\.codex\config.toml`。
2. 找到对应 `[mcp_servers.<name>]`。
3. 确认 `command` 路径存在。
4. 在 PowerShell 中单独运行对应 `npx/uvx/node` 命令。
5. 如果是需要 API Key 的工具，确认 env 已配置且没有拼写错误。
6. 重启 Codex 或在 UI 中重新启用该 MCP。

### 6.2 `npx` 找不到或版本不对

你当前本机 Node 路径类似：

```text
D:\java\Node\nvm\v20.19.1\node.exe
D:\java\Node\nvm\v20.19.1\npx.cmd
```

如果换了 Node 版本，`config.toml` 里的 `npx.cmd` 路径也要同步调整。

### 6.3 `code-index` 找不到

先检查：

```powershell
uvx --version
uvx code-index-mcp --help
```

如果 `uvx` 不存在，先安装 `uv`。如果 `code-index-mcp` 启动失败，优先看 Codex MCP 日志或切换到提示词中提到的 legacy 配置。

### 6.4 `gitnexus` 停止

优先确认 CLI 能跑：

```powershell
npx gitnexus --help
npx gitnexus status
```

如果 CLI 正常但 MCP 停止，说明问题更可能在 Codex 的 MCP server 配置，而不是 GitNexus 包本身。

## 7. 建议的使用顺序

做代码类任务时，推荐这样组合：

1. 用 `code-index` 快速定位文件和符号。
2. 用 `Desktop Commander` 精读目标文件片段。
3. 需要规划复杂任务时，用 `sequential_thinking` 拆解步骤。
4. 需要官方文档时，用 `context7` 查库/框架文档。
5. 需要代码知识图谱和影响面时，用 `gitnexus`。
6. 需要网页搜索时，优先用 `grok-search`，特别是显式触发 `$grok-search-codex-proxy` 时。
## 8. 维护建议

- 新增 skill 时优先使用 `.system/skill-creator` 的规范。
- 每个真正的 skill 都应包含 `SKILL.md`，并在 frontmatter 中写清楚 `name` 和 `description`。
- 大段参考资料放进 `references/`，可执行脚本放进 `scripts/`，输出模板或素材放进 `assets/`。
- 不要在 skill、README 或示例配置中写入真实 API Key。
- 修改 MCP 配置后，通常需要重启 Codex 才能稳定生效。

## 9. 本文依据

本文基于以下本地文件和只读检查整理：

- `AGENTS.md`
- `.system/*/SKILL.md`
- `agents/*.toml`
- `gitnexus/*/SKILL.md`
- `gitnexus-index-guard/SKILL.md`
- `grok-search-codex-proxy/SKILL.md`
- `HelloAgents_v5/SKILL.md`
- `prototype-prompt-generator/SKILL.md`
- `C:\Users\Y3613\.codex\config.toml` 的 MCP `command/args` 摘要

敏感配置如 API Key 未写入本文。
