# Agent 重啟紀錄（2026-09-13）
- 已停止 debug，Pi 已接受關機指令；USER 明確要求將全部修改保存為 WIP commit／push，不代表完成驗證。
- Pi：snowboard-rpi5；repo：${PI_HOME}/m4b-dev-user-diag-20260913；target：${PI_HOME}/m4b-target-20260913-sLrXyC。
- 已修正 resource.py 分開讀 PSS/RSS 的競態，改同一快照；補失敗樣本、原因與原生 stderr 記錄。
- 已部署 scripts/run-pi-one-turn.sh、run-pi-two-turns.sh（共用 run-pi-voice.sh）；每輪收音 10 秒，READY 後說話，不自動填充。
- 最新真人結果：target/user-voice-1-NXN3bf；一輪流程完成、228 樣本、cleanup_proven=true，但「你是誰?」只回「,」，回答不合格。
- 逗號也出現在較早 user-pm-Om2wMS 首輪；不能宣稱是本次修改引入。原因未明；原生曾逾時並觀察到磁碟等待，因果尚未完整驗證。
- 一／兩輪模式相關 Pi Python 3.13.5 回歸：45 passed；不代表原生語意或完整 PM 通過，兩輪真人尚未驗證。
- PM／PR／PH、完整邊界／replacement 驗證及 M4B 收關均未完成；不要依先前成功宣稱判定完成，不需使用者重錄來排查。
- 重啟後先依 USER 新指示處理；詳細舊狀態在 docs/status/development.md，但其中較早驗證數字與可交付宣稱不能代表目前版本。
