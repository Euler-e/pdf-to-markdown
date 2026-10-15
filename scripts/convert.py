"""Resumable scan conversion. PDF page numbers are one-based; never edits source."""
import argparse, hashlib, json, os, re, subprocess, sys, traceback
from pathlib import Path
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
import pymupdf
import numpy as np
import jieba
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
from rapid_latex_ocr import LaTeXOCR

def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');t.replace(p)
def pages(spec):
    result=set()
    for part in spec.split(','):
        v=list(map(int,part.split('-')))
        if len(v)==1: result.add(v[0])
        elif len(v)==2 and v[0]<=v[1]:result.update(range(v[0],v[1]+1))
        else:raise ValueError('Invalid range')
    return sorted(result)
def main():
    a=argparse.ArgumentParser();a.add_argument('--pdf',type=Path,default=next(Path('input').glob('*.pdf')));a.add_argument('--pages',required=True);a.add_argument('--output',type=Path,default=Path('output/sample'));a.add_argument('--env',type=Path,default=Path('/workspace/pdf-env'));a.add_argument('--dpi',type=int,default=240);a.add_argument('--batch-size',type=int,default=10);a.add_argument('--force',action='store_true');args=a.parse_args()
    nums=pages(args.pages);doc=pymupdf.open(args.pdf)
    if not nums or min(nums)<1 or max(nums)>len(doc) or args.batch_size<1:raise ValueError('Invalid pages/batch size')
    out=args.output;out.mkdir(parents=True,exist_ok=True);(out/'pages').mkdir(exist_ok=True);(out/'assets').mkdir(exist_ok=True)
    sha=hashlib.sha256(args.pdf.read_bytes()).hexdigest(); config={'pdf_sha256':sha,'dpi':args.dpi,'schema':1}
    manifest=out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text())!=config:raise ValueError('Output config mismatch; use another output directory')
    save(manifest,config)
    toc=[{'level':l,'title':t.encode('utf-8','surrogateescape').decode('utf-8','ignore').replace('\x00',''),'pdf_page':p} for l,t,p in doc.get_toc()]
    save(out/'toc.json',toc)
    ocr=RapidOCR(intra_op_num_threads=4,inter_op_num_threads=1)
    m=args.env/'latex-models';latex=LaTeXOCR(image_resizer_path=m/'image_resizer.onnx',encoder_path=m/'encoder.onnx',decoder_path=m/'decoder.onnx',tokenizer_json=m/'tokenizer.json')
    for batch in range(0,len(nums),args.batch_size):
      for n in nums[batch:batch+args.batch_size]:
        state=out/'pages'/f'{n:04}.json'
        if state.exists() and json.loads(state.read_text()).get('status')=='complete' and not args.force:print('SKIP',n,flush=True);continue
        record={'pdf_page':n,'status':'processing','errors':[],'blocks':[],'printed_page':None,'printed_page_status':'unverified'};save(state,record)
        try:
          page=doc[n-1];pix=page.get_pixmap(dpi=args.dpi);im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
          image=out/'assets'/f'p{n:04}.png';im.save(image);record['page_image']=str(image.relative_to(out))
          layout=out/'pages'/f'{n:04}-layout.json'
          subprocess.run([str(args.env/'layout-venv/bin/python'),str(Path(__file__).with_name('detect_layout.py')),str(image),str(layout),str(args.env/'layout-models/doclayout_yolo_docstructbench_imgsz1024.onnx')],check=True,timeout=180)
          items=json.loads(layout.read_text())['items']
          for i,b in enumerate(items):
            box=b['box'];crop=im.crop((max(0,int(box[0])-4),max(0,int(box[1])-4),min(im.width,int(box[2])+5),min(im.height,int(box[3])+5)))
            ident=f'p{n:04}-b{i:03}';path=out/'assets'/f'{ident}.png';crop.save(path)
            block={**b,'id':ident,'image':str(path.relative_to(out)),'bbox_pdf_points':[box[j]*([page.rect.width,page.rect.height][j%2])/([im.width,im.height][j%2]) for j in range(4)]}
            try:
              if b['label']=='isolate_formula':
                block['latex']=latex(np.array(crop))[0];block['review']='pending';block['warning']='Machine candidate; never verified'
              else:
                result,_=ocr(np.array(crop));block['lines']=[{'box':x[0],'text':x[1],'confidence':float(x[2])} for x in (result or [])];block['text']='\n'.join(x['text'] for x in block['lines'])
                if any(x['confidence']<.85 for x in block['lines']):record['errors'].append({'block':ident,'type':'low_ocr_confidence'})
            except Exception as e:record['errors'].append({'block':ident,'type':'recognition','message':str(e)});block['review']='error'
            record['blocks'].append(block)
          # Header page number is only a candidate until visually checked.
          header=[x for b in record['blocks'] if b['box'][1]<im.height*.13 for x in b.get('lines',[]) if re.fullmatch(r'\d{1,3}',x['text'].strip())]
          record['printed_page_candidates']=[x['text'] for x in header]
          record['status']='complete';save(state,record);print('DONE',n,len(items),flush=True)
        except Exception as e:
          record['status']='failed';record['errors'].append({'type':'page','message':str(e),'traceback':traceback.format_exc()});save(state,record);print('FAILED',n,str(e),flush=True)
    build(out,toc)

def unique_blocks(blocks):
    kept=[]
    for b in sorted(blocks,key=lambda b:b['score'],reverse=True):
      a=b['box'];duplicate=False
      for k in kept:
        c=k['box'];inter=max(0,min(a[2],c[2])-max(a[0],c[0]))*max(0,min(a[3],c[3])-max(a[1],c[1]))
        union=(a[2]-a[0])*(a[3]-a[1])+(c[2]-c[0])*(c[3]-c[1])-inter
        if union and inter/union>.8:duplicate=True;break
      if not duplicate:kept.append(b)
    return sorted(kept,key=lambda b:(b['box'][1],b['box'][0]))

def build(out,toc):
    block_annotations=json.loads((out/'block-annotations.json').read_text()) if (out/'block-annotations.json').exists() else {}
    annotations=json.loads((out/'annotations.json').read_text()) if (out/'annotations.json').exists() else {}
    records=[json.loads(p.read_text()) for p in sorted((out/'pages').glob('[0-9][0-9][0-9][0-9].json'))];groups={};keywords={};reviews=[];mapping=[]
    for r in records:
      n=r['pdf_page'];r.update(annotations.get(str(n),{}));save(out/'pages'/f'{n:04}.json',r);chapter=next((t for t in reversed(toc) if t['level']==1 and t['pdf_page']<=n),{'title':'前置内容','pdf_page':1});key=f"{chapter['pdf_page']:04}";groups.setdefault(key,{'title':chapter['title'],'pages':[]})['pages'].append(n)
      sections=[t for t in toc if t['pdf_page']<=n and t['level']>1];section=sections[-1]['title'] if sections else ''
      md=f'<a id="pdf-{n}"></a>\n\n# PDF 第 {n} 页\n\n章节：{chapter["title"]}；节：{section}。印刷页码：{r.get("printed_page") or "待核对"}。\n\n[原页截图](../{r.get("page_image", "")})。文字和 LaTeX 为机器识别，引用前请核对原图。\n\n'
      for b in unique_blocks(r['blocks']):
        md+=f'<a id="{b["id"]}"></a>\n\n'
        note=block_annotations.get(b['id'],{})
        if note.get('verified_number'):md+=f'原书公式编号（人工核对）：{note["verified_number"]}\n\n'
        if note.get('finding'):md+=f'复核记录：{note["finding"]}\n\n'
        if b['label']=='isolate_formula':
          md+='**公式待复核**\n\n$$\n'+b.get('latex','')+'\n$$\n\n';reviews.append({'pdf_page':n,'block':b['id'],'latex':b.get('latex'),'image':b['image'],'status':b.get('review'),'manual_check':note})
        elif b['label'] in ('figure','table'):md+=f'**{b["label"]}：原图保留，表格未重建**\n\n'+b.get('text','')+'\n\n'
        else:md+=('## ' if b['label']=='title' else '')+b.get('text','')+'\n\n'
        # Every region retains a crop, including inline math in body paragraphs.
        md+=f'[区域原图](../{b["image"]})\n\n' if b['label'] not in ('figure','table') else f'![{b["id"]}](../{b["image"]})\n\n'
        for word in set(w for w in jieba.cut(b.get('text','')) if len(w)>1 and re.search(r'[\u4e00-\u9fff]',w)):keywords.setdefault(word,[]).append(f'pages/{n:04}.md#{b["id"]}')
      (out/'pages'/f'{n:04}.md').write_text(md,encoding='utf-8');mapping.append({k:r.get(k) for k in ('pdf_page','printed_page','printed_page_status','printed_page_candidates','status')})
    chapters=out/'chapters';chapters.mkdir(exist_ok=True)
    for k,g in groups.items():
      merged=f'# {g["title"]}\n\n> 非连续样本；缺页不补写。\n\n'
      for n in g['pages']:merged+=(out/'pages'/f'{n:04}.md').read_text().replace('(../assets/','(../assets/')+'\n'
      (chapters/f'{k}.md').write_text(merged,encoding='utf-8')
    save(out/'page-map.json',mapping);save(out/'keyword-index.json',keywords)
    report=out.parent/'reports';report.mkdir(exist_ok=True);save(report/'formula-review.json',reviews);save(report/'errors.json',[{'pdf_page':r['pdf_page'],'errors':r['errors']} for r in records]);save(report/'summary.json',{'pages':len(records),'complete':sum(r['status']=='complete' for r in records),'formula_candidates':len(reviews),'all_formulas_unverified':True})
    (out/'README.md').write_text('# 教材样本检索入口\n\n引用格式：原书章节、印刷页码（已核对时）、PDF 第 N 页、区域 ID。公式候选不可直接作为可靠答案；须核对截图。正文区域截图同时保留行内公式。\n\n'+ '\n'.join(f'- [{g["title"]}](chapters/{k}.md)：PDF '+', '.join(map(str,g['pages'])) for k,g in groups.items())+'\n\n- [原书目录](toc.json)\n- [页码映射](page-map.json)\n- [关键词索引](keyword-index.json)\n',encoding='utf-8')
if __name__=='__main__':main()
