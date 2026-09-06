"""Build a sanitized, non-authorizing post-check from a private inventory."""
import argparse
import hashlib
import json
from pathlib import Path


def prepare(source, source_digest):
    roots = dict(zip(source["scope_roots"], (
        "PI_LLM_WORKSPACE", "PI_M4B_PRODUCTS", "PI_M4B_ARTIFACTS", "PI_M4B_RUNS")))

    def locator(path):
        for root, label in roots.items():
            if path == root or path.startswith(root + "/"):
                return label + path[len(root):]
        raise ValueError("Unmapped path; retain privately")

    items = []
    for original in source["items"]:
        name = locator(original["original_path"])
        owner = "LLM POC" if name.startswith("PI_LLM_WORKSPACE/") else "Core M4B; mixed evidence may include Audio"
        record = {"locator": name, "owner": owner}
        for key in ("apparent_file_bytes", "unique_file_bytes", "allocated_unique_bytes",
                    "regular_file_count", "python_cache", "git", "evidence_files",
                    "evidence_file_index_sha256", "all_regular_files_hashed"):
            if key in original:
                record[key] = original[key]
        record["overall_result"] = None
        record["outcome_rule"] = "Per-file declared statuses only; component PASS is not overall PASS"
        items.append(record)
    references = [{"kind": row["kind"], "locator": locator(row["path"])}
                  for row in source["active_references"]["references"]]
    runtimes = [{**{key: val for key, val in row.items() if key != "path"},
                 "locator": locator(row["path"])} for row in source["runtime_trees"]]
    common = {"observed_utc": source["observed_utc"], "private_inventory_sha256": source_digest,
              "collector_sha256": source["collector_sha256"]}
    inventory = {**common, "schema_version": "llm-curation-postcheck/1", "items": items,
        "whole_scope": source["whole_scope"], "runtime_trees": runtimes,
        "origin_llm_sha": source["pi_origin_llm_sha"],
        "llm_m4_tag_object": source["pi_llm_m4_tag_object"],
        "llm_m4_tag_commit": source["pi_llm_m4_tag_commit"],
        "active_reference_audit": {"references": references,
            "inaccessible_or_exited_process_count": source["active_references"]["inaccessible_or_exited_process_count"],
            "persistent_service_reference_audit_complete": False},
        "known_limits": source["known_limits"] + [
            "Concurrent pre-check documents are preserved; this observation supersedes their checkout state only",
            "Root-level non-directory entries and shared caches outside named roots are not covered",
            "Checksums identify files, not correctness or acceptance; no benchmark was performed"]}
    manifest = {**common, "schema_version": "llm-curation-postcheck-cleanup/1",
        "execution_authorized": False, "immediate_reclaimable_unique_bytes": 0,
        "conditional_reclaimable_unique_bytes": None,
        "items": []}
    for row in items:
        is_main = row["locator"] == "PI_LLM_WORKSPACE/snowboard-agent"
        manifest["items"].append({
            "original_locator": row["locator"], "owner": row["owner"],
            "apparent_bytes": row["apparent_file_bytes"],
            "unique_file_bytes": row["unique_file_bytes"],
            "allocated_unique_bytes": row["allocated_unique_bytes"],
            "reclaimable_unique_bytes": 0,
            "category": "retain" if is_main or row["locator"].startswith("PI_M4B_RUNS/") else "hold",
            "reason": "Retain authoritative source/evidence and protected inputs; no purge authority or verified canonical receipt",
            "active_references": [ref for ref in references if ref["locator"] == row["locator"] or ref["locator"].startswith(row["locator"] + "/")],
            "reference_audit_complete": False,
            "retained_evidence_locator": "pi-storage-postcheck-v1.json#" + row["locator"],
            "retained_evidence_sha256": row.get("evidence_file_index_sha256"),
            "rebuild_proof": ({"tracked_source_sha": row["git"]["head"],
                               "reachable_from_origin_llm": row["git"]["reachable_from_origin_llm"],
                               "untracked_and_ignored_content_rebuild_proven": False}
                              if "git" in row else {"complete_rebuild_proven": False}),
            "proposed_expiry": "None before Core canonical receipt, independent evidence retention, fresh reference audit and explicit User purge approval"})
    return inventory, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    inventory, manifest = prepare(json.loads(raw), hashlib.sha256(raw).hexdigest())
    for name, value in (("pi-storage-postcheck-v1.json", inventory),
                        ("pi-cleanup-postcheck-v1.json", manifest)):
        with (args.output_directory / name).open("x", encoding="utf-8") as output:
            json.dump(value, output, indent=2, sort_keys=True)
            output.write("\n")


if __name__ == "__main__":
    main()
