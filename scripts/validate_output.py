"""Artifact integrity checks, independent of recognizers; no semantic accuracy claim."""
import hashlib,json,re
from pathlib import Path
from PIL import Image
root=Path('output/sample');records=[json.loads(p.read_text()) for p in sorted((root/'pages').glob('[0-9][0-9][0-9][0-9].json'))]
assert len(records)==10
assert {30,40}<={r['pdf_page'] for r in records}
pdf=next(Path('input').glob('*.pdf'));assert hashlib.sha256(pdf.read_bytes()).hexdigest()==json.loads((root/'manifest.json').read_text())['pdf_sha256']
counts={};ids=set()
for r in records:
 assert r['status']=='complete'
 assert any('\u4e00'<=c<='\u9fff' for b in r['blocks'] for c in b.get('text',''))
 for b in r['blocks']:
  assert b['id'] not in ids;ids.add(b['id']);counts[b['label']]=counts.get(b['label'],0)+1
  with Image.open(root/b['image']) as im:assert im.width>0 and im.height>0
  assert len(b['bbox_pdf_points'])==4
  if b['label']=='isolate_formula':assert b['review'] in ('pending','error')
for p in root.rglob('*.md'):
 for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' not in link:assert (p.parent/link.split('#')[0]).exists(),(p,link)
idx=json.loads((root/'keyword-index.json').read_text());assert '参考系' in idx and any('0030.md#' in x for x in idx['参考系'])
print(json.dumps({'integrity':'PASS','pages':len(records),'unique_blocks':len(ids),'labels':counts,'keywords':len(idx)},ensure_ascii=False,indent=2))
