---
requestor: "Developer"
owner: "Designer"
status: "Resolved"
---

# IR_dev_M3_process_I — M3 physical-gate workflow simplification feedback

## Request

This is an **Advisory process feedback**, not a Blocking finding against the
approved M3 design or its acceptance criteria.  Please review whether the
physical/manual candidate workflow can be made shorter without weakening its
three essential controls:

1. every formal target result identifies one immutable implementation SHA;
2. a formal target acceptance bundle comes from one complete, fresh run ID;
3. human observations are recorded by the operator during that run and are
   never auto-filled by a runner.

## Observed developer cost

Candidate `5c9e5aac47e7f4f0dd168d8c75541438ee74f858` required an initial
non-manual Audio debug run, then a separate operator-assisted debug run for
manual Audio/Button/OLED cards and the remaining target cards.  The individual
cards passed, but the two debug run IDs cannot be combined into a formal
acceptance bundle.  This is correct fail-closed behaviour, yet it creates
avoidable repeated device setup, operator coordination, and execution time
before the one formal run can begin.

The existing scripts also demonstrate a usability risk: a convenience runner
attempted to write manual observations automatically.  It was not used for
this candidate because it is incompatible with the manual-evidence boundary.

## Proposed streamlined workflow

| Current intent | Proposed implementation |
| --- | --- |
| Developer fast loop | Keep local targeted tests; target-device debug is optional and always writes only `debug/<run-id>/`. |
| Candidate portable gate | One CI/manual command produces a bounded matrix report, static contract result, and an exact-SHA manifest. |
| Candidate freeze | No Designer/Tester SHA-freeze gate.  The target runner creates an implicit freeze only after it verifies the declared commit SHA, clean protected paths, runner version, config/artifact identity, and an unused acceptance run ID. |
| Target preflight | One fail-closed command performs that verification immediately before the target suite; a mismatch prevents the run from starting. |
| Target acceptance | One orchestrator runs all automated cards and pauses at explicit operator prompts; the operator records only observed manual checks. |
| Reconciliation | The orchestrator emits one index and fails if any card, log, manifest, SHA, or run ID differs. |

## Primary-run and debug fallback rule

The **complete interactive target run is the primary and only acceptance
evidence path**.  The operator is invited once the candidate SHA, preflight,
hardware setup, and complete operation checklist are ready; the runner then
executes all automatic cards and pauses at each manual prompt without changing
run ID.

Step-by-step `debug/<run-id>/` testing is permitted **only after that complete
run fails** (for example, a physical button press is not received).  Debug is
for isolating the failure and may be repeated, but its evidence never supplies
missing cards to the formal bundle.  After the issue is corrected, run one new
complete interactive acceptance run and use that single run as the evidence.
If the correction changes source, tests, dependency/artifact identity, or
configuration contract, create a new candidate SHA before the complete rerun.

## Minimum acceptance for a revised process

- Preserve the existing exact-SHA, clean-path, timeout, and no Skip/XFail
  requirements for formal acceptance.
- Make one command the authoritative portable report and one command the
  authoritative target preflight; both must fail closed.
- Treat the commit SHA supplied to a successful target preflight as fixed for
  that acceptance run.  Do not require a separate Designer or Tester action
  to freeze the SHA before hardware testing.
- Provide a single interactive acceptance runner with explicit prompts and
  operator-entered observations.  It must never create `pass` observations
  itself.
- Allow debug runs to diagnose hardware, but clearly label them non-acceptance
  and exclude them from final reconciliation.
- Start with one complete interactive target run; enter incremental debug only
  after that run fails, then return to one new complete run after correction.
- Avoid requiring repeated full target suites when candidate SHA, protected
  paths, config/artifact checksums, and the formal run ID remain unchanged.

## Suggested role boundary

Developer creates the user-approved candidate commit.  The operator starts
the target runner against that full SHA; preflight is the technical authority
that freezes it for the new acceptance run.  Tester reviews the completed
single-run result and evidence index for PASS/FAIL, rather than approving a
separate pre-hardware SHA freeze.  Designer is consulted only when a design
or acceptance-criteria decision is required, not as a mandatory gate after a
successful preflight.

## Requested Designer disposition

Please mark this request `Revised`, `Rejected`, or `Resolved` with the chosen
process direction.  A process revision may be scheduled separately from M3
functional acceptance; this feedback does not request reopening the current
candidate's code scope.

## Designer disposition — 2026-08-17

**Resolved as process guidance; M3 remains closed.** The following parts are accepted
for M4 onward: every formal acceptance invocation starts one complete suite from its
beginning; it uses a fresh run ID; debug evidence never supplies acceptance cards; and
manual observations are entered only by the operator after a matching READY handshake.
`docs/runbooks/candidate_hardware_gate.md` now makes the full-run restart and interactive
operator boundary explicit.

The proposed implicit preflight freeze and removal of the mandatory Designer gate are
not adopted.  Under the current authoritative G0–G7 governance, portable sign-off is
followed by G4 Designer candidate review/freeze.  G5 preflight consumes and validates
that freeze manifest; it cannot create, replace, or self-authorize it from current
`HEAD`.  The required M4 runner and six fail-closed dry-run demonstrations validate the
executable controls but do not, by themselves, change role authority.  Any future
collapse of G4 requires a separate approved governance revision.

The acceptance-first proposal is adopted.  After G5 passes, the first target execution
is one complete formal run.  A passing run proceeds directly to reconciliation and
finalization on the same frozen SHA; debug is entered only after a formal failure or
interruption.  Debug stays under `debug/<run-id>/`, and the next formal attempt must use
a new run ID, pass preflight, and execute the complete suite from its beginning.  A
protected-input correction creates a new candidate SHA; a physical-only correction can
retain the frozen SHA but cannot reuse the failed acceptance run ID.

No M3 product code, evidence, or acceptance result changes under this disposition.
