#!/usr/bin/env python3
"""Cross-platform, multilingual graphical interface for Photo Organizer."""

from __future__ import annotations

import contextlib
import locale
import os
import queue
import re
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import photo_organizer


LANGUAGES = {"Português (Brasil)": "pt-BR", "English (US)": "en-US", "Español": "es-ES"}
SUPPORT_URL = (
    "https://www.paypal.com/donate/?business=QUPBFLPKAXG3E&no_recurring=0&"
    "item_name=Seu+apoio+ajuda+a+manter+o+projeto+atualizado%2C+corrigir+problemas+e+"
    "desenvolver+novos+recursos.&currency_code=BRL"
)
THEME_COLORS = {
    "light": {
        "window": "#f3f3f3", "surface": "#ffffff", "surface_alt": "#fafafa",
        "border": "#d8d8d8", "text": "#1b1b1b", "muted": "#5d5d5d",
        "accent": "#005fb8", "accent_hover": "#196ebe", "accent_pressed": "#004c94",
        "selection": "#d9ebf7", "control_hover": "#eeeeee", "accent_text": "#ffffff",
        "control_pressed": "#e3e3e3", "progress_trough": "#dfdfdf",
    },
    "dark": {
        "window": "#202020", "surface": "#2b2b2b", "surface_alt": "#323232",
        "border": "#454545", "text": "#f5f5f5", "muted": "#c4c4c4",
        "accent": "#60cdff", "accent_hover": "#75d5ff", "accent_pressed": "#4cc2ff",
        "selection": "#0f4c6a", "control_hover": "#3a3a3a", "accent_text": "#102027",
        "control_pressed": "#454545", "progress_trough": "#414141",
    },
}
TEXT = {
    "en-US": {
        "title": "Similaris", "folder": "Source", "select": "Folder...",
        "select_files": "Files...", "destination": "Destination", "select_destination": "Choose...",
        "selected_files": "{count} files selected", "minimum_files": "Select at least two images to compare.",
        "no_source": "No source selected", "no_destination": "Default destination",
        "theme_system": "System", "theme_light": "Light", "theme_dark": "Dark",
        "home": "Home", "settings": "Settings", "appearance": "Appearance",
        "convert_tab": "Convert", "photos_tab": "Photos", "conversion_title": "File conversion",
        "images_page": "Image organization", "enhance_page": "Image enhancement",
        "images_page_description": "Find duplicates and organize image names safely.",
        "convert_page_description": "Convert photos or videos while preserving the original files.",
        "enhance_page_description": "Increase image resolution locally with Real-ESRGAN.",
        "licenses_tab": "Licenses", "appearance_tab": "Appearance",
        "support_tab": "Support", "support_title": "Support Similaris development",
        "support_message": "Similaris is free and independently developed. If the application has been useful to you, consider making a donation. Your support helps keep the project updated, fix issues, and develop new features.",
        "support_thanks": "Every contribution makes a difference. Thank you for supporting Similaris!",
        "donate": "Make a donation", "open_link_error": "The donation page could not be opened.",
        "start_images": "Start analysis", "start_convert": "Start conversion", "start_enhance": "Start enhancement",
        "language_setting": "Language", "theme_setting": "Application theme",
        "settings_description": "Personalize Similaris. System theme follows Windows or Linux automatically.",
        "images_tab": "Images", "videos_tab": "Video conversion", "duplicates": "Find and separate duplicate images",
        "images": "Convert images to JPG", "videos": "Convert videos to MP4",
        "rename": 'Rename images as "img (N)"',
        "jpg": "JPG quality:", "video": "Video quality (CRF):", "lower": "(lower = better)",
        "sensitivity": "Detection sensitivity:",
        "mode": "Image organization mode", "simulate": "Simulate separating/renaming", "apply": "Apply image changes",
        "start": "Start", "ready": "Ready", "about": "About and licenses",
        "show_details": "Show details", "hide_details": "Hide details",
        "results": "Progress and results", "choose": "Select a folder",
        "invalid_title": "Invalid folder", "invalid": "Select a valid folder.",
        "none_title": "No operation", "none": "Select at least one operation.",
        "confirm_title": "Confirm image changes", "confirm": "Separate duplicates and/or rename images? Conversions preserve their originals.",
        "running": "Processing...", "done": "Completed", "failed": "Completed with errors",
        "done_msg": "Processing completed.", "failed_msg": "Processing ended with an error. See the results.",
        "apply_prompt_title": "Simulation completed",
        "apply_prompt": "{count} duplicate image(s) were found. Apply the separation now?",
        "unexpected": "UNEXPECTED ERROR", "product": "Similaris",
        "conservative": "Conservative", "balanced": "Balanced", "sensitive": "Sensitive",
        "sensitivity_conservative": "Fewer false positives; stricter confirmation.",
        "sensitivity_balanced": "Recommended balance between safety and recall.",
        "sensitivity_sensitive": "Finds more edited copies; review the simulation first.",
        "video_only": "Conversion only — Similaris does not compare videos.",
        "video_details": "Creates an MP4 (H.264/AAC) in the converted folder and preserves the original.",
        "enhance_tab": "Image enhancement", "enhance": "Enhance image resolution locally",
        "enhance_details": "Uses Real-ESRGAN and preserves originals. A Vulkan-compatible GPU is recommended.",
        "scale": "Upscale:", "model": "Image type:", "photo": "Photo", "illustration": "Illustration",
    },
    "pt-BR": {
        "title": "Similaris", "folder": "Origem", "select": "Pasta...",
        "select_files": "Arquivos...", "destination": "Destino", "select_destination": "Escolher...",
        "selected_files": "{count} arquivos selecionados", "minimum_files": "Selecione pelo menos duas imagens para comparar.",
        "no_source": "Nenhuma origem selecionada", "no_destination": "Destino padrão",
        "theme_system": "Sistema", "theme_light": "Claro", "theme_dark": "Escuro",
        "home": "Início", "settings": "Configurações", "appearance": "Aparência",
        "convert_tab": "Converter", "photos_tab": "Fotos", "conversion_title": "Conversão de arquivos",
        "images_page": "Organização de imagens", "enhance_page": "Melhoria de imagens",
        "images_page_description": "Encontre duplicatas e organize nomes de imagens com segurança.",
        "convert_page_description": "Converta fotos ou vídeos preservando os arquivos originais.",
        "enhance_page_description": "Aumente a resolução localmente com o Real-ESRGAN.",
        "licenses_tab": "Licenças", "appearance_tab": "Aparência",
        "support_tab": "Apoie", "support_title": "Apoie o desenvolvimento do Similaris",
        "support_message": "O Similaris é gratuito e desenvolvido de forma independente. Se o aplicativo foi útil para você, considere fazer uma doação. Seu apoio ajuda a manter o projeto atualizado, corrigir problemas e desenvolver novos recursos.",
        "support_thanks": "Qualquer valor faz a diferença. Obrigado por apoiar o Similaris!",
        "donate": "Fazer uma doação", "open_link_error": "Não foi possível abrir a página de doação.",
        "start_images": "Iniciar análise", "start_convert": "Iniciar conversão", "start_enhance": "Iniciar melhoria",
        "language_setting": "Idioma", "theme_setting": "Tema do aplicativo",
        "settings_description": "Personalize o Similaris. O tema Sistema acompanha o Windows ou Linux automaticamente.",
        "images_tab": "Imagens", "videos_tab": "Conversão de vídeos", "duplicates": "Detectar e separar imagens repetidas",
        "images": "Converter imagens para JPG", "videos": "Converter vídeos para MP4",
        "rename": 'Renomear imagens como "img (N)"',
        "jpg": "Qualidade JPG:", "video": "Qualidade do vídeo (CRF):", "lower": "(menor = melhor)",
        "sensitivity": "Sensibilidade da detecção:",
        "mode": "Modo de organização das imagens", "simulate": "Simular separação/renomeação", "apply": "Aplicar alterações nas imagens",
        "start": "Iniciar", "ready": "Pronto", "about": "Sobre e licenças",
        "show_details": "Mostrar detalhes", "hide_details": "Ocultar detalhes",
        "results": "Progresso e resultados", "choose": "Selecione a pasta",
        "invalid_title": "Pasta inválida", "invalid": "Selecione uma pasta válida.",
        "none_title": "Nenhuma operação", "none": "Marque ao menos uma operação.",
        "confirm_title": "Confirmar alterações nas imagens", "confirm": "Deseja separar duplicatas e/ou renomear imagens? As conversões preservam os originais.",
        "running": "Processando...", "done": "Concluído", "failed": "Concluído com erro",
        "done_msg": "Processamento concluído.", "failed_msg": "O processamento terminou com erro. Consulte os resultados.",
        "apply_prompt_title": "Simulação concluída",
        "apply_prompt": "Foram encontradas {count} imagem(ns) duplicada(s). Deseja aplicar a separação agora?",
        "unexpected": "ERRO INESPERADO", "product": "Similaris",
        "conservative": "Conservador", "balanced": "Equilibrado", "sensitive": "Sensível",
        "sensitivity_conservative": "Menos falsos positivos; confirmação mais rigorosa.",
        "sensitivity_balanced": "Equilíbrio recomendado entre segurança e cobertura.",
        "sensitivity_sensitive": "Encontra mais cópias editadas; revise a simulação primeiro.",
        "video_only": "Somente conversão — o Similaris não compara vídeos.",
        "video_details": "Cria um MP4 (H.264/AAC) na pasta converted e preserva o arquivo original.",
        "enhance_tab": "Melhoria de imagens", "enhance": "Melhorar a resolução localmente",
        "enhance_details": "Usa Real-ESRGAN e preserva os originais. Recomenda-se uma GPU compatível com Vulkan.",
        "scale": "Ampliação:", "model": "Tipo de imagem:", "photo": "Fotografia", "illustration": "Ilustração",
    },
    "es-ES": {
        "title": "Similaris", "folder": "Origen", "select": "Carpeta...",
        "select_files": "Archivos...", "destination": "Destino", "select_destination": "Elegir...",
        "selected_files": "{count} archivos seleccionados", "minimum_files": "Seleccione al menos dos imágenes para comparar.",
        "no_source": "Ningún origen seleccionado", "no_destination": "Destino predeterminado",
        "theme_system": "Sistema", "theme_light": "Claro", "theme_dark": "Oscuro",
        "home": "Inicio", "settings": "Configuración", "appearance": "Apariencia",
        "convert_tab": "Convertir", "photos_tab": "Fotos", "conversion_title": "Conversión de archivos",
        "images_page": "Organización de imágenes", "enhance_page": "Mejora de imágenes",
        "images_page_description": "Encuentre duplicados y organice nombres de imágenes con seguridad.",
        "convert_page_description": "Convierta fotos o vídeos conservando los archivos originales.",
        "enhance_page_description": "Aumente la resolución localmente con Real-ESRGAN.",
        "licenses_tab": "Licencias", "appearance_tab": "Apariencia",
        "support_tab": "Apoyar", "support_title": "Apoye el desarrollo de Similaris",
        "support_message": "Similaris es gratuito y se desarrolla de forma independiente. Si la aplicación le ha resultado útil, considere hacer una donación. Su apoyo ayuda a mantener el proyecto actualizado, corregir problemas y desarrollar nuevas funciones.",
        "support_thanks": "Cada contribución marca la diferencia. ¡Gracias por apoyar Similaris!",
        "donate": "Hacer una donación", "open_link_error": "No se pudo abrir la página de donación.",
        "start_images": "Iniciar análisis", "start_convert": "Iniciar conversión", "start_enhance": "Iniciar mejora",
        "language_setting": "Idioma", "theme_setting": "Tema de la aplicación",
        "settings_description": "Personalice Similaris. El tema Sistema sigue Windows o Linux automáticamente.",
        "images_tab": "Imágenes", "videos_tab": "Conversión de vídeos", "duplicates": "Detectar y separar imágenes duplicadas",
        "images": "Convertir imágenes a JPG", "videos": "Convertir vídeos a MP4",
        "rename": 'Renombrar imágenes como "img (N)"',
        "jpg": "Calidad JPG:", "video": "Calidad del vídeo (CRF):", "lower": "(menor = mejor)",
        "sensitivity": "Sensibilidad de detección:",
        "mode": "Modo de organización de imágenes", "simulate": "Simular separación/renombrado", "apply": "Aplicar cambios en imágenes",
        "start": "Iniciar", "ready": "Listo", "about": "Acerca de y licencias",
        "show_details": "Mostrar detalles", "hide_details": "Ocultar detalles",
        "results": "Progreso y resultados", "choose": "Seleccione la carpeta",
        "invalid_title": "Carpeta no válida", "invalid": "Seleccione una carpeta válida.",
        "none_title": "Ninguna operación", "none": "Seleccione al menos una operación.",
        "confirm_title": "Confirmar cambios en imágenes", "confirm": "¿Desea separar duplicados y/o renombrar imágenes? Las conversiones conservan los originales.",
        "running": "Procesando...", "done": "Completado", "failed": "Completado con errores",
        "done_msg": "Procesamiento completado.", "failed_msg": "El procesamiento terminó con un error. Consulte los resultados.",
        "apply_prompt_title": "Simulación completada",
        "apply_prompt": "Se encontraron {count} imagen(es) duplicada(s). ¿Desea aplicar la separación ahora?",
        "unexpected": "ERROR INESPERADO", "product": "Similaris",
        "conservative": "Conservador", "balanced": "Equilibrado", "sensitive": "Sensible",
        "sensitivity_conservative": "Menos falsos positivos; confirmación más estricta.",
        "sensitivity_balanced": "Equilibrio recomendado entre seguridad y cobertura.",
        "sensitivity_sensitive": "Encuentra más copias editadas; revise primero la simulación.",
        "video_only": "Solo conversión — Similaris no compara vídeos.",
        "video_details": "Crea un MP4 (H.264/AAC) en la carpeta converted y conserva el archivo original.",
        "enhance_tab": "Mejora de imágenes", "enhance": "Mejorar la resolución localmente",
        "enhance_details": "Utiliza Real-ESRGAN y conserva los originales. Se recomienda una GPU compatible con Vulkan.",
        "scale": "Ampliación:", "model": "Tipo de imagen:", "photo": "Fotografía", "illustration": "Ilustración",
    },
}


def system_language() -> str:
    language = (locale.getlocale()[0] or "en_US").lower()
    return "pt-BR" if language.startswith("pt") else "es-ES" if language.startswith("es") else "en-US"


def system_theme() -> str:
    """Return the operating system's preferred application theme."""
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            ) as key:
                light_theme, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return "light" if light_theme else "dark"
        except (OSError, ImportError):
            return "light"

    gtk_theme = os.environ.get("GTK_THEME", "").lower()
    if "dark" in gtk_theme:
        return "dark"
    if sys.platform.startswith("linux"):
        for setting in ("color-scheme", "gtk-theme"):
            try:
                result = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", setting],
                    capture_output=True, text=True, timeout=0.5, check=False,
                )
                if result.returncode == 0 and "dark" in result.stdout.lower():
                    return "dark"
            except (OSError, subprocess.SubprocessError):
                break
    return "dark" if sys.platform == "darwin" and os.environ.get("AppleInterfaceStyle") == "Dark" else "light"


class QueueWriter:
    def __init__(self, events: queue.Queue[tuple[str, object]]) -> None:
        self.events = events

    def write(self, value: str) -> int:
        if value:
            self.events.put(("text", value))
            analyzed = re.search(
                r"(\d+)/(\d+)\s+(?:processadas|processed|procesadas)", value,
                re.IGNORECASE,
            )
            compared = re.search(
                r"(?:Comparando imagens|Comparing images|Comparando imágenes).*?"
                r"\((\d+(?:[.,]\d+)?)%\)", value, re.IGNORECASE,
            )
            enhanced = re.search(
                r"(?:Progresso da melhoria|Enhancement progress|Progreso de mejora).*?"
                r"\((\d+(?:[.,]\d+)?)%\)", value, re.IGNORECASE,
            )
            if analyzed:
                completed, total = map(int, analyzed.groups())
                self.events.put(("progress", 30 * completed / max(total, 1)))
            elif compared:
                phase_percent = float(compared.group(1).replace(",", "."))
                self.events.put(("progress", 30 + 0.7 * phase_percent))
            elif enhanced:
                self.events.put(("progress", float(enhanced.group(1).replace(",", "."))))
        return len(value)

    def flush(self) -> None:
        pass


class Application(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.geometry("1000x650")
        self.minsize(760, 520)
        self.theme_mode = "system"
        self.effective_theme = system_theme()
        self.colors = THEME_COLORS[self.effective_theme]
        self.configure(background=self.colors["window"])
        self._configure_style()
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        resource_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        self.logo_image = tk.PhotoImage(file=resource_dir / "assets" / "similaris-icon.png")
        self.header_logo = self.logo_image.subsample(9, 9)
        self.ui_icons = {
            name: tk.PhotoImage(file=resource_dir / "assets" / f"ui-{name}.png")
            for name in ("folder", "images", "video", "sparkle", "play", "terminal", "info")
        }
        self.iconphoto(True, self.logo_image)
        detected = system_language()
        self.language_name = tk.StringVar(value=next(name for name, code in LANGUAGES.items() if code == detected))
        self.theme_name = tk.StringVar()
        self.folder = tk.StringVar()
        self.destination = tk.StringVar()
        self.source_display = tk.StringVar()
        self.destination_display = tk.StringVar()
        operations = ("images", "convert", "enhance")
        self.source_kinds = {operation: "folder" for operation in operations}
        self.source_folders = {operation: "" for operation in operations}
        self.source_files: dict[str, list[Path]] = {operation: [] for operation in operations}
        self.output_folders = {operation: "" for operation in operations}
        self.apply_changes = tk.BooleanVar(value=False)
        self.find_duplicates = tk.BooleanVar(value=True)
        self.convert_images = tk.BooleanVar(value=False)
        self.convert_videos = tk.BooleanVar(value=False)
        self.enhance_images = tk.BooleanVar(value=False)
        self.rename_images = tk.BooleanVar(value=False)
        self.jpg_quality = tk.IntVar(value=92)
        self.video_quality = tk.IntVar(value=20)
        self.sensitivity = tk.StringVar(value="balanced")
        self.enhancement_scale = tk.IntVar(value=2)
        self.enhancement_model = tk.StringVar(value="photo")
        self.widgets: dict[str, tk.Misc] = {}
        self.details_visible = False
        self.processing = False
        self.run_generation = 0
        self._build_ui()
        self._translate()
        self.after_idle(self._update_native_titlebar)
        self.after(100, self._read_events)
        self.after(2000, self._watch_system_theme)

    def _configure_style(self) -> None:
        """Apply a cross-platform Fluent/WinUI-inspired visual language."""
        colors = self.colors
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("TFrame", background=colors["window"])
        style.configure("Card.TFrame", background=colors["surface"])
        style.configure("Sidebar.TFrame", background=colors["surface"], relief="flat")
        style.configure(
            "TLabel", background=colors["window"], foreground=colors["text"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Card.TLabel", background=colors["surface"], foreground=colors["text"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Muted.Card.TLabel", background=colors["surface"], foreground=colors["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "Title.TLabel", background=colors["window"], foreground=colors["accent"],
            font=("Segoe UI Semibold", 22),
        )
        style.configure(
            "Card.TLabelframe", background=colors["surface"], bordercolor=colors["border"],
            borderwidth=1, relief="solid",
        )
        style.configure(
            "Card.TLabelframe.Label", background=colors["surface"], foreground=colors["text"],
            font=("Segoe UI Semibold", 10),
        )
        style.configure(
            "TButton", font=("Segoe UI", 10), padding=(14, 7),
            background=colors["surface_alt"], foreground=colors["text"],
            bordercolor=colors["border"], focuscolor=colors["border"], relief="flat",
        )
        style.map(
            "TButton", background=[("pressed", colors["control_pressed"]), ("active", colors["control_hover"])],
            bordercolor=[("focus", colors["accent"]), ("active", colors["border"])],
        )
        style.configure(
            "Accent.TButton", background=colors["accent"], foreground=colors["accent_text"],
            bordercolor=colors["accent"], font=("Segoe UI Semibold", 10), padding=(18, 8),
        )
        style.map(
            "Accent.TButton",
            background=[("disabled", colors["border"]), ("pressed", colors["accent_pressed"]), ("active", colors["accent_hover"])],
            foreground=[("disabled", "#f4f4f4")],
        )
        style.configure(
            "TEntry", fieldbackground=colors["surface_alt"], foreground=colors["text"],
            bordercolor=colors["border"], lightcolor=colors["border"], darkcolor=colors["border"],
            padding=(10, 7), insertcolor=colors["text"],
        )
        style.map("TEntry", bordercolor=[("focus", colors["accent"])])
        style.configure(
            "TCombobox", fieldbackground=colors["surface_alt"], background=colors["surface_alt"],
            foreground=colors["text"], bordercolor=colors["border"], padding=(8, 6),
            arrowcolor=colors["text"],
        )
        style.map(
            "TCombobox",
            bordercolor=[("focus", colors["accent"])],
            fieldbackground=[("readonly", colors["surface_alt"])],
            background=[("readonly", colors["surface_alt"])],
            foreground=[("readonly", colors["text"])],
            selectbackground=[("readonly", colors["surface_alt"])],
            selectforeground=[("readonly", colors["text"])],
        )
        style.configure(
            "TSpinbox", fieldbackground=colors["surface_alt"], foreground=colors["text"],
            bordercolor=colors["border"], padding=(7, 5), arrowcolor=colors["text"],
        )
        style.configure(
            "TCheckbutton", background=colors["surface"], foreground=colors["text"],
            font=("Segoe UI", 10), padding=(0, 3),
        )
        style.map("TCheckbutton", background=[("active", colors["surface"])])
        style.configure(
            "TRadiobutton", background=colors["surface"], foreground=colors["text"],
            font=("Segoe UI", 10), padding=(0, 3),
        )
        style.map("TRadiobutton", background=[("active", colors["surface"])])
        style.configure("Modern.TNotebook", background=colors["window"], borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure(
            "Modern.TNotebook.Tab", background=colors["window"], foreground=colors["muted"],
            borderwidth=0, padding=(18, 10), font=("Segoe UI Semibold", 10),
        )
        style.map(
            "Modern.TNotebook.Tab",
            background=[("selected", colors["surface"]), ("active", colors["control_hover"])],
            foreground=[("selected", colors["accent"]), ("active", colors["text"])],
        )
        style.configure(
            "Nav.TButton", background=colors["surface"], foreground=colors["muted"],
            borderwidth=0, relief="flat", padding=(16, 9), font=("Segoe UI Semibold", 10),
        )
        style.map(
            "Nav.TButton", background=[("active", colors["control_hover"]), ("pressed", colors["control_pressed"])],
            foreground=[("active", colors["text"])],
        )
        style.configure(
            "Selected.Nav.TButton", background=colors["selection"], foreground=colors["accent"],
            borderwidth=0, relief="flat", padding=(16, 9), font=("Segoe UI Semibold", 10),
        )
        style.map(
            "Selected.Nav.TButton", background=[("active", colors["selection"]), ("pressed", colors["control_pressed"])],
            foreground=[("active", colors["accent_pressed"])],
        )
        style.configure(
            "Sidebar.TButton", background=colors["surface"], foreground=colors["text"],
            borderwidth=0, relief="flat", padding=(14, 11), anchor="w",
            font=("Segoe UI Semibold", 10),
        )
        style.map(
            "Sidebar.TButton",
            background=[("active", colors["control_hover"]), ("pressed", colors["control_pressed"])],
        )
        style.configure(
            "Selected.Sidebar.TButton", background=colors["selection"], foreground=colors["accent"],
            borderwidth=0, relief="flat", padding=(14, 11), anchor="w",
            font=("Segoe UI Semibold", 10),
        )
        style.configure(
            "Accent.Horizontal.TProgressbar", background=colors["accent"],
            troughcolor=colors["progress_trough"], borderwidth=0, thickness=5,
        )
        self.option_add("*TCombobox*Listbox.background", colors["surface_alt"])
        self.option_add("*TCombobox*Listbox.foreground", colors["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", colors["selection"])
        self.option_add("*TCombobox*Listbox.selectForeground", colors["text"])

    @property
    def language(self) -> str:
        return LANGUAGES[self.language_name.get()]

    def tr(self, key: str) -> str:
        return TEXT[self.language][key]

    def _widget(self, key: str, widget: tk.Misc) -> tk.Misc:
        self.widgets[key] = widget
        return widget

    def _build_ui(self) -> None:
        self.sidebar_expanded = True
        self.current_section = "images"
        shell = ttk.Frame(self)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        self.sidebar = ttk.Frame(shell, style="Sidebar.TFrame", width=190)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.sidebar.columnconfigure(0, weight=1)
        self.sidebar.rowconfigure(4, weight=1)
        self.hamburger_button = ttk.Button(
            self.sidebar, text="☰", command=self._toggle_sidebar, style="Sidebar.TButton", width=3,
        )
        self.hamburger_button.grid(row=0, column=0, sticky="ew", padx=4, pady=(6, 10))
        self.section_buttons = {
            "images": ttk.Button(
                self.sidebar, command=lambda: self._show_section("images"),
                style="Selected.Sidebar.TButton", image=self.ui_icons["images"], compound="left",
            ),
            "convert": ttk.Button(
                self.sidebar, command=lambda: self._show_section("convert"),
                style="Sidebar.TButton", image=self.ui_icons["video"], compound="left",
            ),
            "enhance": ttk.Button(
                self.sidebar, command=lambda: self._show_section("enhance"),
                style="Sidebar.TButton", image=self.ui_icons["sparkle"], compound="left",
            ),
            "settings": ttk.Button(
                self.sidebar, command=lambda: self._show_section("settings"),
                style="Sidebar.TButton", text="⚙", compound="left",
            ),
        }
        self.section_buttons["images"].grid(row=1, column=0, sticky="ew", padx=4, pady=2)
        self.section_buttons["convert"].grid(row=2, column=0, sticky="ew", padx=4, pady=2)
        self.section_buttons["enhance"].grid(row=3, column=0, sticky="ew", padx=4, pady=2)
        self.section_buttons["settings"].grid(row=5, column=0, sticky="ew", padx=4, pady=2)

        page_host = ttk.Frame(shell)
        page_host.grid(row=0, column=1, sticky="nsew")
        page_host.columnconfigure(0, weight=1)
        page_host.rowconfigure(0, weight=1)
        home = ttk.Frame(page_host, padding=(22, 16, 22, 18))
        settings = ttk.Frame(page_host, padding=(28, 22, 28, 24))
        self.section_pages = {"home": home, "settings": settings}
        for page in self.section_pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        self.main_frame = home
        home.columnconfigure(0, weight=1)
        home.rowconfigure(4, weight=1)
        header = ttk.Frame(home)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.page_icon = ttk.Label(header, image=self.ui_icons["images"])
        self.page_icon.pack(side="left", padx=(0, 12))
        heading_text = ttk.Frame(header)
        heading_text.pack(side="left", fill="x", expand=True)
        self.page_title = ttk.Label(heading_text, style="Title.TLabel")
        self.page_title.pack(anchor="w")
        self.page_description = ttk.Label(heading_text)
        self.page_description.pack(anchor="w", pady=(2, 0))

        self.selection_area = ttk.Frame(home)
        self.selection_area.grid(row=1, column=0, sticky="ew")
        self.source_card = self._widget(
            "folder", ttk.LabelFrame(self.selection_area, padding=12, style="Card.TLabelframe")
        )
        self.source_summary = ttk.Label(
            self.source_card, textvariable=self.source_display, style="Muted.Card.TLabel",
            anchor="w", width=42,
        )
        self.source_summary.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.source_card.columnconfigure(0, weight=1)
        self._widget(
            "select", ttk.Button(
                self.source_card, command=self._select_folder, image=self.ui_icons["folder"],
                compound="left",
            )
        ).grid(row=1, column=0, sticky="w", padx=(0, 6))
        self._widget(
            "select_files", ttk.Button(
                self.source_card, command=self._select_files,
                image=self.ui_icons["images"], compound="left",
            )
        ).grid(row=1, column=1, sticky="w")

        self.destination_card = self._widget(
            "destination", ttk.LabelFrame(
                self.selection_area, padding=12, style="Card.TLabelframe"
            )
        )
        self.destination_summary = ttk.Label(
            self.destination_card, textvariable=self.destination_display,
            style="Muted.Card.TLabel", anchor="w", width=30,
        )
        self.destination_summary.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.destination_card.columnconfigure(0, weight=1)
        self._widget(
            "select_destination", ttk.Button(
                self.destination_card, command=self._select_destination,
                image=self.ui_icons["folder"], compound="left",
            )
        ).grid(row=1, column=0, sticky="w")
        self._layout_selection(False)

        operations_shell = ttk.Frame(home, style="Card.TFrame")
        operations_shell.grid(row=2, column=0, sticky="ew", pady=10)
        operations_shell.columnconfigure(0, weight=1)
        page_container = ttk.Frame(operations_shell, style="Card.TFrame")
        page_container.grid(row=0, column=0, sticky="ew")
        page_container.columnconfigure(0, weight=1)
        self.images_tab = ttk.Frame(page_container, padding=18, style="Card.TFrame")
        self.convert_tab = ttk.Frame(page_container, padding=0, style="Card.TFrame")
        self.enhance_tab = ttk.Frame(page_container, padding=18, style="Card.TFrame")
        self.operation_pages = {
            "images": self.images_tab, "convert": self.convert_tab, "enhance": self.enhance_tab,
        }
        for page in self.operation_pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self.current_operation = "images"
        self._show_operation(self.current_operation)

        self._widget("duplicates", ttk.Checkbutton(self.images_tab, variable=self.find_duplicates)).grid(row=0, column=0, sticky="w")
        self._widget("rename", ttk.Checkbutton(self.images_tab, variable=self.rename_images)).grid(row=0, column=1, sticky="w", padx=(35, 0))
        sensitivity = ttk.Frame(self.images_tab, style="Card.TFrame")
        sensitivity.grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self._widget("sensitivity", ttk.Label(sensitivity, style="Card.TLabel")).pack(side="left")
        self.sensitivity_box = ttk.Combobox(sensitivity, state="readonly", width=16)
        self.sensitivity_box.pack(side="left", padx=5)
        self.sensitivity_box.bind("<<ComboboxSelected>>", self._sensitivity_selected)
        self.sensitivity_help = ttk.Label(sensitivity, style="Muted.Card.TLabel")
        self.sensitivity_help.pack(side="left", padx=(8, 0))

        conversion_navigation = ttk.Frame(self.convert_tab, style="Card.TFrame", padding=(8, 7))
        conversion_navigation.grid(row=0, column=0, sticky="ew")
        self.conversion_buttons: dict[str, ttk.Button] = {}
        for column, page in enumerate(("photos", "videos")):
            button = ttk.Button(
                conversion_navigation, style="Nav.TButton",
                image=self.ui_icons["images" if page == "photos" else "video"], compound="left",
                command=lambda selected=page: self._show_conversion_tab(selected),
            )
            button.grid(row=0, column=column, padx=(0, 4))
            self.conversion_buttons[page] = button
        ttk.Separator(self.convert_tab).grid(row=1, column=0, sticky="ew")
        conversion_pages = ttk.Frame(self.convert_tab, style="Card.TFrame")
        conversion_pages.grid(row=2, column=0, sticky="ew")
        self.photo_conversion_tab = ttk.Frame(conversion_pages, padding=18, style="Card.TFrame")
        self.video_conversion_tab = ttk.Frame(conversion_pages, padding=18, style="Card.TFrame")
        self.conversion_pages = {"photos": self.photo_conversion_tab, "videos": self.video_conversion_tab}
        for page in self.conversion_pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self.current_conversion_tab = "photos"
        self._show_conversion_tab("photos")

        self._widget("images", ttk.Checkbutton(self.photo_conversion_tab, variable=self.convert_images)).grid(row=0, column=0, sticky="w")
        image_quality = ttk.Frame(self.photo_conversion_tab, style="Card.TFrame")
        image_quality.grid(row=1, column=0, sticky="w", pady=(12, 0))
        self._widget("jpg", ttk.Label(image_quality, style="Card.TLabel")).pack(side="left")
        ttk.Spinbox(image_quality, from_=1, to=100, width=5, textvariable=self.jpg_quality).pack(side="left", padx=5)

        self._widget("video_only", ttk.Label(self.video_conversion_tab, style="Card.TLabel", font=("Segoe UI Semibold", 11))).grid(row=0, column=0, sticky="w")
        self._widget("video_details", ttk.Label(self.video_conversion_tab, wraplength=700, style="Muted.Card.TLabel")).grid(row=1, column=0, sticky="w", pady=(4, 12))
        self._widget("videos", ttk.Checkbutton(self.video_conversion_tab, variable=self.convert_videos)).grid(row=2, column=0, sticky="w")
        video_quality = ttk.Frame(self.video_conversion_tab, style="Card.TFrame")
        video_quality.grid(row=3, column=0, sticky="w", pady=(12, 0))
        self._widget("video", ttk.Label(video_quality, style="Card.TLabel")).pack(side="left")
        ttk.Spinbox(video_quality, from_=0, to=51, width=5, textvariable=self.video_quality).pack(side="left", padx=5)
        self._widget("lower", ttk.Label(video_quality, style="Muted.Card.TLabel")).pack(side="left")

        self._widget("enhance_details", ttk.Label(self.enhance_tab, wraplength=760, style="Muted.Card.TLabel")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        self._widget("enhance", ttk.Checkbutton(self.enhance_tab, variable=self.enhance_images)).grid(row=1, column=0, columnspan=2, sticky="w")
        enhance_options = ttk.Frame(self.enhance_tab, style="Card.TFrame")
        enhance_options.grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self._widget("scale", ttk.Label(enhance_options, style="Card.TLabel")).pack(side="left")
        ttk.Combobox(enhance_options, textvariable=self.enhancement_scale, values=(2, 3, 4), state="readonly", width=4).pack(side="left", padx=(5, 24))
        self._widget("model", ttk.Label(enhance_options, style="Card.TLabel")).pack(side="left")
        self.enhancement_model_box = ttk.Combobox(enhance_options, state="readonly", width=16)
        self.enhancement_model_box.pack(side="left", padx=5)
        self.enhancement_model_box.bind("<<ComboboxSelected>>", self._enhancement_model_selected)

        mode = self._widget("mode", ttk.LabelFrame(self.images_tab, padding=12, style="Card.TLabelframe"))
        mode.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self._widget("simulate", ttk.Radiobutton(mode, variable=self.apply_changes, value=False)).pack(side="left")
        self._widget("apply", ttk.Radiobutton(mode, variable=self.apply_changes, value=True)).pack(side="left", padx=25)
        self.action_bar = ttk.Frame(home)
        self.action_bar.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.action_bar.columnconfigure(1, weight=1)
        self.start_button = self._widget(
            "start", ttk.Button(
                self.action_bar, command=self._start, style="Accent.TButton",
                image=self.ui_icons["play"], compound="left",
            )
        )
        self.progress = ttk.Progressbar(self.action_bar, mode="determinate", maximum=100, value=0, style="Accent.Horizontal.TProgressbar")
        self.progress_percent = ttk.Label(self.action_bar, text="—", width=5, anchor="e")
        self.status = ttk.Label(self.action_bar)
        self.details_button = ttk.Button(
            self.action_bar, command=self._toggle_details, image=self.ui_icons["terminal"], compound="left"
        )
        self._layout_actions(True)

        self.results_box = self._widget("results", ttk.LabelFrame(home, padding=8, style="Card.TLabelframe"))
        self.results_box.grid(row=4, column=0, sticky="nsew")
        self.results_box.columnconfigure(0, weight=1)
        self.results_box.rowconfigure(0, weight=1)
        self.log = tk.Text(
            self.results_box, wrap="word", state="disabled", font=("Cascadia Mono", 9),
            background=self.colors["surface_alt"], foreground=self.colors["text"],
            selectbackground=self.colors["selection"], selectforeground=self.colors["text"],
            borderwidth=0, highlightthickness=0, padx=12, pady=10,
        )
        scrollbar = ttk.Scrollbar(self.results_box, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_box.grid_remove()
        home.rowconfigure(4, weight=0)

        settings.columnconfigure(0, weight=1)
        self._widget("settings", ttk.Label(settings, style="Title.TLabel")).grid(row=0, column=0, sticky="w")
        self._widget("settings_description", ttk.Label(settings, wraplength=650)).grid(row=1, column=0, sticky="w", pady=(4, 18))
        settings_navigation = ttk.Frame(settings)
        settings_navigation.grid(row=2, column=0, sticky="ew", pady=(0, 1))
        self.settings_tab_buttons = {}
        for column, tab in enumerate(("appearance", "licenses", "support")):
            button = ttk.Button(
                settings_navigation, style="Nav.TButton",
                command=lambda selected=tab: self._show_settings_tab(selected),
            )
            button.grid(row=0, column=column, padx=(0, 4))
            self.settings_tab_buttons[tab] = button
        settings_content = ttk.Frame(settings, style="Card.TFrame")
        settings_content.grid(row=3, column=0, sticky="nsew")
        settings.rowconfigure(3, weight=1)
        settings_content.columnconfigure(0, weight=1)
        settings_content.rowconfigure(0, weight=1)
        appearance = ttk.Frame(settings_content, padding=18, style="Card.TFrame")
        licenses = ttk.Frame(settings_content, padding=12, style="Card.TFrame")
        support = ttk.Frame(settings_content, padding=24, style="Card.TFrame")
        self.settings_tab_pages = {
            "appearance": appearance, "licenses": licenses, "support": support,
        }
        for page in self.settings_tab_pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        appearance.columnconfigure(1, weight=1)
        self._widget("theme_setting", ttk.Label(appearance, style="Card.TLabel")).grid(row=0, column=0, sticky="w", padx=(0, 25), pady=(0, 14))
        self.theme_box = ttk.Combobox(appearance, textvariable=self.theme_name, state="readonly", width=24)
        self.theme_box.grid(row=0, column=1, sticky="w", pady=(0, 14))
        self.theme_box.bind("<<ComboboxSelected>>", self._theme_selected)
        self._widget("language_setting", ttk.Label(appearance, style="Card.TLabel")).grid(row=1, column=0, sticky="w", padx=(0, 25))
        self.language_box = ttk.Combobox(
            appearance, textvariable=self.language_name, values=list(LANGUAGES), state="readonly", width=24,
        )
        self.language_box.grid(row=1, column=1, sticky="w")
        self.language_name.trace_add("write", lambda *_: self._translate())

        licenses.columnconfigure(0, weight=1)
        licenses.rowconfigure(0, weight=1)
        self.license_text = tk.Text(
            licenses, wrap="word", padx=14, pady=12, state="normal",
            background=self.colors["surface_alt"], foreground=self.colors["text"],
            selectbackground=self.colors["selection"], selectforeground=self.colors["text"],
            borderwidth=0, highlightthickness=0,
        )
        license_scrollbar = ttk.Scrollbar(licenses, orient="vertical", command=self.license_text.yview)
        self.license_text.configure(yscrollcommand=license_scrollbar.set)
        self.license_text.grid(row=0, column=0, sticky="nsew")
        license_scrollbar.grid(row=0, column=1, sticky="ns")
        self.license_text.insert("1.0", self._license_content())
        self.license_text.configure(state="disabled")

        support.columnconfigure(0, weight=1)
        self._widget(
            "support_title", ttk.Label(
                support, style="Card.TLabel", font=("Segoe UI Semibold", 16),
            )
        ).grid(row=0, column=0, sticky="w")
        self._widget(
            "support_message", ttk.Label(
                support, style="Card.TLabel", wraplength=680, justify="left",
            )
        ).grid(row=1, column=0, sticky="w", pady=(14, 18))
        self._widget(
            "support_thanks", ttk.Label(
                support, style="Card.TLabel", font=("Segoe UI Semibold", 10),
                wraplength=680, justify="left",
            )
        ).grid(row=2, column=0, sticky="w", pady=(0, 22))
        self._widget(
            "donate", ttk.Button(
                support, command=self._open_support_page, style="Accent.TButton",
            )
        ).grid(row=3, column=0, sticky="w")
        self.current_settings_tab = "appearance"
        self._show_settings_tab("appearance")

        self._show_section("images")
        self.bind("<Configure>", self._on_window_resize)

    def _translate(self) -> None:
        self.title(self.tr("title"))
        for key, widget in self.widgets.items():
            widget.configure(text=self.tr(key))
        self.conversion_buttons["photos"].configure(text=self.tr("photos_tab"))
        self.conversion_buttons["videos"].configure(text=self.tr("videos_tab"))
        self.settings_tab_buttons["appearance"].configure(text=self.tr("appearance_tab"))
        self.settings_tab_buttons["licenses"].configure(text=self.tr("licenses_tab"))
        self.settings_tab_buttons["support"].configure(text=self.tr("support_tab"))
        sensitivity_values = [self.tr(name) for name in ("conservative", "balanced", "sensitive")]
        self.sensitivity_box.configure(values=sensitivity_values)
        self.sensitivity_box.current(("conservative", "balanced", "sensitive").index(self.sensitivity.get()))
        self.sensitivity_help.configure(text=self.tr(f"sensitivity_{self.sensitivity.get()}"))
        enhancement_models = [self.tr(name) for name in ("photo", "illustration")]
        self.enhancement_model_box.configure(values=enhancement_models)
        self.enhancement_model_box.current(("photo", "illustration").index(self.enhancement_model.get()))
        self.details_button.configure(text=self.tr("hide_details" if self.details_visible else "show_details"))
        self._set_sidebar(self.sidebar_expanded)
        theme_modes = ("system", "light", "dark")
        self.theme_box.configure(values=[self.tr(f"theme_{mode}") for mode in theme_modes])
        self.theme_box.current(theme_modes.index(self.theme_mode))
        self._update_page_header()
        if self.start_button.instate(["disabled"]):
            self.status.configure(text=self.tr("running"))
        else:
            self.status.configure(text=self.tr("ready"))
        if self.current_section in {"images", "convert", "enhance"}:
            self._load_source_state()

    def _theme_selected(self, _event: object = None) -> None:
        self.theme_mode = ("system", "light", "dark")[self.theme_box.current()]
        self._apply_theme()

    def _apply_theme(self) -> None:
        effective = system_theme() if self.theme_mode == "system" else self.theme_mode
        if effective == self.effective_theme and self.log.cget("background") == self.colors["surface_alt"]:
            return
        self.effective_theme = effective
        self.colors = THEME_COLORS[effective]
        self.configure(background=self.colors["window"])
        self._configure_style()
        self.log.configure(
            background=self.colors["surface_alt"], foreground=self.colors["text"],
            selectbackground=self.colors["selection"], selectforeground=self.colors["text"],
            insertbackground=self.colors["text"],
        )
        self.license_text.configure(
            background=self.colors["surface_alt"], foreground=self.colors["text"],
            selectbackground=self.colors["selection"], selectforeground=self.colors["text"],
            insertbackground=self.colors["text"],
        )
        self.after_idle(self._update_native_titlebar)

    def _update_native_titlebar(self) -> None:
        """Keep the Windows frame synchronized with the application theme."""
        if sys.platform != "win32":
            return
        try:
            import ctypes

            self.update_idletasks()
            child = self.winfo_id()
            hwnd = ctypes.windll.user32.GetParent(child) or child
            enabled = ctypes.c_int(1 if self.effective_theme == "dark" else 0)
            for attribute in (20, 19):
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled)
                ) == 0:
                    break
            color = self.colors["window"].lstrip("#")
            red, green, blue = (int(color[index:index + 2], 16) for index in (0, 2, 4))
            caption_color = ctypes.c_int(red | (green << 8) | (blue << 16))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color)
            )
        except (AttributeError, OSError, ValueError):
            pass

    def _watch_system_theme(self) -> None:
        if self.theme_mode == "system" and system_theme() != self.effective_theme:
            self._apply_theme()
        self.after(2000, self._watch_system_theme)

    def _select_folder(self) -> None:
        selected = filedialog.askdirectory(title=self.tr("choose"))
        if selected:
            self.source_kinds[self.current_operation] = "folder"
            self.source_folders[self.current_operation] = selected
            self.folder.set(selected)
            if not self.destination.get():
                self.destination.set(str(Path(selected) / self._default_output_name()))
            self._save_source_state()
            self._refresh_selection_summaries()

    def _select_files(self) -> None:
        image_patterns = " ".join(f"*{extension}" for extension in sorted(photo_organizer.IMAGE_EXTENSIONS))
        video_patterns = " ".join(f"*{extension}" for extension in sorted(photo_organizer.VIDEO_EXTENSIONS))
        if self.current_operation == "convert":
            filetypes = [
                (self.tr("photos_tab"), image_patterns),
                (self.tr("videos_tab"), video_patterns),
                ("All files", "*.*"),
            ]
        else:
            filetypes = [(self.tr("images_tab"), image_patterns), ("All files", "*.*")]
        selected = [Path(path) for path in filedialog.askopenfilenames(filetypes=filetypes)]
        if not selected:
            return
        if self.current_operation == "images" and len(selected) < 2:
            messagebox.showwarning(self.tr("none_title"), self.tr("minimum_files"))
            return
        self.source_kinds[self.current_operation] = "files"
        self.source_files[self.current_operation] = selected
        if not self.destination.get():
            self.destination.set(str(selected[0].parent / self._default_output_name()))
        self._save_source_state()
        self._refresh_selection_summaries()

    def _select_destination(self) -> None:
        selected = filedialog.askdirectory(title=self.tr("select_destination"))
        if selected:
            self.destination.set(selected)
            self.output_folders[self.current_operation] = selected
            self._refresh_selection_summaries()

    def _default_output_name(self) -> str:
        return {"images": "duplicates", "convert": "converted", "enhance": "enhanced"}[
            self.current_operation
        ]

    def _save_source_state(self) -> None:
        if not hasattr(self, "current_operation") or self.current_operation not in self.source_kinds:
            return
        if self.source_kinds[self.current_operation] == "folder":
            self.source_folders[self.current_operation] = self.folder.get()
        self.output_folders[self.current_operation] = self.destination.get()

    def _load_source_state(self) -> None:
        operation = self.current_operation
        if self.source_kinds[operation] == "files":
            self.folder.set("")
        else:
            self.folder.set(self.source_folders[operation])
        self.destination.set(self.output_folders[operation])
        self._refresh_selection_summaries()

    @staticmethod
    def _compact_path(value: str, limit: int = 58) -> str:
        if len(value) <= limit:
            return value
        return f"…{value[-(limit - 1):]}"

    def _refresh_selection_summaries(self) -> None:
        operation = self.current_operation
        if self.source_kinds[operation] == "files":
            files = self.source_files[operation]
            names = ", ".join(path.name for path in files[:2])
            if len(files) > 2:
                names += ", …"
            source = f"{self.tr('selected_files').format(count=len(files))}  ·  {names}"
        else:
            source = self.source_folders[operation]
        self.source_display.set(self._compact_path(source) if source else self.tr("no_source"))
        destination = self.output_folders[operation]
        self.destination_display.set(
            self._compact_path(destination) if destination else self.tr("no_destination")
        )

    def _show_section(self, section: str) -> None:
        self._save_source_state()
        self.current_section = section
        if section == "settings":
            self.section_pages["settings"].tkraise()
        else:
            self.section_pages["home"].tkraise()
            self._show_operation(section)
            self._load_source_state()
        for name, button in self.section_buttons.items():
            button.configure(style="Selected.Sidebar.TButton" if name == section else "Sidebar.TButton")

    def _set_sidebar(self, expanded: bool) -> None:
        self.sidebar_expanded = expanded
        self.sidebar.configure(width=190 if expanded else 56)
        self.section_buttons["images"].configure(text=self.tr("images_tab") if expanded else "", compound="left")
        self.section_buttons["convert"].configure(text=self.tr("convert_tab") if expanded else "", compound="left")
        self.section_buttons["enhance"].configure(text=self.tr("enhance_tab") if expanded else "", compound="left")
        self.section_buttons["settings"].configure(
            text=f"⚙  {self.tr('settings')}" if expanded else "⚙", image="",
        )

    def _toggle_sidebar(self) -> None:
        self._set_sidebar(not self.sidebar_expanded)

    def _layout_actions(self, compact: bool) -> None:
        for widget in (
            self.start_button, self.progress, self.progress_percent, self.status,
            self.details_button,
        ):
            widget.grid_forget()
        self.start_button.grid(row=0, column=0, sticky="w")
        self.progress.grid(row=0, column=1, sticky="ew", padx=(14, 6))
        self.progress_percent.grid(row=0, column=2, sticky="e")
        self.status.grid(row=0, column=3, sticky="w", padx=(8, 12))
        self.details_button.grid(row=0, column=4, sticky="e")
        self.details_button.configure(
            text="" if compact else self.tr("hide_details" if self.details_visible else "show_details"),
            width=3 if compact else 15,
        )

    def _layout_selection(self, compact: bool) -> None:
        self.source_card.grid_forget()
        self.destination_card.grid_forget()
        if compact:
            self.selection_area.columnconfigure(0, weight=1)
            self.selection_area.columnconfigure(1, weight=0)
            self.source_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
            self.destination_card.grid(row=1, column=0, sticky="ew")
        else:
            self.selection_area.columnconfigure(0, weight=3)
            self.selection_area.columnconfigure(1, weight=2)
            self.source_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            self.destination_card.grid(row=0, column=1, sticky="nsew")

    def _on_window_resize(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        compact = event.width < 900
        if compact and self.sidebar_expanded:
            self._set_sidebar(False)
        self._layout_selection(event.width < 800)
        self._layout_actions(event.width < 820)

    def _show_operation(self, page: str) -> None:
        self.current_operation = page
        self.operation_pages[page].tkraise()
        self._update_page_header()

    def _update_page_header(self) -> None:
        titles = {
            "images": "images_page", "convert": "conversion_title", "enhance": "enhance_page",
        }
        descriptions = {
            "images": "images_page_description", "convert": "convert_page_description",
            "enhance": "enhance_page_description",
        }
        icons = {"images": "images", "convert": "video", "enhance": "sparkle"}
        if hasattr(self, "page_title") and self.current_operation in titles:
            self.page_title.configure(text=self.tr(titles[self.current_operation]))
            self.page_description.configure(text=self.tr(descriptions[self.current_operation]))
            self.page_icon.configure(image=self.ui_icons[icons[self.current_operation]])
            if hasattr(self, "start_button"):
                self.start_button.configure(text=self.tr(f"start_{self.current_operation}"))

    def _show_settings_tab(self, tab: str) -> None:
        self.current_settings_tab = tab
        self.settings_tab_pages[tab].tkraise()
        for name, button in self.settings_tab_buttons.items():
            button.configure(style="Selected.Nav.TButton" if name == tab else "Nav.TButton")

    def _open_support_page(self) -> None:
        try:
            opened = webbrowser.open_new_tab(SUPPORT_URL)
        except webbrowser.Error:
            opened = False
        if not opened:
            messagebox.showerror(self.tr("product"), self.tr("open_link_error"))

    def _show_conversion_tab(self, page: str) -> None:
        self.current_conversion_tab = page
        self.conversion_pages[page].tkraise()
        for name, button in self.conversion_buttons.items():
            button.configure(style="Selected.Nav.TButton" if name == page else "Nav.TButton")

    def _toggle_details(self) -> None:
        self.details_visible = not self.details_visible
        if self.details_visible:
            self.main_frame.rowconfigure(4, weight=1, minsize=120)
            self.results_box.grid()
        else:
            self.results_box.grid_remove()
            self.main_frame.rowconfigure(4, weight=0, minsize=0)
        self.details_button.configure(
            text="" if self.winfo_width() < 820 else self.tr("hide_details" if self.details_visible else "show_details")
        )

    def _sensitivity_selected(self, _event: object = None) -> None:
        self.sensitivity.set(("conservative", "balanced", "sensitive")[self.sensitivity_box.current()])
        self.sensitivity_help.configure(text=self.tr(f"sensitivity_{self.sensitivity.get()}"))

    def _enhancement_model_selected(self, _event: object = None) -> None:
        self.enhancement_model.set(("photo", "illustration")[self.enhancement_model_box.current()])

    def _about(self) -> None:
        window = tk.Toplevel(self)
        window.configure(background=self.colors["window"])
        window.title(self.tr("about"))
        window.geometry("680x480")
        text = tk.Text(
            window, wrap="word", padx=12, pady=12,
            background=self.colors["surface_alt"], foreground=self.colors["text"],
            selectbackground=self.colors["selection"], selectforeground=self.colors["text"],
            insertbackground=self.colors["text"], borderwidth=0,
        )
        text.pack(fill="both", expand=True)
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        parts = [self.tr("title") + "\n\n"]
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.txt", "REALESRGAN-LICENSE.txt", "GPL-3.0.txt"):
            file = base / name
            if file.is_file():
                parts.extend((file.read_text(encoding="utf-8", errors="replace"), "\n\n"))
        text.insert("1.0", "".join(parts))
        text.configure(state="disabled")

    def _license_content(self) -> str:
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        parts = []
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.txt", "REALESRGAN-LICENSE.txt", "GPL-3.0.txt"):
            file = base / name
            if file.is_file():
                parts.extend((f"{name}\n{'=' * len(name)}\n\n", file.read_text(encoding="utf-8", errors="replace"), "\n\n"))
        return "".join(parts)

    def _arguments(self) -> list[str]:
        self._save_source_state()
        selected = self.source_files[self.current_operation]
        if self.source_kinds[self.current_operation] == "files":
            base_folder = selected[0].parent
        else:
            base_folder = Path(self.source_folders[self.current_operation])
        arguments = [str(base_folder)]
        if self.source_kinds[self.current_operation] == "files":
            arguments.extend(("--files", *(str(path) for path in selected)))
        if self.output_folders[self.current_operation]:
            arguments.extend(("--output-folder", self.output_folders[self.current_operation]))
        if self.current_operation == "images":
            if self.apply_changes.get(): arguments.append("--apply")
            if not self.find_duplicates.get(): arguments.append("--skip-duplicates")
            if self.rename_images.get(): arguments.append("--rename")
        elif self.current_operation == "convert":
            if self.convert_images.get(): arguments.append("--convert-images")
            if self.convert_videos.get(): arguments.append("--convert-videos")
            arguments.extend(("--skip-duplicates", "--convert-only"))
        elif self.current_operation == "enhance":
            if self.enhance_images.get(): arguments.append("--enhance-images")
            arguments.extend(("--skip-duplicates", "--enhance-only"))
        arguments += ["--jpg-quality", str(self.jpg_quality.get()), "--video-quality", str(self.video_quality.get())]
        arguments += ["--language", self.language]
        arguments += ["--sensitivity", self.sensitivity.get()]
        arguments += ["--enhancement-scale", str(self.enhancement_scale.get())]
        arguments += ["--enhancement-model", self.enhancement_model.get()]
        return arguments

    def _start(self, skip_confirmation: bool = False, cached_apply_only: bool = False) -> None:
        self._save_source_state()
        source_kind = self.source_kinds[self.current_operation]
        selected_files = self.source_files[self.current_operation]
        if source_kind == "folder":
            folder = Path(self.source_folders[self.current_operation]).expanduser()
            if not folder.is_dir():
                messagebox.showerror(self.tr("invalid_title"), self.tr("invalid")); return
            if self.current_operation == "images":
                candidates = [
                    path for path in folder.iterdir()
                    if path.is_file() and path.suffix.lower() in photo_organizer.IMAGE_EXTENSIONS
                ]
                if len(candidates) < 2:
                    messagebox.showwarning(self.tr("none_title"), self.tr("minimum_files")); return
        else:
            if not selected_files or any(not path.is_file() for path in selected_files):
                messagebox.showerror(self.tr("invalid_title"), self.tr("invalid")); return
            if self.current_operation == "images" and len(selected_files) < 2:
                messagebox.showwarning(self.tr("none_title"), self.tr("minimum_files")); return
        if not self.output_folders[self.current_operation]:
            base = folder if source_kind == "folder" else selected_files[0].parent
            default_destination = str(base / self._default_output_name())
            self.output_folders[self.current_operation] = default_destination
            self.destination.set(default_destination)
            self._refresh_selection_summaries()
        selected_operation = {
            "images": self.find_duplicates.get() or self.rename_images.get(),
            "convert": self.convert_images.get() or self.convert_videos.get(),
            "enhance": self.enhance_images.get(),
        }[self.current_operation]
        if not selected_operation:
            messagebox.showwarning(self.tr("none_title"), self.tr("none")); return
        changes_images = self.current_operation == "images" and self.apply_changes.get()
        if changes_images and not skip_confirmation and not messagebox.askyesno(self.tr("confirm_title"), self.tr("confirm")): return
        self.log.configure(state="normal"); self.log.delete("1.0", "end"); self.log.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.progress.configure(mode="indeterminate", value=0); self.progress.start(10)
        self.progress_percent.configure(text="—")
        self.status.configure(text=self.tr("running"))
        self.processing = True
        self.run_generation += 1
        self.run_started_at = time.monotonic()
        self._update_elapsed_status(self.run_generation)
        arguments = self._arguments()
        if cached_apply_only:
            arguments = [
                argument for argument in arguments
                if argument not in {"--convert-images", "--convert-videos", "--enhance-images"}
            ]
        offer_apply = self.current_operation == "images" and "--apply" not in arguments and "--skip-duplicates" not in arguments
        threading.Thread(target=self._run, args=(arguments, offer_apply), daemon=True).start()

    def _run(self, arguments: list[str], offer_apply: bool) -> None:
        writer = QueueWriter(self.events)
        try:
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                code = photo_organizer.main(arguments)
            duplicate_count = 0
            plan = photo_organizer._LAST_DUPLICATE_PLAN
            if code == 0 and offer_apply and plan is not None:
                duplicate_count = sum(len(group) - 1 for group in plan.groups)
            self.events.put(("done", (code, duplicate_count)))
        except Exception:
            self.events.put(("text", f"\n{self.tr('unexpected')}:\n{traceback.format_exc()}")); self.events.put(("done", (1, 0)))

    def _update_elapsed_status(self, generation: int) -> None:
        if not self.processing or generation != self.run_generation:
            return
        elapsed = max(0, int(time.monotonic() - self.run_started_at))
        minutes, seconds = divmod(elapsed, 60)
        self.status.configure(text=f"{self.tr('running')} · {minutes:02d}:{seconds:02d}")
        self.after(1000, lambda: self._update_elapsed_status(generation))

    def _read_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "text":
                    self.log.configure(state="normal"); self.log.insert("end", str(value)); self.log.see("end"); self.log.configure(state="disabled")
                elif event == "progress":
                    percentage = max(0.0, min(100.0, float(value)))
                    self.progress.stop()
                    self.progress.configure(mode="determinate", value=percentage)
                    self.progress_percent.configure(text=f"{percentage:.0f}%")
                elif event == "done":
                    self.progress.stop(); self.start_button.configure(state="normal")
                    self.processing = False
                    code, duplicate_count = value
                    success = int(code) == 0
                    if success:
                        self.progress.configure(mode="determinate", value=100)
                        self.progress_percent.configure(text="100%")
                    self.status.configure(text=self.tr("done" if success else "failed"))
                    if success and duplicate_count:
                        apply_now = messagebox.askyesno(
                            self.tr("apply_prompt_title"),
                            self.tr("apply_prompt").format(count=duplicate_count),
                        )
                        if apply_now:
                            self._show_section("images")
                            self.apply_changes.set(True)
                            self.after(0, lambda: self._start(True, True))
                    else:
                        (messagebox.showinfo if success else messagebox.showerror)(
                            self.tr("product"), self.tr("done_msg" if success else "failed_msg")
                        )
        except queue.Empty:
            pass
        self.after(100, self._read_events)


if __name__ == "__main__":
    Application().mainloop()
