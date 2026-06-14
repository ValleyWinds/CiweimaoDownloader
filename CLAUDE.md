# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

CiweimaoDownloader downloads novels from ciweimao.com (刺猬猫), decrypts them, and outputs TXT + EPUB files. Downloaded chapters arrive as encrypted files from a companion mobile app; this tool decrypts and packages them locally. No login/account data is involved.

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

## Architecture

The entry point is `src/main.py` (guarded by `if __name__ == "__main__"`). The `src/` directory is a flat module collection — no `__init__.py`, no package structure.

### Data flow

1. **`config.init()`** — loads `setting.yaml` (Pydantic models from `models.py`), or writes a default config from an embedded base64 string
2. **`fileUtils.TransformFilename("key")`** — base64-decodes key filenames into plain chapter IDs (skipped if a `done` marker exists)
3. **`fileUtils.RemoveNewlinesInEachFile(book_id)`** — strips `\r`/`\n` from encrypted chapter text (one-time operation per book folder, tracked by a `done` marker)
4. **`requestUtils.GetName(book)`** — scrapes book metadata (name, author, cover image, description) from ciweimao.com via `og:` meta tags, mutating the `Book` object
5. **`requestUtils.GetContents(book)`** — POSTs to a ciweimao API to fetch the chapter list, appending `Chapters` objects (including volume-intro markers) to the book
6. **`config.CalculateParama(book)`** — computes derived paths (safe filenames, decrypted output paths, key/encrypted file paths)
7. **Chapter decryption loop** — for each chapter, reads the `key` (seed) and `encryptedTxt`, then calls `decrypt.decrypt()` (AES-256-CBC, SHA-256 of seed as key, zero IV). Caches decrypted text if configured
8. **`epubUtils.GenerateEpub(book, path)`** — builds the EPUB in phases:
   - **Phase A** (sync, ThreadPoolExecutor): parses each chapter with BeautifulSoup — strips spans, extracts image URLs, handles `<Book>` tags, wraps text in `<p>` tags
   - **Phase B** (async, asyncio.Queue + worker pool): downloads all unique images concurrently via `asyncHttp.AsyncHTTP` (aiohttp), with optional filesystem caching
   - **Phases C-F**: assembles epub (cover, spine, TOC with volume grouping) and writes with `ebooklib`

### Key modules

| File | Purpose |
|------|---------|
| `src/models.py` | `Book`/`Chapters` dataclasses, Pydantic `Config` model for YAML, colorama-based `Print` logger, requests session-with-retry wrapper |
| `src/config.py` | Config init (embedded default as base64), `CalculateParama()` that derives per-chapter paths |
| `src/requestUtils.py` | Two functions scraping ciweimao.com — `GetName` and `GetContents` |
| `src/decrypt.py` | Single `decrypt()` function — AES-CBC via pycryptodome |
| `src/fileUtils.py` | YAML loader, newline-stripping pass, base64→chapter-ID rename pass |
| `src/epubUtils.py` | Full EPUB generation pipeline with thread pool + async image downloader |
| `src/asyncHttp.py` | Class-level aiohttp session manager |
| `src/tools.py` | `SanitizeName` (Windows-safe filenames), `CheckImageMIME` (via `filetype`), `ProcessString` (template expansion for `{bookID}` etc.) |

### File layout convention

Encrypted chapter data lives in `./{book_id}/` — one file per chapter named `{chapter_id}.txt`. Decryption keys live in `./key/` — base64-encoded filenames that decode to chapter IDs. Both folders include a `done` marker file after one-time preprocessing completes.

### CI

The GitHub Actions workflow (`python-app.yml`) is manually triggered (`workflow_dispatch`) and builds a standalone Windows EXE via Nuitka, then creates a GitHub Release with the EXE + config + readme zipped.
