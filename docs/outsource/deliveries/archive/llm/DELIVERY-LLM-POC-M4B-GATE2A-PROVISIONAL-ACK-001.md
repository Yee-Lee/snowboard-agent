# DELIVERY-LLM-POC-M4B-GATE2A-PROVISIONAL-ACK-001

- **Date**: 2026-08-29
- **From**: Core Designer
- **To**: LLM POC Team (M4b) / PM Team
- **Status**: `GATE 2A USER DECISION ACKNOWLEDGED / GEMMA MODEL FINALIST / GATE 2B ENTRY REVISION REQUIRED`
- **POC branch / closure SHA**: `llm` / `3c012eb65cc7c8b706fe1c29a3fcafab17696d0f`
- **Gate 2A execution SHA**: `e2b59fac609e0d768ff3554754363900cbed70a9`
- **Gate 2A execution-surface SHA-256**: `eccbcdc1a099c40a80cc86de8f711711b9ed351400197a505d4f4f466b37b2e1`
- **References**: `DELIVERY-019`, `DELIVERY-020`, `DELIVERY-021`, `ASSESSMENT-LLM-M3-GATE2A-20260829-USER-REVIEW`

## 1. Core acknowledgement

Core acknowledges the User-reviewed Gate 2A closure and accepts the following decision without
rewriting any machine disposition:

1. `CAND-LRT-G4E2B-MOBILE-R1` (Gemma 4 E2B mobile) is the sole **model finalist**.
2. Qwen is excluded from the formal Gate 2B path. Its P7.1 `FAIL / SLOW_RECOVERY`, true-cold READY
   observations and no-credit 30-second operational window remain immutable history.
3. P2 qualifies the complete model/chat-template/prompt/config pairing, P3 independently qualifies
   deterministic containment, and P8 distinguishes prior-state pollution from current-turn semantic
   failure.
4. The current Gemma pairing is not a deliverable product configuration: P2 remains `FAIL (3/30)` and
   P8 remains `FAIL / DEPENDENCY_LIMITED_BY_P2` with no observed history pollution.
5. This ACK closes the Gate 2A model-selection round. It is not a Gate 2B winner, product baseline,
   production dependency/model lock, Core Tester PASS or physical-Pi Gate 2B authorization.

## 2. Immutable result record

| Candidate / run | P2 | P3 | P4 | P5 | P8 | Sanitized evidence SHA-256 / bytes | Core disposition |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Qwen / `G2A-PI-QWEN-004` | `FAIL` 0/30 | `PASS` | `Core threshold decision required` | `PASS` | `FAIL / DEPENDENCY_LIMITED_BY_P2` | `e0c000df51c26af5c9cc1f1704f13b8b8816b087d64ba596808b4e3be5b4530f` / 27645 | `NOT SELECTED / EXCLUDED FROM FORMAL GATE 2B` |
| Gemma / `G2A-PI-GEMMA-002` | `FAIL` 3/30 | `PASS` | `PASS` | `PASS` | `FAIL / DEPENDENCY_LIMITED_BY_P2` | `41f1d8e4f74bac25fd83a17fd0bdb776e9cb0bae1c4c04fdc345f378592681e7` / 27357 | `SOLE MODEL FINALIST / CURRENT PAIRING NOT PRODUCT-ELIGIBLE` |

The User assessment attests that both final observations used separate reboot-isolated Pi 5 4 GB
boots, the same clean execution SHA and locked surface, read-only authenticated artifacts, offline
namespaces, `swap=0`, no full-model rehash, clean log-hygiene scans and zero final process residue.
Core accepts that completed User evidence review as the authority for this Gate 2A model-selection
closure. Raw evidence remains immutable outside Git as required by the packet.

## 3. Required integration-qualified Gemma revision

Before Gate 2B entry, the POC team must submit one append-only Gemma integration revision. The
recommended identity is `CAND-LRT-G4E2B-MOBILE-R2`; an equivalent versioned identity is acceptable
if all references use it consistently. The revision must:

1. keep the selected Gemma model artifact and LiteRT-LM runtime identities unchanged unless a separate
   Core change request is accepted;
2. version the complete chat template, PromptBuilder, product prompt, generation profile and product
   config; do not overwrite any R1 file or Gate 2A receipt;
3. declare a bounded adaptation budget and development cases that are disjoint from the new frozen
   scored catalog;
4. freeze the revised surface before scoring, then execute focused P2 and P8 qualification on a new
   clean Pi run/evidence namespace using precommitted or independently held-out cases;
5. retain Gate 2A R1 P3/P4/P5 and Gate 1 evidence only when the lock proves their inputs unchanged;
   otherwise rerun only the affected P items under a reviewed replacement packet;
6. emit immutable machine results. P2 and P8 must be `PASS` for the revision to enter Gate 2B; a valid
   `FAIL` is no-go and must not be tuned or rerun under the same revision;
7. preserve offline, `swap=0`, cleanup, log-hygiene and no-model-text-in-Git requirements.

Core bounds adaptation to at most two new development revisions: first one prompt-only revision; then,
only when a documented template/capacity root cause remains, one config revision. Scored cases, private
R1 output, nonce/trap values and expected literals must not be copied into the prompt. Normalizer repair,
retry/best-of/majority-vote, threshold relaxation, model/runtime substitution and fine-tuning are outside
this authorization. The exact lever order and affected-P matrix are fixed in
`docs/implement/ch_m4b_llm_production.md` §1.4.

## 4. Gate 2B consumer package required

The current Gate 2B lock digest `03c68362dd5ea6e299f262d773eeda1da611dbe10705bde909bb8445676e1c41`
still binds the failed R1 product config and therefore is not authorized for scored execution. Submit
one reviewed replacement package containing:

- the exact revision SHA and regenerated Gate 2B lock digest;
- the new Gemma revision manifest, product-config checksum and focused P2/P8 result identity;
- a `gate2a-provisional-receipt-v1` consumer receipt naming the selected revision and preserved R1
  lineage;
- a consumer receipt binding each User-reviewed sanitized result consumed by `run_gate2b_pi_v1.py`
  to its run ID, SHA-256 and byte length; the operator-provided controlled file must reproduce that
  identity and no prompt or model text may be committed;
- the unchanged Accepted Audio entry `POC-audio-DEL-2026-001-R1`, Audio completion
  `5694ead4ba6be928fdb4dbdf6da7155b214d72bd`, corrected delivery
  `ca51bce9b4e205d9c9faf004d41c27169f108a3f` and combined execution
  `8be3bc095b504b8eab1dfeb21b94173728b9656f`;
- Gate 2B P9/P10B command, 4 GB thresholds, bounded timeout, cleanup/privacy assertions and the exact
  no-surrogate boundary.

Core will review this replacement package once. Physical Gate 2B remains blocked until the package
is accepted and a separate exact-SHA Pi authorization is issued.

## 5. Core product work allowed now

Core may review and implement the engine-agnostic protocol/fake package and a LiteRT-LM parent/worker
adapter scaffold that does not pin the production model, prompt/config checksum or final dependency
lock. Core must not mark M4b Design Ready, baseline locked or Accepted until the replacement revision,
Gate 2B final winner, full Tester coverage and Core exact-SHA Gate 3 acceptance are complete.
