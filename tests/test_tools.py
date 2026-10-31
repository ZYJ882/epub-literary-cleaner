from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts"


def make_epub(path: Path, epub3: bool):
    nav_name = "OEBPS/nav.xhtml" if epub3 else "OEBPS/toc.ncx"
    nav_item = '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav" />' if epub3 else '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml" />'
    toc_attr = '' if epub3 else ' toc="ncx"'
    if epub3:
        nav = '''<html xmlns="http://www.w3.org/1999/xhtml"><body><nav epub:type="toc" xmlns:epub="http://www.idpf.org/2007/ops"><ol><li><a href="ch1.xhtml">测试卷</a><ol><li><a href="ch1.xhtml">第一章 开始</a></li><li><a href="ch2.xhtml">第二章 继续</a></li></ol></li></ol></nav></body></html>'''
    else:
        nav = '''<ncx xmlns="http://www.daisy.org/z3986/2005/ncx"><navMap><navPoint><navLabel><text>测试卷</text></navLabel><content src="ch1.xhtml"/><navPoint><navLabel><text>第一章 开始</text></navLabel><content src="ch1.xhtml"/></navPoint><navPoint><navLabel><text>第二章 继续</text></navLabel><content src="ch2.xhtml"/></navPoint></navPoint></navMap></ncx>'''
    opf = f'''<package xmlns="http://www.idpf.org/2007/opf" version="{'3.0' if epub3 else '2.0'}"{toc_attr}><manifest><item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/><item id="ch2" href="ch2.xhtml" media-type="application/xhtml+xml"/>{nav_item}</manifest><spine><itemref idref="ch1"/><itemref idref="ch2"/></spine></package>'''
    files = {
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": b'<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>',
        "OEBPS/content.opf": opf.encode(),
        nav_name: nav.encode(),
        "OEBPS/ch1.xhtml": '<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>第一章 开始</h1><p>第一段正文。</p><p>第二段正文。</p></body></html>'.encode(),
        "OEBPS/ch2.xhtml": '<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>第二章 继续</h1><p>第三段正文。</p></body></html>'.encode(),
    }
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", files.pop("mimetype"), compress_type=zipfile.ZIP_STORED)
        for name, data in files.items():
            z.writestr(name, data)


def run_extract(epub, txt):
    subprocess.run([sys.executable, str(SCRIPT / "epub_to_clean_txt.py"), str(epub), str(txt)], check=True)
    return txt.read_text(encoding="utf-8")


def test_epub2_and_epub3(tmp_path):
    for epub3 in (False, True):
        epub = tmp_path / ("book3.epub" if epub3 else "book2.epub")
        txt = tmp_path / ("book3.txt" if epub3 else "book2.txt")
        make_epub(epub, epub3)
        text = run_extract(epub, txt)
        assert "测试卷" in text
        assert "第一章 开始" in text and "第二章 继续" in text
        assert "第一段正文。" in text and "第三段正文。" in text
        assert "<p>" not in text


def test_audit_json(tmp_path):
    epub = tmp_path / "book.epub"
    make_epub(epub, True)
    report = tmp_path / "report.json"
    subprocess.run([sys.executable, str(SCRIPT / "audit_epub.py"), str(epub), str(report)], check=True)
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["resources"]["files"] >= 5
    assert data["navigation"]["candidates"]
    assert not data["severity"]["error"]


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        test_epub2_and_epub3(root)
        test_audit_json(root)
    print("all tests passed")
