"""Fetch official RapidLaTeXOCR release assets with TLS and pinned SHA-256."""
from pathlib import Path
import hashlib
import os
import tempfile
import urllib.request

base = Path('/workspace/pdf-env/latex-models')
base.mkdir(parents=True, exist_ok=True)
hashes = {
    'image_resizer.onnx':'e0b075c39700f64d50400f39c8fc186bbb3b5d84d31864008313f376603aca9d',
    'encoder.onnx':'01bf5dc25539ca0cd5b1bd29296ea495977a6ba5f629dc4178277809d26e5e7d',
    'decoder.onnx':'bd695497bf1b22279b7626f5916c79226e1e244c84355f8da7edfd2d921d0072',
    'tokenizer.json':'1dc27b18d6a518d0d5ff3f4bb7bd98521fe80ad39e5b2a246d4109f1bb9d5019',
}
for name, expected in hashes.items():
    path = base / name
    if path.exists():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, f'Existing model checksum mismatch: {name}'
        print('Model verified:',name)
        continue
    url = 'https://github.com/RapidAI/RapidLaTeXOCR/releases/download/v0.0.0/' + name
    with tempfile.NamedTemporaryFile(dir=base, delete=False) as f:
        temporary = Path(f.name)
        with urllib.request.urlopen(url,timeout=60) as response:
            while block := response.read(1048576):
                f.write(block)
    assert hashlib.sha256(temporary.read_bytes()).hexdigest() == expected, f'Downloaded model checksum mismatch: {name}'
    os.replace(temporary,path)
    print('Model downloaded and verified:',name)
