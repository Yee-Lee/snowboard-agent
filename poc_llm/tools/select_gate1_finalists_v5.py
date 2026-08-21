#!/usr/bin/env python3
"""R5 selector: platform identity is authenticated before ranking or finalization."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from poc_llm.harness.gate1_r5_projection import digest, load, locked, projection
def expected_identity(record, lock_path, platform):
 native=record['acquisition']['platforms'][platform]
 return {'lock_sha256':digest(lock_path),'manifest_sha256':record['manifest_sha256'],'acquisition_manifest_sha256':record['acquisition_sha256'],'config_sha256':record['config_sha256'],'runtime_sha256':native['runtime_artifact']['sha256'],'model_sha256':record['manifest']['model']['sha256'],'dependency_bundle_sha256':native['dependency_bundle']['sha256'],'adapter_binding_bundle_sha256':native['adapter_binding_bundle']['sha256'],'command_sha256':record['manifest']['commands'][platform]['sha256']}
def require_result_identity(result, record, lock_path, platform):
 if result['runner_platform'] != platform: raise ValueError('cross-platform result identity')
 expected=expected_identity(record,lock_path,platform)
 if any(result['identity'].get(key) != value for key,value in expected.items()): raise ValueError('result identity mismatch')
def main() -> int:
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=('preselect','final'),required=True);p.add_argument('--selection-cycle-id',required=True);p.add_argument('--lock',type=Path,required=True);p.add_argument('--candidate-manifests',type=Path,nargs='+',required=True);p.add_argument('--x86-results',type=Path,nargs='+',required=True);p.add_argument('--pi-results',type=Path,nargs='*',default=[]);a=p.parse_args()
 try:
  paths=locked(load(a.lock)); schema=load(paths['run_result_schema']); records={}
  for path in a.candidate_manifests:
   value=projection(path,a.lock,'ubuntu-x86_64'); records[(value['manifest']['candidate_id'],value['manifest']['pairing_revision'])]=value
  pre=[]
  for path in a.x86_results:
   result=load(path);jsonschema.validate(result,schema);key=(result['candidate_id'],result['pairing_revision']);record=records.get(key)
   if not record: raise ValueError('x86 result has no candidate projection')
   require_result_identity(result,record,a.lock,'ubuntu-x86_64')
   if result['result']=='PASS': pre.append({'candidate_id':key[0],'pairing_revision':key[1]})
  pre=sorted(pre,key=lambda x:(x['candidate_id'],x['pairing_revision']))[:2]
  final=[]
  if a.stage=='final':
   allowed={(x['candidate_id'],x['pairing_revision']) for x in pre}
   for path in a.pi_results:
    result=load(path);jsonschema.validate(result,schema);key=(result['candidate_id'],result['pairing_revision'])
    if key not in allowed: raise ValueError('third-candidate backfill')
    pi=projection(next(p for p in a.candidate_manifests if load(p)['candidate_id']==key[0]),a.lock,'pi-debian13-aarch64')
    require_result_identity(result,pi,a.lock,'pi-debian13-aarch64')
    if result['result']=='PASS': final.append({'candidate_id':key[0],'pairing_revision':key[1]})
  out={'packet_id':'G1-X86-PI-COMPAT-005','selection_cycle_id':a.selection_cycle_id,'stage':'PRESELECTION' if a.stage=='preselect' else 'FINAL','result':'PRESELECTED' if a.stage=='preselect' and pre else ('PASS' if final else 'FAIL'),'preselected_candidates':pre,'proposed_finalists':final,'max_two_enforced':True,'backfill_forbidden':True,'gate2_credit':False,'violations':[]};jsonschema.validate(out,load(paths['selection_schema']));print(json.dumps(out,sort_keys=True,separators=(',',':')));return 0 if out['result'] in ('PRESELECTED','PASS') else 1
 except Exception as e: print(json.dumps({'packet_id':'G1-X86-PI-COMPAT-005','result':'INCONCLUSIVE','violations':[str(e)]},sort_keys=True,separators=(',',':')));return 2
if __name__=='__main__': raise SystemExit(main())
