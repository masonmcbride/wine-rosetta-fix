#!/usr/bin/env python3
"""Export only the tables needed to validate synchronized pilot coverage."""
import argparse,os,subprocess
from pathlib import Path
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('trace',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True);env=os.environ.copy();env['DEVELOPER_DIR']='/Applications/Xcode.app/Contents/Developer'
    for schema in ['os-signpost','displayed-surfaces-interval','thread-state']:
        subprocess.run(['xcrun','xctrace','export','--input',str(a.trace),'--xpath',f'/trace-toc/run[@number="1"]/data/table[@schema="{schema}"]','--output',str(a.output/(schema+'.xml'))],env=env,check=True,timeout=120)
