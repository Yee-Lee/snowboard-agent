# Voice POC 工作骨架

本目錄說明到 Mac 工作站後如何啟動獨立 Voice POC。當前進度見[進度文件](../status/voice_poc.md)；任務邊界、各階段前進條件及兩個最小實驗以[正式請求](../outsource/pm_handoff/REQUEST-VOICE-POC-RVC-MATCHA-001.md)為準。現有產品 TTS 設定以[模型規格 §2.3](../model_spec.md#23-tts)為比較基準，不因本 POC 改寫。

## 先做的事

1. 在 arm64 Mac mini 原生環境確認 `uname -m` 為 `arm64`，記錄可用記憶體／磁碟，檢查 Python、`ffmpeg`／`ffprobe`、PyTorch MPS 是否可用。訓練及批次轉換不在 x86 UTM 執行。先確定上游實際需要的版本，再建立專用虛擬環境；不要把訓練依賴加入 Core 的 `pyproject.toml`。
2. 在 Git 外準備下列相對路徑，將英文原音、清理片段、保留參考、中文原聲與普通中文 smoke 語料放入對應目錄。這些路徑在本 checkout 已建好，但空目錄不會隨 Git 傳到 Mac；到 Mac 後重新建立即可。

   ```text
   private-evidence/voice-poc/
     inputs/target-en/{raw,clean,holdout}/
     inputs/source-zh/
     inputs/tts-smoke/
     baseline/
     runs/{rvc,tts}/
     models/
     logs/
   ```

3. 定位現有 Matcha 聲學模型包、`vocos-16khz-univ.onnx` 與隔離的 `sherpa-onnx==1.13.5` 環境；repo 的[產品鎖定檔](../../requirements/m4a/audio-artifacts.json)、[前端 closure](../../requirements/m4a/matcha-closure.json)與[推論 worker](../../src/sbd/action/speak/matcha/worker.py)只提供規格和介面，不包含模型 payload。先核查來源與可用性，再產生 P0 基準音。
4. 從任務交接的 ModelScope 來源核對 `.pt` 的確切檔名／revision、config、訓練 recipe、中英前端、匯出入口與 Vocos 相容性。記錄缺口後才決定需要補哪些 POC 腳本；現有 repo 沒有 RVC 訓練或 Matcha 微調／匯出腳本。

## P0 固定比較句

下表是供使用者選定的**草案**，還不是已鎖定的測試集。選定 8–12 句後保留編號與逐字稿，讓中文原聲、既有 Matcha、RVC、TTS 使用同句。使用者需說明「中文自然」與「目標音色相似」何者優先。

| ID | 台詞草案 | 要聽的風險 |
| --- | --- | --- |
| S01 | 慢一點，板子會等你。 | 短句、收尾清晰度 |
| S02 | 先看坡，再看我。 | 短停頓與語氣 |
| S03 | 買板容易，賣板難；滑得好看更難。 | 聲調與近音字 |
| S04 | 右腳先踩穩，左腳再轉向。 | 動作指令可懂度 |
| S05 | 這不是摔倒，是和雪地開個短會。 | 幽默語氣、長句 |
| S06 | 今天的 powder 很軟，別把勇氣滑成衝動。 | 中英混說銜接 |
| S07 | Ollie，先收膝，再把板頭帶起來。 | 名稱與中英混說 |
| S08 | 坡度變陡了，先減速，再選下一條線。 | 安全指令與聲調 |
| S09 | 你剛才那一跳很漂亮，落地卻有自己的想法。 | 較長句、角色感 |
| S10 | Ready？呼吸、看前方，然後滑。 | 英文起句與短節奏 |

P0 產物放 `baseline/`，每句保留原文和 16 kHz mono 輸出。試聽時對每句記三個面向：**中文可懂／四聲、目標音色、角色語氣**；各用 `PASS`、`BORDERLINE` 或 `FAIL`，並記具體失敗句與瑕疵。公開進度只記摘要，不貼原音或私人試聽逐字內容。

## P1–P5 的最小執行順序

| 階段 | 操作與保留結果 | 繼續條件 |
| --- | --- | --- |
| P1 | 盤點約 20 分鐘英文原音的實際可用時長、片段數、噪聲／重疊人聲；分出 `clean` 與未進訓練的 `holdout`。 | 有單人、音色一致的訓練片段與獨立參考。 |
| P2 | 以 P1 英文片段訓練一版 RVC，只轉換 P0 同句中文女聲；對比原聲、Matcha 與英文參考，記錄訓練時間、記憶體及聲調／金屬音問題。 | 中文可懂、四聲保留，音色提升值得繼續；系統性失真先作單輪有因修正，再決定停止或前進。 |
| P3 | 用極小量普通中文語料載入 `.pt`、短訓數步、匯出 ONNX、搭配既有前端與 Vocos 在 `sherpa-onnx==1.13.5` 合成 P0 中英句，記錄耗時、記憶體與具體相容斷點。 | 訓練→匯出→離線合成可重現，輸出規格與前端正常；否則評估替代 TTS 及 Core adapter 影響。 |
| P4 | **僅 P2、P3 都通過後**，轉換小批中文語料並訓練一版 TTS；以未見句和 P0 基準比清晰度、自然度與音色。 | 未見句有價值才考慮擴充。 |
| P5 | 有候選後在 Pi 5 完整 App 中測首段出聲、整句時間、峰值 RSS、中英混說、中斷、重新使用與真人聽感。 | 對照現有 ALPHA 基準，給出 `SUPPORTED`／`NOT_SUPPORTED`／`INCONCLUSIVE`。 |

P2 與 P3 可並行。每次實驗只保留足以判斷上述產品風險的結果；不在執行腳本或產品啟動時加入自動內容 digest、行政簽核或重複的 closure 測試。產品採用若成立，另走 `Design → Test Spec → Developer → Verify`，並在 Pi 驗證正式待提交內容。

## 到 Mac 前仍需取得

- 使用者英文目標音源的實際位置，以及可供 P1 篩選的原檔。
- P0 草案台詞取捨、兩項聽感目標的優先順序，與同句中文女聲原聲／transcript 來源。
- Mac 上既有產品 Matcha／Vocos payload、RVC／Matcha 上游來源及可用加速資源的實際位置；若缺少，先查明可取得版本與環境相容性。
