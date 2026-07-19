#!/bin/bash

# 取得放大倍率參數，如果沒有輸入則預設為 1
MULTIPLIER=${1:-1}

echo "=== 開始 INMP441 麥克風測試 ==="
echo "[設定] 預計放大倍率: $MULTIPLIER 倍"

# 1. 列出目前的錄音裝置
echo "------------------------------------"
echo "目前的錄音裝置清單 (arecord -l):"
arecord -l
echo "------------------------------------"

# 2. 尋找錄音卡號
CARD_NUM=$(arecord -l | grep -E "snd-snd-pi-i2s|voicehat|dmic" | head -n 1 | cut -d ' ' -f 2 | tr -d ':')

# 如果自動抓不到，預設帶入 card 0
if [ -z "$CARD_NUM" ]; then
    echo "[提示] 未精準比對到關鍵字，預設使用 card 0 進行錄音。"
    REC_DEV="plughw:0,0"
else
    echo "[資訊] 偵測到錄音卡號: card $CARD_NUM"
    REC_DEV="plughw:$CARD_NUM,0"
fi

RAW_WAV="mic_test_raw.wav"
AMP_WAV="mic_test_amplified.wav"

# 3. 開始錄音
echo "------------------------------------"
echo "請對著麥克風說話，即將開始錄音 5 秒鐘..."
echo "使用裝置: $REC_DEV"
echo "------------------------------------"

# 錄製原始音檔
arecord -D $REC_DEV -d 5 -c 2 -r 44100 -f S16_LE $RAW_WAV

if [ $? -eq 0 ]; then
    echo "[ OK ] 原始錄音完成，檔案儲存為: $RAW_WAV"
else
    echo "[錯誤] 錄音失敗，請檢查接線或裝置狀態。"
    exit 1
fi

# 4. 呼叫 Python 進行訊號放大
echo "------------------------------------"
echo "正在透過 Python 放大音訊訊號 ($MULTIPLIER 倍)..."
python3 amplify.py $RAW_WAV $AMP_WAV $MULTIPLIER

if [ $? -eq 0 ]; then
    echo "[ OK ] 音訊處理完成，產生檔案: $AMP_WAV"
else
    echo "[錯誤] Python 音訊處理失敗，請確認有安裝 numpy (pip install numpy)。"
    exit 1
fi

# 5. 詢問是否播放
echo "------------------------------------"
read -p "是否要立刻播放處理後的錄音？(y/n): " choice

if [[ "$choice" == "y" || "$choice" == "Y" ]]; then
    echo "正在播放放大的錄音 ($AMP_WAV)..."
    # 播放時尋找播放卡號
    PLAY_CARD=$(aplay -l | grep -E "MAX98357A|voicehat" | head -n 1 | cut -d ' ' -f 2 | tr -d ':')
    
    if [ -z "$PLAY_CARD" ]; then
        aplay $AMP_WAV
    else
        aplay -D plughw:$PLAY_CARD,0 $AMP_WAV
    fi
else
    echo "已取消播放。你可以稍後自行執行 'aplay $AMP_WAV' 來聆聽。"
fi

echo "=== 麥克風測試結束 ==="
