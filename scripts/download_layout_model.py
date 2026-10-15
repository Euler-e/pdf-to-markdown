"""Official GitHub asset; hash is from RapidLayout 1.2.1's model registry."""
from pathlib import Path
import hashlib
import os
import tempfile
import urllib.request

p=Path('/workspace/pdf-env/layout-models/doclayout_yolo_docstructbench_imgsz1024.onnx')
expected='3b452baef10ecabd615491bc82cc4d49475fbc2cd7a8e535044f2c6bb28fb9fe'
p.parent.mkdir(exist_ok=True,parents=True)
if p.exists():
    assert hashlib.sha256(p.read_bytes()).hexdigest()==expected, 'Existing layout model checksum mismatch'
else:
    url='https://github.com/RapidAI/RapidLayout/releases/download/v0.0.0/'+p.name
    with tempfile.NamedTemporaryFile(dir=p.parent,delete=False) as f:
        tmp=Path(f.name)
        with urllib.request.urlopen(url,timeout=60) as r:
            while b:=r.read(1048576):f.write(b)
    assert hashlib.sha256(tmp.read_bytes()).hexdigest()==expected, 'Downloaded model checksum mismatch'
    os.replace(tmp,p)
print('DocLayout-YOLO model checksum PASS')
