"""Prepare immutable M1 native fixtures in the Core-selected delivery PCM format."""
from __future__ import annotations
import argparse, json, wave
from pathlib import Path
from .fixture_recorder import build_capture_items, load_plan, read_manifest, sha256_file
from .option_a_conversion import OptionAStreamConverter, ValidBitMapping

MANIFEST_NAME = "delivered_fixture_manifest.json"

def prepare(plan_path: Path, source_dir: Path, output_dir: Path) -> dict:
    plan=load_plan(plan_path); plan["_path"]=str(plan_path)
    native=read_manifest(source_dir/"fixture_manifest.json",plan)
    output_dir.mkdir(parents=True,exist_ok=True); records={}
    for item in build_capture_items(plan):
        source=source_dir/native["records"][item.fixture_id]["file"]
        with wave.open(str(source),"rb") as w:
            if (w.getframerate(),w.getnchannels(),w.getsampwidth()) != (48000,2,4): raise ValueError(f"invalid native WAV: {item.fixture_id}")
            payload=w.readframes(w.getnframes())
        converter=OptionAStreamConverter(ValidBitMapping(channel_index=0,valid_bits=24,alignment="left"))
        pcm=b"".join(converter.feed(payload))+converter.flush().partial_pcm
        expected=len(payload)//8//3
        if len(pcm)!=expected*2: raise ValueError(f"unexpected output length: {item.fixture_id}")
        destination=output_dir/f"{item.fixture_id}.wav"
        with wave.open(str(destination),"wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(pcm)
        records[item.fixture_id]={"file":destination.name,"native_sha256":sha256_file(source),"derived_sha256":sha256_file(destination),"metadata":{"sample_rate_hz":16000,"channels":1,"sample_width_bytes":2,"frames":expected,"duration_seconds":round(expected/16000,3)}}
    result={"schema_version":"1.0","preparer_id":"m1-option-a-delivery-v1","plan_id":plan["plan_id"],"native_manifest_sha256":sha256_file(source_dir/"fixture_manifest.json"),"mapping":{"channel_index":0,"valid_bits":24,"alignment":"left"},"resampler":{"library":"samplerate","converter_type":"sinc_best","ratio":"1:3","stateful":True},"delivered_pcm":{"sample_rate_hz":16000,"channels":1,"sample_format":"S16_LE"},"records":records}
    (output_dir/MANIFEST_NAME).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    return {"result":"PASS","valid_files":len(records),"manifest_sha256":sha256_file(output_dir/MANIFEST_NAME)}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--source-dir",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); p.add_argument("--plan",type=Path,default=Path("poc_audio/fixtures/authorized/recording_plan_v1.json")); a=p.parse_args(); print(json.dumps(prepare(a.plan,a.source_dir,a.output_dir),sort_keys=True))
if __name__=="__main__": main()
