# M4a Generic Scaffold 設計

屬於 `implement.md` 索引 | 對應 `docs/milestones/M4.md` §6.1–6.2 M4a Audio  
狀態：**設計定稿 — 等待 Developer 實作**

---

## 0. 設計範圍與授權邊界

依 `DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003` §4 放行邊界：

| Audio POC 狀態 | Core 授權範圍 |
| :--- | :--- |
| **M2A in progress（現在）** | ✅ 本文件所有內容 |
| M2B reviewed selection 後 | Candidate-specific adapter + provisional dependency/config（另立設計） |
| Gate 2B `POC Accepted` | Production lock（另立設計） |

**禁止在本 scaffold 引入：** 真實 engine import、固定 model path / engine class、production dependency、POC branch HEAD 引用

---

## 1. 設計目標與不改變的契約

**目標：**
1. 建立 `null` adapter，讓 M4 integration test 中 ASR/TTS 可安全降級（P5 路徑）
2. 為 config schema 加入 M4a engine-agnostic placeholder 欄位
3. 建立 factory wiring 骨架，M2B ACK 後只需新增一個 `elif` 分支
4. 移除早期佔位 Literal（`"whisper"` / `"piper"`），更新為語意準確的 `"null"` 選項

**不改變的契約：**
- `ASRAdapter.transcribe(frames: AsyncIterator[bytes]) -> ASRResult` 簽名不變
- `TTSAdapter.synthesize(text: str) -> AsyncIterator[bytes]` 簽名不變
- `Listen` / `Speak` worker 邏輯不變
- `MockASRAdapter` / `MockTTSAdapter` 行為不變

---

## 2. ASR Scaffold

### 2.1 NullASRAdapter

落點：[`src/sbd/perception/listen/asr.py`](file:///home/yee/workspace/snowboard-agent/src/sbd/perception/listen/asr.py)，新增於 `MockASRAdapter` 之後

```python
class NullASRAdapter:
    """ASR null implementation.

    start()/stop() are no-ops.  transcribe() drains the frame iterator
    (honouring abort) and returns an empty ASRResult, which the Listen worker
    maps to status='timeout'.  No real engine is imported.
    """

    async def start(self) -> None:
        import logging
        logging.getLogger(__name__).info("ASRAdapter: running in null mode")

    async def stop(self) -> None:
        pass

    async def abort(self) -> None:
        pass

    async def force_abort(self) -> ForceAbortReport:
        return ForceAbortReport()

    async def transcribe(self, frames: AsyncIterator[bytes]) -> ASRResult:
        # Drain frames until cancelled/aclose(); return empty text.
        # Listen worker treats empty text as status='timeout' (ch2b §2.1 step 3).
        try:
            async for _ in frames:
                await asyncio.sleep(0)
        except GeneratorExit:
            pass
        return ASRResult(text="")
```

**語意說明：**
- `transcribe()` 必須消耗 iterator（不立即 return），才能讓 `Listen.perceive()` 的 `finally: await self._close_frames()` 正確運作
- `ASRResult(text="")` → Listen 第 3 步 `value.text.strip()` 為空 → `status="timeout"`（ch2b §2.1）
- 只在 `start()` log info 一次，後續呼叫不 log

### 2.2 ASR factory

落點：[`src/sbd/perception/listen/__init__.py`](file:///home/yee/workspace/snowboard-agent/src/sbd/perception/listen/__init__.py)（新建或擴充）

```python
from __future__ import annotations
from sbd.core.config.models import ASRConfig
from sbd.perception.listen.asr import ASRAdapter, MockASRAdapter, NullASRAdapter


def make_asr_adapter(cfg: ASRConfig) -> ASRAdapter:
    if cfg.driver == "mock":
        return MockASRAdapter()
    if cfg.driver == "null":
        return NullASRAdapter()
    raise ValueError(
        f"ASR driver '{cfg.driver}' is not yet available. "
        "Candidate-specific backend requires M2B provisional selection ACK."
    )
```

---

## 3. TTS Scaffold

### 3.1 NullTTSAdapter

落點：[`src/sbd/action/speak/tts.py`](file:///home/yee/workspace/snowboard-agent/src/sbd/action/speak/tts.py)，新增於 `MockTTSAdapter` 之後

```python
class NullTTSAdapter:
    """TTS null implementation.

    synthesize() yields one silent 20 ms frame (640 bytes of 0x00),
    matching 16 kHz / mono / S16_LE stream_format.
    Speak worker maps to ActionCompleted(status='ok') — silence is valid output.
    No real engine is imported.
    """

    async def start(self) -> None:
        import logging
        logging.getLogger(__name__).info("TTSAdapter: running in null mode")

    async def stop(self) -> None:
        pass

    async def abort(self) -> None:
        pass

    async def force_abort(self) -> ForceAbortReport:
        return ForceAbortReport()

    def synthesize(self, text: str) -> AsyncIterator[bytes]:
        async def _generate() -> AsyncIterator[bytes]:
            # One silent 20 ms frame: 320 samples * 2 bytes = 640 bytes
            yield b"\x00" * 640
        return _generate()
```

**語意說明：**
- 輸出一個靜音 frame 而非空 iterator，確保 `AudioOutput.play()` 的消費 loop 至少跑一次
- 640 bytes = M3 accepted stream_format（16 kHz / mono / S16_LE / 20 ms）
- Speak worker → `ActionCompleted(status="ok")`，session 正常繼續

### 3.2 TTS factory

落點：[`src/sbd/action/speak/__init__.py`](file:///home/yee/workspace/snowboard-agent/src/sbd/action/speak/__init__.py)（新建或擴充）

```python
from __future__ import annotations
from sbd.core.config.models import TTSConfig
from sbd.action.speak.tts import TTSAdapter, MockTTSAdapter, NullTTSAdapter


def make_tts_adapter(cfg: TTSConfig) -> TTSAdapter:
    if cfg.driver == "mock":
        return MockTTSAdapter()
    if cfg.driver == "null":
        return NullTTSAdapter()
    raise ValueError(
        f"TTS driver '{cfg.driver}' is not yet available. "
        "Candidate-specific backend requires M2B provisional selection ACK."
    )
```

---

## 4. Config Schema 更新

落點：[`src/sbd/core/config/models.py`](file:///home/yee/workspace/snowboard-agent/src/sbd/core/config/models.py)

### 4.1 ASRConfig

```python
@dataclass(frozen=True, slots=True)
class ASRConfig:
    driver: Literal["mock", "null"] = "mock"
    # 以下欄位為 M2B provisional selection 後填入的佔位
    engine_name: str | None = None      # e.g. "sherpa_sensevoice" (TBD after M2B ACK)
    model_path: Path | None = None
    language: str | None = None
    dsp_profile: str | None = None      # e.g. "dc_removal+fixed_gain" (TBD)
    decoder_profile: str | None = None  # e.g. "greedy" (TBD)
```

> 移除舊的 `Literal["mock", "whisper"]`（`"whisper"` 是早期佔位名，非已選定 engine）

### 4.2 TTSConfig

```python
@dataclass(frozen=True, slots=True)
class TTSConfig:
    driver: Literal["mock", "null"] = "mock"
    # 以下欄位為 M2B provisional selection 後填入的佔位
    engine_name: str | None = None           # e.g. "sherpa_matcha" (TBD after M2B ACK)
    model_path: Path | None = None
    voice_id: str | None = None
    native_sample_rate: int | None = None    # e.g. 16000 (TBD — M4a驗收關鍵欄位)
    native_channels: int | None = None       # e.g. 1 (TBD)
    native_sample_format: str | None = None  # e.g. "s16_le" (TBD)
```

> 移除舊的 `Literal["mock", "piper"]`（`"piper"` 是早期佔位名）  
> `native_*` 欄位是 M4a 驗收要求（M4.md §6.4）：TTS PCM 格式必須與 AudioOutput stream_format 一致

### 4.3 Cross-field validation

落點：[`src/sbd/core/config/validate.py`](file:///home/yee/workspace/snowboard-agent/src/sbd/core/config/validate.py)

```python
def _validate_asr_config(cfg: ASRConfig) -> None:
    if cfg.driver not in ("mock", "null") and cfg.engine_name is None:
        raise ConfigValueError(
            "perception.listen.adapter.engine_name",
            "engine_name is required when driver is not 'mock' or 'null'",
        )

def _validate_tts_config(cfg: TTSConfig) -> None:
    if cfg.driver not in ("mock", "null") and cfg.engine_name is None:
        raise ConfigValueError(
            "action.tts.engine_name",
            "engine_name is required when driver is not 'mock' or 'null'",
        )
```

### 4.4 config.example.yaml 更新片段

```yaml
perception:
  listen:
    adapter:
      driver: mock
      engine_name: null     # TBD: M2B ACK 後填入，e.g. "sherpa_sensevoice"
      model_path: null
      language: zh-TW
      dsp_profile: null
      decoder_profile: null

action:
  tts:
    driver: mock
    engine_name: null       # TBD: M2B ACK 後填入，e.g. "sherpa_matcha"
    model_path: null
    voice_id: null
    native_sample_rate: null
    native_channels: null
    native_sample_format: null
```

---

## 5. RM Resource Key 登記

落點：[`src/sbd/core/resource_manager.py`](file:///home/yee/workspace/snowboard-agent/src/sbd/core/resource_manager.py)

新增至 Ch 5 §3.1 stable ResourceKey registry：

| ResourceKey | Startup timeout | Stop timeout |
| :--- | :--- | :--- |
| `backend.perception.listen.asr` | `30.0` | `5.0` |
| `backend.action.speak.tts` | `30.0` | `5.0` |

對應 `config.example.yaml` resource 區段：

```yaml
resource:
  startup_timeout_seconds:
    by_kind:
      backend.cognition.reasoner.llm: 120.0
      backend.perception.listen.asr: 30.0   # 新增
      backend.action.speak.tts: 30.0        # 新增
  stop_timeout_seconds:
    by_kind:
      backend.cognition.reasoner.llm: 10.0
      backend.perception.listen.asr: 5.0    # 新增
      backend.action.speak.tts: 5.0         # 新增
```

---

## 6. 檔案落點總覽

```
src/sbd/
├── perception/listen/
│   ├── asr.py              # 新增 NullASRAdapter（既有 MockASRAdapter 保留）
│   └── __init__.py         # 新建 make_asr_adapter(cfg: ASRConfig) -> ASRAdapter
├── action/speak/
│   ├── tts.py              # 新增 NullTTSAdapter（既有 MockTTSAdapter 保留）
│   └── __init__.py         # 新建 make_tts_adapter(cfg: TTSConfig) -> TTSAdapter
└── core/config/
    ├── models.py            # ASRConfig / TTSConfig schema 更新
    ├── validate.py          # 新增 cross-field validation rules
    └── defaults.py          # DEFAULT_CONFIG 新欄位補 None 預設值

config.example.yaml          # perception.listen.adapter / action.tts / resource 區段更新
```

---

## 7. 測試設計（Developer 實作，Tester 驗收）

### NullASRAdapter（落點：`tests/perception/`）

| Test ID | 情境 | 驗收條件 |
| :--- | :--- | :--- |
| `ASR-NULL-001` | `NullASRAdapter.transcribe()` 正常執行 | 回傳 `ASRResult(text="")`；不 raise |
| `ASR-NULL-002` | `transcribe()` 被 frames `aclose()` 中斷 | 乾淨退出；無 orphan task |
| `ASR-NULL-003` | `Listen` worker 使用 NullASRAdapter 整合 | publish `PerceptionResult(status="timeout")` |
| `ASR-NULL-004` | `make_asr_adapter(ASRConfig(driver="null"))` | 回傳 `NullASRAdapter` instance |
| `ASR-NULL-005` | `make_asr_adapter(ASRConfig(driver="unknown"))` | raise `ValueError` |

### NullTTSAdapter（落點：`tests/action/`）

| Test ID | 情境 | 驗收條件 |
| :--- | :--- | :--- |
| `TTS-NULL-001` | `NullTTSAdapter.synthesize()` 產出 frame | 至少 1 chunk；每 chunk 均為 `bytes`；total len > 0 |
| `TTS-NULL-002` | `Speak` worker 使用 NullTTSAdapter 整合 | publish `ActionCompleted(status="ok")` |
| `TTS-NULL-003` | `make_tts_adapter(TTSConfig(driver="null"))` | 回傳 `NullTTSAdapter` instance |
| `TTS-NULL-004` | `make_tts_adapter(TTSConfig(driver="unknown"))` | raise `ValueError` |

### Config schema（落點：`tests/core/config/`）

| Test ID | 情境 | 驗收條件 |
| :--- | :--- | :--- |
| `CFG-ASR-001` | `driver="null"`, `engine_name=None` | validation pass |
| `CFG-ASR-002` | `driver="real_engine"`, `engine_name=None` | `ConfigValueError` |
| `CFG-ASR-003` | `driver="real_engine"`, `engine_name="sherpa_sensevoice"` | validation pass |
| `CFG-TTS-001` | `driver="null"`, `engine_name=None` | validation pass |
| `CFG-TTS-002` | `driver="real_engine"`, `engine_name=None` | `ConfigValueError` |
| `CFG-EXAMPLE-001` | 新版 `config.example.yaml` 完整 `load_config()` | 無 `ConfigValueError` |

### Regression

`python -m pytest -v -m "not rpi"` 全數 pass，含既有 M1/M2/M3 tests。

---

## 8. M2B 後的接線流程（Preview）

當 Core 收到 M2B provisional selection ACK：

1. 新建 `src/sbd/perception/listen/<engine_name>/adapter.py`，實作 `ASRAdapter` Protocol
2. `make_asr_adapter()` 新增 `elif cfg.driver == "<engine_name>": ...` 分支（lazy import）
3. `ASRConfig.driver` Literal 加入新 engine driver key；`engine_name` 欄位填入對應值
4. TTS 同上操作
5. `pyproject.toml` `[project.optional-dependencies]` 新增 candidate-specific 套件（provisional extra group，不進 `[project.dependencies]`）

整個過程不改動 `Listen` / `Speak` worker 邏輯，不改動 Protocol 定義。

---

## 9. 交接說明

- **Owner**：Developer
- **驗收**：Tester 依 §7 Test ID 驗收；所有 M1/M2/M3 regression pass
- **設計依據**：本文件、[`ch02b_workers.md`](file:///home/yee/workspace/snowboard-agent/docs/implement/ch02b_workers.md) §2.1 / §4.1、[`ch10_config.md`](file:///home/yee/workspace/snowboard-agent/docs/implement/ch10_config.md) §5–§6、`DELIVERY-AUDIO-POC-M4A-M2AB-SCOPE-ACK-003` §4
- **禁止事項**：引入任何真實 engine dependency；以未獲 ACK 的 engine name 填入 config Literal
- **完成標誌**：`python -m pytest -v -m "not rpi"` 全數 pass，含 §7 所有新增 Test ID

---

*Designer: 2026-08-25*  
*Audio POC M2B provisional selection ACK 後，Designer 另立 candidate-specific integration 設計。*
