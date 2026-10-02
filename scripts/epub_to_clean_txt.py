#!/usr/bin/env python3
"""Extract a clean UTF-8 TXT from an EPUB using its NCX hierarchy and spine order."""
from __future__ import annotations
import argparse, html, re, zipfile
from pathlib import Path
from urllib.parse import unquote
from lxml import etree

SKIP_TOP = {"书籍封面", "制作说明", "内容介绍", "角色图鉴（部分）", "封面", "Cover"}

def text_of(node):
    return "".join(node.itertext())

def clean_space(s: str) -> str:
    return " ".join(s.replace("\xa0", " ").split())

def compact(s: str) -> str:
    return re.sub(r"\s+", "", s)

def node_label(node) -> str:
    return clean_space("".join(node.xpath("./*[local-name()='navLabel']/*[local-name()='text']/text()")))

def node_href(node) -> str:
    return unquote("".join(node.xpath("./*[local-name()='content']/@src")).split("#", 1)[0])

def child_points(node):
    return [x for x in node if etree.QName(x).localname == "navPoint"]

def body_paragraphs(raw: bytes) -> list[str]:
    root = etree.fromstring(raw)
    body = root.xpath("//*[local-name()='body']")
    if not body:
        return []
    out = []
    for el in body[0]:
        s = clean_space(text_of(el))
        if s:
            out.append(s)
    return out

def strip_leading_title(paras: list[str], title: str) -> list[str]:
    # XHTML conversions commonly put the same chapter title in two headings.
    t = compact(title)
    while paras and compact(paras[0]) == t:
        paras.pop(0)
    return paras

def main() -> None:
    ap = argparse.ArgumentParser(description="Extract clean TXT from an EPUB using its original NCX hierarchy")
    ap.add_argument("epub", type=Path)
    ap.add_argument("txt", type=Path)
    ap.add_argument("--include-frontmatter", action="store_true", help="include cover/production/intro/character pages when they contain text")
    args = ap.parse_args()
    lines = [f"{args.epub.stem}（整理文本）", ""]
    with zipfile.ZipFile(args.epub) as z:
        names = set(z.namelist())
        ncx_name = next((n for n in names if n.lower().endswith(".ncx")), None)
        if not ncx_name:
            raise SystemExit("EPUB 中未找到 NCX 目录文件")
        ncx = etree.fromstring(z.read(ncx_name))
        nav = ncx.xpath("//*[local-name()='navMap']")
        if not nav:
            raise SystemExit("NCX 中未找到 navMap")
        nav = nav[0]
        # EPUB2 NCX hrefs are relative to the OPF directory; locate the OEBPS path from the href.
        def read_href(href: str):
            candidates = [href, "OEBPS/" + href]
            for c in candidates:
                if c in names:
                    return z.read(c)
            # Find by suffix for books whose OPF is in a named directory.
            suffix = "/" + href.lstrip("/")
            for n in names:
                if n.endswith(suffix):
                    return z.read(n)
            return None
        def emit_chapter(node):
            title = node_label(node)
            if not title:
                return
            lines.extend([title, ""])
            raw = read_href(node_href(node))
            if raw:
                ps = strip_leading_title(body_paragraphs(raw), title)
                lines.extend(ps)
            lines.append("")
        for top in [x for x in nav if etree.QName(x).localname == "navPoint"]:
            title = node_label(top)
            children = child_points(top)
            is_volume = title.startswith("龙族") or bool(children)
            if title in SKIP_TOP and not args.include_frontmatter:
                continue
            if is_volume and children:
                lines.extend([title, ""])
                for child in children:
                    emit_chapter(child)
                continue
            if title == "致各位亲爱的读者" or args.include_frontmatter:
                emit_chapter(top)
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"
        if re.search(r"<[^>]+>", text):
            raise SystemExit("生成文本仍包含 HTML/XML 标签")
    args.txt.parent.mkdir(parents=True, exist_ok=True)
    args.txt.write_text(text, encoding="utf-8")
    print(f"wrote {args.txt} ({args.txt.stat().st_size} bytes, {len(text)} chars)")

if __name__ == "__main__":
    main()
