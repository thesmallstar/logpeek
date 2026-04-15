# logpeek

A lightweight, zero-dependency browser-based log viewer for JSON log files. One Python file, no `pip install`, just point at a file and go.

![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue) ![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-green) ![License](https://img.shields.io/badge/license-MIT-gray)

## Quick Start

```bash
# Clone
git clone https://github.com/thesmallstar/logpeek.git
cd logpeek

# Run (opens browser automatically)
python3 logpeek.py /path/to/your/app.log

# Custom port
python3 logpeek.py --port 9090 /path/to/your/app.log

# Don't auto-open browser
python3 logpeek.py --no-open /path/to/your/app.log
```

For quick access, symlink to your PATH:

```bash
ln -s $(pwd)/logpeek.py /usr/local/bin/logpeek

# Then use from anywhere:
logpeek ~/codes/my-app/logs/dev.log
```

## Features

### Live Tail
Watches the log file and pushes new lines to the browser in real-time via Server-Sent Events. Auto-scrolls to keep up with new logs, pauses when you scroll up, and shows a "New logs" button to jump back.

### JSON Auto-Parsing
Detects JSON log lines and displays them as structured rows with **timestamp**, **level**, and **message** columns. Non-JSON lines (like Django dev server output) are shown as plain text.

### Search
Full-text search across all fields with real-time filtering and highlighted matches. Press `/` to focus, `Esc` to clear.

### Include / Exclude Filters
Powerful text-based filtering with tag system:
- **Include** (green): Only show lines containing the text. Multiple includes are OR-matched.
- **Exclude** (red): Hide lines containing the text. Excludes always win over includes.
- Press `F` to toggle the filter bar, `I` to focus include, `X` to focus exclude.
- Type your filter text and press `Enter` to add a tag. Click `x` on a tag to remove it.
- Quick action: expand any row and click **+ Include msg** or **- Exclude msg** to filter by that log's message.

### Level Filtering
Toggle visibility of log levels with chips in the toolbar or keyboard shortcuts:
- `1` = DEBUG, `2` = INFO, `3` = WARNING, `4` = ERROR, `5` = RAW (plain text)

### Pinned Fields
Pin any JSON field to the main row view — see key values without expanding:
1. Click a log row to expand it
2. Hover over any value in the JSON tree — a pin icon appears
3. Click the pin icon to pin that field
4. The field's value now shows as a chip beneath the message for **every log row** that has it

Great for pinning fields like `attributes.assessment_id`, `context.tenant.tenant_id`, or `metadata.source.module` so you can scan them across all logs at a glance.

### Expandable JSON Tree
Click any row to expand the full JSON with:
- Syntax highlighting (keys, strings, numbers, booleans, null)
- Collapsible nested objects
- Copy JSON button

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `/` | Focus search |
| `Esc` | Clear search / close panels |
| `G` | Jump to latest logs |
| `F` | Toggle include/exclude filter bar |
| `I` | Focus include filter input |
| `X` | Focus exclude filter input |
| `C` | Clear all include/exclude filters |
| `?` | Open guide overlay |
| `1-5` | Toggle DBG / INF / WRN / ERR / RAW |

Press `?` in the browser for the full interactive guide.

## Log Format

Designed for structured JSON logs (one object per line):

```json
{"time": "2026-04-15T10:56:55", "level": "INFO", "message": "Request processed", "attributes": {"status": 200}}
```

Supports common field names: `time`/`timestamp`/`ts`/`@timestamp`, `level`/`Level`/`severity`, `message`/`msg`/`Message`.

Plain text lines are also handled gracefully:

```
[15/Apr/2026 10:57:55] "GET /api/v1/health/ HTTP/1.1" 200 129
```

## Requirements

- Python 3.8+
- A modern browser
- That's it. No pip install. No node_modules. No Docker. One file.
