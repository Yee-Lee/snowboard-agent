#!/bin/bash
# 自動化硬體診斷工具捷徑
# 取得目前腳本所在目錄的上一層（專案根目錄）
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "啟動自動化硬體診斷 (hw_diag.py)..."
PYTHONPATH=src .venv/bin/python3 scripts/hw_diag/hw_diag.py
