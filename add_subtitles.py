"""
Add word-by-word TikTok-style captions to all videos in a folder.
Uses Whisper to auto-transcribe audio — no pre-written text needed.

Output: <original_name>_subtitled.mp4     (normal mode)
        <original_name>_subtitled_wh.mp4  (word-highlight mode)

Original files are never touched.

To switch modes, change HIGHLIGHT_MODE below and just run the script.

CLI parameters (all optional, override the config variables below):
    --wh                         word-highlight mode
    --font  <path/to/font.ttf>   font to use
    --case  upper|lower|original  text case (default: upper)
"""
import random
import tempfile
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import whisper
from moviepy import VideoFileClip

# ── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_FOLDER  = Path(r"C:\Users\User\Documents\add subtitles")
SCRIPTS_FOLDER = INPUT_FOLDER / "scripts"  # .txt files with voiceover scripts (optional)
                                             # filename must match video name, e.g. MyVideo.txt
OUTPUT_SUFFIX = "_subtitled"          # appended before .mp4 (wh mode adds "_wh")
HIGHLIGHT_MODE = False                # ← set True for yellow word-highlight mode
WHISPER_MODEL = "base"                # tiny | base | small | medium | large
LANGUAGE      = "es"               # None = auto-detect, "es" = Spanish, "en" = English
FONT_SIZE     = 100
OUTLINE_WIDTH = 6
Y_POSITION    = 0.60                  # 0.0 = top, 1.0 = bottom

# ── FONT SELECTION ────────────────────────────────────────────────────────────
# Set the full path to any .ttf font file you want to use.
# The script will automatically use the filename from the path.
FONT_PATH = Path(r"C:\Users\User\Documents\video subtitles\fonts\static\OpenSans_Condensed-ExtraBold.ttf")
FONT_NAME = FONT_PATH.name   # derived automatically

# ── TEXT CASE ─────────────────────────────────────────────────────────────────
# Controls how words are displayed on screen.
# Options: "upper" (ALL CAPS), "lower" (all lowercase), "original" (as Whisper heard it)
TEXT_CASE = "upper"
# ─────────────────────────────────────────────────────────────────────────────

# ── WORD-HIGHLIGHT CONFIG ─────────────────────────────────────────────────────
HIGHLIGHT_COLOR      = "#FAD628"      # yellow tone
HIGHLIGHT_SIZE_MIN   = 1.2            # minimum scale factor vs FONT_SIZE
HIGHLIGHT_SIZE_MAX   = 1.6            # maximum scale factor vs FONT_SIZE
HIGHLIGHT_MAX_PCT    = 0.20           # maximum fraction of words that can be highlighted
HIGHLIGHT_LONG_WORD = 7              # words longer than this keep their normal size
PAUSE_THRESHOLD      = 0.18           # seconds gap after word → treat as sentence-end

# ── SCRIPT CORRECTION CONFIG ──────────────────────────────────────────────────
# If a .txt script is found for a video, Whisper words are compared to it.
# Single mismatched words (Whisper mishear) are replaced with the script word.
# Runs of more than MAX_CORRECTION_RUN consecutive mismatches are kept as-is
# (assumed to be camera audio not present in the voiceover script).
MAX_CORRECTION_RUN  = 3              # max consecutive replacements before giving up

# Stop words (articles, pronouns, prepositions, conjunctions, auxiliary verbs)
# Words NOT in this list are candidates for highlighting.
STOP_WORDS = {
    # English
    "a", "an", "the",
    "i", "me", "my", "we", "us", "our", "you", "your", "he", "him", "his",
    "she", "her", "it", "its", "they", "them", "their",
    "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "shall", "should", "may", "might", "must", "can", "could",
    "and", "but", "or", "nor", "so", "yet", "for", "as",
    "in", "on", "at", "to", "of", "up", "by", "from", "with",
    "about", "into", "through", "during", "before", "after",
    "above", "below", "between", "out", "off", "over", "under",
    "not", "no", "just", "also", "then", "than", "if", "when",
    "what", "which", "who", "how", "all", "each", "every",
    # Spanish
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "yo", "tu", "él", "ella", "nosotros", "vosotros", "ellos", "ellas",
    "me", "te", "se", "le", "nos", "os", "les",
    "mi", "tu", "su", "nuestro", "vuestro",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
    "de", "en", "a", "al", "del", "con", "por", "para", "sin",
    "sobre", "bajo", "ante", "tras", "entre", "hacia", "hasta",
    "y", "e", "o", "u", "pero", "sino", "aunque", "porque", "que",
    "es", "son", "era", "fue", "ser", "estar", "hay", "ha", "han",
    "lo", "le", "les", "nos", "ya", "no", "si", "más", "muy",
    "como", "cuando", "donde", "quien", "cual", "qué", "cómo",
}
# ─────────────────────────────────────────────────────────────────────────────


def extract_audio(video_path: Path, tmp_dir: Path) -> Path:
    """Extract audio from video to a temporary WAV file."""
    audio_path = tmp_dir / (video_path.stem + "_audio.wav")
    print(f"  Extracting audio → {audio_path.name}")
    clip = VideoFileClip(str(video_path))
    clip.audio.write_audiofile(str(audio_path), logger=None)
    clip.close()
    return audio_path


def transcribe_audio(audio_path: Path, model) -> list:
    """
    Run Whisper with word-level timestamps.
    Returns list of (word_uppercase, start_sec, end_sec).
    """
    print(f"  Transcribing with Whisper ({WHISPER_MODEL})…")
    opts = dict(word_timestamps=True)
    if LANGUAGE:
        opts["language"] = LANGUAGE

    result = model.transcribe(str(audio_path), **opts)

    timings = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            word = w.get("word", "").strip()
            if word:
                # Strip punctuation Whisper attaches to words
                word = word.strip(".,!?;:\"'¿¡()[]{}…-–—")
                if not word:
                    continue
                if TEXT_CASE == "upper":
                    word = word.upper()
                elif TEXT_CASE == "lower":
                    word = word.lower()
                # "original" → keep as-is from Whisper
                timings.append((word, w["start"], w["end"]))

    print(f"  Found {len(timings)} words")
    return timings


def load_script(video_path: Path) -> list:
    """
    Look for a .docx (or .txt fallback) in SCRIPTS_FOLDER with the same stem as the video.
    Returns a list of clean lowercase words, or [] if not found.
    """
    import re

    docx_path = SCRIPTS_FOLDER / (video_path.stem + ".docx")
    txt_path  = SCRIPTS_FOLDER / (video_path.stem + ".txt")

    if docx_path.exists():
        try:
            from docx import Document
            doc  = Document(docx_path)
            text = "\n".join(p.text for p in doc.paragraphs)
            print(f"  Script file: {docx_path.name}")
        except Exception as e:
            print(f"  WARNING: could not read {docx_path.name}: {e}")
            return []
    elif txt_path.exists():
        text = txt_path.read_text(encoding="utf-8", errors="ignore")
        print(f"  Script file: {txt_path.name}")
    else:
        return []

    words = re.sub(r"[.,!?;:\"'\u00bf\u00a1()\[\]{}\u2026\-\u2013\u2014]", "", text).split()
    return [w.lower() for w in words if w.strip()]


def correct_with_script(word_timings: list, script_words: list) -> list:
    """
    Align Whisper word timings with the voiceover script using difflib opcodes.
    - 'replace' (equal length, ≤ MAX_CORRECTION_RUN): Whisper mishear → use script word
    - 'delete': Whisper heard extra words not in script (ad-libs, camera talk) → keep
    - 'insert': Script words Whisper missed entirely → nothing to do (no timing)
    - Adjacent delete+insert pairs are merged into a replace when small enough,
      catching cases where difflib splits a substitution into two operations.
    Timings are never touched — only the displayed text changes.
    """
    import difflib

    whisper_clean = [w[0].lower().strip(".,!?;:\"'\u00bf\u00a1") for w in word_timings]
    matcher = difflib.SequenceMatcher(None, whisper_clean, script_words, autojunk=False)
    opcodes = list(matcher.get_opcodes())

    # Merge adjacent delete+insert (or insert+delete) into replace when both sides are small
    merged = []
    i = 0
    while i < len(opcodes):
        tag, i1, i2, j1, j2 = opcodes[i]
        if i + 1 < len(opcodes):
            ntag, ni1, ni2, nj1, nj2 = opcodes[i + 1]
            # Only merge equal-length adjacent delete+insert pairs into a replace.
            # Unequal pairs are left separate so each word reaches the fuzzy pass.
            if tag == 'delete' and ntag == 'insert':
                w_len, s_len = i2 - i1, nj2 - nj1
                if w_len == s_len and w_len <= MAX_CORRECTION_RUN:
                    merged.append(('replace', i1, i2, nj1, nj2))
                    i += 2
                    continue
            elif tag == 'insert' and ntag == 'delete':
                w_len, s_len = ni2 - ni1, j2 - j1
                if w_len == s_len and w_len <= MAX_CORRECTION_RUN:
                    merged.append(('replace', ni1, ni2, j1, j2))
                    i += 2
                    continue
        merged.append((tag, i1, i2, j1, j2))
        i += 1

    corrections = {}
    unmatched_deletes = []   # whisper indices with no script match
    unmatched_inserts = []   # (script_idx, word) with no whisper match

    for tag, i1, i2, j1, j2 in merged:
        if tag == 'equal':
            continue
        if tag == 'replace':
            w_len, s_len = i2 - i1, j2 - j1
            if w_len == s_len and w_len <= MAX_CORRECTION_RUN:
                # Clean 1:1 or 2:2 or 3:3 swap — correct directly
                for wi, si in zip(range(i1, i2), range(j1, j2)):
                    corrections[wi] = script_words[si]
            else:
                # Unequal lengths — send both sides to fuzzy pass
                for wi in range(i1, i2):
                    unmatched_deletes.append(wi)
                for si in range(j1, j2):
                    unmatched_inserts.append((si, script_words[si]))
        elif tag == 'delete':
            for wi in range(i1, i2):
                unmatched_deletes.append(wi)
        elif tag == 'insert':
            for si in range(j1, j2):
                unmatched_inserts.append((si, script_words[si]))

    # Fuzzy pass: for every unmatched Whisper word, find the most similar
    # unmatched script word anywhere in the remaining pool.
    # High similarity → Whisper mishear → correct it.
    # Low similarity → extra audio (ad-lib) → keep Whisper word as-is.
    # Guard: only replace if the script word is MORE similar to the whisper word
    # than the whisper word already is (prevents replacing correct words with typos).
    FUZZY_THRESHOLD = 0.70
    used_inserts = set()
    for wi in unmatched_deletes:
        if wi in corrections:
            continue
        w_word = whisper_clean[wi]
        best_ratio, best_si, best_sword = 0.0, None, None
        for si, sword in unmatched_inserts:
            if si in used_inserts:
                continue
            ratio = difflib.SequenceMatcher(None, w_word, sword).ratio()
            if ratio > best_ratio:
                best_ratio, best_si, best_sword = ratio, si, sword
        # Only correct if similarity is high AND the script word is longer
        # (avoids replacing 'sobresale' with 'sobre', or 'nuevo' with 'muevo')
        if (best_ratio >= FUZZY_THRESHOLD
                and best_si is not None
                and len(best_sword) >= len(w_word) * 0.7):
            corrections[wi] = best_sword
            used_inserts.add(best_si)

    corrected = []
    replaced = 0
    for i, (word, start, end) in enumerate(word_timings):
        if i in corrections:
            new_word = corrections[i]
            if TEXT_CASE == "upper":
                new_word = new_word.upper()
            elif TEXT_CASE == "lower":
                new_word = new_word.lower()
            corrected.append((new_word, start, end))
            replaced += 1
        else:
            corrected.append((word, start, end))

    print(f"  Script correction: {replaced} word(s) replaced out of {len(word_timings)}")
    for i in sorted(corrections):
        print(f"    [{i}] '{word_timings[i][0]}' -> '{corrections[i]}'")
    return corrected


def mark_highlights(word_timings: list) -> list:
    """
    Given word timings, return an enriched list of
    (word, start, end, is_highlight, font_size) tuples.

    Candidates for highlighting (content words + sentence endings) are scored
    and only the top HIGHLIGHT_MAX_PCT % are actually highlighted.
    Words longer than HIGHLIGHT_LONG_WORD letters are not scaled up.
    """
    n = len(word_timings)

    # First pass: score every word
    scored = []   # (score, index)
    for i, (word, start, end) in enumerate(word_timings):
        clean = word.lower().strip(".,!?;:\"'¿¡")

        pause_after = 0.0
        if i < n - 1:
            pause_after = word_timings[i + 1][1] - end

        is_sentence_end = pause_after >= PAUSE_THRESHOLD
        is_content_word = clean not in STOP_WORDS and len(clean) > 1

        # Score: content words get 1 point, sentence endings get 2 (prioritised)
        score = 0
        if is_content_word:  score += 1
        if is_sentence_end:  score += 2
        scored.append((score, i))

    # Distribute highlights evenly across the video by splitting into chunks.
    # Each chunk gets its own budget so highlights are spread consistently.
    NUM_CHUNKS = 10
    chunk_size = max(1, n // NUM_CHUNKS)
    highlight_indices = set()

    for chunk_start in range(0, n, chunk_size):
        chunk = scored[chunk_start: chunk_start + chunk_size]
        chunk_budget = max(1, int(len(chunk) * HIGHLIGHT_MAX_PCT))
        eligible = [(s, i) for s, i in chunk if s > 0]
        eligible.sort(key=lambda x: (-x[0], x[1]))
        for _, i in eligible[:chunk_budget]:
            highlight_indices.add(i)

    # Second pass: build result
    result = []
    for i, (word, start, end) in enumerate(word_timings):
        if i in highlight_indices:
            clean = word.lower().strip(".,!?;:\"'¿¡")
            # Don't scale up long words to avoid overflow
            if len(clean) > HIGHLIGHT_LONG_WORD:
                size = FONT_SIZE
            else:
                scale = random.uniform(HIGHLIGHT_SIZE_MIN, HIGHLIGHT_SIZE_MAX)
                size  = int(FONT_SIZE * scale)
            result.append((word, start, end, True, size))
        else:
            result.append((word, start, end, False, FONT_SIZE))

    highlighted = len(highlight_indices)
    print(f"  Highlight mode: {highlighted}/{n} words highlighted ({highlighted/n*100:.0f}%)")
    return result


def load_font(size: int = FONT_SIZE) -> ImageFont.FreeTypeFont:
    """Load the font at a given size; fall back to PIL default if not found."""
    if FONT_PATH.exists():
        return ImageFont.truetype(str(FONT_PATH), size)
    return ImageFont.load_default()


def draw_word(img: Image.Image, word: str, font_size: int,
              video_w: int, video_h: int,
              color: str = "white") -> Image.Image:
    """
    Draw text with black outline, centred horizontally at Y_POSITION.
    Loads the font at the requested size each call (cached via lru_cache below).
    """
    font = _get_font(font_size)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), word, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (video_w - text_w) // 2
    y = int(video_h * Y_POSITION) - text_h // 2  # vertically centre around anchor

    # Black outline
    for dx in range(-OUTLINE_WIDTH, OUTLINE_WIDTH + 1):
        for dy in range(-OUTLINE_WIDTH, OUTLINE_WIDTH + 1):
            if dx * dx + dy * dy <= OUTLINE_WIDTH * OUTLINE_WIDTH:
                draw.text((x + dx, y + dy), word, font=font, fill="black")

    # Coloured text on top
    draw.text((x, y), word, font=font, fill=color)
    return img


from functools import lru_cache

@lru_cache(maxsize=32)
def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Cached font loader — avoids re-reading the TTF file on every frame."""
    if FONT_PATH.exists():
        return ImageFont.truetype(str(FONT_PATH), size)
    return ImageFont.load_default()


def burn_captions(video_path: Path, word_timings: list, output_path: Path,
                  highlight_mode: bool = False):
    """
    Apply captions frame-by-frame via moviepy's transform(),
    then write with high-quality settings (CRF 18 = visually lossless).

    word_timings: list of (word, start, end) tuples  [normal mode]
                  OR (word, start, end, is_highlight, font_size) tuples  [wh mode]
    """
    clip = VideoFileClip(str(video_path))
    fps = clip.fps
    video_w, video_h = clip.size

    # Pre-build a lookup dict for O(1) frame access: end_time → entry
    # We'll keep it as a sorted list and binary-search per frame.
    import bisect
    starts = [w[1] for w in word_timings]
    ends   = [w[2] for w in word_timings]

    def add_caption(get_frame, t):
        frame = get_frame(t)

        # Find word active at time t via binary search
        idx = bisect.bisect_right(starts, t) - 1
        if idx < 0 or t >= ends[idx]:
            return frame

        entry = word_timings[idx]
        word  = entry[0]

        if highlight_mode:
            _, _, _, is_highlight, font_size = entry
            color = HIGHLIGHT_COLOR if is_highlight else "white"
        else:
            font_size = FONT_SIZE
            color     = "white"

        img = Image.fromarray(frame)
        img = draw_word(img, word, font_size, video_w, video_h, color)
        return np.array(img)

    mode_label = "highlight" if highlight_mode else "normal"
    print(f"  Burning captions [{mode_label} mode] "
          f"(duration {clip.duration:.1f}s @ {fps:.0f}fps)…")
    captioned = clip.transform(add_caption, apply_to=["video"])

    captioned.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=fps,
        preset="slow",
        threads=4,
        logger=None,
        ffmpeg_params=["-crf", "18"],
    )

    clip.close()
    captioned.close()
    print(f"  ✓ Saved → {output_path.name}")


def process_folder(folder: Path, highlight_mode: bool = False):
    video_files = sorted(folder.glob("*.mp4"))
    if not video_files:
        print(f"No .mp4 files found in {folder}")
        return

    suffix = OUTPUT_SUFFIX + ("_wh" if highlight_mode else "")
    mode_label = "WORD-HIGHLIGHT" if highlight_mode else "NORMAL"

    print(f"Found {len(video_files)} video(s) in {folder}")
    print(f"Mode: {mode_label}\n")
    print(f"Loading Whisper model '{WHISPER_MODEL}'…")
    model = whisper.load_model(WHISPER_MODEL)

    # Pre-warm font cache
    _get_font(FONT_SIZE)
    if FONT_PATH.exists():
        print(f"  Font: {FONT_PATH.name}")
    else:
        print(f"  Warning: font not found at {FONT_PATH}, using PIL default")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        for video_path in video_files:
            # Skip already-subtitled files
            if "_subtitled" in video_path.stem:
                continue

            output_path = folder / (video_path.stem + suffix + ".mp4")

            print("\n" + "=" * 60)
            print(f"VIDEO: {video_path.name}")
            print("=" * 60)

            if output_path.exists():
                print(f"  Output already exists, skipping ({output_path.name})")
                continue

            try:
                audio_path   = extract_audio(video_path, tmp_dir)
                word_timings = transcribe_audio(audio_path, model)

                if not word_timings:
                    print("  No words detected — skipping.")
                    continue

                # Correct with voiceover script if available
                script_words = load_script(video_path)
                if script_words:
                    print(f"  Script found: {video_path.stem}.txt ({len(script_words)} words)")
                    word_timings = correct_with_script(word_timings, script_words)
                else:
                    print(f"  No script found in {SCRIPTS_FOLDER.name}/, using Whisper output as-is")

                if highlight_mode:
                    word_timings = mark_highlights(word_timings)

                burn_captions(video_path, word_timings, output_path,
                              highlight_mode=highlight_mode)

            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()

    print("\n" + "=" * 60)
    print("All done!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Add word-by-word captions to all videos in the input folder."
    )
    parser.add_argument("--wh", action="store_true",
                        help="Word-highlight mode: important words in yellow at a larger size.")
    parser.add_argument("--font", type=str, default=None,
                        help="Full path to a .ttf font file to use.")
    parser.add_argument("--case", choices=["upper", "lower", "original"], default=None,
                        help="Text case: upper (ALL CAPS), lower (all lowercase), original.")
    args = parser.parse_args()

    # CLI args override config variables
    if args.font:
        FONT_PATH = Path(args.font)
    if args.case:
        TEXT_CASE = args.case

    process_folder(INPUT_FOLDER, highlight_mode=args.wh or HIGHLIGHT_MODE)
