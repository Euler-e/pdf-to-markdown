"""CPU layout subprocess, isolated because RapidLayout needs NumPy >=2."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
from rapid_layout import RapidLayout
from PIL import Image, ImageDraw

model = Path(sys.argv[3])
assert hashlib.sha256(model.read_bytes()).hexdigest() == '3b452baef10ecabd615491bc82cc4d49475fbc2cd7a8e535044f2c6bb28fb9fe'
engine = RapidLayout(model_type='doclayout_docstructbench', model_dir_or_path=str(model), conf_thresh=0.25, engine_cfg={'intra_op_num_threads':4,'inter_op_num_threads':1,'use_cuda':False})
start = time.perf_counter()
result = engine(sys.argv[1])
items = [{'box':[float(v) for v in b], 'label':str(n), 'score':float(s)} for b,n,s in zip(result.boxes,result.class_names,result.scores)]
items.sort(key=lambda x:(x['box'][1],x['box'][0]))
target = Path(sys.argv[2])
target.write_text(json.dumps({'items':items,'seconds':round(time.perf_counter()-start,3)},ensure_ascii=False,indent=2))
im=Image.open(sys.argv[1]).convert('RGB'); draw=ImageDraw.Draw(im)
for i,item in enumerate(items):
    draw.rectangle(item['box'],outline='red',width=2)
    draw.text(tuple(item['box'][:2]),f"{i}: {item['label']}",fill='blue')
im.save(target.with_suffix('.png'))
print('LAYOUT',sys.argv[1],len(items),'regions',flush=True)
