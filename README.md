# Video Subtitles

Automatically adds **word-by-word TikTok-style captions** to any MP4 video using [OpenAI Whisper](https://github.com/openai/whisper) for transcription. Optionally corrects Whisper's misheard words using a voiceover script (`.docx` or `.txt`).

Two modes available:
- **Normal** — every word appears in white with a black outline
- **Word-Highlight** — important words (content words and sentence endings) appear in **yellow** at a randomly larger size to boost retention

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

- Python 3.11 (or 3.9+)
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
> The first run will download the Whisper model (~145 MB for `base`).

### 4. (Optional) Font

Place any `.ttf` font file in the `fonts/` folder and update `FONT_PATH` in the script. If no font is found the script falls back to the PIL default.

---

## Usage

### Step 1 — Configure the script

Open `add_subtitles.py` and set these variables near the top:

```python
INPUT_FOLDER = Path(r"C:\path\to\your\videos")   # folder with your .mp4 files
LANGUAGE     = "es"    # or "en", or None for auto-detect
```

### Step 2 — Run

Normal captions:
```bash
python add_subtitles.py
```

Word-highlight mode + lowercase:
```bash
python add_subtitles.py --wh --case lower
```

The script processes every `.mp4` in `INPUT_FOLDER` and saves the subtitled versions alongside the originals. Already-subtitled files are skipped automatically.

### CLI arguments

| Argument | Description |
|----------|-------------|
| `--wh` | Enable word-highlight mode (yellow important words) |
| `--case upper` | Display all words in UPPER CASE (default) |
| `--case lower` | Display all words in lower case |
| `--case original` | Keep Whisper's casing as-is |
| `--font <path>` | Override the font path at runtime |

---

## Script correction (optional)

If you have a voiceover script, the corrector will fix Whisper's misheared words automatically. Timings are never touched — only the displayed text changes.

### How to set it up

1. Create a folder called `scripts/` inside your `INPUT_FOLDER`
2. Save a `.docx` (or `.txt` fallback) file there with the **same name** as the video:

```
add subtitles/
├── MyVideo.mp4
└── scripts/
    └── MyVideo.docx
```

3. Run as normal — the script detects and uses it automatically

### How correction works

The Whisper transcript is aligned against the script using `difflib`. Four situations are handled:

| Situation | What happens |
|-----------|-------------|
| 1-to-1 word mismatch (Whisper mishear) | Replaced with the script word |
| Extra Whisper words not in script (ad-libs, camera talk) | Kept as-is |
| Script words Whisper missed entirely | Silently skipped (no timing to attach to) |
| Similar-sounding words in nearby positions | Fuzzy character match (≥65% similarity) corrects them |

`MAX_CORRECTION_RUN = 2` controls how many consecutive words can be replaced in one group. Increase it if your script and audio diverge more.

---

## Configuration reference

| Variable | Default | Description |
|----------|---------|-------------|
| `INPUT_FOLDER` | *(set this)* | Folder containing the input `.mp4` files |
| `SCRIPTS_FOLDER` | `INPUT_FOLDER/scripts` | Folder with `.docx`/`.txt` correction scripts |
| `HIGHLIGHT_MODE` | `False` | `True` = word-highlight mode, `False` = normal white captions |
| `WHISPER_MODEL` | `"base"` | Whisper model size: `tiny` → `large` |
| `LANGUAGE` | `"es"` | Force a language e.g. `"es"` or `"en"`. `None` = auto-detect |
| `FONT_SIZE` | `100` | Base font size in pixels |
| `OUTLINE_WIDTH` | `6` | Black outline thickness in pixels |
| `Y_POSITION` | `0.60` | Vertical position of captions (`0.0` = top, `1.0` = bottom) |
| `FONT_PATH` | `fonts/static/OpenSans_Condensed-ExtraBold.ttf` | Path to a `.ttf` font file |
| `TEXT_CASE` | `"upper"` | `"upper"`, `"lower"`, or `"original"` |
| `MAX_CORRECTION_RUN` | `2` | Max consecutive word replacements per correction group |

### Word-Highlight specific

| Variable | Default | Description |
|----------|---------|-------------|
| `HIGHLIGHT_COLOR` | `"#FAD628"` | Colour for highlighted words |
| `HIGHLIGHT_SIZE_MIN` | `1.2` | Minimum scale factor vs base font size |
| `HIGHLIGHT_SIZE_MAX` | `1.6` | Maximum scale factor vs base font size |
| `HIGHLIGHT_MAX_PCT` | `0.20` | Max fraction of words highlighted (0.20 = 20%) |
| `HIGHLIGHT_LONG_WORD` | `7` | Words longer than this are not scaled up (avoids overflow) |
| `PAUSE_THRESHOLD` | `0.18` | Seconds of silence after a word to treat it as a sentence ending |

---

## How word-highlight works

A word is highlighted in yellow if **either** condition is true:

1. **It is a content word** — not an article, pronoun, preposition, conjunction or auxiliary verb (stop-word list covers both English and Spanish)
2. **It ends a sentence** — the gap to the next word is ≥ `PAUSE_THRESHOLD` seconds (from Whisper's timestamps)

Highlighted words are shown at a **random size** between `HIGHLIGHT_SIZE_MIN` and `HIGHLIGHT_SIZE_MAX` times the base font size. Highlights are distributed evenly across the video (10 equal chunks, each with its own 20% budget) to avoid front-loading.

---

## Video quality

Output is encoded with `libx264` at **CRF 18** (`preset slow`), which is visually lossless.

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

Two modes available:
- **Normal** — every word appears in white with a black outline
- **Word-Highlight** — important words (content words and sentence endings) appear in **yellow** at a randomly larger size to boost retention

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

- Python 3.11 (or 3.9+)
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
pip install moviepy pillow openai-whisper
```

> `openai-whisper` will also install `torch` and `numba` automatically. The first run will download the Whisper model (~145 MB for `base`).

### 4. (Optional) Font

Place a `.ttf` font file at `fonts/more-sugar.regular.ttf` (or any font you prefer — update `FONT_PATH` in the script). If no font is found the script falls back to the PIL default.

---

## Usage

### Step 1 — Configure the script

Open `add_subtitles.py` and set these variables near the top:

```python
INPUT_FOLDER   = Path(r"C:\path\to\your\videos")   # folder with your .mp4 files
HIGHLIGHT_MODE = False   # ← set True for word-highlight mode
```

### Step 2 — Run

```bash
python add_subtitles.py
```

That's it. The script will process every `.mp4` in `INPUT_FOLDER` and save the subtitled versions alongside the originals.

---

## Configuration reference

| Variable | Default | Description |
|----------|---------|-------------|
| `INPUT_FOLDER` | *(set this)* | Folder containing the input `.mp4` files |
| `HIGHLIGHT_MODE` | `False` | `True` = word-highlight mode, `False` = normal white captions |
| `WHISPER_MODEL` | `"base"` | Whisper model size: `tiny` (fastest) → `large` (most accurate) |
| `LANGUAGE` | `None` | Force a language e.g. `"es"` or `"en"`. `None` = auto-detect |
| `FONT_SIZE` | `100` | Base font size in pixels |
| `OUTLINE_WIDTH` | `6` | Black outline thickness in pixels |
| `Y_POSITION` | `0.60` | Vertical position of captions (`0.0` = top, `1.0` = bottom) |
| `FONT_PATH` | `fonts/more-sugar.regular.ttf` | Path to a `.ttf` font file |

### Word-Highlight specific

| Variable | Default | Description |
|----------|---------|-------------|
| `HIGHLIGHT_COLOR` | `"#FAD628"` | Colour for highlighted words |
| `HIGHLIGHT_SIZE_MIN` | `1.2` | Minimum scale factor vs base font size |
| `HIGHLIGHT_SIZE_MAX` | `1.6` | Maximum scale factor vs base font size |
| `HIGHLIGHT_MAX_PCT` | `0.20` | Maximum fraction of words that get highlighted (e.g. 0.20 = 20%) |
| `HIGHLIGHT_LONG_WORD` | `7` | Words longer than this number of letters are not scaled up (avoids overflow) |
| `PAUSE_THRESHOLD` | `0.18` | Seconds of silence after a word to treat it as a sentence ending |

---

## How word-highlight works

A word is highlighted in yellow if **either** condition is true:

1. **It is a content word** — not an article, pronoun, preposition, conjunction or auxiliary verb (stop-word list covers both English and Spanish)
2. **It ends a sentence** — the gap to the next word is ≥ `PAUSE_THRESHOLD` seconds (detected from Whisper's timestamps)

Highlighted words are shown at a **random size** between `HIGHLIGHT_SIZE_MIN` and `HIGHLIGHT_SIZE_MAX` times the base font size, giving a dynamic feel.

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
| `torch` | Required by Whisper (installed automatically) |
| `numpy` | Frame array manipulation (installed automatically) |
