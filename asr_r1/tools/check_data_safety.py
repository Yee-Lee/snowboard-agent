"""Fail closed when forbidden artifacts or likely secrets enter the worktree."""

from __future__ import annotations

from pathlib import Path

from asr_r1.data_safety import scan_repository


REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    findings = scan_repository(REPO_ROOT)
    if findings:
        for finding in findings:
            print(f"FAIL {finding.path}: {finding.reason}")
        return 1
    print("PASS data-safety scan: no prohibited worktree content found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
