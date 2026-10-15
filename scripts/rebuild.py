"""Regenerate chapter/index/report artifacts without re-running OCR."""
from pathlib import Path
import json
from convert import build
out=Path('output/sample')
build(out,json.loads((out/'toc.json').read_text()))
