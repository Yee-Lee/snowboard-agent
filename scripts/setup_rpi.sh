#!/usr/bin/env bash
# One-shot setup for a fresh Raspberry Pi OS on RPi5.
# Enables SPI/I2S, installs system packages, and creates a Python 3.11 venv.
set -euo pipefail

sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2s 0 || true   # some images expose I2S via dtoverlay only
sudo raspi-config nonint do_camera 0

sudo apt-get update
sudo apt-get install -y \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    libatlas-base-dev libportaudio2 \
    mosquitto mosquitto-clients

python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

echo "Snowboard base environment ready (Python 3.11). Fetch models into ./models/ next."
