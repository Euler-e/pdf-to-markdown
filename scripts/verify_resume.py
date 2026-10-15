"""Verify resume skips completed pages without changing page crops."""
from pathlib import Path
import subprocess,sys
out=Path('output/sample');paths=sorted((out/'assets').glob('*.png'));before={str(p):p.stat().st_mtime_ns for p in paths}
r=subprocess.run([sys.executable,'scripts/convert.py','--pages','14,20,21,29,30,40,80,150,260,350'],capture_output=True,text=True,check=True)
assert r.stdout.count('SKIP ')==10,r.stdout
assert before=={str(p):p.stat().st_mtime_ns for p in paths}
print('PASS: 10 completed pages skipped; source crop timestamps unchanged')
