#!/usr/bin/env python3
"""R5 synthetic regressions.  Fixtures are never candidate or hardware evidence."""
from __future__ import annotations
import copy, hashlib, json, subprocess, tempfile, unittest
from pathlib import Path
from poc_llm.harness.gate1_r5_projection import command_digest, projection

ROOT=Path(__file__).resolve().parents[3]
LOCK=ROOT/'poc_llm/harness/gate1-lock-v5.json'
VALIDATOR=ROOT/'poc_llm/harness/gate1_r5_validator.py'
GATE2=ROOT/'poc_llm/tools/run_m4b_gate.py'
SELECTOR=ROOT/'poc_llm/tools/select_gate1_finalists_v5.py'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p:Path,value:object)->None:p.write_text(json.dumps(value,sort_keys=True),encoding='utf-8')

class Gate1PacketV5Test(unittest.TestCase):
 def setUp(self)->None:
  self.tmp=tempfile.TemporaryDirectory(prefix='gate1-v5-',dir=ROOT/'poc_llm/tests/gate1'); self.d=Path(self.tmp.name)
  self.files={}
  for name,content in {'x86-runtime':'x86','pi-runtime':'pi','model-x86':'model','model-pi':'model','x86-deps':'deps','pi-deps':'deps','x86-adapter':'adapter','pi-adapter':'adapter'}.items():
   p=self.d/name;p.write_text(content,encoding='utf-8');self.files[name]=p
  logical={'name':'test-runtime','version':'0','source_sha256':sha(self.files['x86-runtime']),'license':'test'}
  platforms={}
  configs={}
  for platform,prefix in [('ubuntu-x86_64','x86'),('pi-debian13-aarch64','pi')]:
   native={'runtime_artifact':{'path':str(self.files[f'{prefix}-runtime']),'sha256':sha(self.files[f'{prefix}-runtime'])},'dependency_bundle':{'path':str(self.files[f'{prefix}-deps']),'sha256':sha(self.files[f'{prefix}-deps'])},'adapter_binding_bundle':{'path':str(self.files[f'{prefix}-adapter']),'sha256':sha(self.files[f'{prefix}-adapter'])},'deployed_model':{'path':str(self.files[f'model-{prefix}']),'sha256':sha(self.files[f'model-{prefix}'])},'install_argv':['true']}
   native['install_argv_sha256']=command_digest(native['install_argv']);platforms[platform]=native
   config={'candidate_id':'CAND-V5-TEST','pairing_revision':'synthetic-r5','platform':platform,'protocol_version':'snowboard.llm/1','driver':'litert_lm','runtime_path':native['runtime_artifact']['path'],'model_path':native['deployed_model']['path'],'runtime_sha256':native['runtime_artifact']['sha256'],'model_sha256':native['deployed_model']['sha256'],'max_input_tokens':128,'max_output_tokens':16,'temperature':0.0,'top_p':1.0,'threads':4,'ready_timeout_ms':10000,'generate_timeout_ms':15000,'cancel_timeout_ms':500,'term_timeout_ms':2000,'kill_timeout_ms':1000,'rebuild_timeout_ms':10000,'runtime_download':False,'network_fallback':False,'fallback_model':None}
   cp=self.d/f'{prefix}-config.json';write(cp,config);configs[platform]={'path':str(cp),'sha256':sha(cp)}
  self.acq={'acquisition_id':'ACQ-V5-TEST','candidate_id':'CAND-V5-TEST','pairing_revision':'synthetic-r5','logical_runtime':logical,'platforms':platforms};self.acq_path=self.d/'acq.json';write(self.acq_path,self.acq)
  commands={key:{'argv':['synthetic-runner',key],'sha256':command_digest(['synthetic-runner',key])} for key in platforms}
  self.manifest={'candidate_id':'CAND-V5-TEST','pairing_revision':'synthetic-r5','logical_runtime':logical,'model':{'name':'model','version':'0','path':str(self.files['model-x86']),'sha256':sha(self.files['model-x86'])},'configs':configs,'quantization':'synthetic','license':'test','offline':True,'acquisition_manifest':{'path':str(self.acq_path),'sha256':sha(self.acq_path)},'commands':commands};self.path=self.d/'candidate.json';write(self.path,self.manifest)
 def tearDown(self)->None:self.tmp.cleanup()
 def test_projection_authenticates_each_platform(self)->None:
  for platform in ('ubuntu-x86_64','pi-debian13-aarch64'):
   value=projection(self.path,LOCK,platform);self.assertEqual(value['config']['platform'],platform)
 def test_missing_extra_legacy_or_reused_configs_are_rejected(self)->None:
  for mutate in (lambda x:x['configs'].pop('ubuntu-x86_64'),lambda x:x.update({'config':{}}),lambda x:x['configs'].update({'extra':{}}),lambda x:x['configs'].update({'pi-debian13-aarch64':copy.deepcopy(x['configs']['ubuntu-x86_64'])})):
   value=copy.deepcopy(self.manifest);mutate(value);p=self.d/f'bad-{len(list(self.d.glob("bad-*.json")))}.json';write(p,value)
   with self.assertRaises(Exception):projection(p,LOCK,'ubuntu-x86_64')
 def test_swapped_config_hash_and_artifact_drift_are_rejected(self)->None:
  value=copy.deepcopy(self.manifest);value['configs']['ubuntu-x86_64']=copy.deepcopy(value['configs']['pi-debian13-aarch64']);p=self.d/'swapped.json';write(p,value)
  with self.assertRaises(Exception):projection(p,LOCK,'ubuntu-x86_64')
  self.files['x86-adapter'].write_text('tampered',encoding='utf-8')
  with self.assertRaises(Exception):projection(self.path,LOCK,'ubuntu-x86_64')
 def test_strict_config_runtime_and_model_drift_are_rejected(self)->None:
  for field,value in [('runtime_path',str(self.files['pi-runtime'])),('model_path',str(self.files['model-pi'])),('model_sha256',sha(self.files['pi-runtime']))]:
   original=json.loads(Path(self.manifest['configs']['ubuntu-x86_64']['path']).read_text(encoding='utf-8'));original[field]=value
   config=self.d/f'{field}-config.json';write(config,original)
   manifest=copy.deepcopy(self.manifest);manifest['configs']['ubuntu-x86_64']['sha256']=sha(config);path=self.d/f'{field}.json';write(path,manifest)
   manifest['configs']['ubuntu-x86_64']['path']=str(config);write(path,manifest)
   with self.assertRaises(Exception):projection(path,LOCK,'ubuntu-x86_64')
 def test_actual_config_hash_drift_is_rejected(self)->None:
  config=Path(self.manifest['configs']['ubuntu-x86_64']['path']);config.write_text('{}',encoding='utf-8')
  with self.assertRaises(Exception):projection(self.path,LOCK,'ubuntu-x86_64')
 def test_forged_r4_result_is_not_r5_selection_evidence(self)->None:
  record=projection(self.path,LOCK,'ubuntu-x86_64');native=record['acquisition']['platforms']['ubuntu-x86_64']
  result={'packet_id':'G1-X86-PI-COMPAT-004','runner_platform':'ubuntu-x86_64','candidate_id':record['manifest']['candidate_id'],'pairing_revision':record['manifest']['pairing_revision'],'result':'PASS','identity':{'lock_sha256':sha(LOCK),'manifest_sha256':record['manifest_sha256'],'acquisition_manifest_sha256':record['acquisition_sha256'],'config_sha256':record['config_sha256'],'runtime_sha256':native['runtime_artifact']['sha256'],'model_sha256':record['manifest']['model']['sha256'],'dependency_bundle_sha256':native['dependency_bundle']['sha256'],'adapter_binding_bundle_sha256':native['adapter_binding_bundle']['sha256'],'command_sha256':record['manifest']['commands']['ubuntu-x86_64']['sha256']},'violations':[]}
  result_path=self.d/'forged-r4.json';write(result_path,result)
  run=subprocess.run(['python3',str(SELECTOR),'--stage','preselect','--selection-cycle-id','G1-CYCLE-V5-TEST','--lock',str(LOCK),'--candidate-manifests',str(self.path),'--x86-results',str(result_path)],cwd=ROOT,text=True,capture_output=True,check=False)
  self.assertEqual(run.returncode,2,run.stdout+run.stderr)
 def test_r5_self_test_and_gate2_carry_over_guard(self)->None:
  run=subprocess.run(['python3',str(VALIDATOR),'--lock',str(LOCK),'--catalog','poc_llm/fixtures/gate1/gate1-r5-catalog.json','--self-test'],cwd=ROOT,text=True,capture_output=True,check=False);self.assertEqual(run.returncode,0,run.stdout+run.stderr)
  guard=subprocess.run(['python3',str(GATE2),'--gate','2A','--cases','P1,P2,P3,P4,P5,P6,P7,P8,P10A,P11,P12','--plan-only','--source-packet-id','G1-X86-PI-COMPAT-005','--run-id','G1-PI-R5-SYNTHETIC','--evidence-namespace','evidence/gate1/r5'],cwd=ROOT,text=True,capture_output=True,check=False);self.assertEqual(guard.returncode,1,guard.stdout+guard.stderr)
if __name__=='__main__':unittest.main()
