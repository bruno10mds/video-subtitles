# Video Subtitles

Automatically adds **word-by-word TikTok-style captions** to any MP4 video using [OpenAI Whisper](https://github.com/openai/whisper) for transcription. Optionally corrects Whisper's misheard words using a voiceover script (`.docx` or `.txt`).

Two modes available:
- **Normal** — every word appears in white with a black outline
- **Word-Highlight** — important words (content words and sentence endings) appear at a highlighted color and randomly larger size to boost retention

---

## Output

| Mode | Output filename |
|------|----------------|
| Normal | `<original name>_subtitled.mp4` |
| Word-Highlight | `<original name>_subtitled_wh.mp4` |

Original files are **never modified**.

---

## Setup

### 1. Prerequisites

- Python 3.10+ 
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on your PATH

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

- **Windows:** `.venv\Scripts\activate`
- **Mac/Linux:** `source .venv/bin/activate`

### 3. Install dependencies

```bash
pip install moviepy pillow openai-whisper python-docx
```

> `openai-whisper` will also install `torch` and `numba` automatically.  
> The first run will download the Whisper model (~145 MB for `base`, ~3 GB for `large`).

### 4. (Optional) Font

Place any `.ttf` font file in the `fonts/` folder and pass it with `--font <path>`. If no font is specified, the script uses PIL default.

---

## Usage

### Quick start — No manual corrections

Transcribe and add captions in one step with word-highlighting, purple color, large font, and Whisper large model:

```powershell
python add_subtitles.py --input "D:\your\videos" --wh --model large --color "#4F2BC7" --font-size 200
```

---

### With manual transcription correction (3 steps)

#### Step 1 — Transcribe only

Generate `.txt` files with raw transcriptions in `<video_folder>/scripts/`:

```powershell
python add_subtitles.py --input "D:\your\videos" --model large --save-transcripts-only
```

The script will:
- Extract audio from each video
- Transcribe with Whisper
- Save raw transcriptions to `D:\your\videos\scripts\<video_name>.txt`
- **Stop** so you can edit the `.txt` files manually

#### Step 2 — Edit manually

Open and correct each `.txt` file in `D:\your\videos\scripts\`. Fix Whisper's mistakes, correct mistranslations, etc. Save each file.

#### Step 3 — Burn captions with corrections applied

Process videos using your corrected transcriptions:

```powershell
python add_subtitles.py --input "D:\your\videos" --wh --model large --color "#4F2BC7" --font-size 200
```

The script will:
- Read your corrected `.txt` files
- Generate subtitled videos with word-highlighting in the specified color
- Save as `*_subtitled_wh.mp4`

---

## CLI arguments

| Argument | Example | Description |
|----------|---------|-------------|
| `--input` | `D:\my\videos` | Input folder with `.mp4` files |
| `--wh` | — | Enable word-highlight mode |
| `--model` | `large` | Whisper model: `tiny`, `base`, `small`, `medium`, `large` |
| `--color` | `#4F2BC7` | Highlight color (hex code) |
| `--font-size` | `200` | Font size in pixels (default: 100) |
| `--case` | `upper\|lower\|original` | Text case (default: `upper`) |
| `--font` | `/path/to/font.ttf` | Custom `.ttf` font file |
| `--save-transcripts-only` | — | Step 1: only transcribe, don't burn captions |

---

## Configuration reference

Each parameter can also be set in the script's CONFIG section. CLI arguments **override** these defaults.

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `"base"` | Whisper model size: `tiny` (fastest) → `large` (most accurate) |
| `LANGUAGE` | `"es"` | Force a language e.g. `"es"` or `"en"`. `None` = auto-detect |
| `FONT_SIZE` | `100` | Base font size in pixels |
| `OUTLINE_WIDTH` | `6` | Black outline thickness in pixels |
| `Y_POSITION` | `0.60` | Vertical position of captions (`0.0` = top, `1.0` = bottom) |
| `FONT_PATH` | (system default) | Path to a `.ttf` font file |
| `TEXT_CASE` | `"upper"` | `"upper"`, `"lower"`, or `"original"` |
| `MAX_CORRECTION_RUN` | `3` | Max consecutive word replacements per correction group |

### Word-Highlight specific

| Variable | Default | Description |
|----------|---------|-------------|
| `HIGHLIGHT_COLOR` | `"#FAD628"` | Colour for highlighted words (hex code) |
| `HIGHLIGHT_SIZE_MIN` | `1.2` | Minimum scale factor vs base font size |
| `HIGHLIGHT_SIZE_MAX` | `1.6` | Maximum scale factor vs base font size |
| `HIGHLIGHT_MAX_PCT` | `0.20` | Max fraction of words highlighted (0.20 = 20%) |
| `HIGHLIGHT_LONG_WORD` | `7` | Words longer than this are not scaled up |
| `PAUSE_THRESHOLD` | `0.18` | Silence (seconds) after a word to mark it as sentence-ending |

---

## How word-highlight works

A word is highlighted (colored and optionally enlarged) if **either** condition is true:

1. **It is a content word** — not an article, pronoun, preposition, conjunction, or auxiliary verb (stop-word list covers both English and Spanish)
2. **It ends a sentence** — there is a silence gap ≥ `PAUSE_THRESHOLD` seconds after it (detected from Whisper's timestamps)

Highlighted words are shown at a **random size** between `HIGHLIGHT_SIZE_MIN` and `HIGHLIGHT_SIZE_MAX` times the base font size. Highlights are distributed evenly across the video to avoid front-loading.

---

## Script correction (optional)

If you provide a voiceover script, the corrector will fix Whisper's misheared words automatically. Timings are never touched — only the displayed text changes.

### How to set it up

1. Save a `.docx` or `.txt` file with the voiceover script
2. Place it in `<video_folder>/scripts/` with the **same stem** as the video:

```
D:\my\videos\
├── MyVideo.mp4
└── scripts/
    └── MyVideo.txt          ← Whisper output is aligned against this
```

3. Correct the `.txt` file manually
4. Run the script — it detects and uses the corrected script automatically

### How correction works

The Whisper transcript is aligned against the script using `difflib`. Four situations are handled:

| Situation | What happens |
|-----------|--------------|
| 1-to-1 word mismatch (Whisper mishear) | Replaced with the script word if similar enough |
| Extra Whisper words not in script | Kept as-is (e.g., ad-libs, camera talk) |
| Script words Whisper missed | Skipped (no timing to attach to) |
| Similar-sounding words | Fuzzy character match (≥70% similarity) corrects them |

Adjustable via `MAX_CORRECTION_RUN`: how many consecutive words can be replaced in one group. Increase it if your script and audio diverge significantly.

---

## Video quality

Output is encoded with `libx264` at **CRF 18** (`preset slow`), which is visually lossless — the quality of the original video is fully preserved.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `openai-whisper` | Speech-to-text with word-level timestamps |
| `moviepy` | Video reading, frame transformation, writing |
| `pillow` | Drawing text onto frames |
| `python-docx` | Reading `.docx` voiceover scripts |
| `torch` | Required by Whisper (installed automatically) |
| `numpy` | Frame array manipulation (installed automatically) |
