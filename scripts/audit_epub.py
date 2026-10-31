#!/usr/bin/env python3
"""Conservative EPUB 2/3 audit report.
Usage: python audit_epub.py input.epub [report.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from lxml import etree


def safe_name(name: str) -> bool:
    p = PurePosixPath(name.replace("\\", "/"))
    return not name.startswith(("/", "\\")) and ".." not in p.parts


def clean_text(raw: bytes) -> str:
    root = etree.fromstring(raw, parser=etree.XMLParser(recover=True, resolve_entities=False, no_network=True))
    body = root.xpath("//*[local-name()='body']")
    return " ".join("".join(body[0].itertext()).split()) if body else ""


def parse(epub: Path) -> dict:
    report = {"input": str(epub.resolve()), "severity": {"error": [], "warning": [], "info": []}, "resources": {}, "spine": [], "navigation": {}}
    with zipfile.ZipFile(epub) as z:
        names = z.namelist()
        if names and names[0] != "mimetype":
            report["severity"]["warning"].append("mimetype 不是 ZIP 首项")
        if "mimetype" not in names:
            report["severity"]["error"].append("缺少 mimetype")
        elif z.read("mimetype").decode("utf-8", "replace") != "application/epub+zip":
            report["severity"]["error"].append("mimetype 内容错误")
        unsafe = [n for n in names if not safe_name(n)]
        if unsafe:
            report["severity"]["error"].append(f"存在不安全 ZIP 路径: {unsafe[:5]}")
        if "META-INF/container.xml" not in names:
            report["severity"]["error"].append("缺少 META-INF/container.xml")
            return report
        container = etree.fromstring(z.read("META-INF/container.xml"))
        roots = container.xpath("//*[local-name()='rootfile']/@full-path")
        if not roots or roots[0] not in names:
            report["severity"]["error"].append("container.xml 指向的 OPF 不存在")
            return report
        opf_name = roots[0]
        opf = etree.fromstring(z.read(opf_name))
        base = str(PurePosixPath(opf_name).parent)
        manifest = {}
        for item in opf.xpath("//*[local-name()='manifest']/*[local-name()='item']"):
            href = str(PurePosixPath(base).joinpath(item.get("href", "").split("#", 1)[0]))
            manifest[item.get("id")] = {"href": href, "media_type": item.get("media-type", ""), "properties": item.get("properties", "")}
            if href not in names:
                report["severity"]["warning"].append(f"manifest 资源不存在: {href}")
        spine = opf.xpath("//*[local-name()='spine']/*[local-name()='itemref']")
        for idx, ref in enumerate(spine, 1):
            item = manifest.get(ref.get("idref"))
            row = {"index": idx, "idref": ref.get("idref"), "href": item["href"] if item else None, "chars": 0, "sha256": None, "start": "", "end": ""}
            if not item:
                report["severity"]["error"].append(f"spine itemref 无对应 manifest: {ref.get('idref')}")
            elif item["href"] in names:
                try:
                    text = clean_text(z.read(item["href"]))
                    row.update(chars=len(text), sha256=hashlib.sha256(text.encode()).hexdigest(), start=text[:120], end=text[-120:])
                except Exception as exc:
                    report["severity"]["warning"].append(f"正文解析失败 {item['href']}: {exc}")
            report["spine"].append(row)
        hashes = {}
        for row in report["spine"]:
            if row["sha256"] and row["chars"] >= 200:
                hashes.setdefault(row["sha256"], []).append(row["index"])
        report["duplicates"] = {"exact_nonadjacent_or_adjacent": [v for v in hashes.values() if len(v) > 1]}
        if report["duplicates"]["exact_nonadjacent_or_adjacent"]:
            report["severity"]["warning"].append("发现正文完全相同的多个 spine 单元，需人工判断是否为制作重复")
        nums = []
        for row in report["spine"]:
            m = re.search(r"第\s*([一二三四五六七八九十百千万零〇两0-9]+)\s*章", row["start"])
            if m:
                nums.append((row["index"], m.group(1)))
        report["chapter_number_candidates"] = nums
        nav_items = [x for x in manifest.values() if "nav" in x["properties"].split() or x["media_type"] == "application/x-dtbncx+xml"]
        report["navigation"] = {"opf": opf_name, "candidates": nav_items, "spine_count": len(spine)}
        report["resources"] = {"files": len(names), "images": sum(1 for n in names if n.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"))), "css": sum(1 for n in names if n.lower().endswith(".css")), "fonts": sum(1 for n in names if n.lower().endswith((".ttf", ".otf", ".woff", ".woff2")))}
    return report


def main():
    ap = argparse.ArgumentParser(description="Audit EPUB structure, navigation, resources and suspicious duplicates")
    ap.add_argument("epub", type=Path)
    ap.add_argument("report", nargs="?", type=Path, default=Path("epub_audit.json"))
    args = ap.parse_args()
    result = parse(args.epub)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.report}")
    for level in ("error", "warning", "info"):
        print(f"{level}: {len(result['severity'][level])}")


if __name__ == "__main__":
    main()
