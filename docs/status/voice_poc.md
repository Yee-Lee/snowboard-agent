# Voice POC 進度

- 更新：2026-10-27
- 任務來源：[REQUEST-VOICE-POC-RVC-MATCHA-001](../outsource/pm_handoff/REQUEST-VOICE-POC-RVC-MATCHA-001.md)；[原始提案](../outsource/pm_handoff/proposal_voice_poc.md)
- 工作分支：`voice`；產品 TTS 基準仍見 [model_spec.md §2.3](../model_spec.md#23-tts)
- 執行方法與資料布局：[Voice POC 工作骨架](../voice_poc/README.md)
- 狀態：環境與輸入盤點中；尚無 P0–P5 實驗結果。

## 目標與決策邊界

驗證以英文目標音源訓練的 RVC 能否保留中文清晰度與四聲，確認少量轉換語料能否訓練並匯出供 `sherpa-onnx==1.13.5` 使用的中英 TTS，最後在 Raspberry Pi 5 完整 App 中量測聽感、延遲和記憶體。現有 Matcha `sid=0` 是比較基準。P2 與 P3 都通過才做 P4；是否納入產品留待 M7 Accepted 後、BETA 設計前決定。

## 階段

| 階段 | 目前進度 | 下一個具體動作 |
| --- | --- | --- |
| P0 比較樣本 | 已備 10 句草案與三軸試聽方式；尚待選定 | 與使用者固定 8–12 句編號台詞；在指定 Mac 產生同句 Matcha 基準音。 |
| P1 英文目標素材 | 待素材 | 取得使用者約 20 分鐘原音；盤點可用時長、單人一致性，切分訓練與未訓練參考片段。 |
| P2 RVC 小試 | 待 P0/P1 與中文原聲 | 只轉換固定句，先判斷聲調、清晰度、音色與偽影。 |
| P3 Matcha 路徑 | 本機靜態盤點完成；上游與實機核查待做 | 在 arm64 Mac mini 核對 `.pt`、config、recipe、前端與 ONNX 介面，做短訓→匯出→`sherpa-onnx` 合成閉環。 |
| P4 小批 TTS | 未開啟 | P2/P3 都通過後才取小批轉換語料，保留未見句。 |
| P5 Pi 整合 | 未開啟 | 有候選模型後在 Pi 5 完整 App 量測與真人試聽。 |

## 工作環境與資料位置

- 目前 checkout 並非指定的訓練機，只完成文件與靜態盤點；任務指定 P0–P4 在 **arm64 Mac mini 原生環境／PyTorch MPS** 執行，P5 在 **Raspberry Pi 5** 執行。尚未在兩台目標機建立環境或執行實驗。
- 已建立 Git 忽略的 `private-evidence/voice-poc/`：`inputs/target-en/{raw,clean,holdout}`、`inputs/source-zh`、`inputs/tts-smoke`、`baseline`、`runs/{rvc,tts}`、`models`、`logs`。原音、生成音、模型與私有試聽結果只放在此類 Git 外目錄；移往 Mac 時沿用相同相對結構。
- 本 checkout 未具備 `ffmpeg`／`ffprobe`、`sox`、PyTorch／torchaudio、`sherpa_onnx`、ONNX Runtime、soundfile、librosa；不能據此推定 Mac mini 的套件狀態。Mac 上應按[工作骨架](../voice_poc/README.md)逐項檢查，再決定安裝。

## 已有輸入與待取得項目

| 項目 | 現況／需要 |
| --- | --- |
| 產品 Matcha 基準 | [model_spec.md §2.3](../model_spec.md#23-tts)、[鎖定檔](../../requirements/m4a/audio-artifacts.json)、[前端 closure](../../requirements/m4a/matcha-closure.json) 與 [worker](../../src/sbd/action/speak/matcha/worker.py) 已在 repo；本 checkout 未找到實際 ONNX／Vocos payload 或可重播 P0 基準音。 |
| 英文目標音源 | 交接稱使用者已收集約 20 分鐘；本 checkout 尚未取得音檔、來源／片段清單或可用時長。 |
| 中文原聲與文字 | 尚無固定台詞、同句中文女聲原音、對齊 transcript；需選能保留四聲、咬字與角色韻律的來源。 |
| P3 訓練輸入 | 上游 ModelScope `.pt`、revision、config、訓練 recipe、token／lexicon 對應及匯出腳本尚未核實或取得；不能由產品 ONNX 推定可微調。 |
| 腳本 | repo 有產品 Matcha worker、adapter、安裝／preflight 腳本；未見本 POC 的 RVC 訓練、素材切句、Matcha 微調／匯出或試聽比較腳本。應先核實上游可用流程，再只補閉環所需腳本。 |

## 接下來

1. 在 Mac mini 查明 CPU／記憶體、macOS、Python、MPS、音訊工具及可用儲存空間，並定位既有產品 Matcha／Vocos payload；在確認相容版本後才建立隔離環境。
2. 固定 P0 台詞與聽感優先順序，取得英文素材與中文原聲的實際位置；原音只進私有工作目錄。
3. 優先核查 P3 上游訓練／匯出可行性；P2 只做固定句最小試驗。依兩者結果決定是否進 P4。
