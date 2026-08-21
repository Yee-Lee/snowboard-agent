#!/usr/bin/env python3
import sys
from run_gate1_r5 import main
if __name__ == "__main__":
    sys.argv.extend(["--platform", "pi-debian13-aarch64"])
    raise SystemExit(main())
