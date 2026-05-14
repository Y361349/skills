#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建 HelloAgents_v5 方案包（why/how/task）

Usage:
    python create_package.py <feature-name> [--path <base-path>] [--type <implementation|overview>]
        [--complexity-initial <TWEAK|LIGHT|STANDARD|UNKNOWN>] [--complexity-review <TWEAK|LIGHT|STANDARD|UNKNOWN>]
        [--delivery-mode <NORMAL|CLOSE_LOOP>]

Examples:
    python create_package.py user-login
    python create_package.py api-refactor --type overview
    python create_package.py auth-system --path /path/to/project
    python create_package.py login-fix --complexity-initial LIGHT --complexity-review STANDARD --delivery-mode NORMAL
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

# 确保能找到同目录下的 utils 模块
sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    ExecutionReport,
    generate_package_name,
    get_plan_path,
    get_template_loader,
    setup_encoding,
    validate_base_path,
)

TEMPLATE_WHY = "plan-why-template.md"
TEMPLATE_HOW = "plan-how-template.md"
TEMPLATE_TASK = "plan-task-template.md"

META_LINE_RE = re.compile(r"^>\s*\*\*@(?P<key>[a-zA-Z0-9_]+):\*\*\s*(?P<value>.*)\s*$")

COMPLEXITY_DESC_ZH = {
    "TWEAK": "单点小改、实现路径明确、无高风险",
    "LIGHT": "局部变更，需要简要设计",
    "STANDARD": "跨模块/多路径/架构变化/高风险",
    "UNKNOWN": "未评估/待复核",
}

DELIVERY_MODE_DESC_ZH = {
    "NORMAL": "普通交付（必须同步知识库）",
    "CLOSE_LOOP": "闭环交付（同步知识库 + 记忆体 + 本地 commit）",
}


def _format_meta_line(key: str, value: str) -> str:
    return f"> **@{key}:** {value}"


def _set_metadata_block(content: str, meta: Dict[str, str], order: list[str]) -> str:
    """
    在首个 Markdown 标题后写入/更新元信息区块（blockquote 行）。

    规则：
    - 先移除全文中同 key 的旧元信息行，避免重复
    - 再在首个标题后插入“标准顺序”的元信息区块
    """
    if not meta:
        return content

    keys = set(meta.keys())
    meta_lines = [_format_meta_line(k, meta[k]) for k in order if k in meta and meta[k]]
    if not meta_lines:
        return content

    lines = content.splitlines()
    filtered: list[str] = []
    for line in lines:
        m = META_LINE_RE.match(line.lstrip())
        if m and m.group("key") in keys:
            continue
        filtered.append(line)
    lines = filtered

    heading_idx = None
    for idx, raw in enumerate(lines):
        if raw.lstrip().startswith("#"):
            heading_idx = idx
            break

    # 若没有标题，则把元信息放在文件最前
    if heading_idx is None:
        return ("\n".join(meta_lines + [""] + lines)).rstrip() + "\n"

    insert_at = heading_idx + 1
    while insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1

    block = meta_lines + [""]
    lines[insert_at:insert_at] = block
    return "\n".join(lines).rstrip() + "\n"


def _format_complexity_value(level: str) -> str:
    code = (level or "").strip().upper()
    desc = COMPLEXITY_DESC_ZH.get(code)
    return f"{code}（{desc}）" if desc else code


def _format_delivery_mode_value(mode: str) -> str:
    code = (mode or "").strip().upper()
    desc = DELIVERY_MODE_DESC_ZH.get(code)
    return f"{code}（{desc}）" if desc else code


def _fill_placeholders(content: str, replacements: Dict[str, str]) -> str:
    for old, new in replacements.items():
        content = content.replace(old, new)
    return content


def _insert_after_first_heading(content: str, line: str) -> str:
    lines = content.splitlines()
    for idx, raw in enumerate(lines):
        if raw.lstrip().startswith("#"):
            insert_at = idx + 1
            # 标题后若紧接空行，插在空行后更自然
            if insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1
            lines.insert(insert_at, line)
            lines.insert(insert_at + 1, "")
            return "\n".join(lines).rstrip() + "\n"
    return (content.rstrip() + "\n\n" + line + "\n").rstrip() + "\n"


def create_package(
    feature: str,
    base_path: str | None = None,
    pkg_type: str = "implementation",
    complexity_initial: str = "UNKNOWN",
    complexity_review: str | None = None,
    delivery_mode: str = "NORMAL",
) -> ExecutionReport:
    """
    创建方案包（并发安全，支持 AI 降级接手）

    Args:
        feature: 功能名称
        base_path: 项目根目录
        pkg_type: 方案包类型 (implementation/overview)
        complexity_initial: 复杂度初判 (TWEAK/LIGHT/STANDARD/UNKNOWN)
        complexity_review: 复杂度复核 (TWEAK/LIGHT/STANDARD/UNKNOWN)，默认同初判
        delivery_mode: 交付模式 (NORMAL/CLOSE_LOOP)
    """
    report = ExecutionReport("create_package")
    if complexity_review is None:
        complexity_review = complexity_initial
    report.set_context(
        feature=feature,
        pkg_type=pkg_type,
        complexity_initial=complexity_initial,
        complexity_review=complexity_review,
        delivery_mode=delivery_mode,
        base_path=base_path or "cwd",
    )

    plan_path = get_plan_path(base_path)
    original_name = generate_package_name(feature)

    # 步骤1: 确保父目录存在
    try:
        plan_path.mkdir(parents=True, exist_ok=True)
        report.mark_completed("创建 plan/ 目录", str(plan_path), "检查目录是否存在")
    except PermissionError as exc:
        report.mark_failed(
            "创建 plan/ 目录",
            ["创建 plan/ 目录", "创建方案包目录", "创建 why.md", "创建 how.md", "创建 task.md"],
            f"权限不足: {exc}",
        )
        return report

    # 步骤2: 并发安全的目录创建（原子操作 + 重试）
    max_retries = 100
    package_path: Path | None = None
    package_name: str | None = None

    for version in range(1, max_retries + 1):
        package_name = original_name if version == 1 else f"{original_name}_v{version}"
        package_path = plan_path / package_name
        try:
            package_path.mkdir(exist_ok=False)
            report.mark_completed("创建方案包目录", str(package_path), "检查目录存在且为新建目录")
            report.set_context(package_path=str(package_path), package_name=package_name)
            break
        except FileExistsError:
            continue
        except PermissionError as exc:
            report.mark_failed(
                "创建方案包目录",
                ["创建方案包目录", "创建 why.md", "创建 how.md", "创建 task.md"],
                f"权限不足: {exc}",
            )
            return report
    else:
        report.mark_failed(
            "创建方案包目录",
            ["创建方案包目录", "创建 why.md", "创建 how.md", "创建 task.md"],
            f"超过最大重试次数 ({max_retries})，存在大量同名方案包",
        )
        return report

    assert package_path is not None
    assert package_name is not None

    # 步骤3: 加载模板
    loader = get_template_loader()

    why_template = loader.load(TEMPLATE_WHY)
    how_template = loader.load(TEMPLATE_HOW)
    task_template = loader.load(TEMPLATE_TASK)

    if why_template is None or how_template is None or task_template is None:
        missing = [p for p, t in [(TEMPLATE_WHY, why_template), (TEMPLATE_HOW, how_template), (TEMPLATE_TASK, task_template)] if t is None]
        report.mark_failed(
            "加载模板",
            ["创建 why.md", "创建 how.md", "创建 task.md"],
            f"模板文件不存在: {', '.join(missing)}（期望位于 templates/ 目录）",
        )
        return report

    # 步骤4: 生成文件内容（模板为 v2 风格的方括号占位符）
    replacements = {
        "[功能名称]": feature,
        "YYYYMMDDHHMM_<feature>": package_name,
    }

    why_content = _fill_placeholders(why_template, replacements)
    how_content = _fill_placeholders(how_template, replacements)

    if pkg_type == "overview":
        task_content = (
            f"# 任务清单: {feature}\n\n"
            f"目录: `helloagents/plan/{package_name}/`\n\n"
            "> **@pkg_type:** overview\n"
            "> 无执行任务（概述文档，不进入开发实施阶段）\n\n"
            "## 说明\n"
            "- 本方案包用于沉淀共识/范围/风险，不包含可执行任务。\n"
            "- 如需落地实施，请创建 `implementation` 类型方案包。\n"
        )
    else:
        task_content = _fill_placeholders(task_template, replacements)

    # 元信息（语言无关）：为 validator 提供类型标记，同时记录复杂度“初判/复核”与交付模式
    why_content = _set_metadata_block(
        why_content,
        {
            "pkg_type": pkg_type,
            "complexity_initial": _format_complexity_value(complexity_initial),
            "complexity_review": _format_complexity_value(complexity_review),
            "delivery_mode": _format_delivery_mode_value(delivery_mode),
            # 最终执行前必须由主代理收口定稿，并将该标记更新为 YES
            "final_confirm": "NO（未收口定稿/禁止执行）",
        },
        ["pkg_type", "complexity_initial", "complexity_review", "delivery_mode", "final_confirm"],
    )
    how_content = _set_metadata_block(how_content, {"pkg_type": pkg_type}, ["pkg_type"])
    task_content = _set_metadata_block(task_content, {"pkg_type": pkg_type}, ["pkg_type"])

    # 步骤5: 写入文件
    try:
        (package_path / "why.md").write_text(why_content, encoding="utf-8")
        report.mark_completed("创建 why.md", str(package_path / "why.md"), "检查文件存在且非空")
    except Exception as exc:
        report.mark_failed("写入 why.md", ["创建 why.md", "创建 how.md", "创建 task.md"], str(exc))
        return report

    try:
        (package_path / "how.md").write_text(how_content, encoding="utf-8")
        report.mark_completed("创建 how.md", str(package_path / "how.md"), "检查文件存在且非空")
    except Exception as exc:
        report.mark_failed("写入 how.md", ["创建 how.md", "创建 task.md"], str(exc))
        return report

    try:
        (package_path / "task.md").write_text(task_content.rstrip() + "\n", encoding="utf-8")
        report.mark_completed("创建 task.md", str(package_path / "task.md"), "检查文件存在且包含任务/说明")
    except Exception as exc:
        report.mark_failed("写入 task.md", ["创建 task.md"], str(exc))
        return report

    report.set_context(created_at=datetime.now().isoformat())
    report.mark_success(str(package_path))
    return report


def main() -> None:
    setup_encoding()
    parser = argparse.ArgumentParser(description="创建 HelloAgents_v5 方案包（why/how/task）")
    parser.add_argument("feature", help="功能名称 (如: user-login, api-refactor)")
    parser.add_argument("--path", default=None, help="项目根目录 (默认: 当前目录)")
    parser.add_argument(
        "--type",
        choices=["implementation", "overview"],
        default="implementation",
        help="方案包类型: implementation(实施计划) 或 overview(概述文档)",
    )
    parser.add_argument(
        "--complexity-initial",
        choices=["TWEAK", "LIGHT", "STANDARD", "UNKNOWN"],
        default="UNKNOWN",
        help="复杂度初判（用于写入 why.md 元信息）",
    )
    parser.add_argument(
        "--complexity-review",
        choices=["TWEAK", "LIGHT", "STANDARD", "UNKNOWN"],
        default=None,
        help="复杂度复核（不传则默认同初判）",
    )
    parser.add_argument(
        "--delivery-mode",
        choices=["NORMAL", "CLOSE_LOOP"],
        default="NORMAL",
        help="交付模式（用于写入 why.md 元信息）",
    )

    args = parser.parse_args()

    try:
        validate_base_path(args.path)
    except ValueError as exc:
        report = ExecutionReport("create_package")
        report.mark_failed("验证基础路径", ["验证路径", "创建方案包"], str(exc))
        report.print_report()
        raise SystemExit(1)

    feature = args.feature.strip()
    if not feature:
        report = ExecutionReport("create_package")
        report.mark_failed("验证功能名称", ["创建方案包"], "功能名称不能为空")
        report.print_report()
        raise SystemExit(1)

    try:
        generate_package_name(feature)
    except ValueError as exc:
        report = ExecutionReport("create_package")
        report.mark_failed("验证功能名称", ["创建方案包"], str(exc))
        report.print_report()
        raise SystemExit(1)

    report = create_package(
        feature,
        args.path,
        args.type,
        complexity_initial=args.complexity_initial,
        complexity_review=args.complexity_review,
        delivery_mode=args.delivery_mode,
    )
    report.print_report()
    raise SystemExit(0 if report.success else 1)


if __name__ == "__main__":
    main()
