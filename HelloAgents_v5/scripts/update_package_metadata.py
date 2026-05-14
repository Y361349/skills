#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新 HelloAgents_v5 方案包元信息（why/how/task）。

用途：
- 自动写入/更新方案包的复杂度“初判/复核”与交付模式，支持后续阶段发现影响面变化时回写。
- 元信息写入位置：文件首个 Markdown 标题之后（blockquote 行）。

元信息键（推荐）：
- @pkg_type: implementation|overview
- @complexity_initial: TWEAK|LIGHT|STANDARD|UNKNOWN
- @complexity_review: TWEAK|LIGHT|STANDARD|UNKNOWN
- @delivery_mode: NORMAL|CLOSE_LOOP
- @final_confirm: YES|NO（仅 why.md；YES 表示已收口定稿，执行仅按此口径）

Usage:
    python update_package_metadata.py <package> [--path <project-root>]
        [--pkg-type <implementation|overview>]
        [--complexity-initial <TWEAK|LIGHT|STANDARD|UNKNOWN>]
        [--complexity-review <TWEAK|LIGHT|STANDARD|UNKNOWN>]
        [--delivery-mode <NORMAL|CLOSE_LOOP>]
        [--apply-to <why|how|task|all>] [--dry-run]

Examples:
    python update_package_metadata.py 202602092117_demo --path d:/Project/repo \\
        --complexity-initial LIGHT --complexity-review STANDARD --delivery-mode NORMAL
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import get_plan_path, script_error_handler, setup_encoding, validate_base_path

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

FINAL_CONFIRM_DESC_ZH = {
    "YES": "已收口定稿，仅按此口径执行",
    "NO": "未收口定稿/禁止执行",
}


def _format_meta_line(key: str, value: str) -> str:
    return f"> **@{key}:** {value}"


def _set_metadata_block(content: str, meta: dict[str, str], order: list[str]) -> str:
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

    if heading_idx is None:
        return ("\n".join(meta_lines + [""] + lines)).rstrip() + "\n"

    insert_at = heading_idx + 1
    while insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1

    lines[insert_at:insert_at] = meta_lines + [""]
    return "\n".join(lines).rstrip() + "\n"


def _extract_metadata(content: str, keys: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in content.splitlines():
        m = META_LINE_RE.match(line.lstrip())
        if not m:
            continue
        key = m.group("key")
        if key in keys:
            result[key] = (m.group("value") or "").strip()
    return result


def _normalize_enum(value: str) -> str:
    """
    支持从 `LIGHT（...）` / `LIGHT(...)` 这类带语义说明的值中提取枚举代码。
    """
    raw = (value or "").strip()
    if not raw:
        return ""
    for sep in ("（", "(", " "):
        if sep in raw:
            raw = raw.split(sep, 1)[0].strip()
    return raw.upper()


def _format_complexity_value(level: str) -> str:
    code = _normalize_enum(level)
    desc = COMPLEXITY_DESC_ZH.get(code)
    return f"{code}（{desc}）" if desc else code


def _format_delivery_mode_value(mode: str) -> str:
    code = _normalize_enum(mode)
    desc = DELIVERY_MODE_DESC_ZH.get(code)
    return f"{code}（{desc}）" if desc else code


def _format_final_confirm_value(value: str) -> str:
    code = _normalize_enum(value)
    desc = FINAL_CONFIRM_DESC_ZH.get(code)
    return f"{code}（{desc}）" if desc else code


def _resolve_package_dir(package: str, base_path: str | None) -> Path:
    p = Path(package)
    if p.is_dir():
        return p

    plan_path = get_plan_path(base_path)
    candidate = plan_path / package
    if candidate.is_dir():
        return candidate

    raise ValueError(f"方案包不存在: {package}")


def _update_file(file_path: Path, meta: dict[str, str], order: list[str], dry_run: bool) -> bool:
    original = file_path.read_text(encoding="utf-8")
    updated = _set_metadata_block(original, meta, order)
    if updated == original:
        return False
    if not dry_run:
        file_path.write_text(updated, encoding="utf-8")
    return True


@script_error_handler
def main() -> None:
    setup_encoding()
    parser = argparse.ArgumentParser(description="更新 HelloAgents_v5 方案包元信息（why/how/task）")
    parser.add_argument("package", help="方案包名称（位于 helloagents/plan/ 下）或方案包目录路径")
    parser.add_argument("--path", default=None, help="项目根目录（默认: 当前目录）")
    parser.add_argument(
        "--pkg-type",
        choices=["implementation", "overview"],
        default=None,
        help="覆盖 @pkg_type",
    )
    parser.add_argument(
        "--complexity-initial",
        choices=["TWEAK", "LIGHT", "STANDARD", "UNKNOWN"],
        default=None,
        help="覆盖 @complexity_initial",
    )
    parser.add_argument(
        "--complexity-review",
        choices=["TWEAK", "LIGHT", "STANDARD", "UNKNOWN"],
        default=None,
        help="覆盖 @complexity_review",
    )
    parser.add_argument(
        "--delivery-mode",
        choices=["NORMAL", "CLOSE_LOOP"],
        default=None,
        help="覆盖 @delivery_mode",
    )
    parser.add_argument(
        "--final-confirm",
        choices=["YES", "NO"],
        default=None,
        help="覆盖 @final_confirm（仅 why.md；YES=已收口定稿，允许进入 develop）",
    )
    parser.add_argument(
        "--apply-to",
        choices=["why", "how", "task", "all"],
        default="why",
        help="更新哪些文件（默认仅 why.md）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只计算变更，不写入文件")
    args = parser.parse_args()

    validate_base_path(args.path)
    package_dir = _resolve_package_dir(args.package, args.path)

    changed: list[str] = []

    targets: list[str] = []
    if args.apply_to in ("why", "all"):
        targets.append("why.md")
    if args.apply_to in ("how", "all"):
        targets.append("how.md")
    if args.apply_to in ("task", "all"):
        targets.append("task.md")

    for name in targets:
        fp = package_dir / name
        if not fp.exists():
            raise FileNotFoundError(f"方案包文件不存在: {fp}")

        if name == "why.md":
            original = fp.read_text(encoding="utf-8")
            existing = _extract_metadata(
                original, {"pkg_type", "complexity_initial", "complexity_review", "delivery_mode", "final_confirm"}
            )
            complexity_initial = _normalize_enum(args.complexity_initial or existing.get("complexity_initial") or "UNKNOWN") or "UNKNOWN"
            complexity_review = (
                _normalize_enum(args.complexity_review or existing.get("complexity_review") or "")  # 允许为空走兜底
                or _normalize_enum(args.complexity_initial or existing.get("complexity_initial") or "UNKNOWN")
                or "UNKNOWN"
            )
            delivery_mode = _normalize_enum(args.delivery_mode or existing.get("delivery_mode") or "NORMAL") or "NORMAL"
            pkg_type = (args.pkg_type or existing.get("pkg_type") or "implementation").strip()

            final_confirm_code = _normalize_enum(args.final_confirm or existing.get("final_confirm") or "")
            final_confirm_value = _format_final_confirm_value(final_confirm_code) if final_confirm_code else None

            merged = {
                "pkg_type": pkg_type,
                "complexity_initial": _format_complexity_value(complexity_initial),
                "complexity_review": _format_complexity_value(complexity_review),
                "delivery_mode": _format_delivery_mode_value(delivery_mode),
            }
            order = ["pkg_type", "complexity_initial", "complexity_review", "delivery_mode"]
            if final_confirm_value:
                merged["final_confirm"] = final_confirm_value
                order.append("final_confirm")

            updated = _update_file(fp, merged, order, args.dry_run)
        else:
            # how/task 默认只更新 pkg_type，避免重复信息
            original = fp.read_text(encoding="utf-8")
            existing = _extract_metadata(original, {"pkg_type"})
            pkg_type = args.pkg_type or existing.get("pkg_type")
            meta_simple: dict[str, str] = {"pkg_type": pkg_type} if pkg_type else {}
            updated = _update_file(fp, meta_simple, ["pkg_type"], args.dry_run)

        if updated:
            changed.append(str(fp))

    # 输出简要结果（JSON 不强制，保持脚本易读）
    if args.dry_run:
        print("dry_run=true")
    print(f"package={package_dir}")
    print(f"changed={len(changed)}")
    for p in changed:
        print(f"- {p}")


if __name__ == "__main__":
    main()
