#!/usr/bin/env python3
import sys
from run_gate1_r5 import main
if __name__ == "__main__":
    sys.argv.extend(["--platform", "ubuntu-x86_64"])
    raise SystemExit(main())
