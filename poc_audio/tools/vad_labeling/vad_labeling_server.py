#!/usr/bin/env python3
"""Interactive Web-based VAD Labelling & Review Server for Audio POC."""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import sys
import urllib.parse
import wave

DEFAULT_PORT = 8765
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PLAN = REPO_ROOT / "poc_audio/fixtures/authorized/recording_plan_v1.json"
DEFAULT_ARTIFACT_DIR = REPO_ROOT / "poc_audio/fixtures/artifacts/m1-authorized-zh-tw-v1-pilot-r1"
DEFAULT_OUTPUT = DEFAULT_ARTIFACT_DIR / "review/vad-labels-v1.json"

HTML_CONTENT = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VAD Labelling & Review Tool (Audio POC)</title>
<style>
:root {
  --bg: #0f172a;
  --panel: #1e293b;
  --panel-border: #334155;
  --text: #f8fafc;
  --text-muted: #94a3b8;
  --primary: #38bdf8;
  --primary-hover: #0ea5e9;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --speech-bg: rgba(16, 185, 129, 0.35);
  --speech-border: #10b981;
  --pause-bg: rgba(245, 158, 11, 0.35);
  --pause-border: #f59e0b;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans TC", sans-serif;
  background-color: var(--bg);
  color: var(--text);
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

header {
  background: var(--panel);
  border-bottom: 1px solid var(--panel-border);
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

header h1 {
  font-size: 1.15rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}

.badge {
  font-size: 0.75rem;
  padding: 3px 8px;
  border-radius: 4px;
  background: #334155;
  color: #cbd5e1;
}

.badge-success { background: #065f46; color: #6ee7b7; }
.badge-warning { background: #78350f; color: #fcd34d; }

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.btn {
  background: #334155;
  color: var(--text);
  border: 1px solid var(--panel-border);
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s;
}

.btn:hover { background: #475569; }
.btn-primary { background: #0284c7; border-color: #38bdf8; }
.btn-primary:hover { background: #0369a1; }
.btn-success { background: #059669; border-color: #34d399; }
.btn-success:hover { background: #047857; }

.speed-btn-group {
  display: inline-flex;
  background: #0f172a;
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  overflow: hidden;
}

.btn-speed {
  background: transparent;
  color: var(--text-muted);
  border: none;
  padding: 6px 12px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-speed:hover { background: #334155; color: #fff; }
.btn-speed.active { background: #0284c7; color: #fff; }

.main-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Sidebar */
.sidebar {
  width: 320px;
  background: var(--panel);
  border-right: 1px solid var(--panel-border);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--panel-border);
  font-size: 0.85rem;
  color: var(--text-muted);
  display: flex;
  justify-content: space-between;
}

.item-list {
  flex: 1;
  overflow-y: auto;
  list-style: none;
}

.list-item {
  padding: 10px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: background 0.15s;
}

.list-item:hover { background: #334155; }
.list-item.active { background: #1e3a5f; border-left: 3px solid var(--primary); }

.item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.item-id { font-weight: 600; font-size: 0.85rem; }
.item-text { font-size: 0.8rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Workspace */
.workspace {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px 30px;
  overflow-y: auto;
  gap: 20px;
}

.card {
  background: var(--panel);
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  padding: 20px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.info-label { font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px; }
.info-val { font-size: 0.95rem; font-weight: 500; }
.display-text-hero {
  font-size: 1.25rem;
  font-weight: 600;
  color: #38bdf8;
  letter-spacing: 0.5px;
}

/* Waveform Canvas Area */
.waveform-container {
  position: relative;
  width: 100%;
  height: 200px;
  background: #090d16;
  border-radius: 6px;
  border: 1px solid var(--panel-border);
  overflow: hidden;
  user-select: none;
}

canvas#waveform {
  width: 100%;
  height: 100%;
  display: block;
}

.time-ruler {
  height: 24px;
  background: #090d16;
  border-top: 1px solid var(--panel-border);
  position: relative;
  font-size: 0.7rem;
  color: var(--text-muted);
}

/* Controls */
.control-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
}

.play-controls {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.inputs-grid {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.input-group label {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.input-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.input-num {
  background: #0f172a;
  border: 1px solid var(--panel-border);
  color: var(--text);
  padding: 6px 8px;
  border-radius: 4px;
  width: 90px;
  font-family: monospace;
  font-size: 0.95rem;
  text-align: right;
}

.btn-step {
  background: #334155;
  border: 1px solid var(--panel-border);
  color: var(--text);
  padding: 4px 6px;
  border-radius: 4px;
  font-size: 0.7rem;
  cursor: pointer;
}

.btn-step:hover { background: #475569; }

.shortcut-tip {
  font-size: 0.75rem;
  color: var(--text-muted);
  line-height: 1.5;
}

.shortcut-tip kbd {
  background: #334155;
  padding: 2px 5px;
  border-radius: 3px;
  font-family: monospace;
  color: #e2e8f0;
}

.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 12px 20px;
  background: #065f46;
  color: #fff;
  border-radius: 6px;
  font-size: 0.9rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
  transform: translateY(100px);
  opacity: 0;
  transition: all 0.3s;
}

.toast.show {
  transform: translateY(0);
  opacity: 1;
}
</style>
</head>
<body>

<header>
  <h1>
    <span>🎙️ VAD Labelling & Review Tool</span>
    <span class="badge" id="plan-badge">Audio POC</span>
  </h1>
  <div class="header-actions">
    <span id="reviewed-count" class="badge badge-warning">0 / 0 Accepted</span>
    <button class="btn btn-success" id="btn-save-all" onclick="saveAllToServer()">
      💾 儲存並產出 vad-labels-v1.json
    </button>
  </div>
</header>

<div class="main-container">
  <div class="sidebar">
    <div class="sidebar-header">
      <span>音訊清單</span>
      <span id="progress-text">0%</span>
    </div>
    <ul class="item-list" id="item-list"></ul>
  </div>

  <div class="workspace" id="workspace">
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
        <div>
          <div class="info-label" id="cur-class-badge">CLASS</div>
          <div class="display-text-hero" id="cur-text">載入中...</div>
        </div>
        <button class="btn" id="btn-toggle-accept" onclick="toggleAcceptCurrent()">
          ✅ 標記已審閱 (ACCEPTED)
        </button>
      </div>
      <div class="info-grid">
        <div>
          <div class="info-label">Fixture ID</div>
          <div class="info-val" id="cur-id">-</div>
        </div>
        <div>
          <div class="info-label">音訊總長度</div>
          <div class="info-val" id="cur-duration">-</div>
        </div>
        <div>
          <div class="info-label">分類 / 語料類型</div>
          <div class="info-val" id="cur-cat">-</div>
        </div>
        <div>
          <div class="info-label">Native SHA-256 (首8碼)</div>
          <div class="info-val" id="cur-sha">-</div>
        </div>
      </div>
    </div>

    <!-- Waveform Card -->
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <span style="font-weight:600; font-size: 0.9rem;">聲學波形與標註區間 (滑鼠拖曳兩側把手微調)</span>
        <div style="display: flex; gap: 16px; align-items: center; font-size: 0.8rem;">
          <div style="display: flex; align-items: center; gap: 6px;">
            <span style="color: var(--text-muted);">播放速度:</span>
            <div class="speed-btn-group">
              <button class="btn-speed active" id="speed-05" onclick="setPlaybackSpeed(0.5)">0.5x</button>
              <button class="btn-speed" id="speed-075" onclick="setPlaybackSpeed(0.75)">0.75x</button>
              <button class="btn-speed" id="speed-10" onclick="setPlaybackSpeed(1.0)">1.0x</button>
            </div>
          </div>

          <div style="display: flex; gap: 10px;">
            <span style="display:inline-flex; align-items:center; gap:4px;">
              <span style="width:12px; height:12px; background:var(--speech-bg); border:1px solid var(--speech-border); border-radius:2px;"></span> Speech 語音
            </span>
            <span id="pause-legend" style="display:inline-flex; align-items:center; gap:4px;">
              <span style="width:12px; height:12px; background:var(--pause-bg); border:1px solid var(--pause-border); border-radius:2px;"></span> Pause 停頓
            </span>
          </div>
        </div>
      </div>

      <div class="waveform-container" id="waveform-box">
        <canvas id="waveform"></canvas>
      </div>
      <div class="time-ruler" id="time-ruler"></div>

      <!-- Playback Controls -->
      <div class="control-panel" style="margin-top: 16px;">
        <div class="play-controls">
          <button class="btn btn-primary" id="btn-play-toggle" onclick="togglePlayPauseAudio()">▶ 播放 (Space)</button>
          <button class="btn" onclick="playInterval('speech')">🔊 播放 Speech (S)</button>
          <button class="btn" id="btn-play-pause" onclick="playInterval('pause')">🔇 播放 Pause (P)</button>
          <button class="btn" onclick="playBoundary('start')">⏮ 聽起點 (1)</button>
          <button class="btn" onclick="playBoundary('end')">⏭ 聽終點 (2)</button>
        </div>

        <div class="shortcut-tip">
          <kbd>Space</kbd> 播放/暫停(續播) | <kbd>S</kbd> 聽語音 | <kbd>P</kbd> 聽停頓 | <kbd>1</kbd>/<kbd>2</kbd> 聽邊界 | <kbd>←</kbd>/<kbd>→</kbd> 切換音檔
        </div>
      </div>
    </div>

    <!-- Fine-tune Numeric Inputs Card -->
    <div class="card">
      <div style="font-weight:600; font-size: 0.9rem; margin-bottom: 12px;">精確時間微調 (單位：毫秒 ms，10ms 粒度)</div>
      
      <div id="clear-inputs" class="inputs-grid">
        <div class="input-group">
          <label>Speech 起點 (ms)</label>
          <div class="input-row">
            <input type="number" step="10" class="input-num" id="input-s1-start" onchange="onManualInputChange()">
            <button class="btn-step" onclick="stepVal('input-s1-start', -50)">-50</button>
            <button class="btn-step" onclick="stepVal('input-s1-start', -10)">-10</button>
            <button class="btn-step" onclick="stepVal('input-s1-start', 10)">+10</button>
            <button class="btn-step" onclick="stepVal('input-s1-start', 50)">+50</button>
          </div>
        </div>

        <div class="input-group">
          <label>Speech 終點 (ms)</label>
          <div class="input-row">
            <input type="number" step="10" class="input-num" id="input-s1-end" onchange="onManualInputChange()">
            <button class="btn-step" onclick="stepVal('input-s1-end', -50)">-50</button>
            <button class="btn-step" onclick="stepVal('input-s1-end', -10)">-10</button>
            <button class="btn-step" onclick="stepVal('input-s1-end', 10)">+10</button>
            <button class="btn-step" onclick="stepVal('input-s1-end', 50)">+50</button>
          </div>
        </div>

        <div class="input-group">
          <label>Speech 總時長</label>
          <div style="font-size:1.1rem; font-family:monospace; padding-top:4px;" id="clear-duration-display">0 ms</div>
        </div>
      </div>

      <div id="pause-inputs" class="inputs-grid" style="display:none;">
        <div class="input-group">
          <label>Speech 1 起點 (ms)</label>
          <div class="input-row">
            <input type="number" step="10" class="input-num" id="input-p-s1-start" onchange="onManualInputChange()">
            <button class="btn-step" onclick="stepVal('input-p-s1-start', -10)">-10</button>
            <button class="btn-step" onclick="stepVal('input-p-s1-start', 10)">+10</button>
          </div>
        </div>

        <div class="input-group">
          <label>Speech 1 終點 (Pause 起點)</label>
          <div class="input-row">
            <input type="number" step="10" class="input-num" id="input-p-s1-end" onchange="onManualInputChange()">
            <button class="btn-step" onclick="stepVal('input-p-s1-end', -10)">-10</button>
            <button class="btn-step" onclick="stepVal('input-p-s1-end', 10)">+10</button>
          </div>
        </div>

        <div class="input-group">
          <label>Speech 2 起點 (Pause 終點)</label>
          <div class="input-row">
            <input type="number" step="10" class="input-num" id="input-p-s2-start" onchange="onManualInputChange()">
            <button class="btn-step" onclick="stepVal('input-p-s2-start', -10)">-10</button>
            <button class="btn-step" onclick="stepVal('input-p-s2-start', 10)">+10</button>
          </div>
        </div>

        <div class="input-group">
          <label>Speech 2 終點 (ms)</label>
          <div class="input-row">
            <input type="number" step="10" class="input-num" id="input-p-s2-end" onchange="onManualInputChange()">
            <button class="btn-step" onclick="stepVal('input-p-s2-end', -10)">-10</button>
            <button class="btn-step" onclick="stepVal('input-p-s2-end', 10)">+10</button>
          </div>
        </div>

        <div class="input-group">
          <label>Pause 停頓長度</label>
          <div style="font-size:1.1rem; font-family:monospace; color:#f59e0b; padding-top:4px;" id="pause-duration-display">0 ms</div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="toast" id="toast">已儲存！</div>

<script>
let globalData = null;
let currentIndex = 0;
let audioContext = null;
let currentAudioBuffer = null;
let currentSource = null;

let isPlaying = false;
let isPaused = false;
let playbackRate = 0.5;
let playStartTime = 0;
let playStartOffset = 0;
let pausedPositionSec = 0;
let currentSegmentEndSec = 0;
let animFrameId = null;

let activeHandle = null;

async function init() {
  const resp = await fetch('/api/data');
  globalData = await resp.json();
  document.getElementById('plan-badge').textContent = globalData.plan_id;
  renderSidebar();
  selectItem(0);
}

function setPlaybackSpeed(rate) {
  playbackRate = rate;
  document.getElementById('speed-05').className = 'btn-speed' + (rate === 0.5 ? ' active' : '');
  document.getElementById('speed-075').className = 'btn-speed' + (rate === 0.75 ? ' active' : '');
  document.getElementById('speed-10').className = 'btn-speed' + (rate === 1.0 ? ' active' : '');

  if (isPlaying && currentSource) {
    try {
      currentSource.playbackRate.setValueAtTime(playbackRate, audioContext.currentTime);
    } catch(e) {}
  }
}

function renderSidebar() {
  const list = document.getElementById('item-list');
  list.innerHTML = '';
  let accepted = 0;
  globalData.fixtures.forEach((item, idx) => {
    const li = document.createElement('li');
    li.className = 'list-item' + (idx === currentIndex ? ' active' : '');
    const isAccepted = item.review_status === 'ACCEPTED_BY_HUMAN_REVIEW';
    if (isAccepted) accepted++;
    
    li.innerHTML = `
      <div class="item-row">
        <span class="item-id">${item.fixture_id}</span>
        <span class="badge ${isAccepted ? 'badge-success' : 'badge-warning'}">${isAccepted ? 'ACCEPTED' : 'PENDING'}</span>
      </div>
      <div class="item-text">${item.display_text || item.category}</div>
    `;
    li.onclick = () => selectItem(idx);
    list.appendChild(li);
  });

  const countBadge = document.getElementById('reviewed-count');
  countBadge.textContent = `${accepted} / ${globalData.fixtures.length} Accepted`;
  if (accepted === globalData.fixtures.length) {
    countBadge.className = 'badge badge-success';
  } else {
    countBadge.className = 'badge badge-warning';
  }
  document.getElementById('progress-text').textContent = Math.round(accepted / globalData.fixtures.length * 100) + '%';
}

async function selectItem(index) {
  if (index < 0 || index >= globalData.fixtures.length) return;
  stopAudio();
  isPaused = false;
  pausedPositionSec = 0;
  updatePlayButtonUI();

  currentIndex = index;
  renderSidebar();
  
  const item = globalData.fixtures[currentIndex];
  document.getElementById('cur-id').textContent = item.fixture_id;
  document.getElementById('cur-text').textContent = item.display_text;
  document.getElementById('cur-duration').textContent = `${item.duration_ms} ms (${(item.duration_ms/1000).toFixed(1)}s)`;
  document.getElementById('cur-cat').textContent = `${item.category} (${item.class})`;
  document.getElementById('cur-sha').textContent = item.native_sha256.substring(0, 16) + '...';
  
  const classBadge = document.getElementById('cur-class-badge');
  classBadge.textContent = item.class.toUpperCase();
  
  const acceptBtn = document.getElementById('btn-toggle-accept');
  if (item.review_status === 'ACCEPTED_BY_HUMAN_REVIEW') {
    acceptBtn.textContent = '✅ 已確認 (點擊改為待審)';
    acceptBtn.className = 'btn btn-success';
  } else {
    acceptBtn.textContent = '⭕ 標記已審閱 (ACCEPTED)';
    acceptBtn.className = 'btn';
  }

  const clearInputs = document.getElementById('clear-inputs');
  const pauseInputs = document.getElementById('pause-inputs');
  const pauseLegend = document.getElementById('pause-legend');
  const btnPlayPause = document.getElementById('btn-play-pause');

  if (item.class === 'clear_speech') {
    clearInputs.style.display = 'flex';
    pauseInputs.style.display = 'none';
    pauseLegend.style.display = 'none';
    btnPlayPause.style.display = 'none';
    
    const s = item.speech_intervals_ms[0] || [300, item.duration_ms - 300];
    document.getElementById('input-s1-start').value = s[0];
    document.getElementById('input-s1-end').value = s[1];
    document.getElementById('clear-duration-display').textContent = `${s[1] - s[0]} ms`;
  } else {
    clearInputs.style.display = 'none';
    pauseInputs.style.display = 'flex';
    pauseLegend.style.display = 'inline-flex';
    btnPlayPause.style.display = 'inline-flex';

    const s1 = item.speech_intervals_ms[0] || [300, 2000];
    const s2 = item.speech_intervals_ms[1] || [3000, item.duration_ms - 300];
    document.getElementById('input-p-s1-start').value = s1[0];
    document.getElementById('input-p-s1-end').value = s1[1];
    document.getElementById('input-p-s2-start').value = s2[0];
    document.getElementById('input-p-s2-end').value = s2[1];
    document.getElementById('pause-duration-display').textContent = `${s2[0] - s1[1]} ms`;
  }

  await loadAudio(item.fixture_id);
  drawWaveform();
  drawRuler();
}

async function loadAudio(fixtureId) {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  const resp = await fetch(`/audio/${fixtureId}.wav`);
  const arrayBuf = await resp.arrayBuffer();
  currentAudioBuffer = await audioContext.decodeAudioData(arrayBuf);
}

function drawRuler() {
  const ruler = document.getElementById('time-ruler');
  ruler.innerHTML = '';
  const item = globalData.fixtures[currentIndex];
  const durSec = item.duration_ms / 1000;
  for (let sec = 0; sec <= durSec; sec += 1) {
    const mark = document.createElement('div');
    mark.style.position = 'absolute';
    mark.style.left = `${(sec / durSec) * 100}%`;
    mark.style.top = '2px';
    mark.style.borderLeft = '1px solid #475569';
    mark.style.paddingLeft = '3px';
    mark.textContent = `${sec}s`;
    ruler.appendChild(mark);
  }
}

function getCurrentPlayheadSec() {
  if (isPlaying) {
    const elapsedAudioTime = (audioContext.currentTime - playStartTime) * playbackRate;
    return playStartOffset + elapsedAudioTime;
  }
  if (isPaused) {
    return pausedPositionSec;
  }
  return 0;
}

function drawWaveform() {
  const canvas = document.getElementById('waveform');
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);
  
  const w = rect.width;
  const h = rect.height;
  
  ctx.clearRect(0, 0, w, h);
  
  const item = globalData.fixtures[currentIndex];
  const durMs = item.duration_ms;

  if (item.class === 'clear_speech') {
    const s = item.speech_intervals_ms[0] || [0, durMs];
    const x1 = (s[0] / durMs) * w;
    const x2 = (s[1] / durMs) * w;
    
    ctx.fillStyle = 'rgba(16, 185, 129, 0.25)';
    ctx.fillRect(x1, 0, x2 - x1, h);
    
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x1, 0); ctx.lineTo(x1, h);
    ctx.moveTo(x2, 0); ctx.lineTo(x2, h);
    ctx.stroke();
    
    drawHandle(ctx, x1, h, 'start');
    drawHandle(ctx, x2, h, 'end');
  } else {
    const s1 = item.speech_intervals_ms[0] || [0, 1000];
    const s2 = item.speech_intervals_ms[1] || [2000, durMs];
    const x1 = (s1[0] / durMs) * w;
    const x2 = (s1[1] / durMs) * w;
    const x3 = (s2[0] / durMs) * w;
    const x4 = (s2[1] / durMs) * w;

    ctx.fillStyle = 'rgba(16, 185, 129, 0.25)';
    ctx.fillRect(x1, 0, x2 - x1, h);
    ctx.fillStyle = 'rgba(245, 158, 11, 0.25)';
    ctx.fillRect(x2, 0, x3 - x2, h);
    ctx.fillStyle = 'rgba(16, 185, 129, 0.25)';
    ctx.fillRect(x3, 0, x4 - x3, h);

    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x1, 0); ctx.lineTo(x1, h);
    ctx.moveTo(x2, 0); ctx.lineTo(x2, h);
    ctx.moveTo(x3, 0); ctx.lineTo(x3, h);
    ctx.moveTo(x4, 0); ctx.lineTo(x4, h);
    ctx.stroke();

    drawHandle(ctx, x1, h, 's1');
    drawHandle(ctx, x2, h, 'p1');
    drawHandle(ctx, x3, h, 'p2');
    drawHandle(ctx, x4, h, 's2');
  }

  if (currentAudioBuffer) {
    const data = currentAudioBuffer.getChannelData(0);
    const step = Math.ceil(data.length / w);
    const amp = h / 2;
    
    ctx.fillStyle = '#38bdf8';
    for (let i = 0; i < w; i++) {
      let min = 1.0;
      let max = -1.0;
      for (let j = 0; j < step; j++) {
        const datum = data[(i * step) + j];
        if (datum < min) min = datum;
        if (datum > max) max = datum;
      }
      ctx.fillRect(i, (1 + min) * amp, 1, Math.max(1, (max - min) * amp));
    }
  }

  const playheadSec = getCurrentPlayheadSec();
  if ((isPlaying || isPaused) && playheadSec > 0 && currentAudioBuffer) {
    const playX = (playheadSec / (durMs / 1000)) * w;
    ctx.strokeStyle = isPaused ? '#f59e0b' : '#ef4444';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(playX, 0);
    ctx.lineTo(playX, h);
    ctx.stroke();
  }
}

function drawHandle(ctx, x, h, label) {
  ctx.fillStyle = '#f8fafc';
  ctx.beginPath();
  ctx.arc(x, 12, 6, 0, Math.PI * 2);
  ctx.arc(x, h - 12, 6, 0, Math.PI * 2);
  ctx.fill();
}

const canvas = document.getElementById('waveform');
canvas.onmousedown = (e) => {
  const rect = canvas.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const w = rect.width;
  const item = globalData.fixtures[currentIndex];
  const durMs = item.duration_ms;

  const msToX = (ms) => (ms / durMs) * w;
  const threshold = 12;

  if (item.class === 'clear_speech') {
    const s = item.speech_intervals_ms[0];
    if (Math.abs(clickX - msToX(s[0])) < threshold) activeHandle = 'start';
    else if (Math.abs(clickX - msToX(s[1])) < threshold) activeHandle = 'end';
  } else {
    const s1 = item.speech_intervals_ms[0];
    const s2 = item.speech_intervals_ms[1];
    if (Math.abs(clickX - msToX(s1[0])) < threshold) activeHandle = 's1';
    else if (Math.abs(clickX - msToX(s1[1])) < threshold) activeHandle = 'p1';
    else if (Math.abs(clickX - msToX(s2[0])) < threshold) activeHandle = 'p2';
    else if (Math.abs(clickX - msToX(s2[1])) < threshold) activeHandle = 's2';
  }
};

window.onmousemove = (e) => {
  if (!activeHandle) return;
  const rect = canvas.getBoundingClientRect();
  const moveX = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
  const item = globalData.fixtures[currentIndex];
  const durMs = item.duration_ms;
  let targetMs = Math.round(((moveX / rect.width) * durMs) / 10) * 10;
  
  if (item.class === 'clear_speech') {
    const s = item.speech_intervals_ms[0];
    if (activeHandle === 'start') {
      s[0] = Math.min(s[1] - 50, Math.max(0, targetMs));
    } else if (activeHandle === 'end') {
      s[1] = Math.max(s[0] + 50, Math.min(durMs, targetMs));
    }
    document.getElementById('input-s1-start').value = s[0];
    document.getElementById('input-s1-end').value = s[1];
    document.getElementById('clear-duration-display').textContent = `${s[1] - s[0]} ms`;
  } else {
    const s1 = item.speech_intervals_ms[0];
    const s2 = item.speech_intervals_ms[1];
    if (activeHandle === 's1') {
      s1[0] = Math.min(s1[1] - 50, Math.max(0, targetMs));
    } else if (activeHandle === 'p1') {
      s1[1] = Math.max(s1[0] + 50, Math.min(s2[0] - 50, targetMs));
      item.internal_pause_interval_ms = [s1[1], s2[0]];
    } else if (activeHandle === 'p2') {
      s2[0] = Math.max(s1[1] + 50, Math.min(s2[1] - 50, targetMs));
      item.internal_pause_interval_ms = [s1[1], s2[0]];
    } else if (activeHandle === 's2') {
      s2[1] = Math.max(s2[0] + 50, Math.min(durMs, targetMs));
    }
    document.getElementById('input-p-s1-start').value = s1[0];
    document.getElementById('input-p-s1-end').value = s1[1];
    document.getElementById('input-p-s2-start').value = s2[0];
    document.getElementById('input-p-s2-end').value = s2[1];
    document.getElementById('pause-duration-display').textContent = `${s2[0] - s1[1]} ms`;
  }
  drawWaveform();
};

window.onmouseup = () => { activeHandle = null; };

function onManualInputChange() {
  const item = globalData.fixtures[currentIndex];
  if (item.class === 'clear_speech') {
    const s0 = parseInt(document.getElementById('input-s1-start').value, 10);
    const s1 = parseInt(document.getElementById('input-s1-end').value, 10);
    item.speech_intervals_ms = [[s0, s1]];
    item.internal_pause_interval_ms = null;
    document.getElementById('clear-duration-display').textContent = `${s1 - s0} ms`;
  } else {
    const s1_0 = parseInt(document.getElementById('input-p-s1-start').value, 10);
    const s1_1 = parseInt(document.getElementById('input-p-s1-end').value, 10);
    const s2_0 = parseInt(document.getElementById('input-p-s2-start').value, 10);
    const s2_1 = parseInt(document.getElementById('input-p-s2-end').value, 10);
    item.speech_intervals_ms = [[s1_0, s1_1], [s2_0, s2_1]];
    item.internal_pause_interval_ms = [s1_1, s2_0];
    document.getElementById('pause-duration-display').textContent = `${s2_0 - s1_1} ms`;
  }
  drawWaveform();
}

function stepVal(id, delta) {
  const el = document.getElementById(id);
  el.value = parseInt(el.value || 0, 10) + delta;
  onManualInputChange();
}

function toggleAcceptCurrent() {
  const item = globalData.fixtures[currentIndex];
  if (item.review_status === 'ACCEPTED_BY_HUMAN_REVIEW') {
    item.review_status = 'PENDING_REVIEW';
  } else {
    item.review_status = 'ACCEPTED_BY_HUMAN_REVIEW';
    setTimeout(() => {
      if (currentIndex < globalData.fixtures.length - 1) {
        selectItem(currentIndex + 1);
      }
    }, 150);
  }
  renderSidebar();
}

function stopAudio() {
  if (currentSource) {
    try { currentSource.stop(); } catch(e){}
    currentSource = null;
  }
  isPlaying = false;
  if (animFrameId) cancelAnimationFrame(animFrameId);
}

function updatePlayButtonUI() {
  const btn = document.getElementById('btn-play-toggle');
  if (isPlaying) {
    btn.textContent = '⏸ 暫停 (Space)';
    btn.className = 'btn btn-primary';
  } else if (isPaused) {
    btn.textContent = '▶ 繼續播放 (Space)';
    btn.className = 'btn btn-primary';
  } else {
    btn.textContent = '▶ 播放 (Space)';
    btn.className = 'btn btn-primary';
  }
}

function playSegment(offsetSec, durationSec) {
  if (!currentAudioBuffer) return;
  stopAudio();
  if (audioContext.state === 'suspended') audioContext.resume();

  currentSource = audioContext.createBufferSource();
  currentSource.buffer = currentAudioBuffer;
  currentSource.playbackRate.value = playbackRate;
  currentSource.connect(audioContext.destination);

  playStartTime = audioContext.currentTime;
  playStartOffset = offsetSec;
  currentSegmentEndSec = offsetSec + durationSec;
  isPlaying = true;
  isPaused = false;
  updatePlayButtonUI();

  currentSource.start(0, offsetSec, durationSec);
  currentSource.onended = () => {
    if (isPlaying) {
      isPlaying = false;
      isPaused = false;
      pausedPositionSec = 0;
      updatePlayButtonUI();
      drawWaveform();
    }
  };

  function loop() {
    if (isPlaying) {
      drawWaveform();
      animFrameId = requestAnimationFrame(loop);
    }
  }
  loop();
}

function togglePlayPauseAudio() {
  const item = globalData.fixtures[currentIndex];
  const totalDurSec = item.duration_ms / 1000;

  if (isPlaying) {
    const currentPos = getCurrentPlayheadSec();
    stopAudio();
    isPaused = true;
    pausedPositionSec = Math.min(totalDurSec, currentPos);
    updatePlayButtonUI();
    drawWaveform();
  } else if (isPaused) {
    const remDur = totalDurSec - pausedPositionSec;
    if (remDur > 0.05) {
      playSegment(pausedPositionSec, remDur);
    } else {
      isPaused = false;
      playSegment(0, totalDurSec);
    }
  } else {
    playSegment(0, totalDurSec);
  }
}

function playInterval(type) {
  const item = globalData.fixtures[currentIndex];
  if (item.class === 'clear_speech') {
    const s = item.speech_intervals_ms[0];
    playSegment(s[0] / 1000, (s[1] - s[0]) / 1000);
  } else {
    if (type === 'speech') {
      const s1 = item.speech_intervals_ms[0];
      playSegment(s1[0] / 1000, (s1[1] - s1[0]) / 1000);
    } else {
      const p = item.internal_pause_interval_ms;
      playSegment(p[0] / 1000, (p[1] - p[0]) / 1000);
    }
  }
}

function playBoundary(type) {
  const item = globalData.fixtures[currentIndex];
  const durMs = item.duration_ms;
  let targetMs = 0;
  if (item.class === 'clear_speech') {
    targetMs = type === 'start' ? item.speech_intervals_ms[0][0] : item.speech_intervals_ms[0][1];
  } else {
    targetMs = type === 'start' ? item.speech_intervals_ms[0][0] : item.speech_intervals_ms[1][1];
  }
  const startSec = Math.max(0, (targetMs - 350) / 1000);
  const playDurSec = Math.min((durMs / 1000) - startSec, 0.7);
  playSegment(startSec, playDurSec);
}

window.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT') return;
  if (e.code === 'Space') {
    e.preventDefault();
    togglePlayPauseAudio();
  } else if (e.key === 's' || e.key === 'S') {
    playInterval('speech');
  } else if (e.key === 'p' || e.key === 'P') {
    playInterval('pause');
  } else if (e.key === '1') {
    playBoundary('start');
  } else if (e.key === '2') {
    playBoundary('end');
  } else if (e.code === 'ArrowLeft') {
    if (currentIndex > 0) selectItem(currentIndex - 1);
  } else if (e.code === 'ArrowRight') {
    if (currentIndex < globalData.fixtures.length - 1) selectItem(currentIndex + 1);
  } else if (e.key === 'Enter') {
    toggleAcceptCurrent();
  }
});

async function saveAllToServer() {
  const doc = {
    schema_version: "1.0",
    label_set_id: "m1-authorized-vad-labels-v1",
    plan_id: globalData.plan_id,
    source_manifest_sha256: globalData.source_manifest_sha256,
    annotation_method: "external_tool_then_human_review",
    records: globalData.fixtures.map(f => ({
      fixture_id: f.fixture_id,
      class: f.class,
      native_sha256: f.native_sha256,
      speech_intervals_ms: f.speech_intervals_ms,
      internal_pause_interval_ms: f.internal_pause_interval_ms,
      review_status: f.review_status
    }))
  };

  const resp = await fetch('/api/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(doc)
  });

  const res = await resp.json();
  if (res.status === 'ok') {
    const toast = document.getElementById('toast');
    toast.textContent = `✅ 成功儲存標籤至 ${res.saved_path}`;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3500);
  } else {
    alert('儲存失敗：' + res.error);
  }
}

window.onload = init;
</script>
</body>
</html>
"""


def create_handler(artifact_dir: Path, plan_path: Path, output_file: Path):
    manifest_path = artifact_dir / "fixture_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found in artifact directory: {manifest_path}")

    with open(manifest_path, "rb") as f:
        manifest_bytes = f.read()
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        manifest = json.loads(manifest_bytes.decode("utf-8"))

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    utterance_map = {u["fixture_id"]: u for u in plan.get("utterances", [])}

    initial_records = {}
    if output_file.exists():
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                saved_doc = json.load(f)
                for r in saved_doc.get("records", []):
                    initial_records[r["fixture_id"]] = r
        except Exception:
            pass

    def get_fixtures_payload():
        fixtures = []
        for i in range(1, 26):
            fid = f"asr-clear-{i:03d}"
            rec = manifest.get("records", {}).get(fid, {})
            u = utterance_map.get(fid, {})
            init_r = initial_records.get(fid, {})
            duration_ms = int(rec.get("metadata", {}).get("duration_seconds", 6.0) * 1000)
            sp = init_r.get("speech_intervals_ms", [[300, duration_ms - 300]])
            pause = init_r.get("internal_pause_interval_ms", None)
            status = init_r.get("review_status", "PENDING_REVIEW")
            fixtures.append({
                "fixture_id": fid,
                "class": "clear_speech",
                "display_text": u.get("display_text", ""),
                "reference_text": u.get("reference_text", ""),
                "category": u.get("category", ""),
                "native_sha256": rec.get("sha256", ""),
                "duration_ms": duration_ms,
                "speech_intervals_ms": sp,
                "internal_pause_interval_ms": pause,
                "review_status": status,
            })

        for i in range(26, 51):
            fid = f"asr-pause-{i:03d}"
            rec = manifest.get("records", {}).get(fid, {})
            u = utterance_map.get(fid, {})
            init_r = initial_records.get(fid, {})
            duration_ms = int(rec.get("metadata", {}).get("duration_seconds", 8.0) * 1000)
            sp = init_r.get("speech_intervals_ms", [[300, duration_ms // 2 - 300], [duration_ms // 2 + 300, duration_ms - 300]])
            pause = init_r.get("internal_pause_interval_ms", [duration_ms // 2 - 300, duration_ms // 2 + 300])
            status = init_r.get("review_status", "PENDING_REVIEW")
            fixtures.append({
                "fixture_id": fid,
                "class": "pause",
                "display_text": u.get("display_text", ""),
                "reference_text": u.get("reference_text", ""),
                "category": u.get("category", ""),
                "native_sha256": rec.get("sha256", ""),
                "duration_ms": duration_ms,
                "speech_intervals_ms": sp,
                "internal_pause_interval_ms": pause,
                "review_status": status,
            })

        return {
            "plan_id": plan.get("plan_id", "m1-authorized-zh-tw-v1"),
            "source_manifest_sha256": manifest_sha256,
            "fixtures": fixtures,
            "output_path": str(output_file)
        }

    class CustomVADHandler(http.server.SimpleHTTPRequestHandler):
        def do_HEAD(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path.startswith("/audio/"):
                filename = parsed.path.replace("/audio/", "")
                filepath = artifact_dir / filename
                if not filepath.exists() or not filepath.is_file():
                    self.send_response(404)
                    self.end_headers()
                    return
                size = filepath.stat().st_size
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
            else:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/" or parsed.path == "/index.html":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(HTML_CONTENT.encode("utf-8"))
                return
            elif parsed.path == "/api/data":
                payload = get_fixtures_payload()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                return
            elif parsed.path.startswith("/audio/"):
                filename = parsed.path.replace("/audio/", "")
                filepath = artifact_dir / filename
                if not filepath.exists() or not filepath.is_file():
                    self.send_response(404)
                    self.end_headers()
                    return
                with open(filepath, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                self.wfile.write(data)
                return
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/api/save":
                content_length = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_length)
                doc = json.loads(post_body.decode("utf-8"))
                
                if doc.get("schema_version") != "1.0":
                    self.send_error(400, "Invalid schema_version")
                    return
                if len(doc.get("records", [])) != 50:
                    self.send_error(400, f"Expected 50 records, got {len(doc.get('records', []))}")
                    return
                    
                for r in doc["records"]:
                    if r["class"] == "clear_speech":
                        if len(r["speech_intervals_ms"]) != 1 or r["internal_pause_interval_ms"] is not None:
                            self.send_error(400, f"Invalid clear_speech intervals in {r['fixture_id']}")
                            return
                    elif r["class"] == "pause":
                        if len(r["speech_intervals_ms"]) != 2 or r["internal_pause_interval_ms"] is None:
                            self.send_error(400, f"Invalid pause intervals in {r['fixture_id']}")
                            return
                        sp1 = r["speech_intervals_ms"][0]
                        sp2 = r["speech_intervals_ms"][1]
                        p = r["internal_pause_interval_ms"]
                        if p[0] != sp1[1] or p[1] != sp2[0]:
                            self.send_error(400, f"Pause interval {p} must equal gap between {sp1} and {sp2}")
                            return
                
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, indent=2)
                    f.write("\n")
                    
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "saved_path": str(output_file)}).encode("utf-8"))
                return
            else:
                self.send_response(404)
                self.end_headers()

    return CustomVADHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"HTTP server port (default: {DEFAULT_PORT})")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN, help="Path to recording_plan_v1.json")
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR, help="Path to fixture artifact directory")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Destination path for vad-labels-v1.json")
    args = parser.parse_args(argv)

    handler = create_handler(args.artifact_dir, args.plan, args.output)
    server = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    print(f"🎙️ VAD Labelling Tool running at: http://localhost:{args.port}")
    print(f"  - Artifact Dir: {args.artifact_dir}")
    print(f"  - Output Target: {args.output}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nServer stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
