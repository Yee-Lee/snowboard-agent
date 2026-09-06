"""Read-only Phase 1 inventory. No deletion, checkout, install or raw-result export."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout.strip()


def safe_statuses(value, prefix=""):
    """Only recognized outcome fields; never export message, prompt or answer values."""
    found = []
    allowed = {"status", "result", "outcome", "overall", "verdict", "summary", "gates", "checks", "tests", "metrics"}
    outcomes = {"PASS", "FAIL", "INCONCLUSIVE", "Blocked", "Pass", "Fail", "Unclear", "SKIP", "SKIPPED", "ERROR"}
    if isinstance(value, dict):
        for key, item in value.items():
            if key not in allowed and not re.fullmatch(r"P(?:[1-9]|1[0-2])(?:[AB]|\.[1-9])?", key):
                continue
            pointer = prefix + "/" + key
            if isinstance(item, str) and item in outcomes:
                found.append({"json_pointer": pointer, "value": item})
            elif isinstance(item, (dict, list)):
                found.extend(safe_statuses(item, pointer))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(safe_statuses(item, prefix + "/" + str(index)))
    return found


def walk_metadata(root):
    rows = []
    def fail(error):
        raise error
    root_info = root.lstat()
    rows.append({"path": str(root), "device": root_info.st_dev, "inode": root_info.st_ino,
                 "size_bytes": root_info.st_size, "allocated_bytes": root_info.st_blocks * 512,
                 "nlink": root_info.st_nlink, "mtime_ns": root_info.st_mtime_ns, "kind": "directory"})
    for directory, directories, files in os.walk(root, followlinks=False, onerror=fail):
        for name in sorted(directories + files):
            path = Path(directory) / name
            info = path.lstat()
            row = {"path": str(path), "device": info.st_dev, "inode": info.st_ino,
                   "size_bytes": info.st_size, "allocated_bytes": info.st_blocks * 512,
                   "nlink": info.st_nlink, "mtime_ns": info.st_mtime_ns}
            if stat.S_ISLNK(info.st_mode):
                row.update(kind="symlink", target=os.readlink(path))
            elif stat.S_ISREG(info.st_mode):
                row["kind"] = "file"
            elif stat.S_ISDIR(info.st_mode):
                row["kind"] = "directory"
            else:
                row["kind"] = "special"
            rows.append(row)
    return rows


def byte_counts(rows):
    files = [row for row in rows if row["kind"] == "file"]
    unique = {(row["device"], row["inode"]): row for row in rows}
    return {"apparent_file_bytes": sum(row["size_bytes"] for row in files),
            "unique_file_bytes": sum(row["size_bytes"] for row in unique.values() if row["kind"] == "file"),
            "allocated_unique_bytes": sum(row["allocated_bytes"] for row in unique.values()),
            "regular_file_count": len(files), "unique_inode_count": len(unique)}


def process_references(roots):
    references, inaccessible = [], 0
    prefixes = tuple(str(root) + "/" for root in roots)
    exact = {str(root) for root in roots}
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            paths = []
            for link in [proc / "cwd", proc / "exe", *(proc / "fd").glob("*")]:
                try:
                    paths.append(("open_reference", os.readlink(link)))
                except FileNotFoundError:
                    pass
            for argument in (proc / "cmdline").read_bytes().split(b"\0"):
                text = argument.decode("utf-8", "replace")
                candidate = text.split("=", 1)[-1]
                if candidate.startswith("/"):
                    paths.append(("argv_path", candidate))
            for line in (proc / "maps").read_text().splitlines():
                fields = line.split(maxsplit=5)
                if len(fields) == 6:
                    paths.append(("mapped_file", fields[5]))
            for kind, path in sorted(set(paths)):
                if path in exact or path.startswith(prefixes):
                    references.append({"pid": int(proc.name), "kind": kind, "path": path})
        except (PermissionError, FileNotFoundError, ProcessLookupError):
            inaccessible += 1
    return {"references": references, "inaccessible_or_exited_process_count": inaccessible,
            "persistent_service_reference_audit_complete": False}


def scan(operator_root):
    roots = [operator_root / "workspace/poc_llm", operator_root / "m4b-products",
             operator_root / "m4b-artifacts", operator_root / "m4b-test-runs"]
    items, all_rows = [], []
    for root in roots:
        if not root.is_dir() or root.is_symlink():
            raise ValueError("scoped root unavailable")
        for item in sorted(root.iterdir()):
            if not item.is_dir() or item.is_symlink():
                continue
            rows = walk_metadata(item)
            all_rows.extend(rows)
            record = {"original_path": str(item), "scope_root": str(root), **byte_counts(rows),
                "python_cache": byte_counts([row for row in rows if "__pycache__" in Path(row["path"]).parts]),
                "symlinks": [row for row in rows if row["kind"] == "symlink"],
                "large_files": [row for row in rows if row["kind"] == "file" and row["size_bytes"] >= 32 * 1024**2]}
            if (item / ".git").exists():
                _, head = git(item, "rev-parse", "HEAD")
                _, branch = git(item, "branch", "--show-current")
                code, status = git(item, "status", "--porcelain", "--untracked-files=all")
                tracked = [line for line in status.splitlines() if not line.startswith("??")]
                record["git"] = {"head": head, "branch": branch or None, "tracked_clean": code == 0 and not tracked,
                    "untracked_count": sum(line.startswith("??") for line in status.splitlines()),
                    "reachable_from_origin_llm": git(item, "merge-base", "--is-ancestor", head, "origin/llm")[0] == 0}
            # Only hash small metadata and runtime files here; do not full-rehash the model/cache.
            metadata = []
            if root.name == "m4b-products":
                for row in rows:
                    path = Path(row["path"])
                    if row["kind"] == "file" and ("manifest" in path.name or "lock" in path.name) and row["size_bytes"] < 1024**2:
                        metadata.append({"path": str(path), "sha256": digest(path)})
            record["identity_metadata"] = metadata
            if root.name == "m4b-test-runs":
                evidence = []
                for row in rows:
                    if row["kind"] != "file":
                        continue
                    path = Path(row["path"])
                    entry = {"relative_path": str(path.relative_to(item)), "size_bytes": row["size_bytes"], "sha256": None}
                    if row["size_bytes"] <= 64 * 1024**2:
                        entry["sha256"] = digest(path)
                    else:
                        entry["missing_reason"] = "LARGE_FILE_UNHASHED_RETAIN"
                    if path.suffix == ".json" and row["size_bytes"] <= 2 * 1024**2:
                        try:
                            entry["declared_status_fields"] = safe_statuses(json.loads(path.read_text()))
                        except (ValueError, UnicodeError):
                            entry["parse_status"] = "UNPARSEABLE_RETAIN"
                    evidence.append(entry)
                record["evidence_files"] = evidence
                record["evidence_file_index_sha256"] = hashlib.sha256(canonical(evidence)).hexdigest()
                record["all_regular_files_hashed"] = all(entry["sha256"] is not None for entry in evidence)
            items.append(record)
    repository = roots[0] / "snowboard-agent"
    _, worktrees = git(repository, "worktree", "list", "--porcelain")
    _, remote_sha = git(repository, "rev-parse", "refs/remotes/origin/llm")
    tag_code, tag_object = git(repository, "rev-parse", "--verify", "refs/tags/llm_m4")
    tag_commit_code, tag_commit = git(repository, "rev-parse", "--verify", "refs/tags/llm_m4^{commit}")
    # Hash each runtime tree, proving duplicate content independently of manifest names.
    runtimes = []
    for runtime in sorted(roots[1].glob("*/runtime")):
        if not runtime.is_dir() or runtime.is_symlink():
            continue
        rows = walk_metadata(runtime)
        files = [{"path": str(Path(row["path"]).relative_to(runtime)), "sha256": digest(Path(row["path"]))}
                 for row in rows if row["kind"] == "file"]
        runtimes.append({"path": str(runtime), **byte_counts(rows),
            "content_tree_sha256": hashlib.sha256(canonical(files)).hexdigest(), "file_count": len(files), "files": files})
    return {"schema_version": "llm-storage-inventory/1", "observed_utc": datetime.now(timezone.utc).isoformat(),
        "scope_roots": [str(root) for root in roots], "items": items, "whole_scope": byte_counts(all_rows),
        "runtime_trees": runtimes, "active_references": process_references(roots),
        "worktree_porcelain": worktrees, "pi_origin_llm_sha": remote_sha,
        "pi_llm_m4_tag_object": tag_object if tag_code == 0 else None,
        "pi_llm_m4_tag_commit": tag_commit if tag_commit_code == 0 else None,
        "mutation_performed": False, "raw_content_exported": False,
        "known_limits": ["No model/cache full hash in this scan", "No persistent service configuration audit",
            "Allocation counts are inode-based st_blocks, not a filesystem snapshot or reflink exclusivity proof",
            "Scan covers named roots only; symlink targets outside scope are not followed"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home-root", type=Path, default=Path.home())
    parser.add_argument("--ssh-target")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.ssh_target:
        # Fixed remote command; endpoint is neither included in JSON nor committed by this tool.
        collector_bytes = Path(__file__).read_bytes()
        result = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", args.ssh_target,
                                 "python3 -"], input=collector_bytes, capture_output=True, timeout=600)
        if result.returncode:
            print(json.dumps({"status": "INVENTORY_FAILED", "exit_code": result.returncode}))
            return 1
        value = json.loads(result.stdout)
        value["collector_sha256"] = hashlib.sha256(collector_bytes).hexdigest()
    else:
        value = scan(args.home_root)
    if args.output:
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(value, output, indent=2, sort_keys=True)
            output.write("\n")
        print(json.dumps({"status": "COLLECTED", "item_count": len(value["items"]),
            "inventory_sha256": digest(args.output), "mutation_performed": False}))
    else:
        print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
