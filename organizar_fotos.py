#!/usr/bin/env python3
"""Encontra fotos duplicadas, separa-as, renomeia e cria um ZIP opcional."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError
    import imagehash
    import numpy as np
except ImportError:
    print(
        "Dependências ausentes. Instale com:\n"
        "  python3 -m pip install Pillow ImageHash\n",
        file=sys.stderr,
    )
    raise SystemExit(2)


EXTENSOES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
EXTENSOES_VIDEO = {
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv", ".flv", ".mts", ".m2ts"
}


@dataclass(frozen=True)
class Foto:
    caminho: Path
    largura: int
    altura: int
    tamanho: int
    hash_arquivo: str
    phash: object
    dhash: object
    ahash: object
    cinza: object
    bordas: object

    @property
    def area(self) -> int:
        return self.largura * self.altura


def argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detecta fotos visualmente repetidas e organiza uma pasta."
    )
    parser.add_argument("pasta", nargs="?", default=".", type=Path)
    parser.add_argument("--aplicar", action="store_true", help="move/renomeia arquivos")
    parser.add_argument("--nao-separar", action="store_true", help="não detecta nem separa repetidas")
    parser.add_argument("--renomear", action="store_true", help='renomeia para "img (N).ext"')
    parser.add_argument("--zip", action="store_true", dest="criar_zip", help="cria fotos.zip")
    parser.add_argument("--destino", default="repetidas", help="pasta das duplicatas")
    parser.add_argument("--nome-zip", default="fotos.zip", help="nome do ZIP")
    parser.add_argument(
        "--converter-imagens", action="store_true", help="converte imagens para JPG otimizado"
    )
    parser.add_argument(
        "--converter-videos", action="store_true", help="converte vídeos para MP4 otimizado"
    )
    parser.add_argument(
        "--converter-tudo", action="store_true", help="converte imagens e vídeos"
    )
    parser.add_argument(
        "--pasta-convertidos", default="convertidos", help="destino das conversões"
    )
    parser.add_argument(
        "--somente-converter", action="store_true",
        help="não procura nem separa duplicatas após converter",
    )
    parser.add_argument(
        "--qualidade-jpg", type=int, default=92, metavar="1-100",
        help="qualidade dos JPGs convertidos (padrão: 92)",
    )
    parser.add_argument(
        "--qualidade-video", type=int, default=20, metavar="CRF",
        help="qualidade H.264: menor é melhor e maior (padrão: 20)",
    )
    return parser.parse_args(argv)


def sha256(caminho: Path) -> str:
    resultado = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resultado.update(bloco)
    return resultado.hexdigest()


def analisar(caminho: Path) -> Foto:
    with Image.open(caminho) as origem:
        largura, altura = origem.size
        orientacao = origem.getexif().get(274, 1)
        if orientacao in {5, 6, 7, 8}:
            largura, altura = altura, largura

        # JPEGs grandes podem ser decodificados diretamente em resolução reduzida.
        origem.draft("RGB", (512, 512))
        imagem = ImageOps.exif_transpose(origem)
        imagem.thumbnail((512, 512))
        imagem = imagem.convert("RGB")
        cinza_imagem = ImageOps.autocontrast(ImageOps.grayscale(imagem)).resize(
            (64, 64), Image.Resampling.LANCZOS
        )
        bordas_imagem = cinza_imagem.filter(ImageFilter.FIND_EDGES)

        def assinatura(imagem_assinatura: Image.Image) -> object:
            valores = np.asarray(imagem_assinatura, dtype=np.float32).reshape(-1)
            valores = (valores - valores.mean()) / (valores.std() + 1e-6)
            return valores.astype(np.float16)

        return Foto(
            caminho=caminho,
            largura=largura,
            altura=altura,
            tamanho=caminho.stat().st_size,
            hash_arquivo=sha256(caminho),
            phash=imagehash.phash(imagem, hash_size=16),
            dhash=imagehash.dhash(imagem, hash_size=16),
            ahash=imagehash.average_hash(imagem, hash_size=8),
            cinza=assinatura(cinza_imagem),
            bordas=assinatura(bordas_imagem),
        )


def semelhantes(a: Foto, b: Foto) -> bool:
    proporcao_a = a.largura / a.altura
    proporcao_b = b.largura / b.altura
    if abs(proporcao_a - proporcao_b) / proporcao_a > 0.006:
        return False

    pd = a.phash - b.phash
    dd = a.dhash - b.dhash
    ad = a.ahash - b.ahash
    correlacao_cinza = float(
        np.dot(a.cinza.astype(np.float32), b.cinza.astype(np.float32)) / 4096
    )
    correlacao_bordas = float(
        np.dot(a.bordas.astype(np.float32), b.bordas.astype(np.float32)) / 4096
    )

    # O primeiro limite encontra recompressões quase idênticas. O segundo é
    # tolerante a cor, brilho, contraste e filtros, mas exige bordas coincidentes
    # para não confundir fotografias consecutivas com poses diferentes.
    quase_identica = pd <= 10 and dd <= 20 and ad <= 8 and correlacao_cinza >= 0.94
    editada = pd <= 35 and correlacao_cinza >= 0.88 and correlacao_bordas >= 0.75
    return quase_identica or editada


def agrupar(fotos: list[Foto]) -> list[list[int]]:
    pais = list(range(len(fotos)))

    def raiz(indice: int) -> int:
        while pais[indice] != indice:
            pais[indice] = pais[pais[indice]]
            indice = pais[indice]
        return indice

    def unir(a: int, b: int) -> None:
        a, b = raiz(a), raiz(b)
        if a != b:
            pais[b] = a

    hashes: dict[str, list[int]] = {}
    for indice, foto in enumerate(fotos):
        hashes.setdefault(foto.hash_arquivo, []).append(indice)
    for indices in hashes.values():
        for indice in indices[1:]:
            unir(indices[0], indice)

    for i, foto_a in enumerate(fotos):
        for j in range(i + 1, len(fotos)):
            if semelhantes(foto_a, fotos[j]):
                unir(i, j)

    grupos: dict[int, list[int]] = {}
    for indice in range(len(fotos)):
        grupos.setdefault(raiz(indice), []).append(indice)
    return [grupo for grupo in grupos.values() if len(grupo) > 1]


def caminho_livre(destino: Path) -> Path:
    if not destino.exists():
        return destino
    contador = 2
    while True:
        candidato = destino.with_name(f"{destino.stem} ({contador}){destino.suffix}")
        if not candidato.exists():
            return candidato
        contador += 1


def separar(fotos: list[Foto], grupos: list[list[int]], destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    movidas: list[Path] = []
    for grupo in grupos:
        # Preserva a maior resolução; tamanho em bytes desempata.
        ordem = sorted(grupo, key=lambda i: (fotos[i].area, fotos[i].tamanho), reverse=True)
        for indice in ordem[1:]:
            origem = fotos[indice].caminho
            alvo = caminho_livre(destino / origem.name)
            shutil.move(origem, alvo)
            movidas.append(alvo)
    return movidas


def fotos_da_pasta(pasta: Path) -> list[Path]:
    return sorted(
        (p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSOES),
        key=lambda p: p.name.casefold(),
    )


def renomear(fotos: list[Path]) -> list[Path]:
    token = uuid.uuid4().hex
    temporarios: list[tuple[Path, str]] = []
    for numero, origem in enumerate(fotos, 1):
        temporario = origem.with_name(f".organizar-{token}-{numero}.tmp")
        origem.rename(temporario)
        temporarios.append((temporario, origem.suffix.lower()))

    resultado: list[Path] = []
    for numero, (temporario, extensao) in enumerate(temporarios, 1):
        alvo = temporario.with_name(f"img ({numero}){extensao}")
        temporario.rename(alvo)
        resultado.append(alvo)
    return resultado


def compactar(fotos: list[Path], destino: Path) -> None:
    temporario = destino.with_name(f".{destino.name}.{uuid.uuid4().hex}.tmp")
    try:
        with zipfile.ZipFile(
            temporario, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True
        ) as arquivo_zip:
            for foto in fotos:
                arquivo_zip.write(foto, arcname=foto.name)
        os.replace(temporario, destino)
    finally:
        if temporario.exists():
            temporario.unlink()


def nome_convertido(origem: Path, destino: Path, extensao: str) -> Path:
    return caminho_livre(destino / f"{origem.stem}{extensao}")


def converter_imagem(origem: Path, destino: Path, qualidade: int) -> Path:
    alvo = nome_convertido(origem, destino, ".jpg")
    temporario = alvo.with_name(f".{alvo.name}.{uuid.uuid4().hex}.tmp")
    try:
        with Image.open(origem) as imagem:
            imagem = ImageOps.exif_transpose(imagem)
            if imagem.mode in {"RGBA", "LA"} or (
                imagem.mode == "P" and "transparency" in imagem.info
            ):
                rgba = imagem.convert("RGBA")
                fundo = Image.new("RGB", rgba.size, "white")
                fundo.paste(rgba, mask=rgba.getchannel("A"))
                imagem = fundo
            else:
                imagem = imagem.convert("RGB")
            # Não redimensiona: preserva toda a resolução da imagem de origem.
            imagem.save(
                temporario,
                format="JPEG",
                quality=qualidade,
                optimize=True,
                progressive=True,
                subsampling=0,
            )
        os.replace(temporario, alvo)
        return alvo
    finally:
        if temporario.exists():
            temporario.unlink()


def converter_video(origem: Path, destino: Path, crf: int) -> Path:
    ffmpeg = localizar_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg não encontrado; instale-o com: sudo apt install ffmpeg")
    alvo = nome_convertido(origem, destino, ".mp4")
    temporario = alvo.with_name(f".{alvo.stem}.{uuid.uuid4().hex}.mp4")
    comando = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(origem),
        "-map", "0:v:0", "-map", "0:a?", "-map_metadata", "0",
        "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
        # H.264 exige dimensões pares; reduz no máximo um pixel quando necessário.
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(temporario),
    ]
    try:
        subprocess.run(comando, check=True)
        os.replace(temporario, alvo)
        return alvo
    except subprocess.CalledProcessError as erro:
        raise RuntimeError(f"ffmpeg falhou com código {erro.returncode}") from erro
    finally:
        if temporario.exists():
            temporario.unlink()


def localizar_ffmpeg() -> str | None:
    encontrado = shutil.which("ffmpeg")
    if encontrado:
        return encontrado
    candidatos = [
        Path(sys.executable).resolve().parent / "ffmpeg.exe",
        Path(__file__).resolve().parent / "ffmpeg.exe",
    ]
    for candidato in candidatos:
        if candidato.is_file():
            return str(candidato)
    return None


def executar_conversoes(args: argparse.Namespace, pasta: Path) -> tuple[int, int, list[str]]:
    imagens = args.converter_imagens or args.converter_tudo
    videos = args.converter_videos or args.converter_tudo
    if not imagens and not videos:
        return 0, 0, []

    destino = pasta / args.pasta_convertidos
    destino.mkdir(parents=True, exist_ok=True)
    feitas_imagens = feitas_videos = 0
    falhas: list[str] = []
    entradas = sorted((p for p in pasta.iterdir() if p.is_file()), key=lambda p: p.name.casefold())

    if imagens:
        for origem in (p for p in entradas if p.suffix.lower() in EXTENSOES):
            try:
                alvo = converter_imagem(origem, destino, args.qualidade_jpg)
                feitas_imagens += 1
                print(f"  imagem: {origem.name} -> {alvo.name}")
            except Exception as erro:
                falhas.append(f"{origem.name}: {erro}")

    if videos:
        for origem in (p for p in entradas if p.suffix.lower() in EXTENSOES_VIDEO):
            try:
                alvo = converter_video(origem, destino, args.qualidade_video)
                feitas_videos += 1
                print(f"  vídeo: {origem.name} -> {alvo.name}")
            except Exception as erro:
                falhas.append(f"{origem.name}: {erro}")
    return feitas_imagens, feitas_videos, falhas


def main(argv: list[str] | None = None) -> int:
    args = argumentos(argv)
    pasta = args.pasta.expanduser().resolve()
    if not pasta.is_dir():
        print(f"Pasta inexistente: {pasta}", file=sys.stderr)
        return 2

    if not 1 <= args.qualidade_jpg <= 100:
        print("--qualidade-jpg deve estar entre 1 e 100.", file=sys.stderr)
        return 2
    if not 0 <= args.qualidade_video <= 51:
        print("--qualidade-video deve estar entre 0 e 51.", file=sys.stderr)
        return 2

    quer_converter = args.converter_imagens or args.converter_videos or args.converter_tudo
    if args.somente_converter and not quer_converter:
        print("--somente-converter exige uma opção --converter-*.", file=sys.stderr)
        return 2
    if quer_converter and not args.aplicar:
        tipos = []
        if args.converter_imagens or args.converter_tudo:
            tipos.append("imagens para JPG")
        if args.converter_videos or args.converter_tudo:
            tipos.append("vídeos para MP4")
        print(f"Conversão solicitada: {' e '.join(tipos)}.")
        print("Simulação: os originais seriam preservados e os resultados iriam para "
              f"{pasta / args.pasta_convertidos}.")

    if quer_converter and args.aplicar:
        print(f"Convertendo arquivos para {pasta / args.pasta_convertidos}...")
        n_imagens, n_videos, falhas_conversao = executar_conversoes(args, pasta)
        print(f"Conversões concluídas: {n_imagens} imagem(ns), {n_videos} vídeo(s).")
        if falhas_conversao:
            print(f"Falharam {len(falhas_conversao)} conversão(ões):")
            for falha in falhas_conversao:
                print(f"  {falha}")

    if args.somente_converter:
        if not args.aplicar:
            print("Use --aplicar para realizar as conversões.")
        return 0

    caminhos = fotos_da_pasta(pasta)
    if not caminhos:
        print("Nenhuma imagem compatível encontrada.")
        return 0

    if args.nao_separar:
        operacoes = []
        if args.renomear:
            operacoes.append("renomear as imagens")
        if args.criar_zip:
            operacoes.append(f"criar {args.nome_zip}")
        if not args.aplicar:
            if operacoes:
                print("Simulação: " + " e ".join(operacoes) + ".")
                print("Use --aplicar para realizar as alterações.")
            return 0
        restantes = caminhos
        if args.renomear:
            restantes = renomear(restantes)
            print(f"Renomeadas {len(restantes)} imagens.")
        if args.criar_zip:
            compactar(restantes, pasta / args.nome_zip)
            print(f"ZIP criado: {pasta / args.nome_zip}")
        return 0

    print(f"Analisando {len(caminhos)} imagens em {pasta}...")
    fotos: list[Foto] = []
    falhas: list[tuple[Path, str]] = []
    for numero, caminho in enumerate(caminhos, 1):
        try:
            fotos.append(analisar(caminho))
        except (OSError, UnidentifiedImageError) as erro:
            falhas.append((caminho, str(erro)))
        if numero % 100 == 0:
            print(f"  {numero}/{len(caminhos)} processadas")

    grupos = agrupar(fotos)
    quantidade = sum(len(grupo) - 1 for grupo in grupos)
    print(f"Encontrados {len(grupos)} grupos e {quantidade} arquivos repetidos.")
    for numero, grupo in enumerate(grupos, 1):
        ordem = sorted(grupo, key=lambda i: (fotos[i].area, fotos[i].tamanho), reverse=True)
        print(f"  Grupo {numero}: manter {fotos[ordem[0]].caminho.name}")
        for indice in ordem[1:]:
            print(f"    separar {fotos[indice].caminho.name}")

    if falhas:
        print(f"Aviso: {len(falhas)} arquivo(s) não puderam ser lidos:")
        for caminho, erro in falhas:
            print(f"  {caminho.name}: {erro}")

    if not args.aplicar:
        print("\nSimulação concluída. Use --aplicar para realizar as alterações.")
        return 0

    destino = pasta / args.destino
    movidas = separar(fotos, grupos, destino)
    restantes = fotos_da_pasta(pasta)
    if args.renomear:
        restantes = renomear(restantes)
    if args.criar_zip:
        compactar(restantes, pasta / args.nome_zip)

    print(f"\nConcluído: {len(movidas)} repetida(s) movida(s) para {destino}.")
    if args.renomear:
        print(f"Renomeadas {len(restantes)} imagens.")
    if args.criar_zip:
        print(f"ZIP criado: {pasta / args.nome_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
