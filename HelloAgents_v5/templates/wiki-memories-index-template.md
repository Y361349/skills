# 功能记忆体索引

> 说明：本目录用于沉淀“可追溯的回归证据与关键结论”，让后续排查/迭代能在几分钟内定位到：
> - 当时的目标与约束
> - 改动的关键点（接口/数据/权限/降级）
> - 回归与验收证据（脚本、请求样例、截图、日志定位）
>
> 建议：每完成一条可验收的变更（尤其跨端/关键业务），就新增/更新一条记忆体，并维护本索引。

## 索引

| id | title | module | source | memory_doc | status | updated_at |
| --- | --- | --- | --- | --- | --- | --- |
| HAYYYYMMDD-XXX | [一句话标题] | [backend/frontend/both/Misc] | `[plan/..]`/`[issues/*.csv]` | `helloagents/wiki/memories/<module>/HAYYYYMMDD-XXX_xxx.md` | dev=, review=, git= | YYYY-MM-DD HH:mm:ss |

## 约定（建议）

- `id`：建议使用可排序的编号（如 `HA20260206-140`），便于按时间检索。
- `module`：用于快速过滤：`backend` / `frontend` / `both` / `Misc`（或按项目自定义）。
- `source`：优先记录“真相源入口”（方案包、issue 台账、验收文档等）。
- `memory_doc`：应包含 **复现/回归入口**（脚本/接口请求/关键页面路径），避免只有结论没有证据。
