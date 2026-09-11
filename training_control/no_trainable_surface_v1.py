#!/usr/bin/env python3
"""Fail closed if Silicon-Pilot gains an authored optimizer/model trainer."""
from __future__ import annotations
import ast,re
from dataclasses import asdict,dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];EXCLUDED={".git",".training_control","node_modules","__pycache__",".venv","venv","build","dist","target"};SELF={"run_all_training.py","training_control/no_trainable_surface_v1.py","scripts/audit_no_trainable_surface_v1.py"}
ATTRS={"fit","partial_fit","fit_generator","train_on_batch","backward","manual_backward","training_step","optimizer_step"};NAMES={"Trainer","Seq2SeqTrainer","TrainingArguments","SGD","Adam","AdamW","Adagrad","Adadelta","RMSprop","LBFGS","SparseAdam"};PREFIX=("torch.optim","tensorflow.keras.optimizers","keras.optimizers","pytorch_lightning","lightning.pytorch")
TEXT=(re.compile(r"\b(?:torch\.optim|tf\.train|tensorflow\.keras\.optimizers)\b",re.I),re.compile(r"\bmodel\.(?:fit|train_on_batch)\s*\(",re.I),re.compile(r"\.(?:backward|manual_backward)\s*\(",re.I))
@dataclass(frozen=True,slots=True)
class Finding:path:str;line:int;kind:str;symbol:str
class Scan(ast.NodeVisitor):
 def __init__(self,p):self.p=p;self.rows=[]
 def add(self,n,k,s):self.rows.append(Finding(self.p.relative_to(ROOT).as_posix(),int(getattr(n,"lineno",0) or 0),k,s))
 def visit_Import(self,n):
  for a in n.names:
   if a.name.startswith(PREFIX):self.add(n,"training_import",a.name)
  self.generic_visit(n)
 def visit_ImportFrom(self,n):
  m=n.module or ""
  if m.startswith(PREFIX):self.add(n,"training_import",m)
  for a in n.names:
   if a.name in NAMES:self.add(n,"training_symbol_import",f"{m}.{a.name}".strip("."))
  self.generic_visit(n)
 def visit_Call(self,n):
  f=n.func
  if isinstance(f,ast.Attribute) and f.attr in ATTRS:self.add(n,"training_call",f.attr)
  elif isinstance(f,ast.Name) and f.id in NAMES:self.add(n,"training_constructor",f.id)
  self.generic_visit(n)
def audit():
 rows=[];errors=[];files=[]
 for p in sorted(ROOT.rglob("*")):
  if not p.is_file():continue
  r=p.relative_to(ROOT)
  if r.as_posix() in SELF or any(x in EXCLUDED for x in r.parts):continue
  if p.suffix==".py":
   files.append(r.as_posix())
   try:t=ast.parse(p.read_text(encoding="utf-8",errors="replace"),filename=str(p))
   except SyntaxError as e:errors.append({"path":r.as_posix(),"line":int(e.lineno or 0),"message":str(e)});continue
   s=Scan(p);s.visit(t);rows.extend(s.rows)
  elif p.suffix.lower() in {".js",".jsx",".ts",".tsx",".rs",".go",".cpp",".cc",".c",".h",".hpp"}:
   files.append(r.as_posix());text=p.read_text(encoding="utf-8",errors="replace")
   for pat in TEXT:
    for m in pat.finditer(text):rows.append(Finding(r.as_posix(),text.count("\n",0,m.start())+1,"text_training_primitive",m.group(0)))
 unresolved=[]
 if errors:unresolved.append({"type":"parse_errors","values":errors})
 if rows:unresolved.append({"type":"retained_training_primitives_detected","values":[asdict(x) for x in rows]})
 return {"schema_version":1,"repository":"Anurag9000/Silicon-Pilot","classification":"silicon_eda_system_without_authored_ml_training" if not unresolved else "training_surface_detected","scanned_source_files":files,"findings":[asdict(x) for x in rows],"parse_errors":errors,"unresolved":unresolved,"complete":not unresolved,"source_configuration_only":True,"training_executed_by_audit":False}
