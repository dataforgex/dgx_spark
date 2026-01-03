# Claude Code Transcripts

Convert Claude Code session files to shareable HTML transcripts.

## Usage

### Update/Generate Archive
```bash
./update.sh
```
This regenerates the HTML archive at `~/claude-archive/` with all your Claude Code sessions.

### Open Archive
```bash
./open.sh
```
Opens the archive in your default browser.

Or manually open: `~/claude-archive/index.html`

## Output Location

HTML files are saved to: `~/claude-archive/`

```
~/claude-archive/
├── index.html              # Master index (start here)
├── project-1/
│   ├── session-id/
│   │   ├── index.html      # Session overview
│   │   ├── page-001.html   # Transcript pages
│   │   └── ...
│   └── ...
└── ...
```

## Privacy

- All data stays local on your machine
- No network requests are made
- HTML files can be opened directly in any browser (file://)

## Tool Info

- Tool: [claude-code-transcripts](https://github.com/simonw/claude-code-transcripts)
- Author: Simon Willison
- License: Apache 2.0

## Manual Commands

If you prefer running commands directly:

```bash
# Activate virtual environment
source venv/bin/activate

# Generate archive
claude-code-transcripts all --output ~/claude-archive --include-agents

# See all options
claude-code-transcripts --help
```
