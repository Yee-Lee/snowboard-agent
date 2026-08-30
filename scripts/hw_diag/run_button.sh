#!/bin/bash
# 實體按鈕手動測試工具捷徑
# 取得目前腳本所在目錄的上一層（專案根目錄）
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "啟動按鈕手動測試 (button_test.py)..."
PYTHONPATH=src .venv/bin/python3 scripts/hw_diag/button_test.py
