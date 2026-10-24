# M3 commit 前 portable reproduction

- **執行時間**：2026-08-17T12:59:58Z
- **目前 HEAD**：`d81601789ef40aeccd01dd8d4b9db67a01d76163`
- **Worktree**：dirty；本結果驗證尚未提交的 Audio / GPIO regression修正，不是
  exact-SHA candidate evidence。
- **平台**：x86_64，Linux 6.8.0-137-generic
- **Python / pytest**：Python 3.12.3，pytest 9.1.1

## TR-M3-001

```text
timeout 20s env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -vv -s -p no:cacheprovider -p pytest_asyncio.plugin tests/test_m3_aud_001_002_003_004.py

collected 4 items
M3-AUD-001 PASSED
M3-AUD-002 PASSED
M3-AUD-003 PASSED
M3-AUD-004 PASSED
4 passed in 1.33s
exit code 0
```

## TR-M3-002

```text
timeout 20s env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -vv -s -p no:cacheprovider -p pytest_asyncio.plugin tests/test_m3_gpiod_backend.py

collected 2 items
test_gpiod_backend_fd_events_output_and_cleanup PASSED
test_gpiod_backend_zero_debounce_omitted PASSED
2 passed in 0.30s
exit code 0
```

`test_gpiod_backend_zero_debounce_omitted` asserts both sides of the contract:
`debounce_ms=0` omits `debounce_period`, while `debounce_ms=50` passes exactly
`timedelta(milliseconds=50)`.

## Entrypoints and complete non-RPI gate

All commands used `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, explicitly loaded
`pytest_asyncio.plugin`, disabled the cache provider, and had an external bounded timeout.

```text
tests/milestones/test_m1_foundation.py
1 passed in 8.05s
exit code 0

tests/milestones/test_m2_mock_pipeline.py
1 passed in 4.72s
exit code 0

-m "not rpi" tests/milestones/test_m3_rpi_hal.py
1 passed, 1 deselected in 5.47s
exit code 0

-m "not rpi"
240 passed, 21 deselected in 40.68s
exit code 0
```

The deselected nodes are the explicitly excluded RPI tests; the selected portable tests contain
no Fail, Blocked, Skip, or XFail disposition.
