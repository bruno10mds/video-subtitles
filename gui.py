import os
import sys
import tempfile
import threading
import traceback
from pathlib import Path

import customtkinter as ctk
from tkinter import colorchooser, filedialog, messagebox
import vlc

import add_subtitles as core

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

MODELS = ["tiny", "base", "small", "medium", "large"]
LANGUAGES = {"Español": "es", "Inglés": "en", "Auto-detectar": None}
CASES = {"MAYÚSCULAS": "upper", "minúsculas": "lower", "Original": "original"}

TMP_DIR = Path(tempfile.gettempdir())
PREVIEW_SRC = TMP_DIR / "vs_preview_src.mp4"
PREVIEW_OUT = TMP_DIR / "vs_preview_out.mp4"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Subtítulos de vídeo")
        self.geometry("1180x800")
        self.minsize(1000, 700)

        self.video_path = ctk.StringVar()
        self.output_dir = ctk.StringVar()
        self.highlight_mode = ctk.BooleanVar(value=True)
        self.model = ctk.StringVar(value="base")
        self.language = ctk.StringVar(value="Español")
        self.case = ctk.StringVar(value="MAYÚSCULAS")
        self.font_size = ctk.StringVar(value=str(core.FONT_SIZE))
        self.outline_width = ctk.StringVar(value=str(core.OUTLINE_WIDTH))
        self.y_position = ctk.DoubleVar(value=core.Y_POSITION)
        self.highlight_color = ctk.StringVar(value=core.HIGHLIGHT_COLOR)
        self.highlight_size_min = ctk.StringVar(value=str(core.HIGHLIGHT_SIZE_MIN))
        self.highlight_size_max = ctk.StringVar(value=str(core.HIGHLIGHT_SIZE_MAX))
        self.highlight_max_pct = ctk.StringVar(value=str(core.HIGHLIGHT_MAX_PCT))
        self.pause_threshold = ctk.StringVar(value=str(core.PAUSE_THRESHOLD))
        self.preview_duration = ctk.StringVar(value="15")

        self.words_data = []  # list of {"word","start","end": StringVar}

        self._build_layout()
        self.after(200, self._attach_player)

    # ── layout ──────────────────────────────────────────────────────────

    def _build_layout(self):
        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=12, pady=12)
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(root, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ctk.CTkFrame(root, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._build_left(left)
        self._build_right(right)

    def _build_left(self, parent):
        ctk.CTkLabel(parent, text="Subtítulos de vídeo",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(4, 10), anchor="w")

        scroll = ctk.CTkScrollableFrame(parent, height=340)
        scroll.pack(fill="x", pady=(0, 10))

        self._file_row(scroll, "Vídeo (.mp4):", self.video_path, self.choose_video)
        self._file_row(scroll, "Guardar en:", self.output_dir, self.choose_output_dir)
        ctk.CTkSwitch(scroll, text="Modo Word-Highlight",
                      variable=self.highlight_mode).pack(anchor="w", pady=(14, 4), padx=4)
        self._select_row(scroll, "Modelo Whisper:", self.model, MODELS)
        self._select_row(scroll, "Idioma:", self.language, list(LANGUAGES.keys()))
        self._select_row(scroll, "Formato de texto:", self.case, list(CASES.keys()))
        self._entry_row(scroll, "Tamaño de fuente (px):", self.font_size)
        self._entry_row(scroll, "Grosor del contorno (px):", self.outline_width)
        self._color_row(scroll, "Color de resaltado:", self.highlight_color)
        self._entry_row(scroll, "Escala mínima resaltado:", self.highlight_size_min)
        self._entry_row(scroll, "Escala máxima resaltado:", self.highlight_size_max)
        self._entry_row(scroll, "% máx. palabras resaltadas:", self.highlight_max_pct)
        self._entry_row(scroll, "Pausa fin de frase (s):", self.pause_threshold)
        ctk.CTkLabel(scroll, text="Posición vertical (0=arriba, 1=abajo):").pack(anchor="w", pady=(14, 0), padx=4)
        ctk.CTkSlider(scroll, from_=0, to=1, variable=self.y_position).pack(fill="x", padx=4, pady=(4, 0))

        self.transcribe_btn = ctk.CTkButton(parent, text="1. Transcribir con Whisper", height=38,
                                            font=ctk.CTkFont(size=14, weight="bold"),
                                            command=self.start_transcribe)
        self.transcribe_btn.pack(fill="x", pady=(4, 8))

        ctk.CTkLabel(parent, text="Transcripción (editable):", anchor="w").pack(fill="x")
        self.words_scroll = ctk.CTkScrollableFrame(parent)
        self.words_scroll.pack(fill="both", expand=True, pady=(4, 8))

        ctk.CTkButton(parent, text="+ Añadir palabra", height=28,
                      command=self.add_word).pack(fill="x")

    def _build_right(self, parent):
        self.video_frame = ctk.CTkFrame(parent, fg_color="black", height=360)
        self.video_frame.pack(fill="both", expand=True, pady=(4, 8))

        controls = ctk.CTkFrame(parent, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(controls, text="▶", width=44, command=lambda: self.player.play()).pack(side="left", padx=2)
        ctk.CTkButton(controls, text="⏸", width=44, command=lambda: self.player.pause()).pack(side="left", padx=2)
        ctk.CTkButton(controls, text="⏹", width=44, command=lambda: self.player.stop()).pack(side="left", padx=2)
        ctk.CTkLabel(controls, text="Duración preview (s):").pack(side="left", padx=(16, 4))
        ctk.CTkEntry(controls, textvariable=self.preview_duration, width=50).pack(side="left")

        self.preview_btn = ctk.CTkButton(parent, text="2. Generar preview", height=38,
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         command=self.start_preview)
        self.preview_btn.pack(fill="x", pady=(0, 6))
        self.export_btn = ctk.CTkButton(parent, text="3. Exportar vídeo final", height=38,
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        fg_color="#2E8B57", hover_color="#256F46",
                                        command=self.start_export)
        self.export_btn.pack(fill="x", pady=(0, 10))

        self.stage_label = ctk.CTkLabel(parent, text="", text_color="gray60")
        self.stage_label.pack()
        self.progress_bar = ctk.CTkProgressBar(parent, height=14)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(4, 10))

        self.log_box = ctk.CTkTextbox(parent, height=140)
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

    def _attach_player(self):
        self.vlc_instance = vlc.Instance("--no-xlib")
        self.player = self.vlc_instance.media_player_new()
        self.player.set_hwnd(self.video_frame.winfo_id())

    # ── small widget helpers ─────────────────────────────────────────────

    def _file_row(self, parent, label, var, command):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(row, text=label, width=110, anchor="w").pack(side="left")
        ctk.CTkEntry(row, textvariable=var, state="readonly").pack(side="left", fill="x", expand=True, padx=8)
        ctk.CTkButton(row, text="Elegir...", width=80, command=command).pack(side="left")

    def _select_row(self, parent, label, var, options):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(row, text=label, width=160, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(row, values=options, variable=var).pack(side="left", fill="x", expand=True)

    def _entry_row(self, parent, label, var):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(row, text=label, width=220, anchor="w").pack(side="left")
        ctk.CTkEntry(row, textvariable=var).pack(side="left", fill="x", expand=True)

    def _color_row(self, parent, label, var):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(row, text=label, width=220, anchor="w").pack(side="left")
        ctk.CTkEntry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        swatch = ctk.CTkButton(row, text="", width=32, height=28, fg_color=var.get(),
                               hover_color=var.get(), border_width=1,
                               command=lambda: self._pick_color(var, swatch))
        swatch.pack(side="left")

    def _pick_color(self, var, swatch):
        chosen = colorchooser.askcolor(color=var.get(), title="Color de resaltado")
        if chosen and chosen[1]:
            var.set(chosen[1])
            swatch.configure(fg_color=chosen[1], hover_color=chosen[1])

    def choose_video(self):
        path = filedialog.askopenfilename(filetypes=[("Vídeo MP4", "*.mp4")])
        if path:
            self.video_path.set(path)
            if not self.output_dir.get():
                self.output_dir.set(str(Path(path).parent))

    def choose_output_dir(self):
        chosen = filedialog.askdirectory()
        if chosen:
            self.output_dir.set(chosen)

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_stage(self, text):
        self.stage_label.configure(text=text)
        if text.startswith("Renderizando"):
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(0)
        elif text in ("Listo", "Error", ""):
            self.progress_bar.stop()
        else:
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start()

    def _set_progress(self, fraction):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(fraction)

    def _reset_progress(self):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.stage_label.configure(text="")

    def _apply_render_globals(self):
        try:
            core.FONT_SIZE = int(self.font_size.get())
            core.OUTLINE_WIDTH = int(self.outline_width.get())
            core.Y_POSITION = self.y_position.get()
            core.HIGHLIGHT_COLOR = self.highlight_color.get()
            core.HIGHLIGHT_SIZE_MIN = float(self.highlight_size_min.get())
            core.HIGHLIGHT_SIZE_MAX = float(self.highlight_size_max.get())
            core.HIGHLIGHT_MAX_PCT = float(self.highlight_max_pct.get())
            core.PAUSE_THRESHOLD = float(self.pause_threshold.get())
        except ValueError:
            raise ValueError("Revisa los campos numéricos de estilo.")

    # ── step 1: transcribe ────────────────────────────────────────────────

    def start_transcribe(self):
        if not self.video_path.get():
            messagebox.showwarning("Falta el vídeo", "Elige un archivo .mp4 antes de continuar.")
            return
        core.TEXT_CASE = CASES[self.case.get()]
        core.LANGUAGE = LANGUAGES[self.language.get()]
        self.transcribe_btn.configure(state="disabled", text="Transcribiendo...")
        self._reset_progress()
        threading.Thread(target=self._run_transcribe, daemon=True).start()

    def _run_transcribe(self):
        video_path = Path(self.video_path.get())
        old_stdout = sys.stdout
        sys.stdout = _TeeToGui(self)
        try:
            self.after(0, self._set_stage, "Transcribiendo con Whisper...")
            timings = core.transcribe_video(video_path, self.model.get())
            self.after(0, self._load_words, timings)
            self.after(0, self._set_stage, "Listo")
            self.after(0, self.log, f"{len(timings)} palabras transcritas.")
        except Exception:
            self.after(0, self.log, "Error:\n" + traceback.format_exc())
            self.after(0, self._set_stage, "Error")
        finally:
            sys.stdout = old_stdout
            self.after(0, lambda: self.transcribe_btn.configure(
                state="normal", text="1. Transcribir con Whisper"))

    # ── word editor ───────────────────────────────────────────────────────

    def _load_words(self, timings):
        self.words_data = [
            {"word": ctk.StringVar(value=w), "start": ctk.StringVar(value=f"{s:.2f}"),
             "end": ctk.StringVar(value=f"{e:.2f}")}
            for w, s, e in timings
        ]
        self._rebuild_word_rows()

    def _rebuild_word_rows(self):
        for child in self.words_scroll.winfo_children():
            child.destroy()

        for i, row in enumerate(self.words_data):
            r = ctk.CTkFrame(self.words_scroll, fg_color="transparent")
            r.pack(fill="x", pady=1)
            ctk.CTkEntry(r, textvariable=row["word"], width=140).pack(side="left", padx=(0, 4))
            ctk.CTkEntry(r, textvariable=row["start"], width=55).pack(side="left", padx=2)
            ctk.CTkEntry(r, textvariable=row["end"], width=55).pack(side="left", padx=2)
            ctk.CTkButton(r, text="🔗", width=28, command=lambda i=i: self.merge_word(i)
                         ).pack(side="left", padx=1)
            ctk.CTkButton(r, text="✂", width=28, command=lambda i=i: self.split_word(i)
                         ).pack(side="left", padx=1)
            ctk.CTkButton(r, text="🗑", width=28, fg_color="#8B3A3A", hover_color="#6E2E2E",
                         command=lambda i=i: self.delete_word(i)).pack(side="left", padx=1)

    def merge_word(self, i):
        if i >= len(self.words_data) - 1:
            return
        a, b = self.words_data[i], self.words_data[i + 1]
        a["word"].set(f"{a['word'].get()} {b['word'].get()}".strip())
        a["end"].set(b["end"].get())
        del self.words_data[i + 1]
        self._rebuild_word_rows()

    def split_word(self, i):
        row = self.words_data[i]
        parts = row["word"].get().strip().split(None, 1)
        if len(parts) < 2:
            messagebox.showinfo("No se puede dividir", "Escribe dos palabras separadas por un espacio para dividir esta entrada.")
            return
        try:
            s, e = float(row["start"].get()), float(row["end"].get())
        except ValueError:
            messagebox.showerror("Tiempo inválido", "Revisa los tiempos de esta palabra.")
            return
        mid = (s + e) / 2
        first = {"word": ctk.StringVar(value=parts[0]), "start": ctk.StringVar(value=f"{s:.2f}"),
                "end": ctk.StringVar(value=f"{mid:.2f}")}
        second = {"word": ctk.StringVar(value=parts[1]), "start": ctk.StringVar(value=f"{mid:.2f}"),
                 "end": ctk.StringVar(value=f"{e:.2f}")}
        self.words_data[i:i + 1] = [first, second]
        self._rebuild_word_rows()

    def delete_word(self, i):
        del self.words_data[i]
        self._rebuild_word_rows()

    def add_word(self):
        last_end = float(self.words_data[-1]["end"].get()) if self.words_data else 0.0
        row = {"word": ctk.StringVar(value="palabra"), "start": ctk.StringVar(value=f"{last_end:.2f}"),
              "end": ctk.StringVar(value=f"{last_end + 0.3:.2f}")}
        self.words_data.append(row)
        self._rebuild_word_rows()

    def _current_word_timings(self):
        out = []
        for row in self.words_data:
            word = row["word"].get().strip()
            if not word:
                continue
            out.append((word, float(row["start"].get()), float(row["end"].get())))
        return out

    # ── step 2: preview ──────────────────────────────────────────────────

    def start_preview(self):
        if not self.words_data:
            messagebox.showwarning("Sin transcripción", "Transcribe el vídeo primero.")
            return
        try:
            self._apply_render_globals()
            duration = float(self.preview_duration.get())
        except ValueError as e:
            messagebox.showerror("Valor inválido", str(e))
            return
        self.preview_btn.configure(state="disabled", text="Generando preview...")
        self._reset_progress()
        threading.Thread(target=self._run_preview, args=(duration,), daemon=True).start()

    def _run_preview(self, duration):
        old_stdout = sys.stdout
        sys.stdout = _TeeToGui(self)
        try:
            video_path = Path(self.video_path.get())
            self.after(0, self._set_stage, "Recortando clip de preview...")
            core.trim_video(video_path, duration, PREVIEW_SRC)

            words = [(w, s, min(e, duration)) for w, s, e in self._current_word_timings() if s < duration]

            self.after(0, self._set_stage, "Renderizando preview...")

            def on_progress(frac):
                self.after(0, self._set_progress, frac)

            core.render_video(PREVIEW_SRC, words, PREVIEW_OUT,
                              highlight_mode=self.highlight_mode.get(), progress_callback=on_progress)
            self.after(0, self._play_file, str(PREVIEW_OUT))
            self.after(0, self._set_stage, "Listo")
        except Exception:
            self.after(0, self.log, "Error:\n" + traceback.format_exc())
            self.after(0, self._set_stage, "Error")
        finally:
            sys.stdout = old_stdout
            self.after(0, lambda: self.preview_btn.configure(state="normal", text="2. Generar preview"))

    def _play_file(self, path):
        media = self.vlc_instance.media_new(path)
        self.player.set_media(media)
        self.player.play()

    # ── step 3: export ───────────────────────────────────────────────────

    def start_export(self):
        if not self.words_data:
            messagebox.showwarning("Sin transcripción", "Transcribe el vídeo primero.")
            return
        if not self.output_dir.get():
            messagebox.showwarning("Falta carpeta", "Elige dónde guardar el vídeo final.")
            return
        try:
            self._apply_render_globals()
        except ValueError as e:
            messagebox.showerror("Valor inválido", str(e))
            return
        self.export_btn.configure(state="disabled", text="Exportando...")
        self._reset_progress()
        threading.Thread(target=self._run_export, daemon=True).start()

    def _run_export(self):
        old_stdout = sys.stdout
        sys.stdout = _TeeToGui(self)
        try:
            video_path = Path(self.video_path.get())
            suffix = core.OUTPUT_SUFFIX + ("_wh" if self.highlight_mode.get() else "")
            out_path = Path(self.output_dir.get()) / (video_path.stem + suffix + ".mp4")

            self.after(0, self._set_stage, "Renderizando vídeo final...")

            def on_progress(frac):
                self.after(0, self._set_progress, frac)

            core.render_video(video_path, self._current_word_timings(), out_path,
                              highlight_mode=self.highlight_mode.get(), progress_callback=on_progress)
            self.after(0, self.log, f"Exportado --> {out_path}")
            self.after(0, self._set_stage, "Listo")
        except Exception:
            self.after(0, self.log, "Error:\n" + traceback.format_exc())
            self.after(0, self._set_stage, "Error")
        finally:
            sys.stdout = old_stdout
            self.after(0, lambda: self.export_btn.configure(state="normal", text="3. Exportar vídeo final"))


class _TeeToGui:
    def __init__(self, app):
        self.app = app

    def write(self, text):
        if text.strip():
            self.app.after(0, self.app.log, text.rstrip())

    def flush(self):
        pass


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    App().mainloop()
