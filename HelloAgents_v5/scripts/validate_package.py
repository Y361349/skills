#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案包验证脚本（why/how/task）

验证项：
- 目录结构与必需文件：why.md / how.md / task.md
- task.md 任务数量与状态分布
- （可选）模板章节存在性（仅做提示/警告，不作为硬失败）

Usage:
    python validate_package.py [--path <base-path>] [package-name]

Examples:
    python validate_package.py
    python validate_package.py --path /project
    python validate_package.py 202501201234_feature
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# 确保能找到同目录下的 utils 模块
sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    get_plan_path,
    get_template_loader,
    script_error_handler,
    setup_encoding,
    validate_base_path,
)

TASK_STATUS = {
    "[ ]": "pending",
    "[√]": "completed",
    "[X]": "failed",
    "[-]": "skipped",
    "[?]": "uncertain",
}

REQUIRED_FILES = ["why.md", "how.md", "task.md"]

TEMPLATE_WHY = "plan-why-template.md"
TEMPLATE_HOW = "plan-how-template.md"
TEMPLATE_TASK = "plan-task-template.md"

META_LINE_RE = re.compile(r"^>\s*\*\*@(?P<key>[a-zA-Z0-9_]+):\*\*\s*(?P<value>.*)\s*$", re.MULTILINE)

COMPLEXITY_ALLOWED = {"TWEAK", "LIGHT", "STANDARD", "UNKNOWN"}
DELIVERY_MODE_ALLOWED = {"NORMAL", "CLOSE_LOOP", "UNKNOWN"}

# 最终执行前“收口定稿”门禁：避免执行阶段仍存在可选/多选/占位符/待确认等不确定性
FINAL_OPTION_MARKERS = [
    # 注意：括号里的“可选/多选”用正则额外检测（覆盖：UX/UI（可选）等变体）
    "可选项",
    "可选附加项",
    "多选",
    "二选一",
]

FINAL_PLACEHOLDER_MARKERS = [
    "path/to/",
    "YYYYMMDDHHMM_<feature>",
    "[功能名称]",
    "[一句话子任务标题]",
    "[具体功能]",
    "[核心功能模块名称]",
    "[次要功能模块名称]",
    "[场景名称]",
    "[场景1名称]",
    "<否|可选|已用",
    "联网：<",
    "时保留；none 时删除",
]

ANGLE_OPTION_RE = re.compile(r"<[^>]*\|[^>]*>")


def _extract_metadata(content: str, keys: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for m in META_LINE_RE.finditer(content or ""):
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


def _has_enum_desc(value: str) -> bool:
    """
    implementation 方案包要求元信息包含中文说明（便于评审可读性与一致性治理）。

    允许格式：
    - STANDARD（跨模块/多路径/架构变化/高风险）
    - STANDARD(跨模块/多路径/架构变化/高风险)
    """
    raw = (value or "").strip()
    if not raw:
        return False
    return bool(re.match(r"^[A-Z_]+\s*[（(]\s*[^）)]+", raw))


def _detect_pkg_type(*contents: str) -> str:
    for content in contents:
        if re.search(r"^>\\s*\\*\\*@pkg_type:\\*\\*\\s*overview\\b", content, re.MULTILINE):
            return "overview"
        if re.search(r"^>\\s*\\*\\*@pkg_type:\\*\\*\\s*implementation\\b", content, re.MULTILINE):
            return "implementation"
    return "implementation"


def parse_tasks(task_content: str) -> dict:
    tasks = {
        "total": 0,
        "by_status": {"pending": 0, "completed": 0, "failed": 0, "skipped": 0, "uncertain": 0},
        "items": [],
    }

    task_pattern = re.compile(r"^[-*]\s*\[([ √X?-])\]\s*(.+)$", re.MULTILINE)
    for match in task_pattern.finditer(task_content):
        status_char = match.group(1)
        description = match.group(2).strip()
        status_key = f"[{status_char}]"
        status = TASK_STATUS.get(status_key, "pending")

        tasks["items"].append({"status": status, "description": description[:120]})
        tasks["total"] += 1
        tasks["by_status"][status] += 1

    return tasks


def _collect_markers(content: str, markers: list[str]) -> list[str]:
    found: list[str] = []
    for m in markers:
        if m and m in (content or ""):
            found.append(m)
    return found


def _final_gate_issues(why_content: str, how_content: str, task_content: str, tasks: dict) -> list[str]:
    issues: list[str] = []

    # 口径锚点章节（用于强制“口径对齐”）
    if "真相源与口径锚点" not in (why_content or ""):
        issues.append("why.md 缺少“真相源与口径锚点”章节（最终执行前必须补齐）")
    if "口径与证据" not in (how_content or ""):
        issues.append("how.md 缺少“口径与证据”章节（最终执行前必须补齐）")

    # 必须显式定稿确认：why.md 元信息 @final_confirm=YES（...）
    final_meta = _extract_metadata(why_content or "", {"final_confirm"})
    raw_final = (final_meta.get("final_confirm") or "").strip()
    final_code = _normalize_enum(raw_final)
    if final_code != "YES":
        issues.append("why.md 缺少元信息 @final_confirm=YES（已收口定稿，仅按此口径执行）")
    elif not _has_enum_desc(raw_final):
        issues.append("why.md 元信息 @final_confirm 缺少中文说明（请写成 YES（已收口定稿，仅按此口径执行））")

    # 不允许存在待确认项
    if "[?]" in (why_content or ""):
        issues.append("why.md 存在待确认标记 [?]（执行前必须清零）")
    if "[?]" in (how_content or ""):
        issues.append("how.md 存在待确认标记 [?]（执行前必须清零）")
    if "[?]" in (task_content or ""):
        issues.append("task.md 存在待确认标记 [?]（执行前必须清零）")

    uncertain_count = 0
    if tasks:
        uncertain_count = int(tasks.get("by_status", {}).get("uncertain", 0) or 0)
    if uncertain_count > 0:
        issues.append(f"task.md 存在 {uncertain_count} 个待确认任务（[?]）")

    # 不允许存在“可选/多选/占位符/多方案未收口”标记
    for label, content in (("why.md", why_content), ("how.md", how_content), ("task.md", task_content)):
        markers = _collect_markers(content or "", FINAL_OPTION_MARKERS + FINAL_PLACEHOLDER_MARKERS)
        for m in markers:
            issues.append(f"{label} 存在未收口标记: {m}")

        if re.search(r"[（(][^）)]*可选[^）)]*[）)]", content or ""):
            issues.append(f"{label} 存在“（...可选...）”可选标记（执行前必须收口删除/改写）")
        if re.search(r"[（(][^）)]*多选[^）)]*[）)]", content or ""):
            issues.append(f"{label} 存在“（...多选...）”多选标记（执行前必须收口删除/改写）")

    if ANGLE_OPTION_RE.search(task_content or ""):
        issues.append("task.md 存在未收口的多选占位符（形如 <A|B|C>），执行前必须替换为唯一值")

    return issues


def _build_final_gate(
    *,
    executable: bool,
    pkg_type: str,
    why_content: str,
    how_content: str,
    task_content: str,
    tasks: dict,
) -> dict:
    if pkg_type == "overview":
        return {"passed": False, "score": 0, "issues": ["overview 方案包不可执行（仅用于共识沉淀）"]}

    issues = _final_gate_issues(why_content, how_content, task_content, tasks)

    score = 10
    # 基础可执行性未达标时，执行评分上限强制降档，避免误判为“可直接执行”
    if not executable:
        score = min(score, 6)

    score = max(0, score - min(len(issues), 10))
    passed = executable and score == 10 and len(issues) == 0
    return {"passed": passed, "score": score, "issues": issues}


def _template_required_sections(template_path: str) -> tuple[list[str], bool]:
    loader = get_template_loader()
    if not loader.exists(template_path):
        return [], True
    return loader.get_required_sections(template_path), False


def _check_required_sections(content: str, template_path: str, label: str) -> tuple[list[str], list[str]]:
    """
    返回 (issues, warnings)。

    章节缺失通常不应阻断（用户可能有意删减），因此默认记为 warnings。
    """
    warnings: list[str] = []
    issues: list[str] = []

    sections, template_missing = _template_required_sections(template_path)
    if template_missing:
        warnings.append(f"模板缺失: {template_path}（已跳过{label}章节提示校验）")
        return issues, warnings

    for section in sections:
        # section 为“核心章节名”（已去除编号与可选标记）
        if section and section not in content:
            warnings.append(f"{label} 缺少章节标题提示: {section}")

    return issues, warnings


def validate_package(package_path: Path, *, require_finalized: bool = False) -> dict:
    result = {
        "name": package_path.name,
        "path": str(package_path),
        "valid": True,
        "executable": True,
        "pkg_type": "implementation",
        "issues": [],
        "warnings": [],
        "files": {"present": [], "missing": []},
        "tasks": None,
        "final_gate": None,
    }

    # 必需文件存在性
    contents: dict[str, str] = {}
    for file_name in REQUIRED_FILES:
        p = package_path / file_name
        if not p.exists():
            result["files"]["missing"].append(file_name)
            result["valid"] = False
            result["executable"] = False
            result["issues"].append(f"缺少必需文件: {file_name}")
            continue

        result["files"]["present"].append(file_name)
        try:
            contents[file_name] = p.read_text(encoding="utf-8")
        except Exception as exc:
            result["valid"] = False
            result["executable"] = False
            result["issues"].append(f"读取失败: {file_name} ({exc})")

    if not result["valid"]:
        return result

    why_content = contents.get("why.md", "")
    how_content = contents.get("how.md", "")
    task_content = contents.get("task.md", "")

    # 包类型
    pkg_type = _detect_pkg_type(why_content, how_content, task_content)
    result["pkg_type"] = pkg_type
    if pkg_type == "overview":
        result["executable"] = False

    # 强制元信息：implementation 类型必须在 why.md 写入复杂度与交付模式
    if pkg_type != "overview":
        meta = _extract_metadata(why_content, {"complexity_initial", "complexity_review", "delivery_mode"})
        missing = [k for k in ("complexity_initial", "complexity_review", "delivery_mode") if not meta.get(k)]
        if missing:
            result["issues"].append(
                "why.md 缺少元信息: "
                + ", ".join([f"@{k}" for k in missing])
                + "（implementation 方案包必须写入复杂度初判/复核与交付模式；可用 update_package_metadata.py 补齐）"
            )
            result["executable"] = False
        else:
            # 元信息必须包含中文说明（如 STANDARD（...））；只要枚举代码为 UNKNOWN 视为未完成评估
            for k in ("complexity_initial", "complexity_review"):
                raw = meta.get(k, "")
                code = _normalize_enum(raw)
                if code and code not in COMPLEXITY_ALLOWED:
                    result["issues"].append(
                        f"why.md 元信息 @{k} 枚举值不合法: {raw}（允许: TWEAK/LIGHT/STANDARD；请用 update_package_metadata.py 统一格式）"
                    )
                    result["executable"] = False
                    continue
                if code.startswith("UNKNOWN"):
                    result["issues"].append(f"why.md 元信息 @{k} 为 UNKNOWN（请在 evaluate/analyze 后复核并更新）")
                    result["executable"] = False
                    continue
                if not _has_enum_desc(raw):
                    result["issues"].append(f"why.md 元信息 @{k} 缺少中文说明（请写成 {code}（...））")
                    result["executable"] = False

            raw_delivery = meta.get("delivery_mode", "")
            delivery_code = _normalize_enum(raw_delivery)
            if delivery_code and delivery_code not in DELIVERY_MODE_ALLOWED:
                result["issues"].append(
                    f"why.md 元信息 @delivery_mode 枚举值不合法: {raw_delivery}（允许: NORMAL/CLOSE_LOOP；请用 update_package_metadata.py 统一格式）"
                )
                result["executable"] = False
            elif delivery_code.startswith("UNKNOWN"):
                result["issues"].append("why.md 元信息 @delivery_mode 为 UNKNOWN（请设置为 NORMAL 或 CLOSE_LOOP）")
                result["executable"] = False
            elif not _has_enum_desc(raw_delivery):
                result["issues"].append(f"why.md 元信息 @delivery_mode 缺少中文说明（请写成 {delivery_code}（...））")
                result["executable"] = False

    # 章节提示校验（非阻断）
    _, warn = _check_required_sections(why_content, TEMPLATE_WHY, "why.md")
    result["warnings"].extend(warn)
    _, warn = _check_required_sections(how_content, TEMPLATE_HOW, "how.md")
    result["warnings"].extend(warn)
    if pkg_type != "overview":
        _, warn = _check_required_sections(task_content, TEMPLATE_TASK, "task.md")
        result["warnings"].extend(warn)

    # 解析 task.md
    result["tasks"] = parse_tasks(task_content)

    if pkg_type != "overview":
        if result["tasks"]["total"] == 0:
            result["issues"].append("task.md 中没有任务项")
            result["executable"] = False

        if result["tasks"]["by_status"]["pending"] == 0:
            if result["tasks"]["by_status"]["completed"] == result["tasks"]["total"] and result["tasks"]["total"] > 0:
                result["warnings"].append("所有任务已完成，建议迁移至 history/")
                result["executable"] = False
            elif result["tasks"]["by_status"]["failed"] > 0:
                result["warnings"].append(f"存在 {result['tasks']['by_status']['failed']} 个失败任务")

    result["final_gate"] = _build_final_gate(
        executable=result["executable"],
        pkg_type=pkg_type,
        why_content=why_content,
        how_content=how_content,
        task_content=task_content,
        tasks=result["tasks"],
    )

    if require_finalized and not result["final_gate"]["passed"]:
        result["executable"] = False
        result["issues"].append(
            "未通过最终收口定稿门禁：执行评分未达 10（请先在 design 阶段收口定稿，并确认 why.md 元信息 @final_confirm=YES）"
        )

    return result


def validate_all_packages(plan_path: Path) -> dict:
    results = {
        "timestamp": datetime.now().isoformat(),
        "plan_path": str(plan_path),
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "executable": 0,
        "packages": [],
    }

    if not plan_path.is_dir():
        return results

    for item in sorted(plan_path.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            pkg_result = validate_package(item)
            results["packages"].append(pkg_result)
            results["total"] += 1
            if pkg_result["valid"]:
                results["valid"] += 1
            else:
                results["invalid"] += 1
            if pkg_result["executable"]:
                results["executable"] += 1

    return results


@script_error_handler
def main() -> None:
    setup_encoding()
    parser = argparse.ArgumentParser(description="验证 HelloAgents_v5 方案包（why/how/task）")
    parser.add_argument("package", nargs="?", help="方案包名称（不指定则验证所有）")
    parser.add_argument("--path", default=None, help="项目根目录（默认: 当前目录）")
    parser.add_argument(
        "--require-finalized",
        action="store_true",
        help="要求通过“最终收口定稿门禁”（执行评分=10）才返回成功退出码（仅对单个方案包校验生效）",
    )
    args = parser.parse_args()

    try:
        validate_base_path(args.path)
    except ValueError as exc:
        print(json.dumps({"error": str(exc), "valid": False}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    plan_path = get_plan_path(args.path)

    if args.package:
        package_path = plan_path / args.package
        if not package_path.is_dir():
            package_path = Path(args.package)

        if package_path.is_dir():
            result = validate_package(package_path, require_finalized=args.require_finalized)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if args.require_finalized:
                passed = bool((result.get("final_gate") or {}).get("passed"))
                raise SystemExit(0 if passed else 1)
            raise SystemExit(0 if result["valid"] else 1)

        print(json.dumps({"error": f"方案包不存在: {args.package}", "valid": False}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    results = validate_all_packages(plan_path)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    raise SystemExit(1 if results["invalid"] > 0 else 0)


if __name__ == "__main__":
    main()
