"""
Download a YouTube video in the best available HD quality.
Usage:
    python download_yt.py <URL>
    python download_yt.py <URL> --out "C:\Some\Folder"
"""
import argparse
import sys
from pathlib import Path
import yt_dlp

DEFAULT_OUT = Path(r"C:\Users\User\Documents\add subtitles")

def download(url: str, out_folder: Path):
    out_folder.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        # Best video+audio merged, prefer mp4, max 1080p
        "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": str(out_folder / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "retries": 10,
        "fragment_retries": 10,
        "file_access_retries": 5,
        "extractor_retries": 5,
        "continuedl": True,
    }

    print(f"Downloading: {url}")
    print(f"Output folder: {out_folder}\n")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        print(f"\nSaved: {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download a YouTube video in HD.")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output folder (default: add subtitles folder)")
    args = parser.parse_args()

    download(args.url, Path(args.out))
