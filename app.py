#!/usr/bin/env python3
"""Cross-platform, multilingual graphical interface for Photo Organizer."""

from __future__ import annotations

import contextlib
import locale
import math
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
from typing import Callable
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
        "window": "#0f1115", "surface": "#1b1f27", "surface_alt": "#20252f",
        "border": "#2c3440", "text": "#f4f7fb", "muted": "#a7b0be",
        "accent": "#2ea8ff", "accent_hover": "#249ceb", "accent_pressed": "#168bd2",
        "selection": "#183a52", "control_hover": "#252c37", "accent_text": "#ffffff",
        "control_pressed": "#2c3440", "progress_trough": "#252c35",
        "disabled": "#667080", "success": "#22c55e", "warning": "#f59e0b",
        "error": "#ef4444", "sidebar": "#151820", "elevated": "#20252f",
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

TEXT["en-US"].update({
    "images_page_description": "Find duplicate images, standardize filenames, and safely organize your library.",
    "convert_page_description": "Convert images and videos while preserving the original files.",
    "enhance_page_description": "Increase image resolution locally with Real-ESRGAN.",
    "start_images": "Analyze images", "start_convert": "Convert files",
    "start_enhance": "Enhance images",
    "nav_organize": "Organize", "nav_convert": "Convert", "nav_enhance": "Enhance",
    "source_hint": "Choose a folder or select individual files to begin.",
    "clear": "Clear", "use_source_folder": "Use source folder",
    "use_default_destination": "Use default destination",
    "destination_hint": "Generated files will be saved here.",
    "duplicates_title": "Find duplicate images",
    "duplicates_description": "Identify identical or visually similar files.",
    "rename_title": "Rename files",
    "rename_description": "Standardize the names of processed files.",
    "rename_prefix": "File name",
    "rename_prefix_hint": "The sequence number and original extension are added automatically.",
    "invalid_prefix_title": "Invalid file name",
    "invalid_prefix": "Enter a valid name without any of these characters: < > : \" / \\ | ? *",
    "sensitivity_title": "Detection sensitivity",
    "simulation_title": "Simulate changes",
    "simulation_description": "Preview the result without moving or renaming files.",
    "apply_title": "Apply changes",
    "apply_description": "Perform the selected changes on the files.",
    "apply_warning": "Files may be moved or renamed. Originals used for conversion are preserved.",
    "output_format": "Output format", "quality": "Quality",
    "quality_help": "Used for JPG and WebP. PNG is always lossless.",
    "video_quality_high": "High quality",
    "video_quality_balanced": "Balanced (recommended)",
    "video_quality_compact": "Smaller file",
    "video_quality_help": "Choose the balance between image quality and file size.",
    "keep_originals": "Original files are always preserved.",
    "image_conversion_title": "Convert images",
    "image_conversion_description": "Create JPG, PNG, or WebP copies without changing resolution.",
    "video_conversion_title": "Convert videos",
    "video_conversion_description": "Create MP4, AVI, or MKV copies while preserving originals.",
    "local_processing_title": "Local processing",
    "local_processing_message": "Real-ESRGAN processes images on this computer. Files are not uploaded to the internet.",
    "hardware_recommendation": "A Vulkan-compatible GPU is recommended for faster processing.",
    "enlargement": "Enlargement", "image_type": "Image type",
    "ready_images": "Ready to analyze", "ready_convert": "Ready to convert",
    "ready_enhance": "Ready to enhance", "select_source_begin": "Select a source to begin",
    "all_files": "All files", "selected_source_count": "{count} compatible files",
    "details_empty": "Processing details will appear here.",
    "copy_log": "Copy log", "open_destination": "Open destination",
    "open_destination_error": "The destination folder could not be opened.",
    "conservative": "Safer", "balanced": "Balanced", "sensitive": "Broader",
    "sensitivity_conservative": "Reduces false positives and prioritizes very close matches.",
    "sensitivity_balanced": "Recommended for most image libraries.",
    "sensitivity_sensitive": "Finds more similar images, with a higher chance of false positives.",
})
TEXT["pt-BR"].update({
    "images_page_description": "Encontre imagens duplicadas, padronize nomes e organize sua biblioteca com segurança.",
    "convert_page_description": "Converta imagens e vídeos preservando os arquivos originais.",
    "enhance_page_description": "Aumente a resolução das imagens localmente com o Real-ESRGAN.",
    "start_images": "Analisar imagens", "start_convert": "Converter arquivos",
    "start_enhance": "Aprimorar imagens",
    "nav_organize": "Organizar", "nav_convert": "Converter", "nav_enhance": "Aprimorar",
    "source_hint": "Escolha uma pasta ou selecione arquivos individuais para começar.",
    "clear": "Limpar", "use_source_folder": "Usar pasta de origem",
    "use_default_destination": "Usar destino padrão",
    "destination_hint": "Os arquivos gerados serão salvos neste local.",
    "duplicates_title": "Encontrar imagens duplicadas",
    "duplicates_description": "Identifique arquivos iguais ou visualmente semelhantes.",
    "rename_title": "Renomear arquivos",
    "rename_description": "Padronize os nomes dos arquivos processados.",
    "rename_prefix": "Nome dos arquivos",
    "rename_prefix_hint": "A numeração e a extensão original são adicionadas automaticamente.",
    "invalid_prefix_title": "Nome inválido",
    "invalid_prefix": "Digite um nome válido, sem estes caracteres: < > : \" / \\ | ? *",
    "sensitivity_title": "Sensibilidade da detecção",
    "simulation_title": "Simular alterações",
    "simulation_description": "Exibe o resultado sem mover ou renomear arquivos.",
    "apply_title": "Aplicar alterações",
    "apply_description": "Executa as alterações selecionadas nos arquivos.",
    "apply_warning": "Arquivos poderão ser movidos ou renomeados. Originais usados em conversões são preservados.",
    "output_format": "Formato de saída", "quality": "Qualidade",
    "quality_help": "Usada em JPG e WebP. PNG é sempre convertido sem perdas.",
    "video_quality_high": "Alta qualidade",
    "video_quality_balanced": "Equilibrada (recomendada)",
    "video_quality_compact": "Arquivo menor",
    "video_quality_help": "Escolha o equilíbrio entre qualidade de imagem e tamanho do arquivo.",
    "keep_originals": "Os arquivos originais são sempre preservados.",
    "image_conversion_title": "Converter imagens",
    "image_conversion_description": "Crie cópias em JPG, PNG ou WebP sem alterar a resolução.",
    "video_conversion_title": "Converter vídeos",
    "video_conversion_description": "Crie cópias em MP4, AVI ou MKV preservando os originais.",
    "local_processing_title": "Processamento local",
    "local_processing_message": "O Real-ESRGAN processa suas imagens neste computador. Os arquivos não são enviados para a internet.",
    "hardware_recommendation": "Recomenda-se uma GPU compatível com Vulkan para maior velocidade.",
    "enlargement": "Ampliação", "image_type": "Tipo de imagem",
    "ready_images": "Pronto para analisar", "ready_convert": "Pronto para converter",
    "ready_enhance": "Pronto para aprimorar", "select_source_begin": "Selecione uma origem para começar",
    "all_files": "Todos os arquivos", "selected_source_count": "{count} arquivos compatíveis",
    "details_empty": "Os detalhes do processamento aparecerão aqui.",
    "copy_log": "Copiar log", "open_destination": "Abrir destino",
    "open_destination_error": "Não foi possível abrir a pasta de destino.",
    "conservative": "Mais segura", "balanced": "Equilibrada", "sensitive": "Mais abrangente",
    "sensitivity_conservative": "Reduz falsos positivos e prioriza correspondências muito próximas.",
    "sensitivity_balanced": "Recomendada para a maioria das bibliotecas.",
    "sensitivity_sensitive": "Encontra mais imagens semelhantes, com maior possibilidade de falsos positivos.",
})
TEXT["es-ES"].update({
    "images_page_description": "Encuentra imágenes duplicadas, estandariza nombres y organiza tu biblioteca de forma segura.",
    "convert_page_description": "Convierte imágenes y videos conservando los archivos originales.",
    "enhance_page_description": "Aumenta localmente la resolución de las imágenes con Real-ESRGAN.",
    "start_images": "Analizar imágenes", "start_convert": "Convertir archivos",
    "start_enhance": "Mejorar imágenes",
    "nav_organize": "Organizar", "nav_convert": "Convertir", "nav_enhance": "Mejorar",
    "source_hint": "Elige una carpeta o selecciona archivos individuales para comenzar.",
    "clear": "Limpiar", "use_source_folder": "Usar la carpeta de origen",
    "use_default_destination": "Usar el destino predeterminado",
    "destination_hint": "Los archivos generados se guardarán en esta ubicación.",
    "duplicates_title": "Encontrar imágenes duplicadas",
    "duplicates_description": "Identifica archivos idénticos o visualmente similares.",
    "rename_title": "Renombrar archivos",
    "rename_description": "Estandariza los nombres de los archivos procesados.",
    "rename_prefix": "Nombre de los archivos",
    "rename_prefix_hint": "La numeración y la extensión original se añaden automáticamente.",
    "invalid_prefix_title": "Nombre no válido",
    "invalid_prefix": "Escribe un nombre válido, sin estos caracteres: < > : \" / \\ | ? *",
    "sensitivity_title": "Sensibilidad de detección",
    "simulation_title": "Simular cambios",
    "simulation_description": "Muestra el resultado sin mover ni renombrar archivos.",
    "apply_title": "Aplicar cambios",
    "apply_description": "Ejecuta los cambios seleccionados en los archivos.",
    "apply_warning": "Los archivos pueden moverse o renombrarse. Los originales usados en conversiones se conservan.",
    "output_format": "Formato de salida", "quality": "Calidad",
    "quality_help": "Se usa en JPG y WebP. PNG siempre se convierte sin pérdidas.",
    "video_quality_high": "Alta calidad",
    "video_quality_balanced": "Equilibrada (recomendada)",
    "video_quality_compact": "Archivo más pequeño",
    "video_quality_help": "Elige el equilibrio entre calidad de imagen y tamaño del archivo.",
    "keep_originals": "Los archivos originales siempre se conservan.",
    "image_conversion_title": "Convertir imágenes",
    "image_conversion_description": "Crea copias en JPG, PNG o WebP sin cambiar la resolución.",
    "video_conversion_title": "Convertir vídeos",
    "video_conversion_description": "Crea copias en MP4, AVI o MKV conservando los originales.",
    "local_processing_title": "Procesamiento local",
    "local_processing_message": "Real-ESRGAN procesa tus imágenes en este equipo. Los archivos no se envían a internet.",
    "hardware_recommendation": "Se recomienda una GPU compatible con Vulkan para un procesamiento más rápido.",
    "enlargement": "Ampliación", "image_type": "Tipo de imagen",
    "ready_images": "Listo para analizar", "ready_convert": "Listo para convertir",
    "ready_enhance": "Listo para mejorar", "select_source_begin": "Selecciona un origen para comenzar",
    "all_files": "Todos los archivos", "selected_source_count": "{count} archivos compatibles",
    "details_empty": "Los detalles del procesamiento aparecerán aquí.",
    "copy_log": "Copiar registro", "open_destination": "Abrir destino",
    "open_destination_error": "No se pudo abrir la carpeta de destino.",
    "conservative": "Más segura", "balanced": "Equilibrada", "sensitive": "Más amplia",
    "sensitivity_conservative": "Reduce los falsos positivos y prioriza coincidencias muy cercanas.",
    "sensitivity_balanced": "Recomendada para la mayoría de las bibliotecas.",
    "sensitivity_sensitive": "Encuentra más imágenes similares, con mayor posibilidad de falsos positivos.",
})


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
                self.events.put(("status", value.strip()))
            elif compared:
                phase_percent = float(compared.group(1).replace(",", "."))
                self.events.put(("progress", 30 + 0.7 * phase_percent))
                self.events.put(("status", value.strip()))
            elif enhanced:
                self.events.put(("progress", float(enhanced.group(1).replace(",", "."))))
                self.events.put(("status", value.strip()))
        return len(value)

    def flush(self) -> None:
        pass


class Tooltip:
    """Small dependency-free tooltip for truncated paths and icon-only navigation."""

    def __init__(self, widget: tk.Misc, text: Callable[[], str]) -> None:
        self.widget = widget
        self.text = text
        self.window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _show(self, _event: object = None) -> None:
        value = str(self.text()).strip()
        if not value or self.window is not None:
            return
        self.window = tk.Toplevel(self.widget)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.window.geometry(f"+{x}+{y}")
        colors = getattr(self.widget.winfo_toplevel(), "colors", THEME_COLORS["dark"])
        tk.Label(
            self.window, text=value, justify="left", wraplength=520,
            background=colors["surface_alt"], foreground=colors["text"],
            relief="solid", borderwidth=1, padx=9, pady=6,
            font=("Segoe UI", 9),
        ).pack()

    def _hide(self, _event: object = None) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None


class ModernChoice(ttk.Frame):
    """Theme-aware radio-card control rendered consistently on every platform."""

    def __init__(
        self, master: tk.Misc, *, variable: tk.Variable, value: object,
        text: str = "", command: Callable[[], None] | None = None,
        surface: str = "surface_alt",
    ) -> None:
        self.variable = variable
        self.value = value
        self.command = command
        self.surface = surface
        self._text = text
        self._state = "normal"
        super().__init__(master, takefocus=True, cursor="hand2")
        self.indicator = tk.Canvas(
            self, width=18, height=18, highlightthickness=0, borderwidth=0,
        )
        self.indicator.pack(side="left", padx=(10, 8), pady=9)
        self.label = tk.Label(
            self, text=text, anchor="w", font=("Segoe UI Semibold", 10),
            borderwidth=0,
        )
        self.label.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=9)
        for widget in (self, self.indicator, self.label):
            widget.bind("<Button-1>", self._select, add="+")
        self.bind("<space>", self._select, add="+")
        self.bind("<Return>", self._select, add="+")
        self.bind("<FocusIn>", lambda _event: self.refresh(), add="+")
        self.bind("<FocusOut>", lambda _event: self.refresh(), add="+")
        self.variable.trace_add("write", lambda *_args: self.refresh())
        self.winfo_toplevel().custom_controls.append(self)
        self.refresh()

    def _select(self, _event: object = None) -> str:
        if self._state != "disabled":
            self.variable.set(self.value)
            if self.command:
                self.command()
            self.focus_set()
        return "break"

    def configure(self, cnf: object = None, **kwargs: object) -> object:
        if isinstance(cnf, dict):
            kwargs.update(cnf)
        if "text" in kwargs:
            self._text = str(kwargs.pop("text"))
            self.label.configure(text=self._text)
        if "state" in kwargs:
            self._state = str(kwargs.pop("state"))
        result = super().configure(**kwargs) if kwargs else None
        self.refresh()
        return result

    config = configure

    def refresh(self) -> None:
        app = self.winfo_toplevel()
        colors = app.colors
        selected = self.variable.get() == self.value
        disabled = self._state == "disabled"
        background = (
            colors["selection"] if selected else colors.get(self.surface, colors["surface_alt"])
        )
        foreground = colors["muted"] if disabled else colors["accent"] if selected else colors["text"]
        focused_widget = self.tk.call("focus")
        has_focus = bool(focused_widget) and str(focused_widget) == str(self)
        surface_name = "Elevated" if self.surface == "elevated" else "Surface"
        style_name = (
            "ChoiceSelected.TFrame" if selected
            else "ChoiceFocused.TFrame" if has_focus
            else f"Choice{surface_name}.TFrame"
        )
        self.configure_raw(style=style_name)
        self.label.configure(background=background, foreground=foreground)
        self.indicator.configure(background=background)
        self.indicator.delete("all")
        self.indicator.create_oval(2, 2, 16, 16, outline=foreground, width=2)
        if selected:
            self.indicator.create_oval(6, 6, 12, 12, fill=colors["accent"], outline="")
        cursor = "arrow" if disabled else "hand2"
        self.configure_raw(cursor=cursor)
        for widget in (self.indicator, self.label):
            widget.configure(cursor=cursor)

    def configure_raw(self, **kwargs: object) -> None:
        ttk.Frame.configure(self, **kwargs)


class ModernToggle(tk.Frame):
    """Compact switch with a text label and a platform-independent appearance."""

    def __init__(
        self, master: tk.Misc, *, variable: tk.BooleanVar, text: str = "",
        command: Callable[[], None] | None = None, surface: str = "elevated",
    ) -> None:
        self.variable = variable
        self.command = command
        self.surface = surface
        self._state = "normal"
        super().__init__(master, takefocus=True, cursor="hand2", borderwidth=0)
        self.switch = tk.Canvas(
            self, width=38, height=22, highlightthickness=0, borderwidth=0,
        )
        self.switch.pack(side="left", padx=(0, 10), pady=3)
        self.label = tk.Label(
            self, text=text, anchor="w", font=("Segoe UI Semibold", 10), borderwidth=0,
        )
        self.label.pack(side="left", fill="x", expand=True, pady=3)
        for widget in (self, self.switch, self.label):
            widget.bind("<Button-1>", self._toggle, add="+")
        self.bind("<space>", self._toggle, add="+")
        self.bind("<Return>", self._toggle, add="+")
        self.variable.trace_add("write", lambda *_args: self.refresh())
        self.winfo_toplevel().custom_controls.append(self)
        self.refresh()

    def _toggle(self, _event: object = None) -> str:
        if self._state != "disabled":
            self.variable.set(not self.variable.get())
            if self.command:
                self.command()
            self.focus_set()
        return "break"

    def configure(self, cnf: object = None, **kwargs: object) -> object:
        if isinstance(cnf, dict):
            kwargs.update(cnf)
        if "text" in kwargs:
            self.label.configure(text=str(kwargs.pop("text")))
        if "state" in kwargs:
            self._state = str(kwargs.pop("state"))
        result = super().configure(**kwargs) if kwargs else None
        self.refresh()
        return result

    config = configure

    def refresh(self) -> None:
        colors = self.winfo_toplevel().colors
        enabled = self.variable.get()
        disabled = self._state == "disabled"
        background = colors.get(self.surface, colors["surface_alt"])
        foreground = colors["muted"] if disabled else colors["text"]
        track = colors["border"] if disabled or not enabled else colors["accent"]
        self.configure_raw(background=background)
        self.label.configure(background=background, foreground=foreground)
        self.switch.configure(background=background)
        self.switch.delete("all")
        self.switch.create_oval(2, 3, 18, 19, fill=track, outline=track)
        self.switch.create_oval(20, 3, 36, 19, fill=track, outline=track)
        self.switch.create_rectangle(10, 3, 28, 19, fill=track, outline=track)
        knob_x = 27 if enabled else 11
        self.switch.create_oval(
            knob_x - 7, 4, knob_x + 7, 18,
            fill="#ffffff", outline="#ffffff",
        )
        cursor = "arrow" if disabled else "hand2"
        self.configure_raw(cursor=cursor)
        for widget in (self.switch, self.label):
            widget.configure(cursor=cursor)

    def configure_raw(self, **kwargs: object) -> None:
        tk.Frame.configure(self, **kwargs)


class ModernSlider(tk.Canvas):
    """Accessible value slider with a modern track, fill, and thumb."""

    def __init__(
        self, master: tk.Misc, *, from_: int, to: int, variable: tk.IntVar,
        command: Callable[[str], None] | None = None,
    ) -> None:
        self.minimum = from_
        self.maximum = to
        self.variable = variable
        self.command = command
        super().__init__(
            master, height=30, width=240, highlightthickness=0, borderwidth=0,
            takefocus=True, cursor="hand2",
        )
        self.bind("<Configure>", lambda _event: self.refresh())
        self.bind("<Button-1>", self._set_from_pointer)
        self.bind("<B1-Motion>", self._set_from_pointer)
        self.bind("<Left>", lambda _event: self._step(-1))
        self.bind("<Right>", lambda _event: self._step(1))
        self.bind("<Home>", lambda _event: self._set_value(self.minimum))
        self.bind("<End>", lambda _event: self._set_value(self.maximum))
        self.variable.trace_add("write", lambda *_args: self.refresh())
        self.winfo_toplevel().custom_controls.append(self)
        self.after_idle(self.refresh)

    def _set_from_pointer(self, event: tk.Event) -> str:
        width = max(self.winfo_width() - 24, 1)
        ratio = min(max((event.x - 12) / width, 0), 1)
        self._set_value(round(self.minimum + ratio * (self.maximum - self.minimum)))
        self.focus_set()
        return "break"

    def _step(self, amount: int) -> str:
        self._set_value(self.variable.get() + amount)
        return "break"

    def _set_value(self, value: int) -> None:
        value = min(max(int(value), self.minimum), self.maximum)
        self.variable.set(value)
        if self.command:
            self.command(str(value))

    def refresh(self) -> None:
        colors = self.winfo_toplevel().colors
        self.configure(background=colors["surface"])
        self.delete("all")
        left, right, center = 12, max(self.winfo_width() - 12, 13), 15
        ratio = (self.variable.get() - self.minimum) / max(self.maximum - self.minimum, 1)
        thumb = left + (right - left) * ratio
        self.create_line(left, center, right, center, fill=colors["border"], width=6)
        self.create_line(left, center, thumb, center, fill=colors["accent"], width=6)
        self.create_oval(
            thumb - 8, center - 8, thumb + 8, center + 8,
            fill=colors["surface"], outline=colors["accent"], width=3,
        )


class ModernSelect(ttk.Frame):
    """Custom dropdown that avoids platform-native combobox styling and popdowns."""

    def __init__(
        self, master: tk.Misc, *, variable: tk.StringVar, values: list[str] | tuple[str, ...],
        command: Callable[[object], None] | None = None, width: int = 24,
    ) -> None:
        self.variable = variable
        self.values = list(values)
        self.command = command
        self._state = "readonly"
        self.popup: tk.Toplevel | None = None
        super().__init__(master, takefocus=True, cursor="hand2")
        self.label = tk.Label(
            self, textvariable=variable, anchor="w", width=width,
            font=("Segoe UI", 10), borderwidth=0,
        )
        self.label.pack(side="left", fill="x", expand=True, padx=(12, 6), pady=9)
        self.arrow = tk.Canvas(
            self, width=22, height=20, highlightthickness=0, borderwidth=0,
        )
        self.arrow.pack(side="right", padx=(0, 7))
        for widget in (self, self.label, self.arrow):
            widget.bind("<Button-1>", self._toggle_popup, add="+")
        self.bind("<space>", self._toggle_popup, add="+")
        self.bind("<Return>", self._toggle_popup, add="+")
        self.bind("<Down>", lambda _event: self._move(1), add="+")
        self.bind("<Up>", lambda _event: self._move(-1), add="+")
        self.bind("<Escape>", lambda _event: self._close_popup(), add="+")
        self.variable.trace_add("write", lambda *_args: self.refresh())
        self.winfo_toplevel().custom_controls.append(self)
        self.refresh()

    def current(self, index: int | None = None) -> int:
        if index is None:
            try:
                return self.values.index(self.variable.get())
            except ValueError:
                return -1
        if not 0 <= index < len(self.values):
            raise tk.TclError(f"select index {index} out of range")
        self.variable.set(self.values[index])
        return index

    def configure(self, cnf: object = None, **kwargs: object) -> object:
        if isinstance(cnf, dict):
            kwargs.update(cnf)
        if "values" in kwargs:
            self.values = list(kwargs.pop("values"))
        if "state" in kwargs:
            self._state = str(kwargs.pop("state"))
        result = super().configure(**kwargs) if kwargs else None
        self.refresh()
        return result

    config = configure

    def _toggle_popup(self, _event: object = None) -> str:
        if self._state == "disabled":
            return "break"
        if self.popup is not None:
            self._close_popup()
        else:
            self._open_popup()
        self.focus_set()
        return "break"

    def _open_popup(self) -> None:
        if not self.values:
            return
        self.update_idletasks()
        colors = self.winfo_toplevel().colors
        self.popup = tk.Toplevel(self)
        self.popup.overrideredirect(True)
        self.popup.attributes("-topmost", True)
        self.popup.configure(background=colors["border"])
        width = max(self.winfo_width(), 180)
        x, y = self.winfo_rootx(), self.winfo_rooty() + self.winfo_height() + 4
        self.popup.geometry(f"{width}x{len(self.values) * 40}+{x}+{y}")
        selected = self.variable.get()
        for row, value in enumerate(self.values):
            active = value == selected
            option = tk.Label(
                self.popup, text=value, anchor="w",
                background=colors["selection"] if active else colors["surface_alt"],
                foreground=colors["accent"] if active else colors["text"],
                font=("Segoe UI Semibold" if active else "Segoe UI", 10),
                padx=12, pady=10, borderwidth=0, cursor="hand2",
            )
            option.pack(fill="x", padx=1, pady=(1 if row == 0 else 0, 0))
            option.bind("<Button-1>", lambda _event, choice=value: self._choose(choice))
            option.bind(
                "<Enter>",
                lambda _event, item=option: item.configure(background=colors["control_hover"]),
            )
            option.bind(
                "<Leave>",
                lambda _event, item=option, is_active=active: item.configure(
                    background=colors["selection"] if is_active else colors["surface_alt"]
                ),
            )
        self.popup.bind("<Escape>", lambda _event: self._close_popup())
        self.popup.lift()
        self.popup.after_idle(self._activate_popup)
        self.refresh()

    def _activate_popup(self) -> None:
        """Acquire the popup grab only after X11/Wayland has mapped the window."""
        if self.popup is None or not self.popup.winfo_exists():
            return
        self.popup.update_idletasks()
        if not self.popup.winfo_viewable():
            self.popup.after(15, self._activate_popup)
            return
        with contextlib.suppress(tk.TclError):
            self.popup.grab_set()

    def _close_popup(self) -> str:
        if self.popup is not None:
            with contextlib.suppress(tk.TclError):
                self.popup.grab_release()
                self.popup.destroy()
            self.popup = None
        self.refresh()
        return "break"

    def _choose(self, value: str) -> None:
        self.variable.set(value)
        self._close_popup()
        if self.command:
            self.command(None)

    def _move(self, amount: int) -> str:
        if not self.values:
            return "break"
        index = self.current()
        self.current((index + amount) % len(self.values))
        if self.command:
            self.command(None)
        return "break"

    def refresh(self) -> None:
        colors = self.winfo_toplevel().colors
        disabled = self._state == "disabled"
        background = colors["surface_alt"]
        foreground = colors["muted"] if disabled else colors["text"]
        ttk.Frame.configure(
            self, style="SelectFocused.TFrame" if self.popup is not None else "Select.TFrame",
            cursor="arrow" if disabled else "hand2",
        )
        self.label.configure(background=background, foreground=foreground)
        self.arrow.configure(background=background)
        self.arrow.delete("all")
        self.arrow.create_line(
            6, 8, 11, 13, 16, 8, fill=foreground, width=2,
            capstyle="round", joinstyle="round",
        )


class FluentScrollbar(tk.Canvas):
    """Thin overlay-like scrollbar matching the Windows 11 visual language."""

    def __init__(
        self, master: tk.Misc, *, command: Callable[..., object],
        orient: str = "vertical",
    ) -> None:
        self.command = command
        self.orient = orient
        self.first = 0.0
        self.last = 1.0
        self.drag_offset = 0
        super().__init__(
            master, width=12, highlightthickness=0, borderwidth=0,
            cursor="arrow",
        )
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<Enter>", lambda _event: self._draw(active=True))
        self.bind("<Leave>", lambda _event: self._draw())
        self.refresh_theme()

    def refresh_theme(self) -> None:
        colors = self.winfo_toplevel().colors
        self.configure(background=colors["window"])
        self._draw()

    def set(self, first: str | float, last: str | float) -> None:
        self.first, self.last = float(first), float(last)
        self._draw()

    def _geometry(self) -> tuple[float, float, float]:
        length = max(self.winfo_height(), 1)
        thumb = max(28.0, length * (self.last - self.first))
        travel = max(length - thumb, 1.0)
        start = min(travel, self.first * length)
        return start, start + thumb, travel

    def _draw(self, active: bool = False) -> None:
        if not self.winfo_exists():
            return
        colors = self.winfo_toplevel().colors
        self.delete("all")
        if self.last - self.first >= 0.999:
            return
        start, end, _travel = self._geometry()
        color = colors["muted"] if active else colors["border"]
        self.create_round_rect(4, start + 2, 8, end - 2, 2, fill=color)

    def create_round_rect(
        self, x1: float, y1: float, x2: float, y2: float, radius: float,
        **kwargs: object,
    ) -> None:
        self.create_rectangle(x1, y1 + radius, x2, y2 - radius, width=0, **kwargs)
        self.create_oval(x1, y1, x2, y1 + radius * 2, width=0, **kwargs)
        self.create_oval(x1, y2 - radius * 2, x2, y2, width=0, **kwargs)

    def _press(self, event: tk.Event) -> str:
        start, end, _travel = self._geometry()
        if start <= event.y <= end:
            self.drag_offset = event.y - start
        else:
            self.drag_offset = (end - start) / 2
            self._move_to(event.y)
        return "break"

    def _drag(self, event: tk.Event) -> str:
        self._move_to(event.y)
        return "break"

    def _move_to(self, pointer: float) -> None:
        _start, _end, travel = self._geometry()
        fraction = min(max((pointer - self.drag_offset) / travel, 0.0), 1.0)
        self.command("moveto", fraction)


class ScrollablePage(ttk.Frame):
    """A page that scrolls only when its content exceeds the viewport."""

    def __init__(self, master: tk.Misc, *, padding: tuple[int, ...]) -> None:
        super().__init__(master)
        self.canvas = tk.Canvas(
            self, highlightthickness=0, borderwidth=0,
            background=self.winfo_toplevel().colors["window"],
        )
        self.scrollbar = FluentScrollbar(
            self, orient="vertical", command=self.canvas.yview,
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.content = ttk.Frame(self.canvas, padding=padding)
        self.window = self.canvas.create_window(
            (0, 0), window=self.content, anchor="nw",
        )
        self.content.bind("<Configure>", self._content_resized, add="+")
        self.canvas.bind("<Configure>", self._viewport_resized, add="+")
        self.canvas.bind("<Enter>", self._enable_wheel, add="+")
        self.canvas.bind("<Leave>", self._disable_wheel, add="+")

    def refresh_theme(self) -> None:
        self.canvas.configure(background=self.winfo_toplevel().colors["window"])
        self.scrollbar.refresh_theme()

    def _content_resized(self, _event: object = None) -> None:
        self.canvas.itemconfigure(
            self.window,
            height=max(self.canvas.winfo_height(), self.content.winfo_reqheight()),
        )
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scrollbar()

    def _viewport_resized(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(
            self.window, width=event.width,
            height=max(event.height, self.content.winfo_reqheight()),
        )
        self._update_scrollbar()

    def _update_scrollbar(self) -> None:
        overflow = self.content.winfo_reqheight() > self.canvas.winfo_height()
        if overflow:
            self.scrollbar.grid(row=0, column=1, sticky="ns")
        else:
            self.scrollbar.grid_remove()
            self.canvas.yview_moveto(0)

    def _enable_wheel(self, _event: object = None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._mousewheel, add="+")
        self.canvas.bind_all("<Button-4>", self._mousewheel, add="+")
        self.canvas.bind_all("<Button-5>", self._mousewheel, add="+")

    def _disable_wheel(self, _event: object = None) -> None:
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _mousewheel(self, event: tk.Event) -> str:
        if self.content.winfo_reqheight() <= self.canvas.winfo_height():
            return "break"
        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            units = -max(-3, min(3, int(event.delta / 120)))
        self.canvas.yview_scroll(units, "units")
        return "break"


class Application(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.geometry("1120x760")
        self.minsize(840, 760)
        self.theme_mode = "system"
        self.effective_theme = system_theme()
        self.colors = THEME_COLORS[self.effective_theme]
        self._style_images: list[tk.PhotoImage] = []
        self._style_generation = 0
        self.custom_controls: list[
            ModernChoice | ModernToggle | ModernSlider | ModernSelect
        ] = []
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
        self.ui_icons["settings"] = self._create_settings_icon()
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
        self.rename_prefix = tk.StringVar(value="img")
        self.jpg_quality = tk.IntVar(value=92)
        self.video_quality = tk.IntVar(value=23)
        self.image_format = tk.StringVar(value="jpg")
        self.video_format = tk.StringVar(value="mp4")
        self.sensitivity = tk.StringVar(value="balanced")
        self.enhancement_scale = tk.IntVar(value=2)
        self.enhancement_model = tk.StringVar(value="photo")
        self.widgets: dict[str, tk.Misc] = {}
        self.widget_groups: dict[str, list[tk.Misc]] = {}
        self.details_visible = False
        self.processing = False
        self.current_progress_status = ""
        self.run_generation = 0
        self._build_ui()
        self._translate()
        self.after_idle(self._update_native_titlebar)
        self.after(350, self._update_native_titlebar)
        self.bind("<Map>", lambda _event: self.after_idle(self._update_native_titlebar), add="+")
        self.after(100, self._read_events)
        self.after(2000, self._watch_system_theme)

    def _create_settings_icon(self) -> tk.PhotoImage:
        """Create a crisp 20 px settings glyph matching the bundled navigation icons."""
        icon = tk.PhotoImage(width=20, height=20)
        for y in range(20):
            for x in range(20):
                dx, dy = x - 9.5, y - 9.5
                radius = math.hypot(dx, dy)
                angle = math.atan2(dy, dx)
                tooth = abs(math.cos(angle * 4)) > 0.72
                outer_radius = 9.2 if tooth else 7.8
                if 3.4 <= radius <= outer_radius:
                    icon.put(self.colors["accent"], (x, y))
        return icon

    def _rounded_style_image(
        self, fill: str, *, border: str | None = None, radius: int = 10,
        size: int = 32, backdrop: str | None = None,
    ) -> tk.PhotoImage:
        """Create a stretchable rounded rectangle used by ttk style elements."""
        image = tk.PhotoImage(width=size, height=size)
        border_width = 1 if border and border != fill else 0
        backdrop_color = backdrop or self.colors["window"]

        def inside(x: int, y: int, inset: int = 0) -> bool:
            left, top = inset, inset
            right, bottom = size - 1 - inset, size - 1 - inset
            effective_radius = max(radius - inset, 1)
            if not (left <= x <= right and top <= y <= bottom):
                return False
            if left + effective_radius <= x <= right - effective_radius:
                return True
            if top + effective_radius <= y <= bottom - effective_radius:
                return True
            center_x = left + effective_radius if x < left + effective_radius else right - effective_radius
            center_y = top + effective_radius if y < top + effective_radius else bottom - effective_radius
            return (x - center_x) ** 2 + (y - center_y) ** 2 <= effective_radius ** 2

        # One Tcl call instead of one call per pixel. On Windows, the old loop
        # caused tens of thousands of cross-interpreter calls during startup.
        pixels: list[tuple[str, ...]] = []
        for y in range(size):
            row: list[str] = []
            for x in range(size):
                if not inside(x, y):
                    row.append(backdrop_color)
                elif border_width and not inside(x, y, border_width):
                    row.append(border or fill)
                else:
                    row.append(fill)
            pixels.append(tuple(row))
        image.put(tuple(pixels))
        self._style_images.append(image)
        return image

    def _install_rounded_style(
        self, style: ttk.Style, style_name: str, *, normal: str,
        active: str | None = None, pressed: str | None = None,
        disabled: str | None = None, border: str | None = None,
        radius: int = 10, kind: str = "button", backdrop: str | None = None,
    ) -> None:
        """Back a ttk button or frame style with a scalable rounded image."""
        if sys.platform == "win32":
            # Tk's Windows renderer becomes dramatically slower when many
            # stretchable image elements cover large widgets (measured at
            # ~18 s for the first frame). Use lightweight ttk backgrounds on
            # Windows; native window rounding still comes from DWM.
            return
        self._style_generation += 1
        element = f"SimilarisRounded{self._style_generation}"
        normal_image = self._rounded_style_image(
            normal, border=border, radius=radius, backdrop=backdrop
        )
        states: list[tuple[str, tk.PhotoImage]] = []
        for state, color in (
            ("disabled", disabled), ("pressed", pressed), ("active", active),
        ):
            if color:
                states.append((state, self._rounded_style_image(
                    color, border=border, radius=radius, backdrop=backdrop
                )))
        style.element_create(
            element, "image", normal_image, *states,
            border=(radius, radius, radius, radius), sticky="nsew",
        )
        if kind == "frame":
            style.layout(style_name, [(element, {"sticky": "nsew"})])
        else:
            style.layout(style_name, [(
                element,
                {"sticky": "nsew", "children": [(
                    "Button.padding",
                    {"sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]},
                )]},
            )])

    def _install_rounded_entry_style(
        self, style: ttk.Style, style_name: str, *, fill: str, border: str,
        backdrop: str,
    ) -> None:
        if sys.platform == "win32":
            return
        self._style_generation += 1
        element = f"SimilarisRoundedEntry{self._style_generation}"
        normal = self._rounded_style_image(
            fill, border=border, radius=9, backdrop=backdrop
        )
        focused = self._rounded_style_image(
            fill, border=self.colors["accent"], radius=9, backdrop=backdrop
        )
        disabled = self._rounded_style_image(
            self.colors["surface"], border=border, radius=9, backdrop=backdrop
        )
        style.element_create(
            element, "image", normal,
            ("focus", focused), ("disabled", disabled),
            border=(9, 9, 9, 9), sticky="nsew",
        )
        style.layout(style_name, [(
            element,
            {"sticky": "nsew", "children": [(
                "Entry.padding",
                {"sticky": "nsew", "children": [("Entry.textarea", {"sticky": "nsew"})]},
            )]},
        )])

    def _install_rounded_label_style(
        self, style: ttk.Style, style_name: str, *, fill: str,
        border: str | None = None, backdrop: str,
    ) -> None:
        if sys.platform == "win32":
            return
        self._style_generation += 1
        element = f"SimilarisRoundedLabel{self._style_generation}"
        image = self._rounded_style_image(
            fill, border=border, radius=8, backdrop=backdrop
        )
        style.element_create(
            element, "image", image, border=(8, 8, 8, 8), sticky="nsew",
        )
        style.layout(style_name, [(
            element,
            {"sticky": "nsew", "children": [(
                "Label.padding",
                {"sticky": "nsew", "children": [("Label.label", {"sticky": "nsew"})]},
            )]},
        )])

    def _configure_style(self) -> None:
        """Apply a cross-platform Fluent/WinUI-inspired visual language."""
        colors = self.colors
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        self._install_rounded_style(
            style, "Card.TFrame", normal=colors["surface"], radius=14, kind="frame",
            backdrop=colors["window"],
        )
        self._install_rounded_style(
            style, "Elevated.TFrame",
            normal=colors.get("elevated", colors["surface_alt"]), radius=12, kind="frame",
            backdrop=colors["surface"],
        )
        self._install_rounded_style(
            style, "ChoiceSurface.TFrame", normal=colors["surface"],
            border=colors["border"], radius=9, kind="frame", backdrop=colors["surface"],
        )
        self._install_rounded_style(
            style, "ChoiceElevated.TFrame",
            normal=colors.get("elevated", colors["surface_alt"]),
            border=colors["border"], radius=9, kind="frame",
            backdrop=colors.get("elevated", colors["surface_alt"]),
        )
        self._install_rounded_style(
            style, "ChoiceSelected.TFrame", normal=colors["selection"],
            border=colors["accent"], radius=9, kind="frame",
            backdrop=colors.get("elevated", colors["surface_alt"]),
        )
        self._install_rounded_style(
            style, "ChoiceFocused.TFrame", normal=colors["surface_alt"],
            border=colors["accent"], radius=9, kind="frame",
            backdrop=colors.get("elevated", colors["surface_alt"]),
        )
        self._install_rounded_style(
            style, "Select.TFrame", normal=colors["surface_alt"],
            border=colors["border"], radius=9, kind="frame", backdrop=colors["surface"],
        )
        self._install_rounded_style(
            style, "SelectFocused.TFrame", normal=colors["surface_alt"],
            border=colors["accent"], radius=9, kind="frame", backdrop=colors["surface"],
        )

        style.configure("TFrame", background=colors["window"])
        # The image element paints the surface. The style background is the
        # color visible through its transparent rounded corners.
        style.configure("Card.TFrame", background=colors["window"])
        style.configure(
            "Elevated.TFrame", background=colors["surface"],
            relief="flat",
        )
        style.configure("ChoiceSurface.TFrame", background=colors["surface"])
        style.configure(
            "ChoiceElevated.TFrame",
            background=colors.get("elevated", colors["surface_alt"]),
        )
        style.configure("ChoiceSelected.TFrame", background=colors["selection"])
        style.configure("ChoiceFocused.TFrame", background=colors["surface_alt"])
        style.configure("Select.TFrame", background=colors["surface_alt"])
        style.configure("SelectFocused.TFrame", background=colors["surface_alt"])
        style.configure(
            "Sidebar.TFrame", background=colors.get("sidebar", colors["surface"]), relief="flat"
        )
        style.configure(
            "Sidebar.TLabel", background=colors.get("sidebar", colors["surface"]),
            foreground=colors["text"], font=("Segoe UI", 10),
        )
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
            "Elevated.TLabel", background=colors.get("elevated", colors["surface_alt"]),
            foreground=colors["text"], font=("Segoe UI", 10),
        )
        style.configure(
            "Muted.Elevated.TLabel", background=colors.get("elevated", colors["surface_alt"]),
            foreground=colors["muted"], font=("Segoe UI", 9),
        )
        style.configure(
            "Title.TLabel", background=colors["window"], foreground=colors["text"],
            font=("Segoe UI Semibold", 24),
        )
        style.configure(
            "Subtitle.TLabel", background=colors["window"], foreground=colors["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Section.Card.TLabel", background=colors["surface"], foreground=colors["text"],
            font=("Segoe UI Semibold", 12),
        )
        style.configure(
            "Accent.Card.TLabel", background=colors["surface"], foreground=colors["accent"],
            font=("Segoe UI Semibold", 10),
        )
        style.configure(
            "Value.Card.TLabel", background=colors["selection"], foreground=colors["accent"],
            font=("Segoe UI Semibold", 10), padding=(10, 5), anchor="center",
        )
        self._install_rounded_label_style(
            style, "Value.Card.TLabel", fill=colors["selection"],
            backdrop=colors["surface"],
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
            "TButton", font=("Segoe UI Semibold", 10), padding=(16, 10),
            background=colors["surface"], foreground=colors["text"],
            bordercolor=colors["border"], focuscolor=colors["accent"],
            borderwidth=1, relief="flat",
        )
        style.map("TButton", bordercolor=[("focus", colors["accent"])])
        self._install_rounded_style(
            style, "TButton", normal=colors["surface_alt"],
            active=colors["control_hover"], pressed=colors["control_pressed"],
            disabled=colors["surface"], border=colors["border"],
            backdrop=colors["surface"],
        )
        style.configure(
            "Accent.TButton",
            background=colors.get("elevated", colors["surface_alt"]),
            foreground=colors["accent_text"],
            bordercolor=colors["accent"], borderwidth=0,
            font=("Segoe UI Semibold", 10), padding=(20, 12),
        )
        style.map(
            "Accent.TButton",
            foreground=[("disabled", "#f4f4f4")],
        )
        self._install_rounded_style(
            style, "Accent.TButton", normal=colors["accent"],
            active=colors["accent_hover"], pressed=colors["accent_pressed"],
            disabled=colors["border"],
            backdrop=colors.get("elevated", colors["surface_alt"]),
        )
        style.configure(
            "TEntry", fieldbackground=colors["surface_alt"], foreground=colors["text"],
            bordercolor=colors["border"], lightcolor=colors["border"], darkcolor=colors["border"],
            padding=(10, 7), insertcolor=colors["text"],
        )
        style.map("TEntry", bordercolor=[("focus", colors["accent"])])
        self._install_rounded_entry_style(
            style, "TEntry", fill=colors["surface_alt"], border=colors["border"],
            backdrop=colors.get("elevated", colors["surface_alt"]),
        )
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
            font=("Segoe UI Semibold", 10), padding=(0, 3),
        )
        style.map("TCheckbutton", background=[("active", colors["surface"])])
        style.configure(
            "Elevated.TCheckbutton",
            background=colors.get("elevated", colors["surface_alt"]),
            foreground=colors["text"], font=("Segoe UI Semibold", 10), padding=(0, 3),
        )
        style.map(
            "Elevated.TCheckbutton",
            background=[("active", colors.get("elevated", colors["surface_alt"]))],
        )
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
        style.map("Nav.TButton", foreground=[("active", colors["text"])])
        self._install_rounded_style(
            style, "Nav.TButton", normal=colors["surface"],
            active=colors["control_hover"], pressed=colors["control_pressed"],
            backdrop=colors["surface"],
        )
        style.configure(
            "Selected.Nav.TButton", background=colors["surface"], foreground=colors["accent"],
            borderwidth=0, relief="flat", padding=(16, 9), font=("Segoe UI Semibold", 10),
        )
        style.map(
            "Selected.Nav.TButton", foreground=[("active", colors["accent_pressed"])]
        )
        self._install_rounded_style(
            style, "Selected.Nav.TButton", normal=colors["selection"],
            active=colors["selection"], pressed=colors["control_pressed"],
            backdrop=colors["surface"],
        )
        style.configure(
            "Sidebar.TButton", background=colors["surface"], foreground=colors["text"],
            borderwidth=0, relief="flat", padding=(14, 11), anchor="w",
            font=("Segoe UI Semibold", 10),
        )
        style.configure(
            "Selected.Sidebar.TButton", background=colors["selection"], foreground=colors["accent"],
            borderwidth=0, relief="flat", padding=(14, 11), anchor="w",
            font=("Segoe UI Semibold", 10),
        )
        sidebar_color = colors.get("sidebar", colors["surface"])
        style.configure("Sidebar.TButton", background=sidebar_color)
        style.configure("Selected.Sidebar.TButton", background=sidebar_color)
        style.map(
            "Selected.Sidebar.TButton",
            foreground=[("active", colors["accent"])],
        )
        self._install_rounded_style(
            style, "Sidebar.TButton", normal=sidebar_color,
            active=colors["control_hover"], pressed=colors["control_pressed"],
            backdrop=sidebar_color,
        )
        self._install_rounded_style(
            style, "Selected.Sidebar.TButton", normal=colors["selection"],
            active=colors["selection"], pressed=colors["control_pressed"],
            backdrop=sidebar_color,
        )
        style.configure(
            "Settings.Sidebar.TButton",
            background=sidebar_color, foreground=colors["text"],
            borderwidth=0, relief="flat", padding=(14, 16), anchor="w",
            font=("Segoe UI Semibold", 11),
        )
        self._install_rounded_style(
            style, "Settings.Sidebar.TButton", normal=sidebar_color,
            active=colors["control_hover"], pressed=colors["control_pressed"],
            backdrop=sidebar_color,
        )
        style.configure(
            "Selected.Settings.Sidebar.TButton",
            background=sidebar_color, foreground=colors["accent"],
            borderwidth=0, relief="flat", padding=(14, 16), anchor="w",
            font=("Segoe UI Semibold", 11),
        )
        style.map(
            "Selected.Settings.Sidebar.TButton",
            foreground=[("active", colors["accent"])],
        )
        self._install_rounded_style(
            style, "Selected.Settings.Sidebar.TButton", normal=colors["selection"],
            active=colors["selection"], pressed=colors["control_pressed"],
            backdrop=sidebar_color,
        )
        style.configure(
            "Choice.TRadiobutton", background=colors["surface_alt"], foreground=colors["text"],
            font=("Segoe UI Semibold", 10), padding=(10, 8),
        )
        style.map(
            "Choice.TRadiobutton",
            background=[("active", colors["control_hover"]), ("selected", colors["selection"])],
            foreground=[("selected", colors["accent"])],
        )
        style.configure(
            "Horizontal.TScale", background=colors["surface"], troughcolor=colors["progress_trough"],
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
        self.widget_groups.setdefault(key, []).append(widget)
        return widget

    def _build_ui(self) -> None:
        self.sidebar_expanded = True
        self.current_section = "images"
        shell = ttk.Frame(self)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        self.sidebar = ttk.Frame(shell, style="Sidebar.TFrame", width=228)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.sidebar.columnconfigure(0, weight=1)
        self.sidebar.rowconfigure(5, weight=1)
        brand = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        self.sidebar_brand = brand
        brand.grid(row=0, column=0, sticky="ew", padx=12, pady=(16, 18))
        brand.columnconfigure(1, weight=1)
        ttk.Label(brand, image=self.header_logo, style="Sidebar.TLabel").grid(
            row=0, column=0, padx=(2, 10)
        )
        self.sidebar_brand_text = ttk.Label(
            brand, text="Similaris", style="Sidebar.TLabel",
            font=("Segoe UI Semibold", 15),
        )
        self.sidebar_brand_text.grid(row=0, column=1, sticky="w")
        self.hamburger_button = ttk.Button(
            self.sidebar, text="☰", command=self._toggle_sidebar, style="Sidebar.TButton", width=3,
        )
        self.hamburger_button.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 10))
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
                style="Settings.Sidebar.TButton", image=self.ui_icons["settings"],
                compound="left",
            ),
        }
        self.section_buttons["images"].grid(row=2, column=0, sticky="ew", padx=8, pady=3)
        self.section_buttons["convert"].grid(row=3, column=0, sticky="ew", padx=8, pady=3)
        self.section_buttons["enhance"].grid(row=4, column=0, sticky="ew", padx=8, pady=3)
        self.section_buttons["settings"].grid(row=6, column=0, sticky="ew", padx=8, pady=(3, 14))
        navigation_keys = {
            "images": "nav_organize", "convert": "nav_convert",
            "enhance": "nav_enhance", "settings": "settings",
        }
        for name, button in self.section_buttons.items():
            Tooltip(button, lambda key=navigation_keys[name]: self.tr(key))

        page_host = ttk.Frame(shell)
        page_host.grid(row=0, column=1, sticky="nsew")
        page_host.columnconfigure(0, weight=1)
        page_host.rowconfigure(0, weight=1)
        self.home_scroll = ScrollablePage(
            page_host, padding=(30, 24, 30, 24)
        )
        self.settings_scroll = ScrollablePage(
            page_host, padding=(32, 28, 32, 28)
        )
        home = self.home_scroll.content
        settings = self.settings_scroll.content
        self.scrollable_pages = (self.home_scroll, self.settings_scroll)
        self.section_pages = {
            "home": self.home_scroll, "settings": self.settings_scroll,
        }
        for page in self.section_pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        self.main_frame = home
        home.columnconfigure(0, weight=1)
        home.rowconfigure(4, weight=1)
        header = ttk.Frame(home)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.page_icon = ttk.Label(header, image=self.ui_icons["images"])
        self.page_icon.pack(side="left", padx=(0, 12))
        heading_text = ttk.Frame(header)
        heading_text.pack(side="left", fill="x", expand=True)
        self.page_title = ttk.Label(heading_text, style="Title.TLabel")
        self.page_title.pack(anchor="w")
        self.page_description = ttk.Label(
            heading_text, style="Subtitle.TLabel", wraplength=720, justify="left"
        )
        self.page_description.pack(anchor="w", pady=(2, 0))

        self.selection_area = ttk.Frame(home)
        self.selection_area.grid(row=1, column=0, sticky="ew")
        self.source_card = ttk.Frame(self.selection_area, padding=16, style="Card.TFrame")
        self._widget(
            "folder", ttk.Label(
                self.source_card, style="Card.TLabel", font=("Segoe UI Semibold", 10)
            )
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 9))
        self._widget(
            "source_hint", ttk.Label(
                self.source_card, style="Muted.Card.TLabel", wraplength=480, justify="left"
            )
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))
        self.source_summary = ttk.Label(
            self.source_card, textvariable=self.source_display, style="Muted.Card.TLabel",
            anchor="w",
        )
        self.source_summary.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        Tooltip(self.source_summary, self._source_tooltip_text)
        self.source_card.columnconfigure(0, weight=1)
        self._widget(
            "select", ttk.Button(
                self.source_card, command=self._select_folder, image=self.ui_icons["folder"],
                compound="left",
            )
        ).grid(row=3, column=0, sticky="w", padx=(0, 6))
        self._widget(
            "select_files", ttk.Button(
                self.source_card, command=self._select_files,
                image=self.ui_icons["images"], compound="left",
            )
        ).grid(row=3, column=1, sticky="w", padx=(0, 6))
        self._widget(
            "clear", ttk.Button(self.source_card, command=self._clear_source)
        ).grid(row=3, column=2, sticky="e")

        self.destination_card = ttk.Frame(
            self.selection_area, padding=16, style="Card.TFrame"
        )
        self._widget(
            "destination", ttk.Label(
                self.destination_card, style="Card.TLabel",
                font=("Segoe UI Semibold", 10),
            )
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 9))
        self._widget(
            "destination_hint", ttk.Label(
                self.destination_card, style="Muted.Card.TLabel", wraplength=360, justify="left"
            )
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))
        self.destination_summary = ttk.Label(
            self.destination_card, textvariable=self.destination_display,
            style="Muted.Card.TLabel", anchor="w",
        )
        self.destination_summary.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        Tooltip(
            self.destination_summary,
            lambda: self.output_folders.get(self.current_operation, "") or self.tr("no_destination"),
        )
        self.destination_card.columnconfigure(0, weight=1)
        self._widget(
            "select_destination", ttk.Button(
                self.destination_card, command=self._select_destination,
                image=self.ui_icons["folder"], compound="left",
            )
        ).grid(row=3, column=0, sticky="w")
        self._widget(
            "use_default_destination",
            ttk.Button(self.destination_card, command=self._use_default_destination),
        ).grid(row=3, column=1, sticky="e")
        self._layout_selection(False)

        self.operations_shell = ttk.Frame(home, style="Card.TFrame")
        self.operations_shell.grid(row=2, column=0, sticky="ew", pady=10)
        self.operations_shell.columnconfigure(0, weight=1)
        page_container = ttk.Frame(self.operations_shell, style="Card.TFrame")
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

        self.images_tab.columnconfigure((0, 1), weight=1, uniform="features")
        self.duplicate_card = ttk.Frame(self.images_tab, padding=16, style="Elevated.TFrame")
        self.duplicate_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._widget(
            "duplicates_title", ModernToggle(
                self.duplicate_card, variable=self.find_duplicates,
                command=self._refresh_feature_states,
            )
        ).grid(row=0, column=0, sticky="w")
        self._widget(
            "duplicates_description", ttk.Label(
                self.duplicate_card, style="Muted.Elevated.TLabel", wraplength=290, justify="left"
            )
        ).grid(row=1, column=0, sticky="w", pady=(2, 14))
        self._widget(
            "sensitivity_title", ttk.Label(
                self.duplicate_card, style="Elevated.TLabel", font=("Segoe UI Semibold", 10)
            )
        ).grid(row=2, column=0, sticky="w", pady=(0, 6))
        sensitivity = ttk.Frame(self.duplicate_card, style="Elevated.TFrame")
        sensitivity.grid(row=3, column=0, sticky="ew")
        sensitivity.columnconfigure((0, 1), weight=1, uniform="sensitivity")
        self.sensitivity_buttons: dict[str, ModernChoice] = {}
        for index, value in enumerate(("conservative", "balanced", "sensitive")):
            row, column = divmod(index, 2)
            button = ModernChoice(
                sensitivity, variable=self.sensitivity, value=value,
                command=self._refresh_sensitivity_cards, surface="elevated",
            )
            button.grid(
                row=row, column=column, columnspan=2 if index == 2 else 1,
                sticky="ew", padx=(0, 3) if column == 0 and index != 2 else 0,
                pady=(3, 0) if row else 0,
            )
            self.sensitivity_buttons[value] = button
        self.sensitivity_help = ttk.Label(
            self.duplicate_card, style="Muted.Elevated.TLabel", wraplength=290, justify="left"
        )
        self.sensitivity_help.grid(row=4, column=0, sticky="w", pady=(8, 0))

        self.rename_card = ttk.Frame(self.images_tab, padding=16, style="Elevated.TFrame")
        self.rename_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._widget(
            "rename_title", ModernToggle(
                self.rename_card, variable=self.rename_images,
                command=self._refresh_feature_states,
            )
        ).grid(row=0, column=0, sticky="w")
        self._widget(
            "rename_description", ttk.Label(
                self.rename_card, style="Muted.Elevated.TLabel", wraplength=290, justify="left"
            )
        ).grid(row=1, column=0, sticky="w", pady=(2, 14))
        self._widget(
            "rename_prefix", ttk.Label(
                self.rename_card, style="Elevated.TLabel",
                font=("Segoe UI Semibold", 10),
            )
        ).grid(row=2, column=0, sticky="w", pady=(0, 6))
        self.rename_prefix_entry = ttk.Entry(
            self.rename_card, textvariable=self.rename_prefix, width=28,
        )
        self.rename_prefix_entry.grid(row=3, column=0, sticky="ew")
        self.rename_preview = ttk.Label(self.rename_card, style="Elevated.TLabel")
        self.rename_preview.grid(row=4, column=0, sticky="w", pady=(9, 2))
        self._widget(
            "rename_prefix_hint", ttk.Label(
                self.rename_card, style="Muted.Elevated.TLabel",
                wraplength=290, justify="left",
            )
        ).grid(row=5, column=0, sticky="w")
        self.rename_prefix.trace_add("write", lambda *_args: self._update_rename_preview())
        self._update_rename_preview()

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

        self._widget(
            "image_conversion_title", ttk.Label(
                self.photo_conversion_tab, style="Section.Card.TLabel"
            )
        ).grid(row=0, column=0, sticky="w")
        self._widget(
            "image_conversion_description", ttk.Label(
                self.photo_conversion_tab, style="Muted.Card.TLabel", wraplength=680
            )
        ).grid(row=1, column=0, sticky="w", pady=(3, 16))
        image_quality = ttk.Frame(self.photo_conversion_tab, style="Card.TFrame")
        image_quality.grid(row=2, column=0, sticky="ew")
        image_quality.columnconfigure(1, weight=1)
        self._widget("output_format", ttk.Label(image_quality, style="Card.TLabel")).grid(row=0, column=0, sticky="w")
        image_format_choices = ttk.Frame(image_quality, style="Card.TFrame")
        image_format_choices.grid(row=0, column=1, sticky="ew", padx=(18, 0))
        image_format_choices.columnconfigure((0, 1, 2), weight=1, uniform="image_format")
        for column, image_format in enumerate(("jpg", "png", "webp")):
            ModernChoice(
                image_format_choices, text=image_format.upper(),
                variable=self.image_format, value=image_format, surface="surface",
            ).grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 4, 0))
        self._widget("quality", ttk.Label(image_quality, style="Card.TLabel")).grid(row=1, column=0, sticky="w", pady=(16, 0))
        self.jpg_scale = ModernSlider(
            image_quality, from_=1, to=100, variable=self.jpg_quality,
            command=lambda _value: self.jpg_quality_value.configure(text=str(self.jpg_quality.get())),
        )
        self.jpg_scale.grid(row=1, column=1, sticky="ew", padx=(18, 10), pady=(16, 0))
        self.jpg_quality_value = ttk.Label(
            image_quality, text=str(self.jpg_quality.get()), style="Value.Card.TLabel", width=3
        )
        self.jpg_quality_value.grid(row=1, column=2, pady=(16, 0))
        self._widget("quality_help", ttk.Label(image_quality, style="Muted.Card.TLabel")).grid(row=2, column=1, sticky="w", padx=(18, 0), pady=(4, 0))
        self._widget("keep_originals", ttk.Label(self.photo_conversion_tab, style="Muted.Card.TLabel")).grid(row=3, column=0, sticky="w", pady=(18, 0))

        self._widget("video_conversion_title", ttk.Label(self.video_conversion_tab, style="Section.Card.TLabel")).grid(row=0, column=0, sticky="w")
        self._widget("video_conversion_description", ttk.Label(self.video_conversion_tab, wraplength=700, style="Muted.Card.TLabel")).grid(row=1, column=0, sticky="w", pady=(3, 16))
        video_quality = ttk.Frame(self.video_conversion_tab, style="Card.TFrame")
        video_quality.grid(row=2, column=0, sticky="ew")
        video_quality.columnconfigure(1, weight=1)
        self._widget("output_format", ttk.Label(video_quality, style="Card.TLabel")).grid(row=0, column=0, sticky="w")
        video_format_choices = ttk.Frame(video_quality, style="Card.TFrame")
        video_format_choices.grid(row=0, column=1, sticky="ew", padx=(18, 0))
        video_format_choices.columnconfigure((0, 1, 2), weight=1, uniform="video_format")
        for column, video_format in enumerate(("mp4", "avi", "mkv")):
            ModernChoice(
                video_format_choices, text=video_format.upper(),
                variable=self.video_format, value=video_format, surface="surface",
            ).grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 4, 0))
        self._widget("quality", ttk.Label(video_quality, style="Card.TLabel")).grid(row=1, column=0, sticky="w", pady=(16, 0))
        video_quality_choices = ttk.Frame(video_quality, style="Card.TFrame")
        video_quality_choices.grid(row=1, column=1, sticky="ew", padx=(18, 0), pady=(16, 0))
        video_quality_choices.columnconfigure((0, 1, 2), weight=1, uniform="video_quality")
        for column, (key, crf) in enumerate((
            ("video_quality_high", 18),
            ("video_quality_balanced", 23),
            ("video_quality_compact", 28),
        )):
            self._widget(
                key,
                ModernChoice(
                    video_quality_choices, variable=self.video_quality,
                    value=crf, surface="surface",
                ),
            ).grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 4, 0))
        self._widget(
            "video_quality_help",
            ttk.Label(video_quality, style="Muted.Card.TLabel"),
        ).grid(row=2, column=1, sticky="w", padx=(18, 0), pady=(7, 0))
        self._widget("keep_originals", ttk.Label(self.video_conversion_tab, style="Muted.Card.TLabel")).grid(row=3, column=0, sticky="w", pady=(18, 0))

        self._widget("hardware_recommendation", ttk.Label(self.enhance_tab, wraplength=760, style="Muted.Card.TLabel")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))
        enhance_options = ttk.Frame(self.enhance_tab, style="Card.TFrame")
        enhance_options.grid(row=1, column=0, columnspan=2, sticky="ew")
        self._widget("enlargement", ttk.Label(enhance_options, style="Card.TLabel")).grid(row=0, column=0, sticky="w", padx=(0, 14))
        self.scale_buttons = {}
        for column, scale in enumerate((2, 3, 4), 1):
            button = ModernChoice(
                enhance_options, text=f"{scale}×", variable=self.enhancement_scale,
                value=scale, surface="surface",
            )
            button.grid(row=0, column=column, padx=(0, 4))
            self.scale_buttons[scale] = button
        self._widget("image_type", ttk.Label(enhance_options, style="Card.TLabel")).grid(row=1, column=0, sticky="w", padx=(0, 14), pady=(14, 0))
        self.model_buttons = {}
        for column, model in enumerate(("photo", "illustration"), 1):
            button = ModernChoice(
                enhance_options, variable=self.enhancement_model, value=model,
                surface="surface",
            )
            button.grid(row=1, column=column, sticky="ew", padx=(0, 4), pady=(14, 0))
            self.model_buttons[model] = button
        privacy = ttk.Frame(self.enhance_tab, padding=14, style="Elevated.TFrame")
        privacy.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        self._widget("local_processing_title", ttk.Label(privacy, style="Elevated.TLabel", font=("Segoe UI Semibold", 10))).grid(row=0, column=0, sticky="w")
        self._widget("local_processing_message", ttk.Label(privacy, style="Muted.Elevated.TLabel", wraplength=720, justify="left")).grid(row=1, column=0, sticky="w", pady=(3, 0))

        mode = ttk.Frame(self.images_tab, style="Card.TFrame")
        mode.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        mode.columnconfigure((0, 1), weight=1, uniform="mode")
        simulation = ttk.Frame(mode, padding=13, style="Elevated.TFrame")
        simulation.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._widget("simulation_title", ModernChoice(
            simulation, variable=self.apply_changes, value=False, surface="elevated"
        )).grid(row=0, column=0, sticky="w")
        self._widget("simulation_description", ttk.Label(
            simulation, style="Muted.Elevated.TLabel", wraplength=290
        )).grid(row=1, column=0, sticky="w", pady=(2, 0))
        apply_mode = ttk.Frame(mode, padding=13, style="Elevated.TFrame")
        apply_mode.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self._widget("apply_title", ModernChoice(
            apply_mode, variable=self.apply_changes, value=True, surface="elevated"
        )).grid(row=0, column=0, sticky="w")
        self._widget("apply_description", ttk.Label(
            apply_mode, style="Muted.Elevated.TLabel", wraplength=290
        )).grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.action_bar = ttk.Frame(home, padding=12, style="Elevated.TFrame")
        self.action_bar.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        self.action_bar.columnconfigure(1, weight=1)
        self.start_button = self._widget(
            "start", ttk.Button(
                self.action_bar, command=self._start, style="Accent.TButton",
                image=self.ui_icons["play"], compound="left",
            )
        )
        self.progress = ttk.Progressbar(self.action_bar, mode="determinate", maximum=100, value=0, style="Accent.Horizontal.TProgressbar")
        self.progress_percent = ttk.Label(
            self.action_bar, text="—", width=5, anchor="e", style="Elevated.TLabel"
        )
        self.status = ttk.Label(self.action_bar, style="Muted.Elevated.TLabel")
        self.details_button = ttk.Button(
            self.action_bar, command=self._toggle_details, image=self.ui_icons["terminal"], compound="left"
        )
        self._layout_actions(True)

        self.results_box = self._widget("results", ttk.LabelFrame(home, padding=8, style="Card.TLabelframe"))
        self.results_box.grid(row=4, column=0, sticky="nsew")
        self.results_box.columnconfigure(0, weight=1)
        self.results_box.rowconfigure(1, weight=1)
        log_actions = ttk.Frame(self.results_box, style="Card.TFrame")
        log_actions.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        log_actions.columnconfigure(0, weight=1)
        self._widget(
            "open_destination", ttk.Button(
                log_actions, command=self._open_destination, image=self.ui_icons["folder"],
                compound="left",
            )
        ).grid(row=0, column=1, padx=(0, 6))
        self._widget(
            "copy_log", ttk.Button(
                log_actions, command=self._copy_log, image=self.ui_icons["terminal"],
                compound="left",
            )
        ).grid(row=0, column=2)
        self.log = tk.Text(
            self.results_box, wrap="word", state="disabled", font=("Cascadia Mono", 9),
            background=self.colors["surface_alt"], foreground=self.colors["text"],
            selectbackground=self.colors["selection"], selectforeground=self.colors["text"],
            borderwidth=0, highlightthickness=0, padx=12, pady=10,
        )
        scrollbar = FluentScrollbar(
            self.results_box, orient="vertical", command=self.log.yview
        )
        self.log_scrollbar = scrollbar
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.log.configure(state="normal")
        self.log.insert("1.0", self.tr("details_empty"))
        self.log.configure(state="disabled")
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
        self.theme_box = ModernSelect(
            appearance, variable=self.theme_name, values=[],
            command=self._theme_selected, width=24,
        )
        self.theme_box.grid(row=0, column=1, sticky="w", pady=(0, 14))
        self._widget("language_setting", ttk.Label(appearance, style="Card.TLabel")).grid(row=1, column=0, sticky="w", padx=(0, 25))
        self.language_box = ModernSelect(
            appearance, variable=self.language_name, values=list(LANGUAGES), width=24,
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
        license_scrollbar = FluentScrollbar(
            licenses, orient="vertical", command=self.license_text.yview
        )
        self.license_scrollbar = license_scrollbar
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
        for key, widgets in self.widget_groups.items():
            for widget in widgets:
                widget.configure(text=self.tr(key))
        self.conversion_buttons["photos"].configure(text=self.tr("photos_tab"))
        self.conversion_buttons["videos"].configure(text=self.tr("videos_tab"))
        self.settings_tab_buttons["appearance"].configure(text=self.tr("appearance_tab"))
        self.settings_tab_buttons["licenses"].configure(text=self.tr("licenses_tab"))
        self.settings_tab_buttons["support"].configure(text=self.tr("support_tab"))
        for name, button in self.sensitivity_buttons.items():
            button.configure(text=self.tr(name))
        self.sensitivity_help.configure(text=self.tr(f"sensitivity_{self.sensitivity.get()}"))
        for name, button in self.model_buttons.items():
            button.configure(text=self.tr(name))
        current_log = self.log.get("1.0", "end-1c").strip()
        if not current_log or current_log in {
            values["details_empty"] for values in TEXT.values()
        }:
            self.log.configure(state="normal")
            self.log.delete("1.0", "end")
            self.log.insert("1.0", self.tr("details_empty"))
            self.log.configure(state="disabled")
        self.details_button.configure(text=self.tr("hide_details" if self.details_visible else "show_details"))
        self._set_sidebar(self.sidebar_expanded)
        theme_modes = ("system", "light", "dark")
        self.theme_box.configure(values=[self.tr(f"theme_{mode}") for mode in theme_modes])
        self.theme_box.current(theme_modes.index(self.theme_mode))
        self._update_page_header()
        if self.start_button.instate(["disabled"]):
            self.status.configure(text=self.tr("running"))
        else:
            self._update_ready_status()
        if self.current_section in {"images", "convert", "enhance"}:
            self._load_source_state()
        self._refresh_feature_states()

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
        for control in self.custom_controls:
            control.refresh()
        for page in getattr(self, "scrollable_pages", ()):
            page.refresh_theme()
        for scrollbar in (
            getattr(self, "log_scrollbar", None),
            getattr(self, "license_scrollbar", None),
        ):
            if scrollbar is not None:
                scrollbar.refresh_theme()
        self.after_idle(self._update_native_titlebar)

    def _update_native_titlebar(self) -> None:
        """Use the native Windows 11 dark caption, rounded corners, and Acrylic."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes

            self.update_idletasks()
            user32 = ctypes.windll.user32
            dwmapi = ctypes.windll.dwmapi
            user32.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
            user32.GetAncestor.restype = wintypes.HWND
            user32.GetParent.argtypes = (wintypes.HWND,)
            user32.GetParent.restype = wintypes.HWND
            dwmapi.DwmSetWindowAttribute.argtypes = (
                wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
            )
            dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long
            child = self.winfo_id()
            # GA_ROOT is more reliable than a single GetParent call for Tk's
            # wrapper/child window hierarchy.
            hwnd = user32.GetAncestor(child, 2)
            if not hwnd:
                hwnd = user32.GetParent(child) or child
            enabled = ctypes.c_int(1 if self.effective_theme == "dark" else 0)
            for attribute in (20, 19):
                if dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled)
                ) == 0:
                    break
            if self.effective_theme == "dark":
                color = self.colors["window"].lstrip("#")
                red, green, blue = (
                    int(color[index:index + 2], 16) for index in (0, 2, 4)
                )
                caption_value = red | (green << 8) | (blue << 16)
                text_value = 0x00FFFFFF
            else:
                # DWMWA_COLOR_DEFAULT lets Windows follow the current system material.
                caption_value = 0xFFFFFFFF
                text_value = 0xFFFFFFFF
            for attribute, value in ((35, caption_value), (36, text_value)):
                native_color = ctypes.c_uint(value)
                dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(native_color), ctypes.sizeof(native_color)
                )

            rounded = ctypes.c_int(2)  # DWMWCP_ROUND
            backdrop = ctypes.c_int(3)  # DWMSBT_TRANSIENTWINDOW (Acrylic)
            for attribute, value in ((33, rounded), (38, backdrop)):
                dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
                )
            user32.RedrawWindow(
                hwnd, None, None, 0x0001 | 0x0100 | 0x0400
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
                (self.tr("all_files"), "*.*"),
            ]
        else:
            filetypes = [(self.tr("images_tab"), image_patterns), (self.tr("all_files"), "*.*")]
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

    def _clear_source(self) -> None:
        operation = self.current_operation
        self.source_kinds[operation] = "folder"
        self.source_folders[operation] = ""
        self.source_files[operation] = []
        self.output_folders[operation] = ""
        self.folder.set("")
        self.destination.set("")
        self._refresh_selection_summaries()

    def _use_default_destination(self) -> None:
        operation = self.current_operation
        if self.source_kinds[operation] == "files" and self.source_files[operation]:
            base = self.source_files[operation][0].parent
        elif self.source_folders[operation]:
            base = Path(self.source_folders[operation])
        else:
            self.output_folders[operation] = ""
            self.destination.set("")
            self._refresh_selection_summaries()
            return
        destination = str(base / self._default_output_name())
        self.output_folders[operation] = destination
        self.destination.set(destination)
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

    def _source_tooltip_text(self) -> str:
        operation = self.current_operation
        if self.source_kinds[operation] == "files":
            return "\n".join(str(path) for path in self.source_files[operation])
        return self.source_folders[operation] or self.tr("no_source")

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
            if source:
                extensions = (
                    photo_organizer.IMAGE_EXTENSIONS | photo_organizer.VIDEO_EXTENSIONS
                    if operation == "convert" else photo_organizer.IMAGE_EXTENSIONS
                )
                try:
                    count = sum(
                        path.is_file() and path.suffix.lower() in extensions
                        for path in Path(source).iterdir()
                    )
                    source = (
                        f"{self._compact_path(source, 44)}  ·  "
                        f"{self.tr('selected_source_count').format(count=count)}"
                    )
                except OSError:
                    pass
        self.source_display.set(self._compact_path(source) if source else self.tr("no_source"))
        destination = self.output_folders[operation]
        self.destination_display.set(
            self._compact_path(destination) if destination else self.tr("no_destination")
        )
        self._update_ready_status()

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
            if name == "settings":
                style = (
                    "Selected.Settings.Sidebar.TButton"
                    if name == section else "Settings.Sidebar.TButton"
                )
            else:
                style = "Selected.Sidebar.TButton" if name == section else "Sidebar.TButton"
            button.configure(style=style)

    def _set_sidebar(self, expanded: bool) -> None:
        self.sidebar_expanded = expanded
        self.sidebar.configure(width=228 if expanded else 68)
        if expanded:
            self.sidebar_brand.grid()
            self.sidebar_brand_text.grid()
        else:
            self.sidebar_brand.grid_remove()
            self.sidebar_brand_text.grid_remove()
        self.section_buttons["images"].configure(text=self.tr("nav_organize") if expanded else "", compound="left")
        self.section_buttons["convert"].configure(text=self.tr("nav_convert") if expanded else "", compound="left")
        self.section_buttons["enhance"].configure(text=self.tr("nav_enhance") if expanded else "", compound="left")
        self.section_buttons["settings"].configure(
            text=self.tr("settings") if expanded else "",
            image=self.ui_icons["settings"], compound="left",
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
        self._layout_selection(event.width < 760)
        self._layout_image_features(event.width < 800)
        self._layout_actions(event.width < 900)

    def _layout_image_features(self, stacked: bool) -> None:
        self.duplicate_card.grid_forget()
        self.rename_card.grid_forget()
        mode = self.widgets["simulation_title"].master.master
        mode.grid_forget()
        if stacked:
            self.duplicate_card.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            self.rename_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
            mode.grid(row=2, column=0, columnspan=2, sticky="ew")
        else:
            self.duplicate_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
            self.rename_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
            mode.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(16, 0))

    def _show_operation(self, page: str) -> None:
        self.current_operation = page
        if page == "enhance":
            self.enhance_images.set(True)
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

    def _copy_log(self) -> None:
        content = self.log.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(content)

    def _open_destination(self) -> None:
        destination = Path(self.output_folders.get(self.current_operation, ""))
        if not destination.is_dir():
            messagebox.showerror(self.tr("product"), self.tr("open_destination_error"))
            return
        try:
            if sys.platform == "win32":
                os.startfile(destination)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(destination)])
            else:
                subprocess.Popen(["xdg-open", str(destination)])
        except OSError:
            messagebox.showerror(self.tr("product"), self.tr("open_destination_error"))

    def _show_conversion_tab(self, page: str) -> None:
        self.current_conversion_tab = page
        self.convert_images.set(page == "photos")
        self.convert_videos.set(page == "videos")
        self.conversion_pages[page].tkraise()
        for name, button in self.conversion_buttons.items():
            button.configure(style="Selected.Nav.TButton" if name == page else "Nav.TButton")

    def _toggle_details(self) -> None:
        self.details_visible = not self.details_visible
        if self.details_visible:
            self.selection_area.grid_remove()
            self.operations_shell.grid_remove()
            self.main_frame.rowconfigure(4, weight=1, minsize=120)
            self.results_box.grid()
        else:
            self.results_box.grid_remove()
            self.selection_area.grid()
            self.operations_shell.grid()
            self.main_frame.rowconfigure(4, weight=0, minsize=0)
        self.details_button.configure(
            text="" if self.winfo_width() < 820 else self.tr("hide_details" if self.details_visible else "show_details")
        )

    def _sensitivity_selected(self, _event: object = None) -> None:
        self.sensitivity_help.configure(text=self.tr(f"sensitivity_{self.sensitivity.get()}"))

    def _refresh_sensitivity_cards(self) -> None:
        self._sensitivity_selected()

    def _update_rename_preview(self) -> None:
        prefix = self.rename_prefix.get().strip() or "…"
        self.rename_preview.configure(
            text=f"{prefix} (1).jpg  ·  {prefix} (2).jpg  ·  {prefix} (3).jpg"
        )

    def _refresh_feature_states(self) -> None:
        state = "normal" if self.find_duplicates.get() else "disabled"
        for button in self.sensitivity_buttons.values():
            button.configure(state=state)
        self.sensitivity_help.configure(
            text=self.tr(f"sensitivity_{self.sensitivity.get()}")
        )
        self.rename_prefix_entry.configure(
            state="normal" if self.rename_images.get() else "disabled"
        )

    def _update_ready_status(self) -> None:
        if not hasattr(self, "status") or self.processing:
            return
        operation = self.current_operation
        has_source = bool(
            self.source_files[operation]
            if self.source_kinds[operation] == "files"
            else self.source_folders[operation]
        )
        key = f"ready_{operation}" if has_source else "select_source_begin"
        self.status.configure(text=self.tr(key))

    def _enhancement_model_selected(self, _event: object = None) -> None:
        if self.enhancement_model.get() not in {"photo", "illustration"}:
            self.enhancement_model.set("photo")

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
            if self.rename_images.get():
                arguments.extend(("--rename", "--rename-prefix", self.rename_prefix.get().strip()))
        elif self.current_operation == "convert":
            if self.convert_images.get(): arguments.append("--convert-images")
            if self.convert_videos.get(): arguments.append("--convert-videos")
            arguments.extend(("--skip-duplicates", "--convert-only"))
        elif self.current_operation == "enhance":
            if self.enhance_images.get(): arguments.append("--enhance-images")
            arguments.extend(("--skip-duplicates", "--enhance-only"))
        arguments += [
            "--jpg-quality", str(self.jpg_quality.get()),
            "--image-format", self.image_format.get(),
            "--video-quality", str(self.video_quality.get()),
            "--video-format", self.video_format.get(),
        ]
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
        if (
            self.current_operation == "images"
            and self.rename_images.get()
            and not photo_organizer.valid_rename_prefix(self.rename_prefix.get())
        ):
            messagebox.showwarning(
                self.tr("invalid_prefix_title"), self.tr("invalid_prefix")
            )
            self.rename_prefix_entry.focus_set()
            return
        changes_images = self.current_operation == "images" and self.apply_changes.get()
        if changes_images and not skip_confirmation and not messagebox.askyesno(self.tr("confirm_title"), self.tr("confirm")): return
        self.log.configure(state="normal"); self.log.delete("1.0", "end"); self.log.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.progress.configure(mode="indeterminate", value=0); self.progress.start(10)
        self.progress_percent.configure(text="—")
        self.status.configure(text=self.tr("running"))
        self.processing = True
        self.current_progress_status = ""
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
        status = self.current_progress_status or self.tr("running")
        self.status.configure(text=f"{status} · {minutes:02d}:{seconds:02d}")
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
                elif event == "status":
                    self.current_progress_status = str(value)
                elif event == "done":
                    self.progress.stop(); self.start_button.configure(state="normal")
                    self.processing = False
                    self.current_progress_status = ""
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
