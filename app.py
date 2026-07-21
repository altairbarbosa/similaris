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
        "images_tab": "Images", "videos_tab": "Video conversion", "duplicates": "Find and separate duplicate images",
        "images": "Convert images to JPG", "videos": "Convert videos to MP4",
        "rename": 'Rename images as "img (N)"',
        "jpg": "JPG quality:", "video": "Video quality (CRF):", "lower": "(lower = better)",
        "sensitivity": "Detection sensitivity:",
        "mode": "Image organization mode", "simulate": "Simulate separating/renaming", "apply": "Apply image changes",
        "start": "Start", "ready": "Ready", "about": "About and licenses",
        "results": "Progress and results", "choose": "Select a folder",
        "invalid_title": "Invalid folder", "invalid": "Select a valid folder.",
        "none_title": "No operation", "none": "Select at least one operation.",
        "confirm_title": "Confirm image changes", "confirm": "Separate duplicates and/or rename images? Conversions preserve their originals.",
        "running": "Processing...", "done": "Completed", "failed": "Completed with errors",
        "done_msg": "Processing completed.", "failed_msg": "Processing ended with an error. See the results.",
        "unexpected": "UNEXPECTED ERROR", "product": "Similaris",
        "conservative": "Conservative", "balanced": "Balanced", "sensitive": "Sensitive",
        "sensitivity_conservative": "Fewer false positives; stricter confirmation.",
        "sensitivity_balanced": "Recommended balance between safety and recall.",
        "sensitivity_sensitive": "Finds more edited copies; review the simulation first.",
        "video_only": "Conversion only — Similaris does not compare videos.",
        "video_details": "Creates an MP4 (H.264/AAC) in the converted folder and preserves the original.",
    },
    "pt-BR": {
        "title": "Similaris", "folder": "Pasta dos arquivos", "select": "Selecionar...",
        "images_tab": "Imagens", "videos_tab": "Conversão de vídeos", "duplicates": "Detectar e separar imagens repetidas",
        "images": "Converter imagens para JPG", "videos": "Converter vídeos para MP4",
        "rename": 'Renomear imagens como "img (N)"',
        "jpg": "Qualidade JPG:", "video": "Qualidade do vídeo (CRF):", "lower": "(menor = melhor)",
        "sensitivity": "Sensibilidade da detecção:",
        "mode": "Modo de organização das imagens", "simulate": "Simular separação/renomeação", "apply": "Aplicar alterações nas imagens",
        "start": "Iniciar", "ready": "Pronto", "about": "Sobre e licenças",
        "results": "Progresso e resultados", "choose": "Selecione a pasta",
        "invalid_title": "Pasta inválida", "invalid": "Selecione uma pasta válida.",
        "none_title": "Nenhuma operação", "none": "Marque ao menos uma operação.",
        "confirm_title": "Confirmar alterações nas imagens", "confirm": "Deseja separar duplicatas e/ou renomear imagens? As conversões preservam os originais.",
        "running": "Processando...", "done": "Concluído", "failed": "Concluído com erro",
        "done_msg": "Processamento concluído.", "failed_msg": "O processamento terminou com erro. Consulte os resultados.",
        "unexpected": "ERRO INESPERADO", "product": "Similaris",
        "conservative": "Conservador", "balanced": "Equilibrado", "sensitive": "Sensível",
        "sensitivity_conservative": "Menos falsos positivos; confirmação mais rigorosa.",
        "sensitivity_balanced": "Equilíbrio recomendado entre segurança e cobertura.",
        "sensitivity_sensitive": "Encontra mais cópias editadas; revise a simulação primeiro.",
        "video_only": "Somente conversão — o Similaris não compara vídeos.",
        "video_details": "Cria um MP4 (H.264/AAC) na pasta converted e preserva o arquivo original.",
    },
    "es-ES": {
        "title": "Similaris", "folder": "Carpeta de archivos", "select": "Seleccionar...",
        "images_tab": "Imágenes", "videos_tab": "Conversión de vídeos", "duplicates": "Detectar y separar imágenes duplicadas",
        "images": "Convertir imágenes a JPG", "videos": "Convertir vídeos a MP4",
        "rename": 'Renombrar imágenes como "img (N)"',
        "jpg": "Calidad JPG:", "video": "Calidad del vídeo (CRF):", "lower": "(menor = mejor)",
        "sensitivity": "Sensibilidad de detección:",
        "mode": "Modo de organización de imágenes", "simulate": "Simular separación/renombrado", "apply": "Aplicar cambios en imágenes",
        "start": "Iniciar", "ready": "Listo", "about": "Acerca de y licencias",
        "results": "Progreso y resultados", "choose": "Seleccione la carpeta",
        "invalid_title": "Carpeta no válida", "invalid": "Seleccione una carpeta válida.",
        "none_title": "Ninguna operación", "none": "Seleccione al menos una operación.",
        "confirm_title": "Confirmar cambios en imágenes", "confirm": "¿Desea separar duplicados y/o renombrar imágenes? Las conversiones conservan los originales.",
        "running": "Procesando...", "done": "Completado", "failed": "Completado con errores",
        "done_msg": "Procesamiento completado.", "failed_msg": "El procesamiento terminó con un error. Consulte los resultados.",
        "unexpected": "ERROR INESPERADO", "product": "Similaris",
        "conservative": "Conservador", "balanced": "Equilibrado", "sensitive": "Sensible",
        "sensitivity_conservative": "Menos falsos positivos; confirmación más estricta.",
        "sensitivity_balanced": "Equilibrio recomendado entre seguridad y cobertura.",
        "sensitivity_sensitive": "Encuentra más copias editadas; revise primero la simulación.",
        "video_only": "Solo conversión — Similaris no compara vídeos.",
        "video_details": "Crea un MP4 (H.264/AAC) en la carpeta converted y conserva el archivo original.",
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
        self.jpg_quality = tk.IntVar(value=92)
        self.video_quality = tk.IntVar(value=20)
        self.sensitivity = tk.StringVar(value="balanced")
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
        main.rowconfigure(5, weight=1)
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

        self.operations = ttk.Notebook(main)
        self.operations.grid(row=2, column=0, sticky="ew", pady=12)
        self.images_tab = ttk.Frame(self.operations, padding=12)
        self.videos_tab = ttk.Frame(self.operations, padding=12)
        self.operations.add(self.images_tab)
        self.operations.add(self.videos_tab)

        self._widget("duplicates", ttk.Checkbutton(self.images_tab, variable=self.find_duplicates)).grid(row=0, column=0, sticky="w")
        self._widget("rename", ttk.Checkbutton(self.images_tab, variable=self.rename_images)).grid(row=0, column=1, sticky="w", padx=(35, 0))
        self._widget("images", ttk.Checkbutton(self.images_tab, variable=self.convert_images)).grid(row=1, column=0, sticky="w", pady=(6, 0))
        image_quality = ttk.Frame(self.images_tab)
        image_quality.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self._widget("jpg", ttk.Label(image_quality)).pack(side="left")
        ttk.Spinbox(image_quality, from_=1, to=100, width=5, textvariable=self.jpg_quality).pack(side="left", padx=5)
        sensitivity = ttk.Frame(self.images_tab)
        sensitivity.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self._widget("sensitivity", ttk.Label(sensitivity)).pack(side="left")
        self.sensitivity_box = ttk.Combobox(sensitivity, state="readonly", width=16)
        self.sensitivity_box.pack(side="left", padx=5)
        self.sensitivity_box.bind("<<ComboboxSelected>>", self._sensitivity_selected)
        self.sensitivity_help = ttk.Label(sensitivity)
        self.sensitivity_help.pack(side="left", padx=(8, 0))

        self._widget("video_only", ttk.Label(self.videos_tab, font=("TkDefaultFont", 10, "bold"))).grid(row=0, column=0, sticky="w")
        self._widget("video_details", ttk.Label(self.videos_tab, wraplength=700)).grid(row=1, column=0, sticky="w", pady=(4, 12))
        self._widget("videos", ttk.Checkbutton(self.videos_tab, variable=self.convert_videos)).grid(row=2, column=0, sticky="w")
        video_quality = ttk.Frame(self.videos_tab)
        video_quality.grid(row=3, column=0, sticky="w", pady=(12, 0))
        self._widget("video", ttk.Label(video_quality)).pack(side="left")
        ttk.Spinbox(video_quality, from_=0, to=51, width=5, textvariable=self.video_quality).pack(side="left", padx=5)
        self._widget("lower", ttk.Label(video_quality)).pack(side="left")

        mode = self._widget("mode", ttk.LabelFrame(self.images_tab, padding=10))
        mode.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self._widget("simulate", ttk.Radiobutton(mode, variable=self.apply_changes, value=False)).pack(side="left")
        self._widget("apply", ttk.Radiobutton(mode, variable=self.apply_changes, value=True)).pack(side="left", padx=25)
        buttons = ttk.Frame(main)
        buttons.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        self.start_button = self._widget("start", ttk.Button(buttons, command=self._start))
        self.start_button.pack(side="left")
        self.progress = ttk.Progressbar(buttons, mode="determinate", maximum=100, value=0, length=220)
        self.progress.pack(side="left", padx=15)
        self.status = ttk.Label(buttons)
        self.status.pack(side="left")
        self._widget("about", ttk.Button(buttons, command=self._about)).pack(side="right")
        log_box = self._widget("results", ttk.LabelFrame(main, padding=6))
        log_box.grid(row=5, column=0, sticky="nsew")
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
        self.operations.tab(self.images_tab, text=self.tr("images_tab"))
        self.operations.tab(self.videos_tab, text=self.tr("videos_tab"))
        sensitivity_values = [self.tr(name) for name in ("conservative", "balanced", "sensitive")]
        self.sensitivity_box.configure(values=sensitivity_values)
        self.sensitivity_box.current(("conservative", "balanced", "sensitive").index(self.sensitivity.get()))
        self.sensitivity_help.configure(text=self.tr(f"sensitivity_{self.sensitivity.get()}"))
        if self.start_button.instate(["disabled"]):
            self.status.configure(text=self.tr("running"))
        else:
            self.status.configure(text=self.tr("ready"))

    def _select_folder(self) -> None:
        selected = filedialog.askdirectory(title=self.tr("choose"))
        if selected:
            self.folder.set(selected)

    def _sensitivity_selected(self, _event: object = None) -> None:
        self.sensitivity.set(("conservative", "balanced", "sensitive")[self.sensitivity_box.current()])
        self.sensitivity_help.configure(text=self.tr(f"sensitivity_{self.sensitivity.get()}"))

    def _about(self) -> None:
        window = tk.Toplevel(self)
        window.title(self.tr("about"))
        window.geometry("680x480")
        text = tk.Text(window, wrap="word", padx=12, pady=12)
        text.pack(fill="both", expand=True)
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        parts = [self.tr("title") + "\n\n"]
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.txt", "GPL-3.0.txt"):
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
        arguments += ["--jpg-quality", str(self.jpg_quality.get()), "--video-quality", str(self.video_quality.get())]
        arguments += ["--language", self.language]
        arguments += ["--sensitivity", self.sensitivity.get()]
        return arguments

    def _start(self) -> None:
        folder = Path(self.folder.get()).expanduser()
        if not folder.is_dir():
            messagebox.showerror(self.tr("invalid_title"), self.tr("invalid")); return
        if not any((self.find_duplicates.get(), self.convert_images.get(), self.convert_videos.get(), self.rename_images.get())):
            messagebox.showwarning(self.tr("none_title"), self.tr("none")); return
        changes_images = self.apply_changes.get() and (self.find_duplicates.get() or self.rename_images.get())
        if changes_images and not messagebox.askyesno(self.tr("confirm_title"), self.tr("confirm")): return
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
