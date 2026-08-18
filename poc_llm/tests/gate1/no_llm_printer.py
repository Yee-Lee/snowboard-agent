#!/usr/bin/env python3
"""Negative test: prints expected catalog JSON without implementing a candidate."""
import argparse, importlib.util, json
from pathlib import Path
parser=argparse.ArgumentParser(); parser.add_argument("--catalog",type=Path,required=True); parser.add_argument("--validator",type=Path,required=True)
args=parser.parse_args(); spec=importlib.util.spec_from_file_location("validator",args.validator)
validator=importlib.util.module_from_spec(spec); spec.loader.exec_module(validator)
catalog=json.loads(args.catalog.read_text())
print(json.dumps(validator.self_test_input(catalog),separators=(",",":")),flush=True)
