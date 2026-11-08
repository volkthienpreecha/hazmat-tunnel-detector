"""Build a board filesystem without credentials. python3 tools/package_firmware.py motion /tmp/motion"""
import argparse, pathlib,shutil
p=argparse.ArgumentParser();p.add_argument('role',choices=['motion','hazard']);p.add_argument('output');a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1];dest=pathlib.Path(a.output).resolve()
if dest.exists():raise SystemExit('Choose a new output directory, refusing overwrite')
dest.mkdir(parents=True)
shutil.copytree(root/'firmware/shared',dest/'shared',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy(root/'firmware'/a.role/'main.py',dest/'main.py')
shutil.copy(root/'firmware/config.example.json',dest/'config.example.json')
if a.role=='hazard':
    shutil.copytree(root/'dashboard',dest/'dashboard')
    shutil.copy(root/'firmware/hazard/gateway.py',dest/'gateway.py')
print('Packaged',a.role,'to',dest,'; add your ignored config.local.json before uploading')
