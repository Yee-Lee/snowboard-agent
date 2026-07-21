/src/snowboard/
├── core/                       
│   ├── config/             
│   ├── logger.py           
│   ├── event_bus/          # 本機純記憶體 IPC (Queue/Asyncio)
│   └── state_manager/      # 掌管全局狀態與模組調度
│
├── wake/                   # [獨立提升] 系統觸發器 (只負責叫醒系統)
│   ├── voice/              # 喚醒詞引擎 (如 Porcupine 聽「雪板」)
│   ├── button/             # 實體 GPIO 按鈕中斷
│   └── event/              # 外部網路 API 或定時任務喚醒
│
├── perception/             # [專注收集情報] 醒來後才開始吃資源
│   ├── listen/             # ASR (將接續的語音轉文字)
│   ├── read/               # 讀取文字 Payload
│   └── look/               # 啟動相機抽幀
│
├── brain/
│   ├── orchestrator.py     # 接收感知，組合 Prompt，解析 LLM 意圖並派發任務
│   ├── llm_engine.py       
│   ├── prompt_builder.py   
│   └── memory.py           
│
├── action/                     
│   ├── speak/              
│   └── tools/              
│
└── adaptor/                    
    ├── display/            # 訂閱全局狀態，顯示畫面
    ├── leds/               
    └── external_broker/    # 負責與外部(如 MQTT / 下位機)對接


系統架構設計總結：事件驅動與星型解耦架構
「雪板」的軟體架構採用事件驅動（Event-Driven）與控制/資料面分離（Control/Data Plane Separation）的設計。

核心思想是「模組互不相識，全靠總線與狀態機溝通」：

Event Bus (資料與事件中樞)： 作為全系統的唯一神經網路。所有模組只對 Event Bus 進行 Publish (發佈) 或 Subscribe (訂閱)。

State Manager (控制大腦)： 系統的唯一獨裁者。它訂閱所有事件，維護全局狀態（IDLE, WAKE, PERCEPTION, THINK, ACTION），並下達強制指令（如：中斷說話、啟動相機）。

無狀態的工作節點 (Stateless Workers)： Wake、Perception、Brain、Action 皆為獨立進程/協程，它們不知道彼此的存在，只負責完成份內工作並回報結果。

目錄架構解釋
這套目錄嚴格對應了系統的生命週期，由上到下分別為：

core/ (核心基礎設施)

系統的神經與心臟。包含 event_bus (本機純記憶體訊息交換) 與 state_manager (全局狀態機)。所有其他模組都依賴於這裡定義的 Topic 與 Payload 格式。

wake/ (守門員 / 觸發層)

唯一 24 小時運作的極低功耗模組。 包含語音喚醒詞、實體按鈕中斷或外部網路觸發。它的唯一責任是把系統從休眠中踢醒，發佈 WAKE_UP 事件給核心，絕不處理複雜邏輯。

perception/ (感知層 / 翻譯官)

被核心喚醒後才吃資源的情報收集區。 將物理世界的混沌訊號轉為數位文字。包含 listen (耗能的串流 STT)、look (鏡頭抽幀辨識) 與 read (讀取純文字)。收集完畢後，把文字與視覺標籤丟給大腦。

brain/ — 認知與決策層 (Cognitive Level)
orchestrator.py： 認知層的指揮官。它訂閱 Perception 收集來的碎塊，從 memory 提取上下文，組裝成完美的 Prompt 交給 LLM；並在 LLM 吐出結果後進行解析，決定下一步是該講話（轉發給 speak）還是執行任務（轉發給 tools）。llm_engine.py： 純粹的推論引擎（如 llama.cpp）。

action/ (行動層 / 執行手腳)

將數位意圖轉化為實際行動。包含 speak (TTS 語音合成) 與 tools (呼叫外部 API 或系統指令)。

adaptor/ (適配層 / 實體介面)

純粹的狀態訂閱者與翻譯員。 將系統內部狀態具現化到物理世界，包含 display (LCD 顯示當下狀態)、leds (閃爍燈號)，以及 external_broker (負責把內部指令轉成 MQTT/UART，去控制 ESP32 下位機)。它們獨立運作，損壞也不會卡死主程式。
