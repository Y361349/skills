# 命令路由（HelloAgents_v5）

## 命令总览

| 命令 | 路径 | 说明 |
|---|---|---|
| `~auto` | evaluate → (tweak 或 analyze→design→develop) | 全授权执行 |
| `~ship` | evaluate → (tweak 或 analyze→design→develop) | 闭环交付执行（同步知识库 + 记忆体 + 本地 commit） |
| `~plan` | evaluate → (analyze) → design | 生成方案包 |
| `~exec` | develop | 执行已有方案包 |
| `~init` | kb | 初始化知识库 |
| `~upgrade` | kb | 升级知识库结构 |
| `~clean` | package | 清理遗留方案包 |
| `~test` | develop | 执行测试 |
| `~review` | develop | 代码审查 |
| `~commit` | commit | 本地提交（需确认，可选推送） |
| `~validate` | kb/package | 校验知识库与方案包 |
| `~rollback` | develop/package | 回滚最近变更 |
| `~help` | current stage | 显示命令帮助 |

## 优先级

1. 显式 `~命令` 优先于语义路由。
2. 无命令时按自然语言走 `evaluate`。

## 错误处理

- 命令不识别：输出帮助并保留当前状态。
- 前置条件不满足：提示缺失条件并给出下一步。

## 命令细则

- `~commit`：见 `references/functions/commit.md`
