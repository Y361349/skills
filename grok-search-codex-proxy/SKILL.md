---
name: grok-search-codex-proxy
description: 在 Codex CLI 中集成 GrokSearch（fastmcp）作为 MCP 网页搜索/抓取工具，并通过 stdio 代理修复 NDJSON vs Content-Length framing 不兼容导致的 initialize 握手失败。用于：需要只用 grok-search 进行网页搜索/抓取（禁止 ddg-search）、或排查/修复 grok-search MCP 启动失败。
---

# GrokSearch（Codex 兼容代理）

## 目标

- 让 `grok-search` MCP 在 Codex CLI 内可用（解决 initialize 握手失败）
- 当用户点名本技能时：网页搜索/抓取只允许用 `grok-search`，不调用 `ddg-search`

## 问题背景（为什么会失败）

- GrokSearch(FastMCP) stdio 使用 NDJSON（每行一条 JSON）
- Codex CLI MCP stdio 客户端使用 Content-Length framing
- 两者不兼容会在 initialize 阶段断开：`handshaking with MCP server failed: connection closed: initialize response`

## 解决方式（本技能做了什么）

- 通过 `scripts/stdio-proxy.js` 进行双向 framing 转换：
  - Codex ↔ 代理：Content-Length
  - 代理 ↔ GrokSearch：NDJSON
- 本技能内置 GrokSearch 源码于 `assets/GrokSearch`，代理默认用内置源码启动
- 安全加固：
  - 代理会对 GrokSearch 的 stderr 做密钥脱敏（防止意外日志泄露）
  - GrokSearch 侧日志也做二次脱敏；`get_config_info` 不回显任何 API Key 字符（始终为 `"***"`）

## 使用范围（强约束：只用 grok-search）

当用户显式点名/调用本技能，并要求“网页搜索、资料检索、开源项目查找、链接收集、抓取网页正文”等任务时：

- 只允许调用 MCP server：`grok-search`
- 只允许使用的工具：`grok-search.web_search`、`grok-search.web_fetch`、`grok-search.get_config_info`
- 严禁调用：`ddg-search`（以及任何其它搜索/抓取类 MCP），除非用户明确要求
- 失败处理：若 `grok-search` 不可用/鉴权失败/返回错误，不要自动降级到 `ddg-search`；应输出排查步骤并引导用户修复配置后重试
- 交互要求：首次回复需明确声明“本次只用 grok-search，不用 ddg-search”；若 grok-search 不可用则直接进入排错流程

说明：
- Codex 目前没有类似 Claude 的 `allowed-tools` 硬限制；因此本技能用“强约束 + 明确失败策略”达到“只用 grok-search”的效果。
- 如果你发现自己将要调用 `ddg-search`，必须立刻停止并改用 `grok-search`（或按失败处理退出）。

## 触发方式（避免未真正激活技能）

- 推荐：在问题开头单独一行写 `$grok-search-codex-proxy`，再写检索需求。
- 仅把 `$grok-search-codex-proxy` 放在 Markdown 链接/代码块里，可能不会被 Codex 识别为显式调用。

示例（推荐，确保触发）：
```
$grok-search-codex-proxy
帮我搜索：<你的问题/关键词>
```

反例（可能不触发）：
```
[$grok-search-codex-proxy](C:\\Users\\Administrator\\.codex\\skills\\grok-search-codex-proxy\\SKILL.md) 帮我搜索：...
```

如果 VSCode 的 Codex 插件“插入技能”会自动变成上述链接格式：
- 请手动把第一行改成纯文本 `$grok-search-codex-proxy`（删掉 `[...] ( ... )` 仅保留 `$...`），第二行再写搜索需求。

## 输入 / 输出

**输入**
- `query`：建议 6-12 个关键词 + 限定词（`site:` / `filetype:` / `after:`）
- 可选：`platform`（若 grok-search 工具支持；不确定就用默认）

**输出**
- 结果列表：标题、URL、简要摘要、抓取时间/来源信息（如果工具返回）
- 抓取正文：Markdown（只截取关键段落，避免超长）

## 标准工作流（必须按顺序）

1) 自检（推荐）：调用 `grok-search.get_config_info`，确认 `GROK_API_URL` 已配置（严禁在聊天中泄露 `GROK_API_KEY`）
   - 注意：`GROK_WEB_SEARCH_MODE` 默认为 `grok-only`，会拒绝在非 `grok-*` 模型下执行 `web_search/web_fetch`（避免生成式假检索）。
   - 建议：为保证“新会话也一定用 grok”，在 `~/.codex/config.toml` 为 grok-search 配置 `GROK_FORCE_MODEL="grok-4-fast"`（或你确认可用的 `grok-*` 模型）。
2) 搜索：调用 `grok-search.web_search` 获取候选链接
3) 过滤：按域名去重，优先官方/权威来源
4) 抓正文：对 1-3 个关键链接调用 `grok-search.web_fetch`
5) 汇总：按“标题 + URL + 3-5 句摘要”输出；如用户要求离线沉淀，再给出保存/索引建议

## 验证与排错（看到 ddg-search 被调用时怎么做）

- 先确认 `grok-search` MCP 可用：调用一次 `grok-search.get_config_info` 或任意 `grok-search.web_search`
- 推荐使用本技能自带冒烟脚本（不依赖对话路由）：`node <本技能路径>/scripts/mcp-smoke-test.js --with-config`
  - 只验证握手与工具列表：不加 `--with-config`
  - 需要验证搜索：加 `--search "你的关键词"`（会产生网络请求）
- 若仍看到 `ddg-search` 被调用：
  1) 确认本技能确实被显式激活（见“触发方式”）
  2) 确认当前会话工具列表里存在 `grok-search.*`（必要时重启 Codex 让配置生效）
  3) 检查 `~/.codex/config.toml` 中 `[mcp_servers.grok-search]` 是否仍指向本技能 `scripts/stdio-proxy.js`
  4) 如需“硬性禁止 ddg-search”：临时注释/移除 `~/.codex/config.toml` 中的 `[mcp_servers.ddg-search]`（会影响其它对话/技能）

## 配置要点（真相源）

- 配置文件：
  - Windows：`%USERPROFILE%\.codex\config.toml`
  - macOS/Linux：`~/.codex/config.toml`
- `grok-search` MCP server 启动应指向本代理脚本（不要直接 `uvx ... grok-search`）：
  - `command = "<node 路径>"`
  - `args = ["<本技能路径>/scripts/stdio-proxy.js"]`
- `grok-search` 环境变量：
  - `GROK_API_URL`
  - `GROK_API_KEY`（不要输出/回显）
  - `GROK_WEB_SEARCH_MODE`（可选，默认 `grok-only`：仅允许 `grok-*` 模型；`any`：允许任意模型但不保证真实性；`disabled`：禁用搜索/抓取）
  - `GROK_FORCE_MODEL`（可选，推荐：强制指定模型，避免“上一会话切到 claude/gpt 导致新会话变成假检索”）
- 代理启动 GrokSearch 的源码来源（可选）：
  - 默认：`assets/GrokSearch`
  - 覆盖：传 `--from <路径/仓库>` 或设置环境变量 `GROK_SEARCH_FROM`

补充建议（避免在终端/日志“误打印密钥”）：
- 不要用 `rg/cat` 直接打印 `~/.codex/config.toml`（里面可能有明文 `GROK_API_KEY`）。
- 优先用 `codex mcp get grok-search`（默认会脱敏显示 env）或用本技能冒烟脚本自检。
