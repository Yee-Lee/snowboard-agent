# Core Team → Audio POC Team: M4a Gate 1A Planning ACK

- **Delivery ID**: `DELIVERY-AUDIO-POC-M4A-G1A-PLANNING-ACK-001`
- **Related handoff**: `PM-OUT-260817-016-m4a-poc-core-evidence-handoff`
- **Related contract**: `DELIVERY-AUDIO-POC-M4A-CONTRACT-001`, revision `2026-08-17 / PM-OUT-260817-016`
- **Reviewed response**: `poc_audio/deliveries/RESP-AUDIO-M4A-GATE-PLAN-001.md`
- **Reviewed POC branch / commit**: `dev_audio_m2` / `5d4086d2ae9011c559b10012b55414a87a3a8522`
- **Status**: `ACCEPTED — GATE 1A PLANNING ONLY; GATE 1B CANDIDATE SCOPE PENDING`
- **Owner**: Core Team Designer
- **User decision**: `Accepted 2026-08-17`
- **Architecture change**: `No`

## 1. Disposition

Core接受`RESP-AUDIO-M4A-GATE-PLAN-001`作為本contract的committed executable plan。其WP0～WP5、S0～S5、P1～P12 crosswalk、evidence boundary、failure / fallback與portable conformance kit規劃可作後續執行基準，不要求Audio POC重寫計畫。

本ACK只關閉Gate 1A planning。它允許§3列明的provenance-only acquisition及artifact-independent fake / protocol scaffold；不核准任何candidate row，不允許build、install、import、inference、benchmark、Pi candidate run或production dependency / model / voice lock。Gate 1B仍須由POC回交exact candidate proposal，再由Core另發candidate-scope ACK。

## 2. D01～D05 written decisions

| Decision | Core decision | Binding effect |
| :--- | :--- | :--- |
| `M4A-G1-D01` | **Accept `zh-TW`** | M1已凍結的100-item fixture、ASR references與20 TTS prompts繼續有效；Audio POC較嚴格的CER、sentence correctness、TTS median / critical-misread gate不得被Core最低門檻放寬。切換語言須走change request並重凍fixture / metric |
| `M4A-G1-D02` | **Authorize VAD in Audio POC evaluation scope** | Gate 1B可提出Silero VAD ONNX與WebRTC VAD exact variants；VAD與endpoint state machine維持`perception/listen`或`voice_wake`軟體責任，位於HAL之外。本ACK不選定Core M4a production dependency，也不授權真實candidate執行 |
| `M4A-G1-D03` | **Accept Gate 1A / 1B split** | Gate 1A只允許§3的provenance-only acquisition；Gate 1B ACK只核准明列的candidate / model / voice / quantization rows進入build與Gate 2A，不得用同名artifact替換 |
| `M4A-G1-D04` | **Core Designer owns the P9 surrogate** | Core須在WP4 / S4 entry前交付versioned deterministic surrogate identity、checksum、command、RSS / thread / CPU envelope與decision rule。交付前P9保持`Blocked`，Audio POC不得自製替代stub或轉Pass |
| `M4A-G1-D05` | **Use separate ACKs** | 本文件是G1A planning ACK；未來G1B candidate-scope ACK須引用POC proposal full SHA並逐列列出accepted / rejected rows。Receipt、elapsed time或branch name不構成授權 |

## 3. Gate 1A permitted / prohibited actions

### Permitted before Gate 1B

- 從POC proposal列明的upstream取得immutable source archive、model / voice artifact及license / notice資料，保存於受控、非Git artifact area；記錄URL、取得時間、檔名、size與SHA-256。
- 為確認identity、license與dependency metadata解包或讀取檔案；產出sanitized manifest、transitive dependency / notice表與offline aarch64 build proposal。
- 以fake assets建立protocol、schema、validator、cleanup assertion與conformance-kit skeleton；執行不載入真實candidate的portable unit tests。

### Prohibited before Gate 1B

- Build、install、import、load或execute任何真實VAD / ASR / TTS runtime、model或voice。
- 執行inference、quality / latency / resource benchmark、Pi candidate run、HAL candidate integration或User scoring。
- 將archive、weights、wheel、`.so`、raw/private audio或大型raw result提交任一Git repo，或把acquisition誤標為candidate eligibility / Pass。

Gate 1B proposal須回交每個variant的immutable upstream identity、POC-computed checksum、engine + artifact license / notice、transitive dependencies、aarch64 build recipe、native input/output format、offline cache與受控artifact locator。Core只審核該exact proposal SHA。

## 4. AudioOutput format clarification

每個TTS variant須在Gate 1B揭露native PCM。Gate 2A selection ACK可記錄POC finalist的native format，供artifact-independent adapter interface與Gate 2B evidence使用；它不是production config freeze。`audio.output.stream_format`、engine / model / voice與dependency lock只在Gate 2B final reference intake後固定。TTS / Speak不得隱式resample；若candidate不能直接符合其揭露格式與產品output contract，須Fail或提出change request。

## 5. P9 surrogate delivery point

Core Designer建立的surrogate specification至少包含：stable ID / revision、script或artifact checksum、process / thread model、steady / peak RSS或PSS reservation、CPU load pattern、duration、thermal / throttling觀察、啟動READY與bounded cleanup、完整command及PASS / FAIL / Blocked規則。它只保留M4b resource envelope，不模擬語意品質，也不能取代LLM Gate 2B或Core product combined test。

交付期限是Audio POC `WP4 / S4` entry之前；它不是WP1 provenance或WP2 fake scaffold的前置條件。若到期仍未交付，WP4 P9維持`Blocked`，其他不依賴P9且entry成立的packet可繼續，但Gate 2A不能close。

## 6. Relay and closure

Core durable ACK path即本文件。Core Designer在本delivery commit完成後，直接以path、Core branch與full SHA交付Audio POC Team；PM / User只記錄該immutable outcome，不代傳技術裁決。Audio POC無須為接受本ACK建立行政commit；其後續G1B proposal commit即為下一個return packet，直接通知Core時須提供path、branch與full SHA。

Core已在本地解析reviewed POC commit；但核對時`origin/dev_audio_m2`仍停在`aad41ce13333bdf94bf6d6ab0996f83982f9f0b1`。Audio POC須將`5d4086d2ae9011c559b10012b55414a87a3a8522` push至約定remote，Core再記錄durable intake。016在POC commit remote可取得且本ACK committed / directly delivered後close；不等待Gate 1B或Gate 2A / 2B實測。
