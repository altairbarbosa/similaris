#!/usr/bin/env python3
"""Interface gráfica do Organizador de Fotos para Windows."""

from __future__ import annotations

import contextlib
import queue
import threading
import traceback
import tkinter as tk
import sys
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import organizar_fotos


class EscritorFila:
    def __init__(self, fila: queue.Queue[tuple[str, object]]) -> None:
        self.fila = fila

    def write(self, texto: str) -> int:
        if texto:
            self.fila.put(("texto", texto))
        return len(texto)

    def flush(self) -> None:
        pass


class Interface(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Organizador de Fotos e Vídeos")
        self.geometry("820x700")
        self.minsize(720, 620)
        self.fila: queue.Queue[tuple[str, object]] = queue.Queue()

        self.pasta = tk.StringVar()
        self.aplicar = tk.BooleanVar(value=False)
        self.separar = tk.BooleanVar(value=True)
        self.converter_imagens = tk.BooleanVar(value=False)
        self.converter_videos = tk.BooleanVar(value=False)
        self.renomear = tk.BooleanVar(value=False)
        self.criar_zip = tk.BooleanVar(value=False)
        self.qualidade_jpg = tk.IntVar(value=92)
        self.qualidade_video = tk.IntVar(value=20)

        self._montar()
        self.after(100, self._ler_fila)

    def _montar(self) -> None:
        principal = ttk.Frame(self, padding=18)
        principal.pack(fill="both", expand=True)
        principal.columnconfigure(0, weight=1)
        principal.rowconfigure(5, weight=1)

        ttk.Label(principal, text="Organizador de Fotos e Vídeos", font=("Segoe UI", 17, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 14)
        )

        pasta_frame = ttk.LabelFrame(principal, text="Pasta dos arquivos", padding=10)
        pasta_frame.grid(row=1, column=0, sticky="ew")
        pasta_frame.columnconfigure(0, weight=1)
        ttk.Entry(pasta_frame, textvariable=self.pasta).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(pasta_frame, text="Selecionar...", command=self._selecionar).grid(row=0, column=1)

        opcoes = ttk.LabelFrame(principal, text="O que deseja fazer?", padding=10)
        opcoes.grid(row=2, column=0, sticky="ew", pady=12)
        ttk.Checkbutton(opcoes, text="Detectar e separar imagens repetidas", variable=self.separar).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(opcoes, text="Converter imagens para JPG", variable=self.converter_imagens).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(opcoes, text="Converter vídeos para MP4", variable=self.converter_videos).grid(row=2, column=0, sticky="w")
        ttk.Checkbutton(opcoes, text='Renomear imagens como "img (N)"', variable=self.renomear).grid(row=0, column=1, sticky="w", padx=(35, 0))
        ttk.Checkbutton(opcoes, text="Criar fotos.zip", variable=self.criar_zip).grid(row=1, column=1, sticky="w", padx=(35, 0))

        qualidade = ttk.Frame(opcoes)
        qualidade.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Label(qualidade, text="Qualidade JPG:").pack(side="left")
        ttk.Spinbox(qualidade, from_=1, to=100, width=5, textvariable=self.qualidade_jpg).pack(side="left", padx=(5, 25))
        ttk.Label(qualidade, text="Qualidade do vídeo (CRF):").pack(side="left")
        ttk.Spinbox(qualidade, from_=0, to=51, width=5, textvariable=self.qualidade_video).pack(side="left", padx=5)
        ttk.Label(qualidade, text="(menor = melhor)").pack(side="left")

        modo = ttk.LabelFrame(principal, text="Modo", padding=10)
        modo.grid(row=3, column=0, sticky="ew")
        ttk.Radiobutton(modo, text="Somente simular (recomendado primeiro)", variable=self.aplicar, value=False).pack(side="left")
        ttk.Radiobutton(modo, text="Aplicar alterações", variable=self.aplicar, value=True).pack(side="left", padx=25)

        botoes = ttk.Frame(principal)
        botoes.grid(row=4, column=0, sticky="ew", pady=12)
        self.botao = ttk.Button(botoes, text="Iniciar", command=self._iniciar)
        self.botao.pack(side="left")
        self.progresso = ttk.Progressbar(botoes, mode="indeterminate", length=220)
        self.progresso.pack(side="left", padx=15)
        self.status = ttk.Label(botoes, text="Pronto")
        self.status.pack(side="left")
        ttk.Button(botoes, text="Sobre e licenças", command=self._sobre).pack(side="right")

        log_frame = ttk.LabelFrame(principal, text="Progresso e resultados", padding=6)
        log_frame.grid(row=5, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = tk.Text(log_frame, wrap="word", state="disabled", font=("Consolas", 9))
        barra = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=barra.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")

    def _selecionar(self) -> None:
        selecionada = filedialog.askdirectory(title="Selecione a pasta")
        if selecionada:
            self.pasta.set(selecionada)

    def _sobre(self) -> None:
        janela = tk.Toplevel(self)
        janela.title("Sobre e licenças")
        janela.geometry("680x480")
        texto = tk.Text(janela, wrap="word", padx=12, pady=12)
        barra = ttk.Scrollbar(janela, orient="vertical", command=texto.yview)
        texto.configure(yscrollcommand=barra.set)
        texto.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        partes = ["Organizador de Fotos e Vídeos\n\n"]
        for nome in ("AVISOS_DE_TERCEIROS.txt", "GPL-3.0.txt"):
            arquivo = base / nome
            if arquivo.is_file():
                partes.append(arquivo.read_text(encoding="utf-8", errors="replace"))
                partes.append("\n\n")
        texto.insert("1.0", "".join(partes))
        texto.configure(state="disabled")

    def _argumentos(self) -> list[str]:
        args = [self.pasta.get()]
        if self.aplicar.get():
            args.append("--aplicar")
        if self.converter_imagens.get():
            args.append("--converter-imagens")
        if self.converter_videos.get():
            args.append("--converter-videos")
        if not self.separar.get():
            args.append("--nao-separar")
        if self.renomear.get():
            args.append("--renomear")
        if self.criar_zip.get():
            args.append("--zip")
        args += ["--qualidade-jpg", str(self.qualidade_jpg.get())]
        args += ["--qualidade-video", str(self.qualidade_video.get())]
        return args

    def _iniciar(self) -> None:
        pasta = Path(self.pasta.get()).expanduser()
        if not pasta.is_dir():
            messagebox.showerror("Pasta inválida", "Selecione uma pasta válida.")
            return
        if not any((self.separar.get(), self.converter_imagens.get(), self.converter_videos.get(), self.renomear.get(), self.criar_zip.get())):
            messagebox.showwarning("Nenhuma operação", "Marque ao menos uma operação.")
            return
        if self.aplicar.get() and not messagebox.askyesno(
            "Confirmar alterações", "Deseja aplicar as operações selecionadas? Os originais convertidos serão preservados."
        ):
            return

        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.botao.configure(state="disabled")
        self.progresso.start(10)
        self.status.configure(text="Processando...")
        threading.Thread(target=self._executar, args=(self._argumentos(),), daemon=True).start()

    def _executar(self, args: list[str]) -> None:
        escritor = EscritorFila(self.fila)
        try:
            with contextlib.redirect_stdout(escritor), contextlib.redirect_stderr(escritor):
                codigo = organizar_fotos.main(args)
            self.fila.put(("fim", codigo))
        except Exception:
            self.fila.put(("texto", "\nERRO INESPERADO:\n" + traceback.format_exc()))
            self.fila.put(("fim", 1))

    def _ler_fila(self) -> None:
        try:
            while True:
                tipo, valor = self.fila.get_nowait()
                if tipo == "texto":
                    self.log.configure(state="normal")
                    self.log.insert("end", str(valor))
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif tipo == "fim":
                    self.progresso.stop()
                    self.botao.configure(state="normal")
                    sucesso = int(valor) == 0
                    self.status.configure(text="Concluído" if sucesso else "Concluído com erro")
                    if sucesso:
                        messagebox.showinfo("Organizador", "Processamento concluído.")
                    else:
                        messagebox.showerror("Organizador", "O processamento terminou com erro. Consulte os resultados.")
        except queue.Empty:
            pass
        self.after(100, self._ler_fila)


if __name__ == "__main__":
    Interface().mainloop()
