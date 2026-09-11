#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from training_control.no_trainable_surface_v1 import audit  # noqa:E402
OUT=ROOT/"artifacts"/"training_control"/"no_trainable_surface_v1.json"
def main():
 payload=audit();OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix(OUT.suffix+".tmp");tmp.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8");tmp.replace(OUT);print(json.dumps(payload,indent=2,sort_keys=True));return 0 if payload["complete"] else 2
if __name__=="__main__":raise SystemExit(main())
