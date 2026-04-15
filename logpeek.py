#!/usr/bin/env python3
"""
logpeek - lightweight browser-based JSON log viewer.
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
# HTML / CSS / JS - the entire frontend is embedded here
# ---------------------------------------------------------------------------

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>logpeek</title>
<style>
/* ── Reset & Foundation ───────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

@font-face {
  font-family: 'Berkeley';
  src: local('Berkeley Mono'), local('BerkeleyMono-Regular'),
       local('SF Mono'), local('Cascadia Code'), local('Fira Code'),
       local('JetBrains Mono'), local('Consolas');
}

:root {
  --bg:         #0c0c14;
  --bg-surface: #111119;
  --bg-row:     #13131d;
  --bg-row-alt: #161622;
  --bg-hover:   #1c1c2e;
  --bg-expand:  #101020;
  --bg-input:   #161625;
  --bg-toolbar: #0f0f18;
  --bg-filter:  #111119;

  --border:     #1e1e32;
  --border-lt:  #2a2a45;
  --border-focus: #5b7fff;

  --text:       #cdd0e0;
  --text-bright:#e8eaf4;
  --text-dim:   #8486a0;
  --text-muted: #555570;

  --accent:     #5b7fff;
  --accent-glow: rgba(91,127,255,0.12);

  --search-hl:     #f0d060;
  --search-hl-bg:  rgba(240,208,96,0.14);

  --info:       #5b9bd5;
  --info-bg:    rgba(91,155,213,0.10);
  --info-border:rgba(91,155,213,0.20);

  --warn:       #d4a843;
  --warn-bg:    rgba(212,168,67,0.10);
  --warn-border:rgba(212,168,67,0.20);

  --error:      #d45555;
  --error-bg:   rgba(212,85,85,0.10);
  --error-border:rgba(212,85,85,0.20);

  --debug:      #707488;
  --debug-bg:   rgba(112,116,136,0.08);
  --debug-border:rgba(112,116,136,0.18);

  --include:    #43b88c;
  --include-bg: rgba(67,184,140,0.08);
  --include-border: rgba(67,184,140,0.25);

  --exclude:    #d45555;
  --exclude-bg: rgba(212,85,85,0.06);
  --exclude-border: rgba(212,85,85,0.25);

  --success:    #43b88c;

  --radius:     5px;
  --radius-sm:  3px;
  --radius-tag: 4px;

  --font-mono:  'Berkeley', 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace;
  --font-ui:    -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;

  --row-height: 40px;
}

html { font-size: 14px; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-mono);
  line-height: 1.55;
  overflow: hidden;
  height: 100vh;
  display: flex;
  flex-direction: column;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ── Scrollbar ────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 7px; height: 7px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-lt); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #3a3a5a; }

/* ── Header Toolbar ───────────────────────────────────────────── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 18px;
  background: var(--bg-toolbar);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  z-index: 100;
}

.logo {
  font-family: var(--font-ui);
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--accent);
  letter-spacing: 0.02em;
  user-select: none;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 8px;
}
.logo-icon {
  width: 18px; height: 18px;
  background: var(--accent);
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.logo-icon svg { width: 12px; height: 12px; }
.logo-file {
  color: var(--text-muted);
  font-weight: 400;
  font-size: 0.82rem;
  margin-left: 2px;
}

/* Search */
.search-wrap {
  position: relative;
  flex: 1;
  max-width: 420px;
}
.search-wrap svg {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  pointer-events: none;
  width: 14px; height: 14px;
}
#search {
  width: 100%;
  padding: 7px 42px 7px 32px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 0.86rem;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
#search:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 2px var(--accent-glow);
}
#search::placeholder { color: var(--text-muted); }
.search-kbd {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.68rem;
  color: var(--text-muted);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 1px 5px;
  pointer-events: none;
  font-family: var(--font-ui);
  line-height: 1.4;
}

/* Level filter chips */
.level-filters {
  display: flex;
  gap: 4px;
  align-items: center;
}
.level-chip {
  padding: 4px 9px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
  border: 1px solid transparent;
  transition: all 0.12s;
  font-family: var(--font-ui);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.level-chip.active { opacity: 1; }
.level-chip:not(.active) { opacity: 0.25; }
.lc-info    { background: var(--info-bg);  color: var(--info);  border-color: var(--info-border); }
.lc-warning { background: var(--warn-bg);  color: var(--warn);  border-color: var(--warn-border); }
.lc-error   { background: var(--error-bg); color: var(--error); border-color: var(--error-border); }
.lc-debug   { background: var(--debug-bg); color: var(--debug); border-color: var(--debug-border); }

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}

.stats {
  font-size: 0.78rem;
  color: var(--text-muted);
  white-space: nowrap;
  font-family: var(--font-ui);
  tabular-nums: true;
}
.stats strong { color: var(--text-dim); font-weight: 600; }

.live-dot {
  width: 6px; height: 6px;
  background: var(--success);
  border-radius: 50%;
  animation: pulse 2.5s ease-in-out infinite;
  flex-shrink: 0;
}
@keyframes pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(67,184,140,0.4); }
  50%      { opacity: 0.5; box-shadow: 0 0 0 4px rgba(67,184,140,0); }
}

.btn-icon {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--bg-input);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.12s;
  flex-shrink: 0;
}
.btn-icon:hover { background: var(--bg-hover); color: var(--text); border-color: var(--border-lt); }
.btn-icon svg { width: 14px; height: 14px; }

/* ── Filter Bar (Include / Exclude) ──────────────────────────── */
.filter-bar {
  display: none;
  align-items: center;
  gap: 8px;
  padding: 7px 18px;
  background: var(--bg-filter);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  flex-wrap: wrap;
  min-height: 38px;
}
.filter-bar.visible { display: flex; }

.filter-section {
  display: flex;
  align-items: center;
  gap: 5px;
}
.filter-label {
  font-family: var(--font-ui);
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 3px 7px;
  border-radius: var(--radius-sm);
  user-select: none;
  flex-shrink: 0;
}
.filter-label.include-label {
  color: var(--include);
  background: var(--include-bg);
  border: 1px solid var(--include-border);
}
.filter-label.exclude-label {
  color: var(--exclude);
  background: var(--exclude-bg);
  border: 1px solid var(--exclude-border);
}

.filter-input {
  padding: 4px 8px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 0.8rem;
  outline: none;
  width: 160px;
  transition: border-color 0.12s, box-shadow 0.12s;
}
.filter-input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 2px var(--accent-glow);
}
.filter-input::placeholder { color: var(--text-muted); font-size: 0.75rem; }
.filter-input.include-input:focus { border-color: var(--include); box-shadow: 0 0 0 2px rgba(67,184,140,0.10); }
.filter-input.exclude-input:focus { border-color: var(--exclude); box-shadow: 0 0 0 2px rgba(212,85,85,0.10); }

/* Filter tags */
.filter-tags {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-wrap: wrap;
}
.filter-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px 2px 8px;
  border-radius: var(--radius-tag);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  line-height: 1.4;
  user-select: none;
  animation: tagIn 0.15s ease-out;
}
@keyframes tagIn {
  from { opacity: 0; transform: scale(0.9); }
  to   { opacity: 1; transform: scale(1); }
}
.filter-tag.include-tag {
  background: var(--include-bg);
  color: var(--include);
  border: 1px solid var(--include-border);
}
.filter-tag.exclude-tag {
  background: var(--exclude-bg);
  color: var(--exclude);
  border: 1px solid var(--exclude-border);
}
.filter-tag .tag-remove {
  cursor: pointer;
  opacity: 0.5;
  transition: opacity 0.1s;
  display: flex;
  align-items: center;
  padding: 1px;
  border-radius: 2px;
}
.filter-tag .tag-remove:hover { opacity: 1; }
.filter-tag .tag-remove svg { width: 10px; height: 10px; }

.filter-divider {
  width: 1px;
  height: 20px;
  background: var(--border);
  margin: 0 6px;
  flex-shrink: 0;
}

.filter-clear {
  font-family: var(--font-ui);
  font-size: 0.7rem;
  color: var(--text-muted);
  cursor: pointer;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  transition: all 0.12s;
  user-select: none;
  margin-left: auto;
}
.filter-clear:hover { color: var(--text); background: var(--bg-hover); }

/* ── Column Headers ──────────────────────────────────────────── */
.col-headers {
  display: flex;
  align-items: center;
  padding: 5px 18px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-family: var(--font-ui);
  flex-shrink: 0;
  user-select: none;
}
.col-line   { width: 54px;  flex-shrink: 0; text-align: right; padding-right: 14px; }
.col-time   { width: 190px; flex-shrink: 0; }
.col-level  { width: 72px;  flex-shrink: 0; }
.col-msg    { flex: 1; min-width: 0; }

/* ── Log Container ───────────────────────────────────────────── */
#log-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
}

/* ── Log Rows ────────────────────────────────────────────────── */
.log-row {
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid rgba(30,30,50,0.5);
  cursor: pointer;
  transition: background 0.08s;
}
.log-row:nth-child(odd) { background: var(--bg-row); }
.log-row:nth-child(even) { background: var(--bg-row-alt); }
.log-row:hover { background: var(--bg-hover); }
.log-row.expanded { background: var(--bg-expand); }

.row-main {
  display: flex;
  align-items: center;
  min-height: var(--row-height);
  padding: 0 18px;
}
.row-line {
  width: 54px;
  flex-shrink: 0;
  text-align: right;
  padding-right: 14px;
  color: var(--text-muted);
  font-size: 0.78rem;
  user-select: none;
}
.row-time {
  width: 190px;
  flex-shrink: 0;
  color: var(--text-dim);
  font-size: 0.86rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.row-level {
  width: 72px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
}
.level-badge {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 3px;
  font-size: 0.66rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-family: var(--font-ui);
}
.level-info    .level-badge { background: var(--info-bg);  color: var(--info);  border: 1px solid var(--info-border); }
.level-warning .level-badge { background: var(--warn-bg);  color: var(--warn);  border: 1px solid var(--warn-border); }
.level-error   .level-badge { background: var(--error-bg); color: var(--error); border: 1px solid var(--error-border); }
.level-debug   .level-badge { background: var(--debug-bg); color: var(--debug); border: 1px solid var(--debug-border); }
.level-unknown .level-badge { background: var(--debug-bg); color: var(--text-muted); border: 1px solid var(--debug-border); }

.row-msg {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.86rem;
  padding-right: 10px;
  color: var(--text);
}
.row-raw {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.86rem;
  color: var(--text-dim);
  padding-right: 10px;
}

/* Expand indicator */
.row-expand-icon {
  width: 20px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  transition: transform 0.15s, color 0.15s;
}
.row-expand-icon svg { width: 10px; height: 10px; }
.log-row.expanded .row-expand-icon { transform: rotate(90deg); color: var(--accent); }

/* ── Expanded Detail ─────────────────────────────────────────── */
.row-detail {
  display: none;
  padding: 14px 18px 16px 86px;
  background: var(--bg-expand);
  border-top: 1px solid var(--border);
  animation: slideDown 0.12s ease-out;
  position: relative;
}
.log-row.expanded .row-detail { display: block; }
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-3px); }
  to   { opacity: 1; transform: translateY(0); }
}
.detail-actions {
  position: absolute;
  top: 12px;
  right: 18px;
  display: flex;
  gap: 5px;
}
.btn-action {
  padding: 3px 10px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-dim);
  font-size: 0.72rem;
  cursor: pointer;
  font-family: var(--font-ui);
  transition: all 0.12s;
}
.btn-action:hover { background: var(--bg-hover); color: var(--text); border-color: var(--border-lt); }
.btn-action.copied { color: var(--success); border-color: var(--success); }
.btn-action.include-action:hover { color: var(--include); border-color: var(--include-border); }
.btn-action.exclude-action:hover { color: var(--exclude); border-color: var(--exclude-border); }

/* JSON tree */
.json-tree { font-size: 0.84rem; line-height: 1.7; }
.json-tree pre { font-family: var(--font-mono); white-space: pre-wrap; word-break: break-word; }
.json-key   { color: #8ba5e8; }
.json-str   { color: #7ec69a; }
.json-num   { color: #c9a0e8; }
.json-bool  { color: #e8b070; }
.json-null  { color: var(--text-muted); font-style: italic; }
.json-brace { color: var(--text-dim); }
.json-toggle {
  cursor: pointer;
  user-select: none;
  color: var(--text-muted);
  display: inline-block;
  width: 14px;
  text-align: center;
  font-size: 0.65rem;
  transition: transform 0.12s;
  margin-right: 2px;
}
.json-toggle:hover { color: var(--accent); }
.json-toggle.collapsed { transform: rotate(-90deg); }
.json-collapsible.collapsed > .json-children { display: none; }
.json-collapsible.collapsed > .json-summary { display: inline; }
.json-summary { display: none; color: var(--text-muted); font-style: italic; font-size: 0.78rem; }

.detail-raw {
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--text-dim);
  font-size: 0.84rem;
}

/* ── Search highlights ───────────────────────────────────────── */
mark {
  background: var(--search-hl-bg);
  color: var(--search-hl);
  border-radius: 2px;
  padding: 0 1px;
  border-bottom: 1.5px solid var(--search-hl);
}

/* ── Jump to bottom ──────────────────────────────────────────── */
#jump-btn {
  position: fixed;
  bottom: 20px;
  right: 20px;
  padding: 7px 16px 7px 12px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-family: var(--font-ui);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(91,127,255,0.25), 0 0 0 1px rgba(91,127,255,0.15);
  transition: all 0.15s;
  z-index: 200;
  display: none;
  align-items: center;
  gap: 5px;
}
#jump-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(91,127,255,0.35); }
#jump-btn svg { width: 12px; height: 12px; }

/* ── Guide Overlay ───────────────────────────────────────────── */
.guide-overlay {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(8,8,16,0.85);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  justify-content: center;
  align-items: center;
  animation: fadeIn 0.15s ease-out;
}
.guide-overlay.visible { display: flex; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.guide-panel {
  background: var(--bg-surface);
  border: 1px solid var(--border-lt);
  border-radius: 10px;
  width: 560px;
  max-width: 92vw;
  max-height: 85vh;
  overflow-y: auto;
  padding: 28px 32px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  animation: slideUp 0.2s ease-out;
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
.guide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 22px;
}
.guide-title {
  font-family: var(--font-ui);
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--text-bright);
}
.guide-close {
  width: 28px; height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.1s;
}
.guide-close:hover { background: var(--bg-hover); color: var(--text); }
.guide-close svg { width: 12px; height: 12px; }

.guide-section {
  margin-bottom: 20px;
}
.guide-section:last-child { margin-bottom: 0; }
.guide-section-title {
  font-family: var(--font-ui);
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 10px;
}
.guide-row {
  display: flex;
  align-items: center;
  padding: 6px 0;
  gap: 12px;
}
.guide-row + .guide-row { border-top: 1px solid rgba(30,30,50,0.4); }
.guide-keys {
  display: flex;
  gap: 4px;
  min-width: 110px;
  flex-shrink: 0;
}
.guide-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 22px;
  padding: 0 6px;
  background: var(--bg-input);
  border: 1px solid var(--border-lt);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--text-dim);
  line-height: 1;
}
.guide-desc {
  font-family: var(--font-ui);
  font-size: 0.82rem;
  color: var(--text);
}
.guide-hint {
  font-family: var(--font-ui);
  font-size: 0.78rem;
  color: var(--text-muted);
  line-height: 1.5;
  margin-top: 4px;
}

/* ── Empty state ─────────────────────────────────────────────── */
#empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  font-family: var(--font-ui);
  gap: 6px;
}
#empty-state .empty-icon {
  font-size: 2rem;
  opacity: 0.3;
  margin-bottom: 4px;
}
#empty-state .empty-text { font-size: 0.9rem; color: var(--text-dim); }
#empty-state .empty-sub  { font-size: 0.78rem; opacity: 0.5; }

/* ── Responsive ──────────────────────────────────────────────── */
@media (max-width: 768px) {
  .toolbar { flex-wrap: wrap; gap: 8px; padding: 8px 12px; }
  .search-wrap { max-width: 100%; order: 10; flex-basis: 100%; }
  .level-filters { order: 11; }
  .toolbar-right { order: 5; }
  .col-time, .row-time { width: 140px; }
  .col-line, .row-line { width: 40px; }
  .row-detail { padding-left: 16px; }
  .filter-bar { padding: 6px 12px; }
}
@media (max-width: 500px) {
  .col-time, .row-time { display: none; }
}
</style>
</head>
<body>

<!-- Toolbar -->
<div class="toolbar">
  <div class="logo">
    <div class="logo-icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="#0c0c14" stroke-width="3" stroke-linecap="round">
        <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
      </svg>
    </div>
    logpeek
    <span class="logo-file" id="filename"></span>
  </div>

  <div class="search-wrap">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    <input type="text" id="search" placeholder="Search logs..." autocomplete="off" spellcheck="false" />
    <span class="search-kbd" id="search-hint">/</span>
  </div>

  <div class="level-filters">
    <div class="level-chip lc-debug active"   data-level="debug"   onclick="toggleLevel('debug')">DBG</div>
    <div class="level-chip lc-info active"     data-level="info"    onclick="toggleLevel('info')">INF</div>
    <div class="level-chip lc-warning active"  data-level="warning" onclick="toggleLevel('warning')">WRN</div>
    <div class="level-chip lc-error active"    data-level="error"   onclick="toggleLevel('error')">ERR</div>
  </div>

  <div class="toolbar-right">
    <div class="stats">
      <strong id="shown-count">0</strong> / <strong id="total-count">0</strong>
    </div>
    <div class="live-dot" title="Connected"></div>
    <button class="btn-icon" onclick="toggleFilterBar()" title="Filters (F)">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
    </button>
    <button class="btn-icon" onclick="toggleGuide()" title="Guide (?)">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
    </button>
  </div>
</div>

<!-- Filter Bar -->
<div class="filter-bar" id="filter-bar">
  <div class="filter-section">
    <span class="filter-label include-label">+ Include</span>
    <input type="text" class="filter-input include-input" id="include-input" placeholder="text to include..." />
    <div class="filter-tags" id="include-tags"></div>
  </div>

  <div class="filter-divider"></div>

  <div class="filter-section">
    <span class="filter-label exclude-label">&minus; Exclude</span>
    <input type="text" class="filter-input exclude-input" id="exclude-input" placeholder="text to exclude..." />
    <div class="filter-tags" id="exclude-tags"></div>
  </div>

  <span class="filter-clear" id="filter-clear" onclick="clearAllFilters()">Clear all</span>
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

<!-- Guide Overlay -->
<div class="guide-overlay" id="guide-overlay" onclick="if(event.target===this)toggleGuide()">
  <div class="guide-panel">
    <div class="guide-header">
      <span class="guide-title">logpeek guide</span>
      <button class="guide-close" onclick="toggleGuide()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>

    <div class="guide-section">
      <div class="guide-section-title">Keyboard shortcuts</div>
      <div class="guide-row"><div class="guide-keys"><span class="guide-key">/</span></div><div class="guide-desc">Focus search</div></div>
      <div class="guide-row"><div class="guide-keys"><span class="guide-key">Esc</span></div><div class="guide-desc">Clear search & close panels</div></div>
      <div class="guide-row"><div class="guide-keys"><span class="guide-key">G</span></div><div class="guide-desc">Jump to latest logs</div></div>
      <div class="guide-row"><div class="guide-keys"><span class="guide-key">F</span></div><div class="guide-desc">Toggle include/exclude filter bar</div></div>
      <div class="guide-row"><div class="guide-keys"><span class="guide-key">I</span></div><div class="guide-desc">Focus include filter input</div></div>
      <div class="guide-row"><div class="guide-keys"><span class="guide-key">X</span></div><div class="guide-desc">Focus exclude filter input</div></div>
      <div class="guide-row"><div class="guide-keys"><span class="guide-key">C</span></div><div class="guide-desc">Clear all include/exclude filters</div></div>
      <div class="guide-row"><div class="guide-keys"><span class="guide-key">?</span></div><div class="guide-desc">Toggle this guide</div></div>
      <div class="guide-row"><div class="guide-keys"><span class="guide-key">1</span><span class="guide-key">2</span><span class="guide-key">3</span><span class="guide-key">4</span></div><div class="guide-desc">Toggle DBG / INF / WRN / ERR level</div></div>
    </div>

    <div class="guide-section">
      <div class="guide-section-title">Filtering</div>
      <div class="guide-hint">
        <strong>Search</strong> filters across all fields in real time.<br>
        <strong>Include</strong> tags show only lines containing that text. Multiple includes are OR-matched (line matches if it contains any include term).<br>
        <strong>Exclude</strong> tags hide any line containing that text. Excludes always win over includes.<br>
        Press <strong>Enter</strong> in the include/exclude input to add a filter tag. Click the &times; on a tag to remove it.
      </div>
    </div>

    <div class="guide-section">
      <div class="guide-section-title">Quick actions</div>
      <div class="guide-hint">
        Click any log row to expand its full JSON. In the expanded view, use <strong>Include msg</strong> or <strong>Exclude msg</strong> buttons to quickly filter by that log's message text.
        Use <strong>Copy JSON</strong> to copy the pretty-printed log entry to your clipboard.
      </div>
    </div>

    <div class="guide-section">
      <div class="guide-section-title">Tips</div>
      <div class="guide-hint">
        Auto-scroll pauses when you scroll up. A &ldquo;New logs&rdquo; button appears to jump back to the bottom.<br>
        The live indicator pulses green when connected to the file watcher.
      </div>
    </div>
  </div>
</div>

<script>
// ── State ──────────────────────────────────────────────────────
const allLines = [];
let searchTerm = '';
let activeFilters = { debug: true, info: true, warning: true, error: true, raw: true };
let includeTags = [];
let excludeTags = [];
let autoScroll = true;
let userScrolledUp = false;
let guideOpen = false;
let filterBarOpen = false;

const container = document.getElementById('log-container');
const emptyState = document.getElementById('empty-state');
const searchInput = document.getElementById('search');
const searchHint = document.getElementById('search-hint');
const jumpBtn = document.getElementById('jump-btn');
const totalCountEl = document.getElementById('total-count');
const shownCountEl = document.getElementById('shown-count');
const filterBar = document.getElementById('filter-bar');
const includeInput = document.getElementById('include-input');
const excludeInput = document.getElementById('exclude-input');
const includeTagsEl = document.getElementById('include-tags');
const excludeTagsEl = document.getElementById('exclude-tags');
const guideOverlay = document.getElementById('guide-overlay');
const filterClear = document.getElementById('filter-clear');

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
  try {
    if (timeStr.includes('T')) {
      const parts = timeStr.split('T');
      let time = parts[1];
      if (time && time.includes('.')) {
        const [sec, frac] = time.split('.');
        time = sec + '.' + frac.substring(0, 3);
      }
      return parts[0] + ' ' + time;
    }
    return timeStr;
  } catch { return timeStr; }
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
    } catch { /* not JSON */ }
  }

  return { lineNum, raw: trimmed, parsed, isJson, level, message, timestamp };
}

// ── Include / Exclude logic ───────────────────────────────────
function matchesIncludeExclude(line) {
  const text = line.raw.toLowerCase();

  // Excludes always win
  for (const ex of excludeTags) {
    if (text.includes(ex.toLowerCase())) return false;
  }

  // If includes exist, line must match at least one
  if (includeTags.length > 0) {
    let matchesAny = false;
    for (const inc of includeTags) {
      if (text.includes(inc.toLowerCase())) { matchesAny = true; break; }
    }
    if (!matchesAny) return false;
  }

  return true;
}

function renderFilterTags() {
  includeTagsEl.innerHTML = includeTags.map((tag, i) =>
    `<span class="filter-tag include-tag">
      ${escapeHtml(tag)}
      <span class="tag-remove" onclick="removeInclude(${i})">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </span>
    </span>`
  ).join('');

  excludeTagsEl.innerHTML = excludeTags.map((tag, i) =>
    `<span class="filter-tag exclude-tag">
      ${escapeHtml(tag)}
      <span class="tag-remove" onclick="removeExclude(${i})">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </span>
    </span>`
  ).join('');

  // Show/hide clear button
  filterClear.style.display = (includeTags.length || excludeTags.length) ? '' : 'none';
}

window.removeInclude = function(index) {
  includeTags.splice(index, 1);
  renderFilterTags();
  renderAll();
};
window.removeExclude = function(index) {
  excludeTags.splice(index, 1);
  renderFilterTags();
  renderAll();
};

window.addInclude = function(text) {
  const trimmed = text.trim();
  if (!trimmed || includeTags.includes(trimmed)) return;
  includeTags.push(trimmed);
  if (!filterBarOpen) toggleFilterBar();
  renderFilterTags();
  renderAll();
};
window.addExclude = function(text) {
  const trimmed = text.trim();
  if (!trimmed || excludeTags.includes(trimmed)) return;
  excludeTags.push(trimmed);
  if (!filterBarOpen) toggleFilterBar();
  renderFilterTags();
  renderAll();
};

window.clearAllFilters = function() {
  includeTags = [];
  excludeTags = [];
  renderFilterTags();
  renderAll();
};

includeInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    addInclude(includeInput.value);
    includeInput.value = '';
  }
});
excludeInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    addExclude(excludeInput.value);
    excludeInput.value = '';
  }
});

// ── Filter bar toggle ─────────────────────────────────────────
window.toggleFilterBar = function() {
  filterBarOpen = !filterBarOpen;
  filterBar.classList.toggle('visible', filterBarOpen);
};

// ── Guide toggle ──────────────────────────────────────────────
window.toggleGuide = function() {
  guideOpen = !guideOpen;
  guideOverlay.classList.toggle('visible', guideOpen);
};

// ── JSON Tree Renderer ────────────────────────────────────────
function renderJsonTree(data, depth, term) {
  if (data === null) return '<span class="json-null">null</span>';
  if (data === undefined) return '<span class="json-null">undefined</span>';

  const type = typeof data;
  if (type === 'boolean') return '<span class="json-bool">' + data + '</span>';
  if (type === 'number')  return '<span class="json-num">' + data + '</span>';
  if (type === 'string') {
    return '<span class="json-str">' + highlightText('"' + data + '"', term) + '</span>';
  }

  const isArray = Array.isArray(data);
  const entries = isArray ? data.map((v, i) => [i, v]) : Object.entries(data);
  const openBrace = isArray ? '[' : '{';
  const closeBrace = isArray ? ']' : '}';

  if (entries.length === 0) {
    return '<span class="json-brace">' + openBrace + closeBrace + '</span>';
  }

  const indent = '  '.repeat(depth + 1);
  const closingIndent = '  '.repeat(depth);
  const id = 'jt-' + Math.random().toString(36).substring(2, 9);
  const summaryText = isArray
    ? entries.length + ' item' + (entries.length !== 1 ? 's' : '')
    : entries.length + ' key' + (entries.length !== 1 ? 's' : '');

  let html = '<span class="json-collapsible" id="' + id + '">';
  html += '<span class="json-toggle" onclick="toggleJsonNode(\'' + id + '\')">&#9660;</span>';
  html += '<span class="json-brace">' + openBrace + '</span>';
  html += '<span class="json-summary">' + summaryText + closeBrace + '</span>';
  html += '<span class="json-children">';

  entries.forEach(([key, value], index) => {
    html += '\n' + indent;
    if (!isArray) {
      html += '<span class="json-key">' + highlightText('"' + key + '"', term) + '</span>: ';
    }
    html += renderJsonTree(value, depth + 1, term);
    if (index < entries.length - 1) html += ',';
  });

  html += '\n' + closingIndent;
  html += '<span class="json-brace">' + closeBrace + '</span>';
  html += '</span></span>';
  return html;
}

window.toggleJsonNode = function(id) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle('collapsed');
};

// ── Row Rendering ─────────────────────────────────────────────
function matchesSearch(line, term) {
  if (!term) return true;
  return line.raw.toLowerCase().includes(term.toLowerCase());
}

function matchesFilter(line) {
  if (!line.isJson) return activeFilters.raw !== false;
  return activeFilters[line.level] !== false;
}

function isVisible(line) {
  return matchesSearch(line, searchTerm) && matchesFilter(line) && matchesIncludeExclude(line);
}

function truncateMsg(msg, max) {
  if (msg.length <= max) return msg;
  return msg.substring(0, max) + '...';
}

function createRowHtml(line) {
  if (!isVisible(line)) return null;

  const levelClass = 'level-' + line.level;
  const levelLabel = line.level === 'unknown' ? 'RAW' : line.level.toUpperCase().substring(0, 3);

  let timeHtml = '';
  let msgHtml = '';

  if (line.isJson) {
    timeHtml = '<div class="row-time">' + highlightText(formatTime(line.timestamp), searchTerm) + '</div>';
    msgHtml = '<div class="row-msg">' + highlightText(String(line.message), searchTerm) + '</div>';
  } else {
    timeHtml = '<div class="row-time"></div>';
    msgHtml = '<div class="row-raw">' + highlightText(line.raw, searchTerm) + '</div>';
  }

  // Inline actions for expanded view
  const msgText = escapeHtml(truncateMsg(String(line.message || line.raw), 60));
  let detailHtml = '';
  if (line.isJson) {
    detailHtml = '<div class="row-detail">' +
      '<div class="detail-actions">' +
        '<button class="btn-action include-action" onclick="addIncludeFromRow(event,' + (line.lineNum - 1) + ')" title="Include this message">+ Include msg</button>' +
        '<button class="btn-action exclude-action" onclick="addExcludeFromRow(event,' + (line.lineNum - 1) + ')" title="Exclude this message">&minus; Exclude msg</button>' +
        '<button class="btn-action" onclick="copyLine(event,' + (line.lineNum - 1) + ')">Copy JSON</button>' +
      '</div>' +
      '<div class="json-tree"><pre>' + renderJsonTree(line.parsed, 0, searchTerm) + '</pre></div>' +
    '</div>';
  } else {
    detailHtml = '<div class="row-detail">' +
      '<div class="detail-actions">' +
        '<button class="btn-action include-action" onclick="addIncludeFromRow(event,' + (line.lineNum - 1) + ')">+ Include</button>' +
        '<button class="btn-action exclude-action" onclick="addExcludeFromRow(event,' + (line.lineNum - 1) + ')">&minus; Exclude</button>' +
        '<button class="btn-action" onclick="copyLine(event,' + (line.lineNum - 1) + ')">Copy</button>' +
      '</div>' +
      '<div class="detail-raw">' + highlightText(line.raw, searchTerm) + '</div>' +
    '</div>';
  }

  return '<div class="log-row ' + levelClass + '" data-line="' + line.lineNum + '" onclick="toggleRow(this,event)">' +
    '<div class="row-main">' +
      '<div class="row-line">' + line.lineNum + '</div>' +
      timeHtml +
      '<div class="row-level"><span class="level-badge">' + levelLabel + '</span></div>' +
      msgHtml +
      '<div class="row-expand-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg></div>' +
    '</div>' +
    detailHtml +
  '</div>';
}

// ── Include/Exclude from expanded row ─────────────────────────
window.addIncludeFromRow = function(event, index) {
  event.stopPropagation();
  const line = allLines[index];
  if (!line) return;
  const text = String(line.message || line.raw).substring(0, 80);
  addInclude(text);
};
window.addExcludeFromRow = function(event, index) {
  event.stopPropagation();
  const line = allLines[index];
  if (!line) return;
  const text = String(line.message || line.raw).substring(0, 80);
  addExclude(text);
};

// ── Full re-render ────────────────────────────────────────────
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

// ── Append new rows (live tail fast path) ─────────────────────
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

// ── Row expand/collapse ───────────────────────────────────────
window.toggleRow = function(rowEl, event) {
  if (event.target.closest('.btn-action') || event.target.closest('a') || event.target.closest('.tag-remove')) return;
  rowEl.classList.toggle('expanded');
};

// ── Copy ──────────────────────────────────────────────────────
window.copyLine = function(event, index) {
  event.stopPropagation();
  const line = allLines[index];
  if (!line) return;

  const text = line.isJson ? JSON.stringify(line.parsed, null, 2) : line.raw;
  navigator.clipboard.writeText(text).then(() => {
    const btn = event.target;
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = orig;
      btn.classList.remove('copied');
    }, 1200);
  });
};

// ── Search ────────────────────────────────────────────────────
let searchTimeout;
searchInput.addEventListener('input', () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    searchTerm = searchInput.value.trim();
    searchHint.style.display = searchTerm ? 'none' : '';
    renderAll();
  }, 150);
});

// ── Level filter toggles ──────────────────────────────────────
window.toggleLevel = function(level) {
  activeFilters[level] = !activeFilters[level];
  const chip = document.querySelector('.level-chip[data-level="' + level + '"]');
  if (chip) chip.classList.toggle('active', activeFilters[level]);
  renderAll();
};

// ── Check if any filter is active (for fast-path decisions) ──
function hasActiveTextFilters() {
  return searchTerm || includeTags.length > 0 || excludeTags.length > 0 ||
         !activeFilters.debug || !activeFilters.info || !activeFilters.warning || !activeFilters.error;
}

// ── Auto-scroll detection ─────────────────────────────────────
container.addEventListener('scroll', () => {
  const threshold = 80;
  const atBottom = container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
  userScrolledUp = !atBottom;
  jumpBtn.style.display = userScrolledUp ? 'flex' : 'none';
  autoScroll = atBottom;
});

window.jumpToBottom = function() {
  container.scrollTop = container.scrollHeight;
  autoScroll = true;
  userScrolledUp = false;
  jumpBtn.style.display = 'none';
};

// ── Keyboard shortcuts ────────────────────────────────────────
function isInInput() {
  const el = document.activeElement;
  return el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA');
}

document.addEventListener('keydown', (e) => {
  const inInput = isInInput();

  // Escape: clear/close everything
  if (e.key === 'Escape') {
    if (guideOpen) { toggleGuide(); return; }
    if (inInput) {
      document.activeElement.blur();
      if (document.activeElement === searchInput) {
        searchInput.value = '';
        searchTerm = '';
        searchHint.style.display = '';
        renderAll();
      }
      return;
    }
  }

  // Shortcuts only when not in an input
  if (inInput) return;

  if (e.key === '/') {
    e.preventDefault();
    searchInput.focus();
    searchInput.select();
  }
  if (e.key === 'g' || e.key === 'G') {
    jumpToBottom();
  }
  if (e.key === 'f' || e.key === 'F') {
    e.preventDefault();
    toggleFilterBar();
  }
  if (e.key === 'i' || e.key === 'I') {
    e.preventDefault();
    if (!filterBarOpen) toggleFilterBar();
    includeInput.focus();
  }
  if (e.key === 'x' || e.key === 'X') {
    e.preventDefault();
    if (!filterBarOpen) toggleFilterBar();
    excludeInput.focus();
  }
  if (e.key === 'c' || e.key === 'C') {
    clearAllFilters();
  }
  if (e.key === '?') {
    toggleGuide();
  }
  // Number keys for level toggles
  if (e.key === '1') toggleLevel('debug');
  if (e.key === '2') toggleLevel('info');
  if (e.key === '3') toggleLevel('warning');
  if (e.key === '4') toggleLevel('error');
});

// ── SSE - Load initial data + live tail ───────────────────────
function connectSSE() {
  const evtSource = new EventSource('/events');

  evtSource.addEventListener('init', (e) => {
    const data = JSON.parse(e.data);
    document.getElementById('filename').textContent = data.filename;
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
      if (hasActiveTextFilters()) {
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
      if (hasActiveTextFilters()) {
        renderAll();
      } else {
        appendRows([parsed]);
      }
    }
  });

  evtSource.onerror = () => {
    evtSource.close();
    setTimeout(connectSSE, 2000);
  };
}

// Init
renderFilterTags();
connectSSE();
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class LogPeekHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves the HTML page and SSE events."""

    log_file_path = None

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

        # Send init event
        filename = os.path.basename(file_path)
        self._send_sse_event('init', json.dumps({'filename': filename}))

        # Wait for file
        while not os.path.exists(file_path):
            try:
                self._send_sse_event('line', json.dumps('[waiting for file...]'))
                time.sleep(1)
            except (BrokenPipeError, ConnectionResetError):
                return

        # Read existing content in bulk
        try:
            with open(file_path, 'r', errors='replace') as f:
                batch = []
                for raw_line in f:
                    stripped = raw_line.rstrip('\n\r')
                    if stripped:
                        batch.append(stripped)
                    if len(batch) >= 500:
                        self._send_sse_event('bulk', json.dumps(batch))
                        batch = []
                if batch:
                    self._send_sse_event('bulk', json.dumps(batch))
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
                if file_size < current_position:
                    current_position = 0
                if file_size > current_position:
                    with open(file_path, 'r', errors='replace') as f:
                        f.seek(current_position)
                        for raw_line in f:
                            stripped = raw_line.rstrip('\n\r')
                            if stripped:
                                self._send_sse_event('line', json.dumps(stripped))
                        current_position = f.tell()
            except (BrokenPipeError, ConnectionResetError, OSError):
                return

    def _send_sse_event(self, event_type, data):
        payload = f"event: {event_type}\ndata: {data}\n\n"
        self.wfile.write(payload.encode('utf-8'))
        self.wfile.flush()


class ThreadedHTTPServer(HTTPServer):
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
    parser.add_argument('--port', '-p', type=int, default=8080, help='Port to serve on (default: 8080)')
    parser.add_argument('--no-open', action='store_true', help='Do not auto-open the browser')
    args = parser.parse_args()

    file_path = os.path.abspath(args.file)
    port = args.port

    parent_directory = os.path.dirname(file_path)
    if not os.path.isdir(parent_directory):
        print(f"Error: directory {parent_directory} does not exist", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(file_path):
        print(f"Note: {file_path} does not exist yet. logpeek will wait for it.")

    LogPeekHandler.log_file_path = file_path
    server = ThreadedHTTPServer(('0.0.0.0', port), LogPeekHandler)
    url = f'http://localhost:{port}'

    print(f"""
  \033[1;34m┌───────────────────────────────────────┐\033[0m
  \033[1;34m│\033[0m  \033[1mlogpeek\033[0m                               \033[1;34m│\033[0m
  \033[1;34m│\033[0m                                       \033[1;34m│\033[0m
  \033[1;34m│\033[0m  File:  \033[33m{os.path.basename(file_path):<29}\033[0m\033[1;34m│\033[0m
  \033[1;34m│\033[0m  URL:   \033[36m{url:<29}\033[0m\033[1;34m│\033[0m
  \033[1;34m│\033[0m                                       \033[1;34m│\033[0m
  \033[1;34m│\033[0m  \033[2mPress ? in browser for shortcuts\033[0m      \033[1;34m│\033[0m
  \033[1;34m│\033[0m  \033[2mPress Ctrl+C to stop\033[0m                 \033[1;34m│\033[0m
  \033[1;34m└───────────────────────────────────────┘\033[0m
""")

    if not args.no_open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        server.shutdown()


if __name__ == '__main__':
    main()
