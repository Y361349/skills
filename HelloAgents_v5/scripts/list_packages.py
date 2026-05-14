#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
列出 HelloAGENTS 方案包

Usage:
    python list_packages.py [--path <base-path>] [--history] [--format <table|json>]

Examples:
    python list_packages.py
    python list_packages.py --history
    python list_packages.py --format json
"""

import argparse
import json
import sys
from pathlib import Path

# 确保能找到同目录下的 utils 模块
sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    setup_encoding,
    get_plan_path,
    get_history_path,
    list_packages,
    get_package_summary,
    print_error,
    validate_base_path
)


def print_table(packages: list, title: str):
    """以表格形式打印方案包列表"""
    if not packages:
        print(f"{title}: 空（无方案包）")
        return

    print(f"\n{title} ({len(packages)} 个):")
    print("-" * 80)
    print(f"{'序号':<4} {'名称':<30} {'任务':<6} {'状态':<8} {'摘要':<30}")
    print("-" * 80)

    for i, pkg in enumerate(packages, 1):
        status = "✅完整" if pkg['complete'] else "⚠️不完整"
        try:
            summary = get_package_summary(pkg['path'])
        except Exception:
            summary = "(读取失败)"
        print(f"{i:<4} {pkg['name']:<30} {pkg['task_count']:<6} {status:<8} {summary:<30}")

    print("-" * 80)


def print_json(packages: list):
    """以 JSON 形式打印方案包列表"""
    output = []
    for pkg in packages:
        try:
            summary = get_package_summary(pkg['path'])
        except Exception:
            summary = "(读取失败)"
        output.append({
            'name': pkg['name'],
            'timestamp': pkg['timestamp'],
            'feature': pkg['feature'],
            'complete': pkg['complete'],
            'task_count': pkg['task_count'],
            'path': str(pkg['path']),
            'summary': summary
        })
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main():
    setup_encoding()
    try:
        parser = argparse.ArgumentParser(
            description="列出 HelloAGENTS 方案包"
        )
        parser.add_argument(
            "--path",
            default=None,
            help="项目根目录 (默认: 当前目录)"
        )
        parser.add_argument(
            "--history",
            "--archive",
            action="store_true",
            help="同时列出 history/ 中的方案包（兼容旧参数 --archive）"
        )
        parser.add_argument(
            "--format",
            choices=["table", "json"],
            default="table",
            help="输出格式: table(表格) 或 json"
        )

        args = parser.parse_args()

        # 验证基础路径
        validate_base_path(args.path)

        # 获取 plan/ 方案包
        plan_path = get_plan_path(args.path)
        plan_packages = list_packages(plan_path)

        if args.format == "json":
            result = {'plan': plan_packages}

            if args.history:
                history_path = get_history_path(args.path)
                # 扫描 history 下的所有年月子目录
                history_packages = []
                if history_path.exists():
                    for month_dir in history_path.iterdir():
                        if month_dir.is_dir() and not month_dir.name.startswith('.'):
                            history_packages.extend(list_packages(month_dir))
                result['history'] = history_packages

            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        else:
            print_table(plan_packages, "📦 plan/ 方案包")

            if args.history:
                history_path = get_history_path(args.path)
                if history_path.exists():
                    for month_dir in sorted(history_path.iterdir(), reverse=True):
                        if month_dir.is_dir() and not month_dir.name.startswith('.'):
                            month_packages = list_packages(month_dir)
                            if month_packages:
                                print_table(month_packages, f"📁 history/{month_dir.name}/")

    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        sys.exit(130)
    except PermissionError as e:
        print_error(f"权限不足 - {e}")
        sys.exit(1)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
