#!/usr/bin/env python3
"""Unified command line entry point for EPUB Literary Cleaner."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_epub import parse as audit_parse
from epub_to_clean_txt import main as extract_main


def audit_command(args):
    result = audit_parse(args.epub)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.report}")
    return 0 if not result["severity"]["error"] else 2


def main():
    parser = argparse.ArgumentParser(prog="epub-cleaner", description="审查 EPUB 或提取干净 TXT")
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="只读审查 EPUB，不修改原文件")
    audit.add_argument("epub", type=Path)
    audit.add_argument("--report", type=Path, default=Path("epub_audit.json"))
    audit.set_defaults(func=audit_command)
    extract = sub.add_parser("extract", help="按 EPUB 2/3 目录提取干净 TXT")
    extract.add_argument("epub", type=Path)
    extract.add_argument("txt", type=Path)
    extract.add_argument("--include-frontmatter", action="store_true")
    extract.add_argument("--report", type=Path)
    extract.set_defaults(func=lambda a: extract_main_with_args(a))
    args = parser.parse_args()
    return args.func(args)


def extract_main_with_args(args):
    import sys
    old = sys.argv
    sys.argv = [old[0], str(args.epub), str(args.txt)]
    if args.include_frontmatter:
        sys.argv.append("--include-frontmatter")
    if args.report:
        sys.argv.extend(["--report", str(args.report)])
    try:
        extract_main()
    finally:
        sys.argv = old
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
