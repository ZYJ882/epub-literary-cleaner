#!/usr/bin/env python3
"""Extract clean UTF-8 TXT from EPUB 2/3 using navigation and spine order."""
from __future__ import annotations

import argparse
import html
import re
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote
from lxml import etree

SKIP_TOP = {"书籍封面", "制作说明", "内容介绍", "角色图鉴（部分）", "封面", "Cover"}
BLOCK_TAGS = {"p", "div", "section", "article", "blockquote", "li", "h1", "h2", "h3", "h4", "h5", "h6", "pre"}


def clean_space(value: str) -> str:
    value = html.unescape(value.replace("\xa0", " "))
    return re.sub(r"[ \t\r\f\v]+", " ", value).strip()


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def safe_member(name: str) -> str:
    name = unquote(name).replace("\\", "/")
    if name.startswith("/") or any(part == ".." for part in PurePosixPath(name).parts):
        raise ValueError(f"不安全的 EPUB 路径: {name}")
    return name


def parse_container(z: zipfile.ZipFile) -> str:
    root = etree.fromstring(z.read("META-INF/container.xml"))
    nodes = root.xpath("//*[local-name()='rootfile']/@full-path")
    if not nodes:
        raise ValueError("EPUB 缺少 OPF rootfile")
    return safe_member(nodes[0])


def href_join(base: str, href: str) -> str:
    href = unquote(href.split("#", 1)[0])
    return safe_member(str(PurePosixPath(base).joinpath(href)))


def parse_opf(z: zipfile.ZipFile, opf_name: str):
    root = etree.fromstring(z.read(opf_name))
    base = str(PurePosixPath(opf_name).parent)
    manifest = {}
    for item in root.xpath("//*[local-name()='manifest']/*[local-name()='item']"):
        manifest[item.get("id")] = {
            "href": href_join(base, item.get("href", "")),
            "media_type": item.get("media-type", ""),
            "properties": item.get("properties", ""),
        }
    spine = []
    for ref in root.xpath("//*[local-name()='spine']/*[local-name()='itemref']"):
        item = manifest.get(ref.get("idref"))
        if item:
            spine.append(item["href"])
    return root, manifest, spine


def node_label(node) -> str:
    return clean_space("".join(node.xpath("./*[local-name()='navLabel']/*[local-name()='text']/text()")))


def node_href(node) -> str:
    return "".join(node.xpath("./*[local-name()='content']/@src"))


def child_points(node):
    return [x for x in node if etree.QName(x).localname == "navPoint"]


def parse_ncx(raw: bytes):
    root = etree.fromstring(raw)
    nav = root.xpath("//*[local-name()='navMap']")
    return nav[0] if nav else None


def parse_nav(raw: bytes):
    root = etree.fromstring(raw)
    navs = root.xpath("//*[local-name()='nav' and contains(concat(' ', normalize-space(@*[local-name()='type']), ' '), ' toc ')]")
    nav = navs[0] if navs else (root.xpath("//*[local-name()='nav']") or [None])[0]
    if nav is None:
        return []

    def convert(ol):
        result = []
        for li in ol.xpath("./*[local-name()='li']"):
            a = li.xpath("./*[local-name()='a']")
            if not a:
                continue
            link = a[0]
            title = clean_space("".join(link.itertext()))
            children = li.xpath("./*[local-name()='ol']")
            result.append({"title": title, "href": link.get("href", ""), "children": convert(children[0]) if children else []})
        return result

    ol = nav.xpath("./*[local-name()='ol']")
    return convert(ol[0]) if ol else []


def ncx_to_points(nav):
    def convert_one(node):
        return {
            "title": node_label(node),
            "href": node_href(node),
            "children": [convert_one(child) for child in child_points(node)],
        }
    return [convert_one(x) for x in child_points(nav)] if nav is not None else []


def find_nav(z: zipfile.ZipFile, opf_name: str, manifest: dict):
    for item in manifest.values():
        if "nav" in item["properties"].split():
            return "nav", item["href"]
    for item in manifest.values():
        if item["media_type"] == "application/x-dtbncx+xml":
            return "ncx", item["href"]
    names = set(z.namelist())
    for name in names:
        if name.lower().endswith(".ncx"):
            return "ncx", name
    return None, None


def paragraphs(raw: bytes) -> list[str]:
    parser = etree.XMLParser(recover=True, resolve_entities=False, no_network=True)
    root = etree.fromstring(raw, parser=parser)
    body = root.xpath("//*[local-name()='body']")
    if not body:
        return []
    body = body[0]
    blocks = body.xpath(".//*[local-name()='p' or local-name()='div' or local-name()='section' or local-name()='article' or local-name()='blockquote' or local-name()='li' or local-name()='h1' or local-name()='h2' or local-name()='h3' or local-name()='h4' or local-name()='h5' or local-name()='h6' or local-name()='pre']")
    if not blocks:
        blocks = list(body)
    result = []
    for block in blocks:
        text = clean_space("".join(block.itertext()))
        if text and (not result or text != result[-1]):
            result.append(text)
    return result


def strip_leading_title(items: list[str], title: str) -> list[str]:
    target = compact(title)
    while items and compact(items[0]) == target:
        items.pop(0)
    return items


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract clean TXT from EPUB 2/3 navigation")
    ap.add_argument("epub", type=Path)
    ap.add_argument("txt", type=Path)
    ap.add_argument("--include-frontmatter", action="store_true")
    ap.add_argument("--report", type=Path, help="write extraction summary JSON")
    args = ap.parse_args()
    lines = [f"{args.epub.stem}（整理文本）", ""]
    summary = {"input": str(args.epub.resolve()), "navigation": None, "entries": 0, "paragraphs": 0, "skipped": []}
    with zipfile.ZipFile(args.epub) as z:
        names = set(z.namelist())
        if "META-INF/container.xml" not in names:
            raise SystemExit("EPUB 缺少 META-INF/container.xml")
        opf_name = parse_container(z)
        _, manifest, spine = parse_opf(z, opf_name)
        kind, nav_name = find_nav(z, opf_name, manifest)
        if not nav_name:
            raise SystemExit("EPUB 中未找到 EPUB 3 nav 或 EPUB 2 NCX")
        points = parse_nav(z.read(nav_name)) if kind == "nav" else ncx_to_points(parse_ncx(z.read(nav_name)))
        summary["navigation"] = {"type": kind, "path": nav_name}
        base = str(PurePosixPath(nav_name).parent)

        def read_href(href):
            path = safe_member(str(PurePosixPath(base).joinpath(unquote(href.split("#", 1)[0]))))
            if path in names:
                return z.read(path)
            for candidate in names:
                if candidate.endswith("/" + path.lstrip("/")) or candidate == path:
                    return z.read(candidate)
            return None

        def emit(node, depth=0, top=False):
            title = clean_space(node.get("title", ""))
            if not title:
                return
            children = node.get("children", [])
            if top and title in SKIP_TOP and not args.include_frontmatter:
                summary["skipped"].append(title)
                return
            lines.extend(["  " * depth + title, ""])
            if children:
                for child in children:
                    emit(child, depth + 1)
                return
            raw = read_href(node.get("href", ""))
            if raw:
                items = strip_leading_title(paragraphs(raw), title)
                lines.extend(items)
                summary["paragraphs"] += len(items)
            summary["entries"] += 1
            lines.append("")

        for point in points:
            emit(point, 0, True)
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"
        if re.search(r"<[^>]+>", text) or "\ufffd" in text:
            raise SystemExit("生成文本仍包含 HTML/XML 标签或替换字符")
    args.txt.parent.mkdir(parents=True, exist_ok=True)
    args.txt.write_text(text, encoding="utf-8")
    if args.report:
        import json
        args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.txt} ({args.txt.stat().st_size} bytes, {len(text)} chars)")


if __name__ == "__main__":
    main()
