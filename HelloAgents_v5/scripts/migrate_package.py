#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移 HelloAgents_v5 方案包到 history/

默认迁移路径：
  helloagents/plan/<package>/ → helloagents/history/YYYY-MM/<package>/

同时更新：
  helloagents/history/index.md

Usage:
    python migrate_package.py <package-name> [--path <base-path>] [--status <completed|skipped>] [--all]

Examples:
    python migrate_package.py 202512191430_login
    python migrate_package.py 202512191430_login --status skipped
    python migrate_package.py --all --status skipped
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    ExecutionReport,
    get_history_path,
    get_plan_path,
    get_template_loader,
    get_year_month,
    list_packages,
    parse_package_name,
    script_error_handler,
    setup_encoding,
    validate_base_path,
)

HISTORY_INDEX_TEMPLATE = "history-index-template.md"


def _update_task_status_markers(task_file: Path, status: str) -> None:
    """
    更新 task.md 的状态备注与 checkbox 状态（尽量保守）。

    - completed: 将仍为 [ ] 的任务标记为 [√]
    - skipped: 将所有任务标记为 [-]
    """
    if not task_file.exists():
        return

    content = task_file.read_text(encoding="utf-8")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    status_line = f"> **@status:** {status} | {timestamp}"

    lines = content.split("\n")
    status_pattern = r"^> \\*\\*(?:@status|Status|状态):\\*\\*"
    found = False
    for i, line in enumerate(lines):
        if re.match(status_pattern, line):
            lines[i] = status_line
            found = True
            break

    if not found:
        # 插入到标题后（若不存在标题则插入文件头）
        insert_at = 0
        for i, raw in enumerate(lines):
            if raw.lstrip().startswith("#"):
                insert_at = i + 1
                if insert_at < len(lines) and lines[insert_at].strip() == "":
                    insert_at += 1
                break
        lines.insert(insert_at, status_line)
        lines.insert(insert_at + 1, "")

    # checkbox 处理
    updated: list[str] = []
    checkbox_pattern = re.compile(r"^([-*]\s*)\[([ √X?-])\](\s+.*)$")
    for raw in lines:
        m = checkbox_pattern.match(raw)
        if not m:
            updated.append(raw)
            continue

        prefix, current, suffix = m.group(1), m.group(2), m.group(3)
        if status == "skipped":
            updated.append(f"{prefix}[-]{suffix}")
        elif status == "completed":
            if current == " ":
                updated.append(f"{prefix}[√]{suffix}")
            else:
                updated.append(raw)
        else:
            updated.append(raw)

    task_file.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")


def _ensure_history_index(history_root: Path) -> Path:
    """
    确保 history/index.md 存在；不存在则用模板创建。
    """
    index_file = history_root / "index.md"
    if index_file.exists():
        return index_file

    loader = get_template_loader()
    tpl = loader.load(HISTORY_INDEX_TEMPLATE)
    if tpl is None:
        # 兜底：最小可用结构
        tpl = (
            "# 变更历史索引\n\n"
            "## 索引\n\n"
            "| 时间戳 | 功能名称 | 类型 | 状态 | 方案包路径 |\n"
            "|--------|----------|------|------|------------|\n"
        )

    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(tpl.rstrip() + "\n", encoding="utf-8")
    return index_file


def _update_history_index(history_root: Path, package_name: str, status: str) -> None:
    """
    更新 history/index.md：
    - 索引表插入一行
    - 按月归档追加一条
    """
    parsed = parse_package_name(package_name)
    if parsed:
        timestamp, feature = parsed
    else:
        # 兜底：无法解析则用目录名
        timestamp = package_name[:12]
        feature = package_name

    ym = get_year_month(timestamp) if timestamp.isdigit() and len(timestamp) >= 6 else datetime.now().strftime("%Y-%m")
    status_cell = "✅已完成" if status == "completed" else "[-]未执行"

    index_file = _ensure_history_index(history_root)
    content = index_file.read_text(encoding="utf-8")
    lines = content.split("\n")

    # 1) 表格插入：找到第一条分隔行后插入
    new_row = f"| {timestamp} | {feature} | - | {status_cell} | {ym}/{package_name}/ |"
    insert_pos = None
    for i, line in enumerate(lines):
        if line.startswith("|") and "---" in line:
            insert_pos = i + 1
            break
    if insert_pos is not None:
        lines.insert(insert_pos, new_row)
    else:
        # 找不到表格，追加到末尾
        lines.append("")
        lines.append("| 时间戳 | 功能名称 | 类型 | 状态 | 方案包路径 |")
        lines.append("|--------|----------|------|------|------------|")
        lines.append(new_row)

    # 2) 按月归档：在对应 YYYY-MM 章节下追加
    bullet = f"- [{package_name}]({ym}/{package_name}/) - {status_cell}"
    month_header = f"### {ym}"
    found_month = False
    for i, line in enumerate(lines):
        if line.strip() == month_header:
            # 找到该月，插入到该段落末尾（下一个 ### 或文件末尾前）
            found_month = True
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("### "):
                j += 1
            lines.insert(j, bullet)
            break

    if not found_month:
        # 尝试定位“按月归档”标题
        archive_anchor = None
        for i, line in enumerate(lines):
            if line.strip() in ("## 按月归档", "## 按月归档 "):
                archive_anchor = i
                break
        if archive_anchor is None:
            lines.append("")
            lines.append("## 按月归档")
            lines.append("")
            archive_anchor = len(lines) - 1

        # 在末尾追加该月
        lines.append("")
        lines.append(month_header)
        lines.append("")
        lines.append(bullet)

    index_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def migrate_package(package_path: Path, history_root: Path, status: str = "completed") -> ExecutionReport:
    report = ExecutionReport("migrate_package")
    report.set_context(package_name=package_path.name, source_path=str(package_path), status=status)

    if not package_path.exists():
        report.mark_failed("验证方案包存在", ["迁移方案包"], f"方案包不存在: {package_path}")
        return report

    report.mark_completed("验证方案包存在", str(package_path), "检查源路径是否存在")

    parsed = parse_package_name(package_path.name)
    if parsed:
        timestamp, _ = parsed
        ym = get_year_month(timestamp)
    else:
        ym = datetime.now().strftime("%Y-%m")

    target_dir = history_root / ym
    target_dir.mkdir(parents=True, exist_ok=True)
    report.mark_completed("创建 history/YYYY-MM 目录", str(target_dir), "检查目录存在")

    # 更新 task.md 状态
    task_file = package_path / "task.md"
    try:
        _update_task_status_markers(task_file, status)
        report.mark_completed("更新 task.md 状态", str(task_file), "检查 task.md 中包含 @status 行")
    except Exception as exc:
        report.mark_failed("更新 task.md 状态", ["更新 task.md 状态", "移动方案包", "更新 history/index.md"], str(exc))
        return report

    target_path = target_dir / package_path.name
    try:
        if target_path.exists():
            shutil.rmtree(target_path)
            report.set_context(overwritten=True)
        shutil.move(str(package_path), str(target_path))
        report.set_context(target_path=str(target_path))
        report.mark_completed("移动方案包", str(target_path), "检查目标存在且源已删除")
    except Exception as exc:
        report.mark_failed("移动方案包", ["移动方案包", "更新 history/index.md"], str(exc))
        return report

    try:
        _update_history_index(history_root, package_path.name, status)
        report.mark_completed("更新 history/index.md", str(history_root / "index.md"), "检查索引中包含新记录")
    except Exception as exc:
        report.mark_failed("更新 history/index.md", ["更新 history/index.md"], str(exc))
        return report

    report.mark_success(str(target_path))
    return report


@script_error_handler
def main() -> None:
    setup_encoding()
    parser = argparse.ArgumentParser(description="迁移 HelloAgents_v5 方案包到 history/")
    parser.add_argument("package", nargs="?", help="方案包名称（目录名）")
    parser.add_argument("--path", default=None, help="项目根目录 (默认: 当前目录)")
    parser.add_argument("--status", choices=["completed", "skipped"], default="completed", help="迁移状态")
    parser.add_argument("--all", action="store_true", help="迁移 plan/ 中所有方案包")
    args = parser.parse_args()

    try:
        validate_base_path(args.path)
    except ValueError as exc:
        report = ExecutionReport("migrate_package")
        report.mark_failed("验证基础路径", ["迁移方案包"], str(exc))
        report.print_report()
        raise SystemExit(1)

    plan_path = get_plan_path(args.path)
    history_root = get_history_path(args.path)

    if args.all:
        packages = list_packages(plan_path)
        if not packages:
            report = ExecutionReport("migrate_package")
            report.set_context(mode="all", status=args.status)
            report.mark_success("plan/ 目录为空，无方案包需要迁移")
            report.print_report()
            raise SystemExit(0)

        summary = ExecutionReport("migrate_package")
        summary.set_context(mode="all", status=args.status, total_packages=len(packages))

        success_count = 0
        failed = []
        for pkg in packages:
            pkg_report = migrate_package(pkg["path"], history_root, args.status)
            if pkg_report.success:
                success_count += 1
                summary.mark_completed(f"迁移 {pkg['name']}", pkg_report.context.get("target_path", ""), "检查目标路径存在")
            else:
                failed.append({"name": pkg["name"], "failed_at": pkg_report.failed_at, "error": pkg_report.error_message})

        if failed:
            summary.set_context(success_count=success_count, failed_packages=failed)
            pending = [f"迁移 {p['name']}" for p in failed]
            summary.mark_failed(f"批量迁移（{success_count}/{len(packages)} 成功）", pending, f"{len(failed)} 个方案包迁移失败")
            summary.print_report()
            raise SystemExit(1)

        summary.set_context(success_count=success_count)
        summary.mark_success(f"全部 {success_count} 个方案包迁移完成")
        summary.print_report()
        raise SystemExit(0)

    if not args.package:
        parser.print_help()
        raise SystemExit(1)

    package_path = plan_path / args.package
    if not package_path.exists():
        report = ExecutionReport("migrate_package")
        report.mark_failed("查找方案包", ["迁移方案包"], f"方案包不存在: {package_path}")
        report.print_report()
        raise SystemExit(1)

    report = migrate_package(package_path, history_root, args.status)
    report.print_report()
    raise SystemExit(0 if report.success else 1)


if __name__ == "__main__":
    main()
