Snowboard Agent：角色音線 Audio Voice POC 規劃輸入
更新日期：2026-10-26
性質：供 Snowboard 專案 AI／Designer 納入正式規劃的提案輸入；不是已核准的 milestone、產品 baseline 或實驗結果。
1. 目標與邊界
為雪板／Ollie 探索一種以 Anne Hathaway 的聲音特徵為目標、能自然說中文（兼顧中英混說）、符合「精簡、幽默、帶點歪理」角色感的本機語音。終端目標是在 Raspberry Pi 5 的現有離線語音 App 中，以可接受的延遲、音質和整機資源運作。此階段是技術 POC；是否採用於真實產品與素材使用範圍另行決定，不作本 POC 的技術阻塞項。

現有 M4／ALPHA Matcha TTS 是比較基準；POC 不直接替換它。優先回答三個問題：
1. 英文目標音源訓練的 RVC，能否將原本咬字與聲調清楚的中文轉為值得繼續追求的目標音色？
2. 能否以少量轉換後的中文語料訓練 TTS、匯出可運行模型，並保住中文清晰度與音色？
3. 新模型能否在完整 Pi App 與 ASR／Gemma／Display 共存時，達到可接受的反應時間與記憶體使用？
以上三題的通過標準須由 Designer／Tester 在實驗前訂清楚，保留主觀試聽與客觀量測兩類結果；不預先保證「完美複製」或「零外國腔」。
2. 已知現況與技術討論紀錄
已驗證或可查證
- Core docs/status/current.md（2026-10-25）：M5.tool Accepted；M5 MQTT Developer entry 已開啟。主線依序為 M5 MQTT → M6 Look → M7 → BETA。BETA 是當時已納入能力的產品收斂 gate。
- Core docs/model_spec.md：目前 TTS 為 sherpa-onnx==1.13.5、matcha-icefall-zh-en/model-steps-3.onnx、vocos-16khz-univ.onnx；單一聲音 sid=0，CPU 2 threads，16 kHz mono 輸出。這些是推論規格，不等同可微調訓練環境。
- 上游模型來源指向 ModelScope dengcunqin/matcha_tts_zh_en_20251010。其模型頁搜尋結果顯示已有 V1 .pt checkpoint；但其檔案、版本與目前 ONNX 的對應、訓練 recipe、匯出及前端相容性尚未實際核查。不可寫成「沒有 checkpoint」，也不可寫成「已確定能直接微調」。
- 使用者表示已收集約 20 分鐘 Anne Hathaway 英文音源；尚未在本交接中取得音檔或驗證品質。
先前與另一 AI 的構想及本次修正
原構想：清理英文目標音源 → 訓練 RVC → 以發音清楚的中文女聲語料經 RVC 批次轉換 → 用轉換後的中文語料訓練／微調 Matcha-TTS → ONNX 匯出 → Pi 5 以 sherpa-onnx 推論。把昂貴的 RVC 放在離線資料製作期，產品端只跑 TTS，是值得驗證的設計方向。

先前 AI 曾主張「凍結 text encoder、更新 speaker embedding 就能保證標準中文＋目標音色」、「20 分鐘素材完美足夠」、「RVC 資料蒸餾徹底消除外國腔」、「一行匯出 ONNX 且幾秒完成」、「Pi 上毫秒級延遲」。這些不是本專案測試結論；尤其現有模型的 sid=0 不代表可直接替換 speaker embedding。RVC 可能改壞聲調或帶入金屬音，二次訓練也可能放大瑕疵。需以小樣本驗證。

可用官方參考：
- 專案現況：https://github.com/Yee-Lee/snowboard-agent/blob/core/docs/status/current.md
- 產品模型鎖定：https://github.com/Yee-Lee/snowboard-agent/blob/core/docs/model_spec.md
- BETA 範圍：https://github.com/Yee-Lee/snowboard-agent/blob/core/docs/milestones/BETA.md
- sherpa-onnx Matcha 模型用法：https://k2-fsa.github.io/sherpa/onnx/tts/all/Chinese-English/matcha-icefall-zh-en.html
- 上游模型：https://modelscope.cn/models/dengcunqin/matcha_tts_zh_en_20251010
- RVC 官方 FAQ：https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI/wiki/FAQ-(Frequently-Asked-Questions)
- sherpa-onnx 自訂 Matcha 的 metadata／vocoder 接口討論：https://github.com/k2-fsa/sherpa-onnx/issues/1779
3. 排程位置與分階段執行
建議建立獨立 Audio Voice POC，可在 M5 MQTT 開發期間並行研究；不插入 M5 MQTT／M6 Look 的既定驗收。完成 POC 後，於 M7 Accepted 後、BETA 設計前做一次是否納入產品的決策。若 POC 時間或結果未達標，BETA 繼續使用已驗收音色。正式納入時依專案 Design → Test Spec → Developer → Verify 流程處理 TTS baseline 變更、產品配置與 Pi 驗證；不以 POC 聽感取代正式產品驗收。
階段	最小工作／交付	使用者人工工作	自動化與算力	前進條件
P0 目標與比較樣本	固定 8–12 句中文／中英混說雪板台詞，含聲調、短句、長句、幽默語氣；保存現有 Matcha 基準輸出	選台詞、說明「像」與「自然」的優先順序：中	生成基準音與記錄可自動化；無訓練	有可重播的同句比較與判讀項目
P1 20 分鐘素材盤點	記下來源、可用時長；切句、去除重疊人聲、過強角色音／背景音，留未訓練的參考片段	親聽、挑片段：中高	切句、格式統一、初篩可批次；本機 CPU／一般加速	得到單人、音色相對一致的英文訓練集
P2 RVC 最小試驗	訓練一版 RVC，只轉 8–12 句中文；與中文原聲、目標英文參考比較	逐句試聽中文聲調、清楚度、音色、金屬音：中	訓練及批次轉換可腳本化；需可用加速資源，時間依硬體實測	中文可懂、聲調保留，且音色有值得追求的提升；否則先修資料／RVC 或停止本路徑
P3 TTS 路徑核查	清點上游 .pt、config、訓練 recipe、tokens／lexicon、16 kHz Vocos 與現有 ONNX 的版本關係；用普通中文小資料完成「載入→短訓→匯出→離線合成」	聽一個技術 smoke 樣本；主要工程判讀：低	多為程式與環境工作，短訓需 GPU；在大批資料轉換前完成	確認可重現的訓練與 sherpa-onnx 輸出；若不相容，評估另一可訓練 TTS 與 Core TTS adapter
P4 小批 TTS	只轉換一小批中文訓練語料，保留未見過的句子；訓練一版新音色 TTS，與基準及 P2 輸出對照	抽查資料與 checkpoint、判斷是否兼顧中文自然度和目標音色：中高	轉換與訓練可批次；本階段主要 GPU 成本，不預設固定時數	未見句的中文仍清晰、自然且音色有價值；否則調整或停止，不直接擴充到數小時
P5 擴充與 Pi 整合	必要時擴充資料與模型；以現有 App 測首段出聲、整句時間、峰值 RSS、中英混說、中斷、重新使用及聽感	真人操作、聽感與採用判斷：中高	測量可自動化；Pi CPU 推論，不在 Pi 訓練	對照 ALPHA 基準，決定採用、繼續研究或保留現狀


P2 與 P3 可以並行，兩者都成功才啟動 P4。P5 的效能界線應看產品體驗與現有完整 App 的實測，不以「單獨 TTS 能跑」或未量測的毫秒數代替。
4. 待定項目與專案 AI 的下一步
1. 先確認訓練路徑：列出 ModelScope .pt 的確切檔案、修訂版、模型結構／config、所需中文前端與訓練 recipe；檢查是否能重現現有 ONNX，或只能作相近的新候選。這件事在訓練前就可查，不能等待訓練完成才判斷。
2. 中文來源語料：選一個咬字與角色韻律適合的中文女聲來源；確認音檔和 transcript／切句品質。AISHELL-3／DataBaker 是資料集名稱，不是可直接微調的模型 checkpoint；不要先假設要轉換 5–10 小時。
3. 算力配置：先核對使用者實際可用的 arm64 原生訓練資源與 RVC、TTS 程式支援；P2／P3 小試驗量出時間與記憶體後，再估完整訓練成本。
4. 品質判斷：由使用者用固定句子聽 RVC 與 TTS 的三個獨立面向：中文可懂與聲調、音色相似感、雪板角色語氣；記錄具體失敗句，不以一句「像／不像」代表全部。
5. 產品納入：若 POC 成功，正式 Designer 定義新的 TTS baseline、artifact provenance、版本配置、前端／聲碼器與 Core adapter delta；Tester 只驗新增與直接受影響路徑，Developer／Verify 依 Pi 同 bytes 規則交付。與 M5／M6／M7 的既有 Accepted 證據分開。
6. 使用範圍：本輪使用者要求暫不以版權／正式產品發布為阻塞；若將來公開展示、分享模型或採用真實產品，再單獨確定素材與聲音的使用範圍。不要把此待定項寫成已取得授權。
請專案 AI 先把本文件轉為獨立 POC 的設計輸入與兩個最小實驗（P2、P3），核對 current authority 與現有 Audio／Core 文件後再決定具體文件位置及 milestone 命名；不要因本提案自行改動 M5 MQTT active work、既有 TTS 產品鎖或已 Accepted 的結果。
