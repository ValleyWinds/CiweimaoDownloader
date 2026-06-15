# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

CiweimaoDownloader downloads novels from ciweimao.com (刺猬猫), decrypts them, and outputs TXT + EPUB files. Downloaded chapters arrive as encrypted files from a companion mobile app; this tool decrypts and packages them locally. No login/account data is involved.

Two data-source modes:
- **ADB mode**: automatically pulls encrypted chapters + keys from a rooted Android emulator via adb
- **Local mode**: user places encrypted data in `data/` manually

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the program
python src/main.py

# Build Windows EXE (Nuitka)
pwsh build.ps1
```

There is no test suite yet.

## Directory structure

```
./
  setting.yaml         # User config
  data/                # Runtime data (gitignored)
    key/               # Decryption keys (base64 filenames → chapter IDs)
    <book_id>/         # Encrypted chapter files per book
    decrypted/         # Cache: decrypted text + downloaded images
  output/              # Final output (gitignored)
    <safeName>.txt     # Decrypted plain-text book
    <safeName>.epub    # Final EPUB
  src/                 # Source code (flat modules, no package)
```

## Architecture

Entry point: `src/main.py` — see `main()` function. Flat module layout in `src/`, no `__init__.py`.

### Data flow

1. **`config.init()`** — loads `setting.yaml` (Pydantic models in `models.py`), writes default config if missing
2. **ADB init** (if `adb.enable`) — `adbUtils.check_adb()` verifies device + root, `adbUtils.pull_keys()` copies key files from device to `data/key/` via `su -c cp` → `adb pull`
3. **`fileUtils.TransformFilename("data/key")`** — base64-decodes key filenames into plain chapter IDs (skipped if `done` marker exists)
4. **Queue resolution** — `resolve_queue()` dispatches based on `interactive.mode`:
   - `auto`: use config if complete, else show menu
   - `always`: always show menu
   - `never`: config must be complete or exit
5. **`_config_resolve()`** evaluates config to build book queue without interaction
6. **`_interactive_resolve()`** shows `menu.py` numbered menu (6 options + exit), returns queue from user choices
7. **Per-book `process_book()`**:
   - Parse book ID from URL or plain ID
   - `adbUtils.pull_book(book_id)` if ADB mode — copies `data/<book_id>/` from device
   - `fileUtils.RemoveNewlinesInEachFile(Path("data") / book_id)` — strips `\r`/`\n` from encrypted text
   - `requestUtils.GetName(book)` — scrapes metadata from ciweimao.com via `og:` meta tags
   - `requestUtils.GetContents(book)` — POSTs to ciweimao API for chapter list
   - `config.CalculateParama(book)` — derives per-chapter paths under `data/` and `output/`
   - Decryption loop — AES-256-CBC (SHA-256 of seed, zero IV) via `decrypt.decrypt()`
   - `epubUtils.GenerateEpub(book, path)` — EPUB generation pipeline
8. Errors skip the book instead of crashing; no blocking prompts at exit

### Key modules

| File | Purpose |
|------|---------|
| `src/models.py` | `Book`/`Chapters` dataclasses, Pydantic `Config` model (`homePage`, `batch`, `cache`, `log`, `multiThread`, `manualBook`, `adb`, `interactive`), colorama `Print` logger, requests session-with-retry |
| `src/config.py` | Config init with embedded default YAML, `CalculateParama()` path derivation |
| `src/menu.py` | Numbered TUI menu system (`show_main_menu`, `input_book_url`, `input_book_id_list`, `confirm`), zero new deps, colorama-styled |
| `src/adbUtils.py` | ADB operations: `check_adb()`, `pull_keys()`, `pull_book()`, `list_books()`. Uses `su -c cp` to sdcard → `adb pull` → cleanup strategy |
| `src/requestUtils.py` | `GetName` (og: meta scraper) and `GetContents` (chapter list API) |
| `src/decrypt.py` | AES-256-CBC decryption via pycryptodome |
| `src/fileUtils.py` | YAML loader, `RemoveNewlinesInEachFile()`, `TransformFilename()` (base64→chapter ID rename) |
| `src/epubUtils.py` | EPUB generation: ThreadPoolExecutor chapter parsing → asyncio image download → ebooklib assembly |
| `src/asyncHttp.py` | Class-level aiohttp session manager for concurrent image downloads |
| `src/tools.py` | `SanitizeName` (Windows-safe filenames), `CheckImageMIME` (`filetype`), `ProcessString` (template expansion) |

### Config modes

| Mode | Config key | Behavior |
|------|-----------|----------|
| ADB auto | `adb.enable` + `adb.auto` | Scans device for all downloaded books, pulls files automatically |
| ADB manual | `adb.enable` + `!adb.auto` | Pulls only books listed in `adb.books` |
| Single book | `!batch.enable` + `batch.url` non-empty | Downloads one book by URL/ID, zero interaction |
| Batch auto | `batch.enable` + `batch.auto` | Scans `data/` for numbered folders |
| Batch queue | `batch.enable` + `!batch.auto` | Processes `batch.queue` list |
| Manual book | `manualBook.enable` | Uses embedded JSON for metadata, reads chapters from `data/<bookID>/` |
| Interactive | `interactive.mode` | `auto` (config-first), `always` (menu), `never` (config required) |

Priority: ADB > manualBook > batch/single > interactive fallback.

### CI

The GitHub Actions workflow (`python-app.yml`) is manually triggered (`workflow_dispatch`) and builds a standalone Windows EXE via Nuitka, then creates a GitHub Release with the EXE + config + readme zipped.
