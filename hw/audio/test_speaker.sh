#!/bin/bash

echo "=== 開始 MAX98357A 喇叭測試 ==="

# 1. 檢查驅動是否有載入
if lsmod | grep -E "max98357a|voicehat" > /dev/null; then
    echo "[ OK ] 音訊核心模組已載入。"
else
    echo "[警告] 未偵測到相關核心模組，請確保 config.txt 已設定並重啟。"
fi

# 2. 列出目前的播放裝置
echo "------------------------------------"
echo "目前的播放裝置清單 (aplay -l):"
aplay -l
echo "------------------------------------"

# 3. 尋找指定的卡號
CARD_NUM=$(aplay -l | grep -E "MAX98357A|voicehat" | head -n 1 | cut -d ' ' -f 2 | tr -d ':')

if [ -z "$CARD_NUM" ]; then
    echo "[錯誤] 找不到 MAX98357A 或 voicehat 裝置！將嘗試使用預設裝置播放..."
    PLAY_DEV="default"
else
    echo "[資訊] 偵測到音訊卡號: card $CARD_NUM"
    PLAY_DEV="hw:$CARD_NUM,0"
fi

# 4. 執行音效測試
echo "準備播放測試語音 (Front Left / Front Right)..."
echo "使用裝置: $PLAY_DEV"
echo "提示: 按 Ctrl + C 可以提前結束測試。"
echo "------------------------------------"

speaker-test -D $PLAY_DEV -c 2 -t wav -l 2

echo "=== 喇叭測試結束 ==="
