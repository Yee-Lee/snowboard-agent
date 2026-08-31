---
requestor: "Developer"
owner: "Designer"
status: "Resolved"
severity: "Blocking"
---

# IR_dev_M4B_I — Exact isolated CPython 3.13 runtime closure authority

## Decision requested

Please define the exact interpreter artifact and closure boundary for the M4b
Raspberry Pi product, or explicitly revise the current closure contract. Developer
cannot complete `M4B-WP-02`, the real worker, or candidate packaging without this
identity. This request does not relax the offline, no-system-site, exact-inventory,
or fail-closed requirements.

## Contract gap

`docs/implement/ch_m4b_llm_production.md` §8 requires the tracked
`llm-runtime-rpi-cp313.json` to list the isolated interpreter, installed
distribution, and native files by relative path, size, and SHA-256. The
`M4B-LOCK-001` test specification likewise rejects a missing, extra, placeholder,
or mismatched interpreter entry.

The Accepted identity fixes Debian 13 aarch64 and CPython 3.13, but does not fix:

- the CPython patch and Debian package revision;
- the exact offline interpreter source artifact and SHA-256;
- the dependent standard-library/native package set;
- whether the closure must contain those dependencies or may depend on the target
  system prefix and ABI;
- the deterministic installation layout and complete expected file inventory.

The current WIP manifest contains the exact 14-file LiteRT-LM wheel inventory but
no interpreter entry. A caller-supplied `python3.13 -m venv --copies` does not close
this gap: its copied launcher identity varies with the caller, and the resulting
venv still resolves the host CPython standard library. Recording a generated
inventory after installation would only self-certify that uncontrolled input; it
would not satisfy the tracked manifest authority.

## Required Designer disposition

Please choose and specify one implementable boundary:

1. **Self-contained runtime artifact:** provide an exact Debian 13 aarch64 CPython
   runtime archive/package set, patch/revision, source artifact sizes/digests,
   deterministic extraction rules, and the required installed file inventory; or
2. **Target ABI boundary:** explicitly permit a pinned target-system CPython/stdlib
   dependency and define which interpreter and ABI/package identities preflight
   must attest, while revising the requirement that every interpreter file lives
   inside the isolated runtime closure.

If option 1 uses Debian packages, the authority must include all packages needed by
the selected interpreter/venv shape rather than naming only
`python3.13-minimal`. If another reproducible runtime distribution is selected,
its provenance, license/notice entries, architecture, version, size, and SHA-256
must be fixed with the same precision as the LiteRT wheel.

## Work that may proceed while open

Portable protocol, strict config, lock parsing, parent lifecycle/recovery,
structured Reasoner integration, resource accounting, inheritance checks, and
test-runner scaffolding can continue. The 14-file LiteRT wheel extraction and its
negative tests remain useful. The following claims remain blocked:

- complete M4b runtime closure or product install/preflight;
- executable real-worker target readiness;
- WP-02, WP-04, or WP-06 Developer completion;
- provisional candidate handoff or any Pi/product PASS.

## Designer disposition（2026-08-30）

**Disposition: Revised — contract gap confirmed；Option 2 target ABI boundary selected.**

Designer已修訂`docs/implement/ch_m4b_llm_production.md` §8／§8.1與`docs/model_spec.md` §6.2。
M4b不再宣稱self-contained CPython closure：target-owned Debian CPython/stdlib/platform libraries與
product-owned LiteRT-LM payload正式分界。`llm-runtime-rpi-cp313.json`只權威化現有14-file
LiteRT-LM wheel/native inventory，不列interpreter或stdlib，也不接受generated inventory作artifact authority。

### Selected contract

- Base interpreter固定regular、non-symlink、root-owned`/usr/bin/python3.13`，exact CPython `3.13.5`、
  aarch64 SOABI/MULTIARCH、stdlib roots與glibc identity；
- 五個Debian Python package須全數installed、皆為同一`3.13.5-*`version。Exact package tuple、base
  executable digest與ABI fields形成run-bound`python_abi_attestation_sha256`；
- venv仍用`--copies --without-pip`，但launcher／`pyvenv.cfg`只屬run-specific install inventory；
  product payload manifest仍只包含14個exact LiteRT files；
- install、Pi preflight與acceptance start重算同一attestation；drift即fail closed。第三方system/user
  site-package仍禁止，stdlib與platform ABI library明確允許；installer不得apt/download/capture target bytes
  回寫tracked manifest。

### Preferred Developer correction

應修改：

1. `requirements/m4b/llm-runtime-rpi-cp313.json`維持14-file payload schema，將`python.version`收窄為
   `3.13.5`並把schema／命名註解明確定義為product payload；重算其tracked digest與
   `llm-artifacts.json`引用。
2. `src/sbd/cognition/litert_lm/lock.py::RuntimeClosure`改名可選；無論名稱是否改，parser／
   `verify_install()`只驗product site-packages payload，不要求venv launcher／stdlib進manifest。
3. `scripts/m4b_llm_product.py`新增pure capture/compare seam（建議
   `capture_python_abi(base_python) -> PythonABIAttestation`與
   `verify_python_abi(expected, actual)`）；install在建立staging前capture，將canonical attestation與digest
   放入`install-inventory.json`，preflight與acceptance重新capture並比對。
4. `install()`拒絕非`/usr/bin/python3.13`、symlink、non-root-owned、wrong version/ABI/package set；驗
   `pyvenv.cfg`與isolated `sys.path`，禁止system/user third-party packages。不得新增apt/download邏輯。
5. `scripts/candidate_gate.py`的target preflight/result保留sanitized
   `python_abi_attestation_sha256`；acceptance啟動前核對與preflight相同，不輸出absolute path或完整package
   inventory至public card。

不需重開：IPC、renderer、Reasoner、recovery、resource、inheritance或M4a Accepted contract；不需把
CPython/stdlib bytes加入Git、LiteRT payload manifest或license notice。

### Minimum regression

- positive：controlled exact 3.13.5／SOABI／MULTIARCH／five-package tuple在install→preflight→acceptance
  三段產生同一attestation digest；14-file payload exact驗證仍PASS；
- fail before staging/child：3.13.4／3.13.6、wrong SOABI/MULTIARCH、symlink／non-root base、package
  missing／mixed version、stdlib root escape；artifact/network side effect=0；
- fail after install：base executable、package revision、stdlib root或ABI任一在preflight／acceptance間
  drift；不得沿用PASS card，child spawn=0；
- isolation：stdlib import可成功；`/usr/lib/python3/dist-packages`、`/usr/local/.../site-packages`、user site
  或environment escape均fail；`litert_lm`與native path只可來自verified product root。

因Tester-owned`M4B-LOCK-001`仍含舊interpreter-in-manifest oracle，Designer已開
`TR_spec_M4B_II`作局部spec delta。Developer可依本修訂實作，但在該TR Resolved前不得宣稱WP-02／04／06
target-ready或建立provisional candidate。請Developer核對上述邊界；若等價實作關閉相同根因亦可接受。

## Developer confirmation（2026-08-30）

**Disposition: Resolved — Option 2 target ABI boundary accepted.**

Developer確認`ch_m4b_llm_production.md` §8／§8.1與`model_spec.md` §6.2已完整關閉原始
interpreter authority缺口。固定CPython 3.13.5、SOABI／MULTIARCH／stdlib boundary、五套件同版
tuple、base executable digest與glibc identity可形成可重現且run-bound的ABI attestation；14-file
LiteRT-LM payload則維持獨立的tracked authority。此邊界可實作、可fail closed，且不需要將target-owned
CPython／stdlib bytes誤列為product closure。

Developer將依Selected contract與Minimum regression修正lock、install、preflight、acceptance binding及
portable tests。`TR_spec_M4B_II`尚未Resolved仍獨立阻擋WP-02／04／06 target-ready、provisional
candidate與Pi Gate 3宣告，但不再構成本IR的設計實作阻礙。
