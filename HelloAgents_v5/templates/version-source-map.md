# 版本号定位参考（主 > 次）

当需要更新版本号或生成 CHANGELOG 条目时，优先从“主来源”读取并更新版本号；如不存在，再使用“次来源”。

| 语言/框架 | 主来源 | 次来源 |
|----------|--------|--------|
| JavaScript/TypeScript | package.json → version | index.js/ts → VERSION 常量 |
| Python | pyproject.toml → [project].version | setup.py / __init__.py → __version__ |
| Java (Maven) | pom.xml → <version> | - |
| Java (Gradle) | gradle.properties / build.gradle → version | - |
| Go | Git tag | - |
| Rust | Cargo.toml → [package].version | - |
| .NET | .csproj → <Version>/<AssemblyVersion> | - |
| C/C++ | CMakeLists.txt → project(...VERSION) | 头文件 → #define PROJECT_VERSION |

## 版本递增建议（SemVer）

- 破坏性变更（不兼容）：`Major + 1`，`Minor=0`，`Patch=0`
- 新功能（向后兼容）：`Minor + 1`，`Patch=0`
- 修复/优化/文档/微调：`Patch + 1`

> 若项目不使用版本号，也可只维护 `Unreleased`，并在交付总结中说明原因。

