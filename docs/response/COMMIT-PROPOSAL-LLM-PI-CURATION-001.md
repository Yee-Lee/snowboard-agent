# COMMIT-PROPOSAL-LLM-PI-CURATION-001

- Date: 2026-09-06
- State: `COMPLETE PROPOSAL / USER CONFIRMATION REQUIRED / NOT STAGED`
- Base SHA: `57390cc1ed7aef7a3a172716bb71e622649c4f67`
- Scope: Phase 1 inventory, Phase 2 receipt, Phase 3 identity, exporter and cleanup gates

## Proposed commit message

```text
feat(m4b-storage/phase3): bind canonical product identities

- Record reconciled Pi inventory, workspace receipt, protected-hold migration,
  and gated post-download cleanup without moving retained inputs.
- Bind profile, schema, model, wheel, runtime manifest, native library, and
  content-addressed cache identities with fail-closed path checks.
- Add the private ready-bundle streaming exporter and small-fixture coverage for
  archive safety, checksums, Git SHA, native drift, and cache forwarding.
- Keep MVA snapshot, measurement, acceptance, materialization, activation,
  cleanup, Attempt 005, and permanent purge behind their governing gates.
```

The body is 76 words. No staging, commit, push, snapshot, Pi target execution, or
data-plane action is authorized by this proposal.

## Exact proposed files

1. `docs/DOCUMENT_INDEX.md`
2. `docs/milestone/README.md`
3. `docs/pm_handoff/RECEIPT-PI-PHASE2-WORKSPACES-001.md`
4. `docs/pm_handoff/REQUEST-POC-LLM-PI-STORAGE-PHASE3-001.md`
5. `docs/pm_handoff/FEEDBACK-POC-LLM-PI-STORAGE-PHASE3-001.md`
6. `docs/delivery/DELIVERY-LLM-PI-CURATION-POSTCHECK-001.md`
7. `docs/delivery/DELIVERY-LLM-PI-STORAGE-PHASE3-001.md`
8. `docs/response/ACK-LLM-PI-CANONICAL-WORKSPACE-RECEIPT-001.md`
9. `docs/response/ACK-POC-LLM-PI-STORAGE-CURATION-001.md`
10. `docs/response/HANDOFF-LLM-PI-STORAGE-CURATION-PHASE1-001.md`
11. `docs/response/RESP-POC-LLM-PI-STORAGE-PHASE3-001.md`
12. `docs/response/COMMIT-PROPOSAL-LLM-PI-CURATION-001.md`
13. `poc_llm/contracts/mva/product-storage-v1.json`
14. `poc_llm/curation/selected-profile-locators-v1.json`
15. `poc_llm/curation/pi-storage-worktree-inventory-v1.json`
16. `poc_llm/curation/pi-cleanup-manifest-v1.json`
17. `poc_llm/curation/llm-result-index-v1.json`
18. `poc_llm/curation/pi-storage-postcheck-v1.json`
19. `poc_llm/curation/pi-cleanup-postcheck-v1.json`
20. `poc_llm/curation/protected-hold-migration-v1.json`
21. `poc_llm/curation/pi-post-download-cleanup-v1.json`
22. `poc_llm/harness/mva_product_layout.py`
23. `poc_llm/harness/mva_controller.py`
24. `poc_llm/harness/mva_identity.py`
25. `poc_llm/harness/mva_litert_backend.py`
26. `poc_llm/harness/mva_surface.py`
27. `poc_llm/tools/run_mva.py`
28. `poc_llm/tools/collect_llm_storage_inventory.py`
29. `poc_llm/tools/prepare_curation_postcheck.py`
30. `poc_llm/tools/export_private_evidence.py`
31. `poc_llm/tests/mva/M4B-MVA-POC-PACKET-001.md`
32. `poc_llm/tests/mva/test_mva_product_layout.py`
33. `poc_llm/tests/mva/test_mva_controller.py`
34. `poc_llm/tests/mva/test_mva_identity.py`
35. `poc_llm/tests/mva/test_mva_litert_backend.py`
36. `poc_llm/tests/curation/test_storage_inventory.py`
37. `poc_llm/tests/curation/test_export_private_evidence.py`

## Explicit exclusions and overlap

- `docs/pm_handoff/REQUEST-POC-LLM-PI-STORAGE-CURATION-001.md` contains a
  concurrent owner modification. It remains untouched by this proposal; status is
  reconciled through response documents.
- `docs/response/HANDOFF-LLM-M4B-MVA-PI-ENTRY-001.md` is concurrent MVA owner work
  and is excluded.
- `docs/milestone/README.md` also contains retained MVA owner edits. The Phase 3
  additions only reconcile inventory/migration status; staging must preserve all
  owner content and review the combined file.
- `poc_llm/harness/mva-surface-lock-v1.json` remains unchanged. The current source
  intentionally requires a later governed snapshot/freeze after commit approval.
- Models, wheels, runtimes, caches, private bundle data, prompts, raw responses,
  endpoints and private absolute locator maps are excluded.

## Validation record

- Affected small-fixture command: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m
  unittest -v poc_llm.tests.mva.test_mva_product_layout
  poc_llm.tests.mva.test_mva_identity poc_llm.tests.mva.test_mva_litert_backend
  poc_llm.tests.curation.test_storage_inventory
  poc_llm.tests.curation.test_export_private_evidence` — 26 passed in 0.252 seconds.
- Follow-up cleanup manifest command: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python
  -m unittest -v poc_llm.tests.curation.test_storage_inventory` — 5 passed in
  0.003 seconds, including the newly added cleanup-plan gate test.
- After aligning to Core's sharded artifact-store/product topology, the 16 directly
  affected layout, identity, curation and exporter tests passed in 0.249 seconds.
- The five earlier local controller child-owner census/cleanup failures remain a
  known environment baseline and were not rerun or relabeled green.
- Pi bounded preflight: clean `llm` at `7a56137b7b2d65219ea4ff2065ab2773c179a0af`,
  HEAD equals `origin/llm`, three assigned roots verified, zero writes/model loads.
- LLM performed no lock refresh, benchmark, activation, hold movement or cleanup.
  Core later verified/downloaded the private bundle and removed the 36 run paths
  and ready tree under the separate receipt.
- Core's new canonical bytes match every fixed digest/size and contain zero
  symlinks. Product preflight remains blocked on writable mode `0664` hardlinks;
  LLM did not chmod shared inodes or change old active inputs.

## Remaining gates

Core accepted the canonical verifier and issued the migration relay. The User then
authorized commit/push. LLM next performs its governed snapshot/freeze and target
M4B-MVA. Attempt 005, measurement/manual review, acceptance, remaining cleanup
eligibility and permanent purge remain open.
