#!/usr/bin/env python3
"""Create a conservative JSON audit report for an EPUB spine.
Usage: python audit_epub.py input.epub [report.json]
"""
import sys, json, zipfile, re, hashlib
from pathlib import Path
from lxml import etree

def main(epub, out):
    root=Path('/tmp/epub-literary-audit'); import shutil; shutil.rmtree(root,ignore_errors=True); root.mkdir()
    with zipfile.ZipFile(epub) as z: z.extractall(root)
    container=etree.parse(str(root/'META-INF/container.xml')); opf_rel=container.xpath('//*[local-name()="rootfile"]')[0].get('full-path'); opf_path=root/opf_rel
    opf=etree.parse(str(opf_path)); base=opf_path.parent; man={x.get('id'):x for x in opf.xpath('//*[local-name()="manifest"]/*[local-name()="item"]')}; rows=[]
    for n,ref in enumerate(opf.xpath('//*[local-name()="spine"]/*[local-name()="itemref"]'),1):
        it=man.get(ref.get('idref')); ifile=base/it.get('href') if it is not None else None
        text='';
        if ifile and ifile.exists():
            try:
                doc=etree.parse(str(ifile),etree.XMLParser(recover=True)); text=' '.join(''.join(doc.xpath('//*[local-name()="body"]')[0].itertext()).split())
            except Exception: pass
        rows.append({'spine_index':n,'idref':ref.get('idref'),'href':it.get('href') if it is not None else None,'chars':len(text),'sha256':hashlib.sha256(text.encode()).hexdigest(),'start':text[:120],'end':text[-120:]})
    report={'epub':str(Path(epub).resolve()),'spine_count':len(rows),'nonempty':sum(x['chars']>0 for x in rows),'rows':rows,'adjacent_exact_duplicates':[]}
    for a,b in zip(rows,rows[1:]):
        if a['chars'] and a['sha256']==b['sha256']: report['adjacent_exact_duplicates'].append([a['spine_index'],b['spine_index']])
    Path(out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); print(out)
if __name__=='__main__':
    if len(sys.argv)<2: raise SystemExit('usage: audit_epub.py input.epub [report.json]')
    main(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else 'epub_audit.json')
