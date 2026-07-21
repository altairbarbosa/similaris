#!/usr/bin/env python3
"""Cross-platform, multilingual graphical interface for Photo Organizer."""

from __future__ import annotations

import contextlib
import locale
import queue
import sys
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import photo_organizer


LANGUAGES = {"Português (Brasil)": "pt-BR", "English (US)": "en-US", "Español": "es-ES"}
TEXT = {
    "en-US": {
        "title": "Similaris", "folder": "Files folder", "select": "Browse...",
        "actions": "What would you like to do?", "duplicates": "Find and separate duplicate images",
        "images": "Convert images to JPG", "videos": "Convert videos to MP4",
        "rename": 'Rename images as "img (N)"', "zip": "Create photos.zip",
        "jpg": "JPG quality:", "video": "Video quality (CRF):", "lower": "(lower = better)",
        "mode": "Mode", "simulate": "Simulate only (recommended first)", "apply": "Apply changes",
        "start": "Start", "ready": "Ready", "about": "About and licenses",
        "results": "Progress and results", "choose": "Select a folder",
        "invalid_title": "Invalid folder", "invalid": "Select a valid folder.",
        "none_title": "No operation", "none": "Select at least one operation.",
        "confirm_title": "Confirm changes", "confirm": "Apply the selected operations? Converted originals will be preserved.",
        "running": "Processing...", "done": "Completed", "failed": "Completed with errors",
        "done_msg": "Processing completed.", "failed_msg": "Processing ended with an error. See the results.",
        "unexpected": "UNEXPECTED ERROR", "product": "Similaris",
    },
    "pt-BR": {
        "title": "Similaris", "folder": "Pasta dos arquivos", "select": "Selecionar...",
        "actions": "O que deseja fazer?", "duplicates": "Detectar e separar imagens repetidas",
        "images": "Converter imagens para JPG", "videos": "Converter vídeos para MP4",
        "rename": 'Renomear imagens como "img (N)"', "zip": "Criar photos.zip",
        "jpg": "Qualidade JPG:", "video": "Qualidade do vídeo (CRF):", "lower": "(menor = melhor)",
        "mode": "Modo", "simulate": "Somente simular (recomendado primeiro)", "apply": "Aplicar alterações",
        "start": "Iniciar", "ready": "Pronto", "about": "Sobre e licenças",
        "results": "Progresso e resultados", "choose": "Selecione a pasta",
        "invalid_title": "Pasta inválida", "invalid": "Selecione uma pasta válida.",
        "none_title": "Nenhuma operação", "none": "Marque ao menos uma operação.",
        "confirm_title": "Confirmar alterações", "confirm": "Deseja aplicar as operações selecionadas? Os originais convertidos serão preservados.",
        "running": "Processando...", "done": "Concluído", "failed": "Concluído com erro",
        "done_msg": "Processamento concluído.", "failed_msg": "O processamento terminou com erro. Consulte os resultados.",
        "unexpected": "ERRO INESPERADO", "product": "Similaris",
    },
    "es-ES": {
        "title": "Similaris", "folder": "Carpeta de archivos", "select": "Seleccionar...",
        "actions": "¿Qué desea hacer?", "duplicates": "Detectar y separar imágenes duplicadas",
        "images": "Convertir imágenes a JPG", "videos": "Convertir vídeos a MP4",
        "rename": 'Renombrar imágenes como "img (N)"', "zip": "Crear photos.zip",
        "jpg": "Calidad JPG:", "video": "Calidad del vídeo (CRF):", "lower": "(menor = mejor)",
        "mode": "Modo", "simulate": "Solo simular (recomendado primero)", "apply": "Aplicar cambios",
        "start": "Iniciar", "ready": "Listo", "about": "Acerca de y licencias",
        "results": "Progreso y resultados", "choose": "Seleccione la carpeta",
        "invalid_title": "Carpeta no válida", "invalid": "Seleccione una carpeta válida.",
        "none_title": "Ninguna operación", "none": "Seleccione al menos una operación.",
        "confirm_title": "Confirmar cambios", "confirm": "¿Desea aplicar las operaciones seleccionadas? Se conservarán los originales convertidos.",
        "running": "Procesando...", "done": "Completado", "failed": "Completado con errores",
        "done_msg": "Procesamiento completado.", "failed_msg": "El procesamiento terminó con un error. Consulte los resultados.",
        "unexpected": "ERROR INESPERADO", "product": "Similaris",
    },
}


def system_language() -> str:
    language = (locale.getlocale()[0] or "en_US").lower()
    return "pt-BR" if language.startswith("pt") else "es-ES" if language.startswith("es") else "en-US"


class QueueWriter:
    def __init__(self, events: queue.Queue[tuple[str, object]]) -> None:
        self.events = events

    def write(self, value: str) -> int:
        if value:
            self.events.put(("text", value))
        return len(value)

    def flush(self) -> None:
        pass


class Application(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.geometry("860x720")
        self.minsize(760, 640)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        resource_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        self.logo_image = tk.PhotoImage(file=resource_dir / "assets" / "similaris-icon.png")
        self.header_logo = self.logo_image.subsample(9, 9)
        self.iconphoto(True, self.logo_image)
        detected = system_language()
        self.language_name = tk.StringVar(value=next(name for name, code in LANGUAGES.items() if code == detected))
        self.folder = tk.StringVar()
        self.apply_changes = tk.BooleanVar(value=False)
        self.find_duplicates = tk.BooleanVar(value=True)
        self.convert_images = tk.BooleanVar(value=False)
        self.convert_videos = tk.BooleanVar(value=False)
        self.rename_images = tk.BooleanVar(value=False)
        self.make_zip = tk.BooleanVar(value=False)
        self.jpg_quality = tk.IntVar(value=92)
        self.video_quality = tk.IntVar(value=20)
        self.widgets: dict[str, tk.Misc] = {}
        self._build_ui()
        self._translate()
        self.after(100, self._read_events)

    @property
    def language(self) -> str:
        return LANGUAGES[self.language_name.get()]

    def tr(self, key: str) -> str:
        return TEXT[self.language][key]

    def _widget(self, key: str, widget: tk.Misc) -> tk.Misc:
        self.widgets[key] = widget
        return widget

    def _build_ui(self) -> None:
        main = ttk.Frame(self, padding=18)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(6, weight=1)
        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        ttk.Label(header, image=self.header_logo).pack(side="left", padx=(0, 10))
        self._widget("title", ttk.Label(header, font=("Segoe UI", 17, "bold"))).pack(side="left")
        ttk.Combobox(header, textvariable=self.language_name, values=list(LANGUAGES), state="readonly", width=20).pack(side="right")
        self.language_name.trace_add("write", lambda *_: self._translate())

        folder_box = self._widget("folder", ttk.LabelFrame(main, padding=10))
        folder_box.grid(row=1, column=0, sticky="ew")
        folder_box.columnconfigure(0, weight=1)
        ttk.Entry(folder_box, textvariable=self.folder).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._widget("select", ttk.Button(folder_box, command=self._select_folder)).grid(row=0, column=1)

        actions = self._widget("actions", ttk.LabelFrame(main, padding=10))
        actions.grid(row=2, column=0, sticky="ew", pady=12)
        for key, variable, row, column in (
            ("duplicates", self.find_duplicates, 0, 0), ("images", self.convert_images, 1, 0),
            ("videos", self.convert_videos, 2, 0), ("rename", self.rename_images, 0, 1), ("zip", self.make_zip, 1, 1),
        ):
            self._widget(key, ttk.Checkbutton(actions, variable=variable)).grid(row=row, column=column, sticky="w", padx=(0 if column == 0 else 35, 0))
        quality = ttk.Frame(actions)
        quality.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self._widget("jpg", ttk.Label(quality)).pack(side="left")
        ttk.Spinbox(quality, from_=1, to=100, width=5, textvariable=self.jpg_quality).pack(side="left", padx=(5, 25))
        self._widget("video", ttk.Label(quality)).pack(side="left")
        ttk.Spinbox(quality, from_=0, to=51, width=5, textvariable=self.video_quality).pack(side="left", padx=5)
        self._widget("lower", ttk.Label(quality)).pack(side="left")

        mode = self._widget("mode", ttk.LabelFrame(main, padding=10))
        mode.grid(row=3, column=0, sticky="ew")
        self._widget("simulate", ttk.Radiobutton(mode, variable=self.apply_changes, value=False)).pack(side="left")
        self._widget("apply", ttk.Radiobutton(mode, variable=self.apply_changes, value=True)).pack(side="left", padx=25)
        buttons = ttk.Frame(main)
        buttons.grid(row=4, column=0, sticky="ew", pady=12)
        self.start_button = self._widget("start", ttk.Button(buttons, command=self._start))
        self.start_button.pack(side="left")
        self.progress = ttk.Progressbar(buttons, mode="determinate", maximum=100, value=0, length=220)
        self.progress.pack(side="left", padx=15)
        self.status = ttk.Label(buttons)
        self.status.pack(side="left")
        self._widget("about", ttk.Button(buttons, command=self._about)).pack(side="right")
        log_box = self._widget("results", ttk.LabelFrame(main, padding=6))
        log_box.grid(row=6, column=0, sticky="nsew")
        log_box.columnconfigure(0, weight=1)
        log_box.rowconfigure(0, weight=1)
        self.log = tk.Text(log_box, wrap="word", state="disabled", font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(log_box, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    def _translate(self) -> None:
        self.title(self.tr("title"))
        for key, widget in self.widgets.items():
            widget.configure(text=self.tr(key))
        if self.start_button.instate(["disabled"]):
            self.status.configure(text=self.tr("running"))
        else:
            self.status.configure(text=self.tr("ready"))

    def _select_folder(self) -> None:
        selected = filedialog.askdirectory(title=self.tr("choose"))
        if selected:
            self.folder.set(selected)

    def _about(self) -> None:
        window = tk.Toplevel(self)
        window.title(self.tr("about"))
        window.geometry("680x480")
        text = tk.Text(window, wrap="word", padx=12, pady=12)
        text.pack(fill="both", expand=True)
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        parts = [self.tr("title") + "\n\n"]
        for name in ("THIRD_PARTY_NOTICES.txt", "GPL-3.0.txt"):
            file = base / name
            if file.is_file():
                parts.extend((file.read_text(encoding="utf-8", errors="replace"), "\n\n"))
        text.insert("1.0", "".join(parts))
        text.configure(state="disabled")

    def _arguments(self) -> list[str]:
        arguments = [self.folder.get()]
        if self.apply_changes.get(): arguments.append("--apply")
        if self.convert_images.get(): arguments.append("--convert-images")
        if self.convert_videos.get(): arguments.append("--convert-videos")
        if not self.find_duplicates.get(): arguments.append("--skip-duplicates")
        if self.rename_images.get(): arguments.append("--rename")
        if self.make_zip.get(): arguments.append("--zip")
        arguments += ["--jpg-quality", str(self.jpg_quality.get()), "--video-quality", str(self.video_quality.get())]
        arguments += ["--language", self.language]
        return arguments

    def _start(self) -> None:
        folder = Path(self.folder.get()).expanduser()
        if not folder.is_dir():
            messagebox.showerror(self.tr("invalid_title"), self.tr("invalid")); return
        if not any((self.find_duplicates.get(), self.convert_images.get(), self.convert_videos.get(), self.rename_images.get(), self.make_zip.get())):
            messagebox.showwarning(self.tr("none_title"), self.tr("none")); return
        if self.apply_changes.get() and not messagebox.askyesno(self.tr("confirm_title"), self.tr("confirm")): return
        self.log.configure(state="normal"); self.log.delete("1.0", "end"); self.log.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.progress.configure(mode="indeterminate", value=0); self.progress.start(10)
        self.status.configure(text=self.tr("running"))
        threading.Thread(target=self._run, args=(self._arguments(),), daemon=True).start()

    def _run(self, arguments: list[str]) -> None:
        writer = QueueWriter(self.events)
        try:
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                code = photo_organizer.main(arguments)
            self.events.put(("done", code))
        except Exception:
            self.events.put(("text", f"\n{self.tr('unexpected')}:\n{traceback.format_exc()}")); self.events.put(("done", 1))

    def _read_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "text":
                    self.log.configure(state="normal"); self.log.insert("end", str(value)); self.log.see("end"); self.log.configure(state="disabled")
                elif event == "done":
                    self.progress.stop(); self.progress.configure(mode="determinate", value=0); self.start_button.configure(state="normal")
                    success = int(value) == 0
                    self.status.configure(text=self.tr("done" if success else "failed"))
                    (messagebox.showinfo if success else messagebox.showerror)(self.tr("product"), self.tr("done_msg" if success else "failed_msg"))
        except queue.Empty:
            pass
        self.after(100, self._read_events)


if __name__ == "__main__":
    Application().mainloop()
