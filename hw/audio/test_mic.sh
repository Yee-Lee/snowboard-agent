#!/bin/bash

echo "=== 開始 INMP441 麥克風測試 ==="

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
    #REC_DEV="hw:0,0
    REC_DEV="plughw:0,0"
else
    echo "[資訊] 偵測到錄音卡號: card $CARD_NUM"
    #REC_DEV="hw:$CARD_NUM,0"
    REC_DEV="plughw:$CARD_NUM,0"
fi

WAV_FILE="mic_test_48k.wav"

# 3. 開始錄音
echo "------------------------------------"
echo "請對著麥克風說話，即將開始錄音 5 秒鐘..."
echo "使用裝置: $REC_DEV"
echo "------------------------------------"

# 使用 48kHz, S32_LE 格式錄音以確保 I2S 麥克風相容性
#arecord -D $REC_DEV -d 5 -c 2 -r 48000 -f S32_LE $WAV_FILE
arecord -D $REC_DEV -d 5 -c 2 -r 44100 -f S16_LE $WAV_FILE

if [ $? -eq 0 ]; then
    echo "[ OK ] 錄音完成，檔案儲存為: $WAV_FILE"
else
    echo "[錯誤] 錄音失敗，請檢查接線或裝置狀態。"
    exit 1
fi

# 4. 詢問是否播放
echo ""
read -p "是否要立刻播放剛才的錄音？(y/n): " choice

if [[ "$choice" == "y" || "$choice" == "Y" ]]; then
    echo "正在播放錄音..."
    # 播放時尋找播放卡號
    PLAY_CARD=$(aplay -l | grep -E "MAX98357A|voicehat" | head -n 1 | cut -d ' ' -f 2 | tr -d ':')
    if [ -z "$PLAY_CARD" ]; then
        aplay $WAV_FILE
    else
#        aplay -D hw:$PLAY_CARD,0 $WAV_FILE
        aplay -D plughw:$PLAY_CARD,0 $WAV_FILE
    fi
else
    echo "已取消播放。你可以稍後自行執行 'aplay $WAV_FILE' 來聆聽。"
fi

echo "=== 麥克風測試結束 ==="
