# logpeek

A lightweight browser-based JSON log viewer. Zero dependencies — just Python stdlib.

## Install

```bash
# Clone and make executable
chmod +x logpeek.py

# Optional: symlink to PATH
ln -s $(pwd)/logpeek.py /usr/local/bin/logpeek
```

## Usage

```bash
# Open a log file in the browser
./logpeek.py /path/to/file.log

# Custom port
./logpeek.py --port 9090 /path/to/file.log

# Don't auto-open browser
./logpeek.py --no-open /path/to/file.log
```

## Features

- **JSON auto-parsing** — detects JSON lines, shows structured columns (time, level, message)
- **Plain text fallback** — non-JSON lines shown as-is
- **Live tail** — watches for new lines via SSE, pushes to browser in real-time
- **Full-text search** — filters across all fields, highlights matches
- **Level filtering** — toggle INFO, WARNING, ERROR, DEBUG
- **Expandable rows** — click to see full JSON with syntax highlighting and collapsible objects
- **Auto-scroll** — follows new logs, pauses when you scroll up, "Jump to bottom" button
- **Keyboard shortcuts** — `/` to search, `Escape` to clear, `G` to jump to bottom
- **Copy** — copy any log line as JSON

## Log format

Designed for structured JSON logs (one object per line):

```json
{"time": "2026-04-15T10:56:55.951063", "level": "INFO", "message": "Request processed", "attributes": {"status": 200}}
```

Plain text lines are also handled:

```
[15/Apr/2026 10:57:55] "GET /api/v1/health/ HTTP/1.1" 200 129
```

## Requirements

- Python 3.8+
- A modern browser
- That's it. No pip install, no node_modules, no Docker.
