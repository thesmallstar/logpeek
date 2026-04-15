#!/usr/bin/env python3
"""
logpeek — lightweight browser-based JSON log viewer.
Zero external dependencies. Just Python stdlib.
"""

import argparse
import json
import os
import sys
import threading
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ---------------------------------------------------------------------------
# HTML / CSS / JS — the entire frontend is embedded here
# ---------------------------------------------------------------------------

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>logpeek</title>
<style>
/* ── Reset & Base ─────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg:        #0f0f1a;
  --bg-row:    #14142a;
  --bg-row-alt:#181833;
  --bg-hover:  #1e1e40;
  --bg-expand: #12122a;
  --bg-input:  #1a1a35;
  --border:    #2a2a4a;
  --border-lt: #35355a;
  --text:      #d4d4e8;
  --text-dim:  #7a7a9a;
  --text-muted:#555578;
  --accent:    #6c8cff;
  --accent-dim:#4a62b8;
  --search-hl: #f5c542;
  --search-hl-bg: rgba(245, 197, 66, 0.18);
  --info:      #4a90d9;
  --info-bg:   rgba(74,144,217,0.12);
  --warn:      #e6a817;
  --warn-bg:   rgba(230,168,23,0.12);
  --error:     #e05555;
  --error-bg:  rgba(224,85,85,0.12);
  --debug:     #6b7280;
  --debug-bg:  rgba(107,114,128,0.12);
  --success:   #34d399;
  --radius:    6px;
  --radius-sm: 4px;
  --font-mono: 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', Consolas, monospace;
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --row-height: 38px;
}
html { font-size: 13px; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-mono);
  line-height: 1.5;
  overflow: hidden;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ── Scrollbar ────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--border-lt); }

/* ── Header / Toolbar ─────────────────────────────────────────── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--bg-row);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  z-index: 100;
}
.logo {
  font-family: var(--font-sans);
  font-weight: 700;
  font-size: 1.15rem;
  color: var(--accent);
  letter-spacing: -0.02em;
  margin-right: 8px;
  user-select: none;
  white-space: nowrap;
}
.logo span { color: var(--text-dim); font-weight: 400; font-size: 0.85rem; margin-left: 6px; }
.search-wrap {
  position: relative;
  flex: 1;
  max-width: 480px;
}
.search-wrap svg {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  pointer-events: none;
}
#search {
  width: 100%;
  padding: 7px 12px 7px 34px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 0.92rem;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
#search:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(108,140,255,0.15);
}
#search::placeholder { color: var(--text-muted); }
.search-shortcut {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 1px 5px;
  pointer-events: none;
  font-family: var(--font-sans);
}

/* Level filter chips */
.filters {
  display: flex;
  gap: 5px;
  align-items: center;
}
.filter-chip {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
  border: 1px solid transparent;
  transition: all 0.15s;
  font-family: var(--font-sans);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.filter-chip.active { opacity: 1; }
.filter-chip:not(.active) { opacity: 0.35; filter: grayscale(0.5); }
.chip-info    { background: var(--info-bg);  color: var(--info);  border-color: rgba(74,144,217,0.25); }
.chip-warning { background: var(--warn-bg);  color: var(--warn);  border-color: rgba(230,168,23,0.25); }
.chip-error   { background: var(--error-bg); color: var(--error); border-color: rgba(224,85,85,0.25); }
.chip-debug   { background: var(--debug-bg); color: var(--debug); border-color: rgba(107,114,128,0.25); }

.stats {
  font-size: 0.8rem;
  color: var(--text-muted);
  white-space: nowrap;
  font-family: var(--font-sans);
  margin-left: auto;
}
.stats b { color: var(--text-dim); font-weight: 600; }

.live-dot {
  width: 7px; height: 7px;
  background: var(--success);
  border-radius: 50%;
  animation: pulse 2s infinite;
  flex-shrink: 0;
}
@keyframes pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(52,211,153,0.5); }
  50%      { opacity: 0.6; box-shadow: 0 0 0 4px rgba(52,211,153,0); }
}

/* ── Column Headers ───────────────────────────────────────────── */
.col-headers {
  display: flex;
  align-items: center;
  padding: 6px 16px;
  background: var(--bg-row);
  border-bottom: 1px solid var(--border);
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-family: var(--font-sans);
  flex-shrink: 0;
}
.col-line   { width: 52px;  flex-shrink: 0; text-align: right; padding-right: 12px; }
.col-time   { width: 200px; flex-shrink: 0; }
.col-level  { width: 76px;  flex-shrink: 0; }
.col-msg    { flex: 1; min-width: 0; }

/* ── Log Container ────────────────────────────────────────────── */
#log-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
}

/* ── Log Rows ─────────────────────────────────────────────────── */
.log-row {
  display: flex;
  align-items: stretch;
  min-height: var(--row-height);
  padding: 0 16px;
  cursor: pointer;
  border-bottom: 1px solid rgba(42,42,74,0.4);
  transition: background 0.1s;
}
.log-row:nth-child(odd) .row-main { background: transparent; }
.log-row:nth-child(even) .row-main { background: rgba(255,255,255,0.01); }
.log-row:hover .row-main { background: var(--bg-hover); }
.log-row.expanded { background: var(--bg-expand); }
.row-main {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: var(--row-height);
}
.row-line {
  width: 52px;
  flex-shrink: 0;
  text-align: right;
  padding-right: 12px;
  color: var(--text-muted);
  font-size: 0.78rem;
  user-select: none;
}
.row-time {
  width: 200px;
  flex-shrink: 0;
  color: var(--text-dim);
  font-size: 0.88rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.row-level {
  width: 76px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
}
.level-badge {
  display: inline-block;
  padding: 1px 7px;
  border-radius: 3px;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-family: var(--font-sans);
}
.level-info    .level-badge { background: var(--info-bg);  color: var(--info); }
.level-warning .level-badge { background: var(--warn-bg);  color: var(--warn); }
.level-error   .level-badge { background: var(--error-bg); color: var(--error); }
.level-debug   .level-badge { background: var(--debug-bg); color: var(--debug); }
.level-unknown .level-badge { background: var(--debug-bg); color: var(--text-muted); }

.row-msg {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.88rem;
  padding-right: 8px;
}
.row-raw {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.88rem;
  color: var(--text-dim);
  font-style: italic;
  padding-left: 0;
}

/* ── Expanded Detail ──────────────────────────────────────────── */
.row-detail {
  display: none;
  padding: 12px 16px 14px 68px;
  background: var(--bg-expand);
  border-bottom: 1px solid var(--border);
  animation: slideDown 0.15s ease-out;
  position: relative;
}
.log-row.expanded .row-detail { display: block; }
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-4px); }
  to   { opacity: 1; transform: translateY(0); }
}
.detail-actions {
  position: absolute;
  top: 10px;
  right: 16px;
  display: flex;
  gap: 6px;
}
.btn-copy {
  padding: 3px 10px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-dim);
  font-size: 0.75rem;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all 0.15s;
}
.btn-copy:hover { background: var(--bg-hover); color: var(--text); border-color: var(--border-lt); }
.btn-copy.copied { color: var(--success); border-color: var(--success); }

/* JSON tree */
.json-tree { font-size: 0.85rem; line-height: 1.65; }
.json-key   { color: #8babff; }
.json-str   { color: #7ec69a; }
.json-num   { color: #d4a0f5; }
.json-bool  { color: #f5a060; }
.json-null  { color: var(--text-muted); font-style: italic; }
.json-brace { color: var(--text-dim); }
.json-toggle {
  cursor: pointer;
  user-select: none;
  color: var(--text-muted);
  display: inline-block;
  width: 14px;
  text-align: center;
  font-size: 0.7rem;
  transition: transform 0.15s;
  margin-right: 2px;
}
.json-toggle.collapsed { transform: rotate(-90deg); }
.json-collapsible.collapsed > .json-children { display: none; }
.json-collapsible.collapsed > .json-summary { display: inline; }
.json-summary { display: none; color: var(--text-muted); font-style: italic; font-size: 0.8rem; }

/* Raw text detail */
.detail-raw {
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--text-dim);
  font-size: 0.85rem;
}

/* ── Search highlights ────────────────────────────────────────── */
mark {
  background: var(--search-hl-bg);
  color: var(--search-hl);
  border-radius: 2px;
  padding: 0 1px;
  border-bottom: 1.5px solid var(--search-hl);
}

/* ── Jump to bottom ───────────────────────────────────────────── */
#jump-btn {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 8px 18px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 999px;
  font-family: var(--font-sans);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(108,140,255,0.3);
  transition: all 0.2s;
  z-index: 200;
  display: none;
  align-items: center;
  gap: 6px;
}
#jump-btn:hover { background: var(--accent-dim); transform: translateY(-1px); box-shadow: 0 6px 24px rgba(108,140,255,0.4); }
#jump-btn svg { width: 14px; height: 14px; }

/* ── Empty state ──────────────────────────────────────────────── */
#empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  font-family: var(--font-sans);
  gap: 8px;
}
#empty-state .empty-icon { font-size: 2.5rem; opacity: 0.4; }
#empty-state .empty-text { font-size: 0.95rem; }
#empty-state .empty-sub  { font-size: 0.8rem; color: var(--text-muted); opacity: 0.6; }

/* ── Responsive ───────────────────────────────────────────────── */
@media (max-width: 768px) {
  .toolbar { flex-wrap: wrap; gap: 8px; padding: 8px 12px; }
  .search-wrap { max-width: 100%; order: 10; }
  .filters { order: 11; }
  .stats { order: 5; }
  .col-time, .row-time { width: 150px; }
  .col-line, .row-line { width: 40px; }
  .row-detail { padding-left: 16px; }
}
@media (max-width: 500px) {
  .col-time, .row-time { display: none; }
}
</style>
</head>
<body>

<!-- Toolbar -->
<div class="toolbar">
  <div class="logo">logpeek<span id="filename"></span></div>
  <div class="search-wrap">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    <input type="text" id="search" placeholder="Search logs..." autocomplete="off" spellcheck="false" />
    <span class="search-shortcut" id="search-hint">/</span>
  </div>
  <div class="filters">
    <div class="filter-chip chip-debug active"   data-level="debug"   onclick="toggleFilter('debug')">DBG</div>
    <div class="filter-chip chip-info active"     data-level="info"    onclick="toggleFilter('info')">INF</div>
    <div class="filter-chip chip-warning active"  data-level="warning" onclick="toggleFilter('warning')">WRN</div>
    <div class="filter-chip chip-error active"    data-level="error"   onclick="toggleFilter('error')">ERR</div>
  </div>
  <div class="stats">
    <span><b id="shown-count">0</b> / <b id="total-count">0</b></span>
  </div>
  <div class="live-dot" title="Live tail connected"></div>
</div>

<!-- Column headers -->
<div class="col-headers">
  <div class="col-line">#</div>
  <div class="col-time">Timestamp</div>
  <div class="col-level">Level</div>
  <div class="col-msg">Message</div>
</div>

<!-- Log rows -->
<div id="log-container">
  <div id="empty-state">
    <div class="empty-icon">&#9671;</div>
    <div class="empty-text">Waiting for logs...</div>
    <div class="empty-sub">Lines will appear here as they arrive</div>
  </div>
</div>

<!-- Jump to bottom -->
<button id="jump-btn" onclick="jumpToBottom()">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>
  New logs
</button>

<script>
// ── State ──────────────────────────────────────────────────────
const allLines = [];          // {lineNum, raw, parsed, level, isJson}
let searchTerm = '';
let activeFilters = { debug: true, info: true, warning: true, error: true, raw: true };
let autoScroll = true;
let userScrolledUp = false;

const container = document.getElementById('log-container');
const emptyState = document.getElementById('empty-state');
const searchInput = document.getElementById('search');
const searchHint = document.getElementById('search-hint');
const jumpBtn = document.getElementById('jump-btn');
const totalCountEl = document.getElementById('total-count');
const shownCountEl = document.getElementById('shown-count');

// ── Helpers ────────────────────────────────────────────────────
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function highlightText(text, term) {
  if (!term) return escapeHtml(text);
  const escaped = escapeHtml(text);
  const regex = new RegExp('(' + term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
  return escaped.replace(regex, '<mark>$1</mark>');
}

function normalizeLevel(level) {
  if (!level) return 'unknown';
  const lower = level.toLowerCase();
  if (lower === 'warn') return 'warning';
  if (['info', 'warning', 'error', 'debug'].includes(lower)) return lower;
  return 'unknown';
}

function formatTime(timeStr) {
  if (!timeStr) return '';
  // Handle ISO format — show date + time with ms
  try {
    if (timeStr.includes('T')) {
      const parts = timeStr.split('T');
      const date = parts[0]; // 2026-04-15
      let time = parts[1];
      // Truncate microseconds to ms
      if (time && time.includes('.')) {
        const [sec, frac] = time.split('.');
        time = sec + '.' + frac.substring(0, 3);
      }
      return date + ' ' + time;
    }
    return timeStr;
  } catch {
    return timeStr;
  }
}

function parseLine(raw, lineNum) {
  const trimmed = raw.trim();
  if (!trimmed) return null;

  let parsed = null;
  let isJson = false;
  let level = 'unknown';
  let message = trimmed;
  let timestamp = '';

  if (trimmed.startsWith('{')) {
    try {
      parsed = JSON.parse(trimmed);
      isJson = true;
      level = normalizeLevel(parsed.level || parsed.Level || parsed.severity || parsed.lvl || '');
      message = parsed.message || parsed.msg || parsed.Message || parsed.text || trimmed;
      timestamp = parsed.time || parsed.timestamp || parsed.ts || parsed.datetime || parsed['@timestamp'] || parsed.t || '';
    } catch {
      // Not valid JSON — treat as raw
    }
  }

  return { lineNum, raw: trimmed, parsed, isJson, level, message, timestamp };
}

// ── JSON Tree Renderer ─────────────────────────────────────────
function renderJsonTree(data, depth = 0, searchTerm = '') {
  if (data === null) return `<span class="json-null">null</span>`;
  if (data === undefined) return `<span class="json-null">undefined</span>`;

  const type = typeof data;

  if (type === 'boolean') return `<span class="json-bool">${data}</span>`;
  if (type === 'number')  return `<span class="json-num">${data}</span>`;
  if (type === 'string') {
    const displayed = highlightText('"' + data + '"', searchTerm);
    // We already escaped inside highlightText — wrap in span
    return `<span class="json-str">${displayed}</span>`;
  }

  const isArray = Array.isArray(data);
  const entries = isArray ? data.map((v, i) => [i, v]) : Object.entries(data);
  const openBrace = isArray ? '[' : '{';
  const closeBrace = isArray ? ']' : '}';

  if (entries.length === 0) {
    return `<span class="json-brace">${openBrace}${closeBrace}</span>`;
  }

  const indent = '  '.repeat(depth + 1);
  const closingIndent = '  '.repeat(depth);
  const id = 'jt-' + Math.random().toString(36).substring(2, 9);
  const summaryText = isArray
    ? `${entries.length} item${entries.length !== 1 ? 's' : ''}`
    : `${entries.length} key${entries.length !== 1 ? 's' : ''}`;

  let html = `<span class="json-collapsible" id="${id}">`;
  html += `<span class="json-toggle" onclick="toggleJsonNode('${id}')">&#9660;</span>`;
  html += `<span class="json-brace">${openBrace}</span>`;
  html += `<span class="json-summary">${summaryText}${closeBrace}</span>`;
  html += `<span class="json-children">`;

  entries.forEach(([key, value], index) => {
    html += '\n' + indent;
    if (!isArray) {
      const keyText = highlightText('"' + key + '"', searchTerm);
      html += `<span class="json-key">${keyText}</span>: `;
    }
    html += renderJsonTree(value, depth + 1, searchTerm);
    if (index < entries.length - 1) html += ',';
  });

  html += '\n' + closingIndent;
  html += `<span class="json-brace">${closeBrace}</span>`;
  html += `</span></span>`;

  return html;
}

window.toggleJsonNode = function(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.toggle('collapsed');
};

// ── Row Rendering ──────────────────────────────────────────────
function matchesSearch(line, term) {
  if (!term) return true;
  const lower = term.toLowerCase();
  return line.raw.toLowerCase().includes(lower);
}

function matchesFilter(line) {
  if (!line.isJson) return activeFilters.raw !== false; // always show raw unless explicitly hidden
  return activeFilters[line.level] !== false;
}

function createRowHtml(line) {
  const display = matchesSearch(line, searchTerm) && matchesFilter(line);
  if (!display) return null;

  const levelClass = 'level-' + line.level;
  const levelLabel = line.level === 'unknown' ? 'RAW' : line.level.toUpperCase().substring(0, 3);

  let timeHtml = '';
  let msgHtml = '';

  if (line.isJson) {
    timeHtml = `<div class="row-time">${highlightText(formatTime(line.timestamp), searchTerm)}</div>`;
    msgHtml = `<div class="row-msg">${highlightText(String(line.message), searchTerm)}</div>`;
  } else {
    timeHtml = `<div class="row-time"></div>`;
    msgHtml = `<div class="row-raw">${highlightText(line.raw, searchTerm)}</div>`;
  }

  // Build detail section
  let detailHtml = '';
  if (line.isJson) {
    detailHtml = `<div class="row-detail">
      <div class="detail-actions"><button class="btn-copy" onclick="copyLine(event, ${line.lineNum - 1})">Copy JSON</button></div>
      <div class="json-tree"><pre>${renderJsonTree(line.parsed, 0, searchTerm)}</pre></div>
    </div>`;
  } else {
    detailHtml = `<div class="row-detail">
      <div class="detail-actions"><button class="btn-copy" onclick="copyLine(event, ${line.lineNum - 1})">Copy</button></div>
      <div class="detail-raw">${highlightText(line.raw, searchTerm)}</div>
    </div>`;
  }

  return `<div class="log-row ${levelClass}" data-line="${line.lineNum}" onclick="toggleRow(this, event)">
    <div class="row-main">
      <div class="row-line">${line.lineNum}</div>
      ${timeHtml}
      <div class="row-level"><span class="level-badge">${levelLabel}</span></div>
      ${msgHtml}
    </div>
    ${detailHtml}
  </div>`;
}

// ── Full re-render (used for search/filter changes) ────────────
function renderAll() {
  const fragment = document.createDocumentFragment();
  const tempDiv = document.createElement('div');
  let shownCount = 0;

  allLines.forEach(line => {
    const html = createRowHtml(line);
    if (html) {
      shownCount++;
      tempDiv.innerHTML = html;
      fragment.appendChild(tempDiv.firstElementChild);
    }
  });

  container.innerHTML = '';
  if (shownCount === 0 && allLines.length === 0) {
    container.appendChild(emptyState);
  } else {
    container.appendChild(fragment);
  }

  totalCountEl.textContent = allLines.length;
  shownCountEl.textContent = shownCount;

  if (autoScroll) {
    container.scrollTop = container.scrollHeight;
  }
}

// ── Append new rows (used for live tail — fast path) ───────────
function appendRows(newLines) {
  if (emptyState.parentElement === container) {
    container.removeChild(emptyState);
  }

  let shownCount = parseInt(shownCountEl.textContent) || 0;
  const tempDiv = document.createElement('div');

  newLines.forEach(line => {
    const html = createRowHtml(line);
    if (html) {
      shownCount++;
      tempDiv.innerHTML = html;
      container.appendChild(tempDiv.firstElementChild);
    }
  });

  totalCountEl.textContent = allLines.length;
  shownCountEl.textContent = shownCount;

  if (autoScroll && !userScrolledUp) {
    container.scrollTop = container.scrollHeight;
  }
}

// ── Row expand/collapse ────────────────────────────────────────
window.toggleRow = function(rowEl, event) {
  // Don't toggle if clicking a button or link
  if (event.target.closest('.btn-copy') || event.target.closest('a')) return;
  rowEl.classList.toggle('expanded');
};

// ── Copy ───────────────────────────────────────────────────────
window.copyLine = function(event, index) {
  event.stopPropagation();
  const line = allLines[index];
  if (!line) return;

  const text = line.isJson ? JSON.stringify(line.parsed, null, 2) : line.raw;
  navigator.clipboard.writeText(text).then(() => {
    const btn = event.target;
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = line.isJson ? 'Copy JSON' : 'Copy';
      btn.classList.remove('copied');
    }, 1500);
  });
};

// ── Search ─────────────────────────────────────────────────────
let searchTimeout;
searchInput.addEventListener('input', () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    searchTerm = searchInput.value.trim();
    searchHint.style.display = searchTerm ? 'none' : '';
    renderAll();
  }, 150);
});

// ── Filter toggles ─────────────────────────────────────────────
window.toggleFilter = function(level) {
  activeFilters[level] = !activeFilters[level];
  const chip = document.querySelector(`.filter-chip[data-level="${level}"]`);
  if (chip) chip.classList.toggle('active', activeFilters[level]);
  renderAll();
};

// ── Auto-scroll detection ──────────────────────────────────────
container.addEventListener('scroll', () => {
  const threshold = 80;
  const atBottom = container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
  userScrolledUp = !atBottom;
  jumpBtn.style.display = userScrolledUp ? 'flex' : 'none';
  if (atBottom) autoScroll = true;
  else autoScroll = false;
});

window.jumpToBottom = function() {
  container.scrollTop = container.scrollHeight;
  autoScroll = true;
  userScrolledUp = false;
  jumpBtn.style.display = 'none';
};

// ── Keyboard shortcuts ─────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  // Don't handle shortcuts when typing in search
  const isSearchFocused = document.activeElement === searchInput;

  if (e.key === '/' && !isSearchFocused) {
    e.preventDefault();
    searchInput.focus();
    searchInput.select();
  }
  if (e.key === 'Escape') {
    if (isSearchFocused) {
      searchInput.value = '';
      searchTerm = '';
      searchHint.style.display = '';
      searchInput.blur();
      renderAll();
    }
  }
  if ((e.key === 'g' || e.key === 'G') && !isSearchFocused) {
    jumpToBottom();
  }
});

// ── SSE — Load initial data + live tail ────────────────────────
function connectSSE() {
  const evtSource = new EventSource('/events');

  evtSource.addEventListener('init', (e) => {
    const data = JSON.parse(e.data);
    document.getElementById('filename').textContent = ' \u2014 ' + data.filename;
    document.title = 'logpeek \u2014 ' + data.filename;
  });

  evtSource.addEventListener('bulk', (e) => {
    const lines = JSON.parse(e.data);
    const newEntries = [];
    lines.forEach(rawLine => {
      const parsed = parseLine(rawLine, allLines.length + 1);
      if (parsed) {
        allLines.push(parsed);
        newEntries.push(parsed);
      }
    });
    if (newEntries.length > 0) {
      if (searchTerm || !activeFilters.debug || !activeFilters.info || !activeFilters.warning || !activeFilters.error) {
        renderAll();
      } else {
        appendRows(newEntries);
      }
    }
  });

  evtSource.addEventListener('line', (e) => {
    const rawLine = JSON.parse(e.data);
    const parsed = parseLine(rawLine, allLines.length + 1);
    if (parsed) {
      allLines.push(parsed);
      if (searchTerm || !activeFilters.debug || !activeFilters.info || !activeFilters.warning || !activeFilters.error) {
        renderAll();
      } else {
        appendRows([parsed]);
      }
    }
  });

  evtSource.onerror = () => {
    // Reconnect after a brief delay
    evtSource.close();
    setTimeout(connectSSE, 2000);
  };
}

connectSSE();
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class LogPeekHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves the HTML page and SSE events."""

    log_file_path = None  # Set by main()
    _file_lock = threading.Lock()

    # Suppress default logging to stderr (we print our own)
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self._serve_html()
        elif self.path == '/events':
            self._serve_sse()
        else:
            self.send_error(404)

    def _serve_html(self):
        content = HTML_PAGE.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(content)

    def _serve_sse(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('X-Accel-Buffering', 'no')
        self.end_headers()

        file_path = self.__class__.log_file_path

        # Send init event with filename
        filename = os.path.basename(file_path)
        self._send_sse_event('init', json.dumps({'filename': filename}))

        # Wait for file to exist
        while not os.path.exists(file_path):
            try:
                self._send_sse_event('line', json.dumps('[waiting for file to be created...]'))
                time.sleep(1)
            except (BrokenPipeError, ConnectionResetError):
                return

        # Read existing content in chunks and send as bulk events
        try:
            with open(file_path, 'r', errors='replace') as f:
                batch = []
                batch_size = 500
                for raw_line in f:
                    stripped = raw_line.rstrip('\n\r')
                    if stripped:
                        batch.append(stripped)
                    if len(batch) >= batch_size:
                        self._send_sse_event('bulk', json.dumps(batch))
                        batch = []
                if batch:
                    self._send_sse_event('bulk', json.dumps(batch))

                # Now tail for new lines
                current_position = f.tell()
        except (BrokenPipeError, ConnectionResetError):
            return
        except OSError as exc:
            self._send_sse_event('line', json.dumps(f'[error reading file: {exc}]'))
            return

        # Poll for new content
        while True:
            try:
                time.sleep(0.5)

                if not os.path.exists(file_path):
                    continue

                file_size = os.path.getsize(file_path)

                # Handle file truncation (log rotation)
                if file_size < current_position:
                    current_position = 0

                if file_size > current_position:
                    with open(file_path, 'r', errors='replace') as f:
                        f.seek(current_position)
                        new_lines = []
                        for raw_line in f:
                            stripped = raw_line.rstrip('\n\r')
                            if stripped:
                                new_lines.append(stripped)
                        current_position = f.tell()

                    for line in new_lines:
                        self._send_sse_event('line', json.dumps(line))

            except (BrokenPipeError, ConnectionResetError, OSError):
                return

    def _send_sse_event(self, event_type, data):
        """Send a single SSE event. Raises on broken connection."""
        payload = f"event: {event_type}\ndata: {data}\n\n"
        self.wfile.write(payload.encode('utf-8'))
        self.wfile.flush()


class ThreadedHTTPServer(HTTPServer):
    """HTTPServer that handles each request in a new daemon thread."""

    daemon_threads = True
    allow_reuse_address = True

    def process_request(self, request, client_address):
        thread = threading.Thread(
            target=self.process_request_thread,
            args=(request, client_address),
            daemon=True,
        )
        thread.start()

    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog='logpeek',
        description='Lightweight browser-based JSON log viewer.',
    )
    parser.add_argument('file', help='Path to the log file to view')
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8080,
        help='Port to serve on (default: 8080)',
    )
    parser.add_argument(
        '--no-open',
        action='store_true',
        help='Do not auto-open the browser',
    )
    args = parser.parse_args()

    file_path = os.path.abspath(args.file)
    port = args.port

    # Validate the file path directory exists
    parent_directory = os.path.dirname(file_path)
    if not os.path.isdir(parent_directory):
        print(f"Error: directory {parent_directory} does not exist", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(file_path):
        print(f"Note: {file_path} does not exist yet. logpeek will wait for it to be created.")

    LogPeekHandler.log_file_path = file_path

    server = ThreadedHTTPServer(('0.0.0.0', port), LogPeekHandler)
    url = f'http://localhost:{port}'

    print(f"""
  \033[1;34m┌──────────────────────────────────────┐\033[0m
  \033[1;34m│\033[0m  \033[1mlogpeek\033[0m                              \033[1;34m│\033[0m
  \033[1;34m│\033[0m                                      \033[1;34m│\033[0m
  \033[1;34m│\033[0m  File:  \033[33m{os.path.basename(file_path):<28}\033[0m\033[1;34m│\033[0m
  \033[1;34m│\033[0m  URL:   \033[36m{url:<28}\033[0m\033[1;34m│\033[0m
  \033[1;34m│\033[0m                                      \033[1;34m│\033[0m
  \033[1;34m│\033[0m  \033[2mPress Ctrl+C to stop\033[0m                \033[1;34m│\033[0m
  \033[1;34m└──────────────────────────────────────┘\033[0m
""")

    if not args.no_open:
        # Open browser in a thread to not block server startup
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        server.shutdown()


if __name__ == '__main__':
    main()
