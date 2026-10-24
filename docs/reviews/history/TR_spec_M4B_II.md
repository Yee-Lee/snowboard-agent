---
requestor: "Designer"
owner: "Tester"
status: "Resolved"
---

# TR_spec_M4B_II — Target CPython ABI boundary delta

## Review boundary

`IR_dev_M4B_I`確認原M4b design把target-owned CPython/stdlib誤列入self-contained product closure，
但未提供可重現的interpreter authority。Designer已在`ch_m4b_llm_production.md` §8.1選定target ABI
boundary。Tester只需修訂`M4B-LOCK-001`、`M4B-PKG-001`及其直接evidence fields；其餘13個Test ID、
Round I/II已核准assertions、M4a boundary與Gate 3門檻不重開。

## Required spec corrections

### TR-M4B-II-01 — `M4B-LOCK-001` closure authority

- 將「runtime manifest含interpreter relative path/size/digest」改為：tracked
  `llm-runtime-rpi-cp313.json`只含product-owned 14-file LiteRT-LM distribution/native payload；manifest
  對payload仍須exact、no-placeholder、no extra/missing/symlink。
- 新增target ABI positive oracle：regular、non-symlink、root-owned`/usr/bin/python3.13`；CPython
  `3.13.5`；SOABI`cpython-313-aarch64-linux-gnu`；MULTIARCH`aarch64-linux-gnu`；64-bit little-endian；
  stdlib／platstdlib`/usr/lib/python3.13`；五個design §8.1 Debian packages皆installed且version為相同
  `3.13.5-*`。
- 新增negative matrix：wrong patch、SOABI/MULTIARCH、symlink/non-root base、package missing/mixed version、
  stdlib root escape，均在staging／native import／child spawn前fail closed且zero artifact/network side effect。

### TR-M4B-II-02 — `M4B-PKG-001` install/preflight/acceptance binding

- 明定`--copies --without-pip` venv可依賴target stdlib；launcher與`pyvenv.cfg`只進run-specific
  install inventory，不得冒充tracked payload authority。
- install inventory保存canonical exact ABI attestation及`python_abi_attestation_sha256`；Pi preflight與
  acceptance開始重算並exact match。任一base executable digest、package tuple、stdlib root、ABI或glibc
  drift均Fail，child spawn=0，舊PASS card不得重用。
- `no system-site`須允許stdlib／`lib-dynload`與platform ABI libraries，但拒絕system/user third-party
  site/dist-packages、environment escape；`litert_lm`與native library只可從verified product root載入。
- Product installer不得apt、下載或把target CPython/stdlib bytes寫回tracked manifest。
- Pi card只公開sanitized attestation digest與status；exact package/path inventory留在protected raw
  preflight，不洩漏absolute private product path。

## Minimum regression package

1. exact controlled ABI在install→preflight→acceptance三段digest一致，14-file payload exact驗證PASS；
2. wrong patch／ABI／ownership／package set／stdlib root逐項Fail且zero pre-staging side effect；
3. install後package revision或base digest drift使preflight／acceptance Fail並禁止spawn／card reuse；
4. stdlib import positive與system/user third-party site-package negative同時成立；
5. existing LOCK/Pkg wheel/model/native/config/notice、offline、atomic staging與no-follow regressions保持PASS。

## Tester revision response（2026-08-31）

| Finding | Revised location in `docs/test_spec/test_spec_M4.md` | Disposition |
| :--- | :--- | :--- |
| `TR-M4B-II-01` tracked closure authority | `M4B-LOCK-001` → `Lock schema negative matrix`的`Wrong runtime closure`；`Target CPython ABI boundary`；`Pi preflight assertions`的runtime manifest、ABI reconciliation與system-site boundary | 已改為exact 14-file product-owned LiteRT-LM payload；明定target-owned CPython／stdlib／venv files不得進tracked manifest；補齊exact CPython 3.13.5 positive oracle、base／ABI／package／stdlib negative matrix、preflight digest reconciliation與drift fail-closed。 |
| `TR-M4B-II-02` install/preflight/acceptance binding | `M4B-PKG-001` → `Evidence`與`Required assertions`；`M4B-INH-001` → `lock_preflight_reconciliation`；`M4b 里程碑結論欄位` | 已明定`--copies --without-pip` target venv、run-specific install inventory、三階段ABI digest一致、post-install drift、stdlib positive／third-party negative、no apt/download/capture及sanitized public card；直接evidence欄位新增ABI與install-inventory digest。 |
| Minimum regression package 1–5 | `M4B-LOCK-001` target ABI／preflight tables及`M4B-PKG-001` required assertions | exact controlled path、zero-side-effect negative matrix、drift/card-reuse rejection、import boundary與既有wheel/model/native/config/notice/offline/atomic/no-follow assertions已形成同一鎖定regression scope；其餘13個Test ID與Gate 3門檻未重開。 |

Tester已完成本輪owner修訂；本單依workflow停在`Revised`，等待Designer只針對上述delta複審。
此狀態不是`Resolved`，也不是portable／Pi acceptance PASS。

## Exit

Tester修訂`docs/test_spec/test_spec_M4.md`後，在本單逐項列出位置並將status改為`Revised`。Designer複審
只核對`TR-M4B-II-01/02`、直接evidence schema與新regression；通過後標`Resolved`並歸檔。該單Resolved
與`IR_dev_M4B_I`均Resolved前，M4b Developer fast loop可繼續，但WP-02／04／06 target-ready、
provisional candidate與Pi Gate 3均阻擋。

## Designer Final Confirmation

確認 Tester 已依指示完整修訂 `M4B-LOCK-001` 與 `M4B-PKG-001`。Target ABI 邊界、digest reconciliation 與隔離環境要求均已正確反映在測試規格中。無新增 blocking findings。狀態改為 `Resolved`。
