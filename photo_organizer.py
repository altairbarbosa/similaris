#!/usr/bin/env python3
"""Find duplicate photos, organize files, convert media, and create ZIPs."""

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


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv", ".flv", ".mts", ".m2ts"
}


@dataclass(frozen=True)
class Photo:
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


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find visually duplicate photos and organize a folder."
    )
    parser.add_argument("folder", nargs="?", default=".", type=Path)
    parser.add_argument("--apply", "--aplicar", action="store_true", help="modify files")
    parser.add_argument("--skip-duplicates", "--nao-separar", action="store_true")
    parser.add_argument("--rename", "--renomear", action="store_true", dest="rename_photos")
    parser.add_argument("--zip", action="store_true", dest="make_zip")
    parser.add_argument("--duplicates-folder", "--destino", default="duplicates")
    parser.add_argument("--zip-name", "--nome-zip", default="photos.zip")
    parser.add_argument(
        "--convert-images", "--converter-imagens", action="store_true", dest="convert_images"
    )
    parser.add_argument(
        "--convert-videos", "--converter-videos", action="store_true", dest="convert_videos"
    )
    parser.add_argument(
        "--convert-all", "--converter-tudo", action="store_true", dest="convert_all"
    )
    parser.add_argument(
        "--converted-folder", "--pasta-convertidos", default="converted"
    )
    parser.add_argument(
        "--convert-only", "--somente-converter", action="store_true", dest="convert_only",
    )
    parser.add_argument(
        "--jpg-quality", "--qualidade-jpg", type=int, default=92, metavar="1-100",
    )
    parser.add_argument(
        "--video-quality", "--qualidade-video", type=int, default=20, metavar="CRF",
    )
    parser.add_argument("--language", choices=("pt-BR", "en-US", "es-ES"), default="en-US")
    return parser.parse_args(argv)


def sha256(caminho: Path) -> str:
    resultado = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resultado.update(bloco)
    return resultado.hexdigest()


def analyze(caminho: Path) -> Photo:
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

        return Photo(
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


def are_similar(a: Photo, b: Photo) -> bool:
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


def group_duplicates(fotos: list[Photo]) -> list[list[int]]:
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
            if are_similar(foto_a, fotos[j]):
                unir(i, j)

    grupos: dict[int, list[int]] = {}
    for indice in range(len(fotos)):
        grupos.setdefault(raiz(indice), []).append(indice)
    return [grupo for grupo in grupos.values() if len(grupo) > 1]


def available_path(destino: Path) -> Path:
    if not destino.exists():
        return destino
    contador = 2
    while True:
        candidato = destino.with_name(f"{destino.stem} ({contador}){destino.suffix}")
        if not candidato.exists():
            return candidato
        contador += 1


def separate(fotos: list[Photo], grupos: list[list[int]], destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    movidas: list[Path] = []
    for grupo in grupos:
        # Preserva a maior resolução; tamanho em bytes desempata.
        ordem = sorted(grupo, key=lambda i: (fotos[i].area, fotos[i].tamanho), reverse=True)
        for indice in ordem[1:]:
            origem = fotos[indice].caminho
            alvo = available_path(destino / origem.name)
            shutil.move(origem, alvo)
            movidas.append(alvo)
    return movidas


def photos_in_folder(pasta: Path) -> list[Path]:
    return sorted(
        (p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda p: p.name.casefold(),
    )


def rename_photos(fotos: list[Path]) -> list[Path]:
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


def create_zip(fotos: list[Path], destino: Path) -> None:
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


def converted_name(origem: Path, destino: Path, extensao: str) -> Path:
    return available_path(destino / f"{origem.stem}{extensao}")


def convert_image(origem: Path, destino: Path, qualidade: int) -> Path:
    alvo = converted_name(origem, destino, ".jpg")
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


def convert_video(origem: Path, destino: Path, crf: int) -> Path:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg não encontrado; instale-o com: sudo apt install ffmpeg")
    alvo = converted_name(origem, destino, ".mp4")
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


def find_ffmpeg() -> str | None:
    encontrado = shutil.which("ffmpeg")
    if encontrado:
        return encontrado
    base_empacotada = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidatos = [
        base_empacotada / "ffmpeg",
        base_empacotada / "ffmpeg.exe",
        Path(sys.executable).resolve().parent / "ffmpeg.exe",
        Path(sys.executable).resolve().parent / "ffmpeg",
        Path(__file__).resolve().parent / "ffmpeg.exe",
        Path(__file__).resolve().parent / "ffmpeg",
    ]
    for candidato in candidatos:
        if candidato.is_file():
            return str(candidato)
    return None


OUTPUT_TRANSLATIONS = {
    "en-US": {
        "  imagem:": "  image:", "  vídeo:": "  video:", "Pasta inexistente:": "Folder does not exist:",
        "deve estar entre": "must be between", "Conversão solicitada:": "Requested conversion:",
        "imagens para JPG": "images to JPG", "vídeos para MP4": "videos to MP4",
        "Simulação: os originais seriam preservados e os resultados iriam para": "Simulation: originals would be preserved and results would go to",
        "Convertendo arquivos para": "Converting files to", "Conversões concluídas:": "Conversions completed:",
        "imagem(ns)": "image(s)", "vídeo(s)": "video(s)", "Falharam": "Failed:",
        "conversão(ões):": "conversion(s)", "Use --aplicar para realizar as conversões.": "Use --apply to perform the conversions.",
        "Nenhuma imagem compatível encontrada.": "No compatible images found.", "renomear as imagens": "rename images",
        "criar": "create", "Simulação:": "Simulation:", "Use --aplicar para realizar as alterações.": "Use --apply to make changes.",
        "Renomeadas": "Renamed", "imagens.": "images.", "ZIP criado:": "ZIP created:", "Analisando": "Analyzing",
        "imagens em": "images in", "processadas": "processed", "Encontrados": "Found", "grupos e": "groups and",
        "arquivos repetidos.": "duplicate files.", "Grupo": "Group", "manter": "keep", "separar": "separate",
        "Aviso:": "Warning:", "arquivo(s) não puderam ser lidos:": "file(s) could not be read:",
        "Simulação concluída.": "Simulation completed.", "Concluído:": "Completed:", "repetida(s) movida(s) para": "duplicate(s) moved to",
        "exige uma opção --converter-*.": "requires a --convert-* option.",
    },
    "es-ES": {
        "  imagem:": "  imagen:", "  vídeo:": "  vídeo:", "Pasta inexistente:": "La carpeta no existe:",
        "deve estar entre": "debe estar entre", "Conversão solicitada:": "Conversión solicitada:",
        "imagens para JPG": "imágenes a JPG", "vídeos para MP4": "vídeos a MP4",
        "Simulação: os originais seriam preservados e os resultados iriam para": "Simulación: se conservarían los originales y los resultados irían a",
        "Convertendo arquivos para": "Convirtiendo archivos a", "Conversões concluídas:": "Conversiones completadas:",
        "imagem(ns)": "imagen(es)", "vídeo(s)": "vídeo(s)", "Falharam": "Fallaron",
        "conversão(ões):": "conversión(es):", "Use --aplicar para realizar as conversões.": "Use --apply para realizar las conversiones.",
        "Nenhuma imagem compatível encontrada.": "No se encontraron imágenes compatibles.", "renomear as imagens": "renombrar las imágenes",
        "criar": "crear", "Simulação:": "Simulación:", "Use --aplicar para realizar as alterações.": "Use --apply para realizar los cambios.",
        "Renomeadas": "Renombradas", "imagens.": "imágenes.", "ZIP criado:": "ZIP creado:", "Analisando": "Analizando",
        "imagens em": "imágenes en", "processadas": "procesadas", "Encontrados": "Encontrados", "grupos e": "grupos y",
        "arquivos repetidos.": "archivos duplicados.", "Grupo": "Grupo", "manter": "conservar", "separar": "separar",
        "Aviso:": "Aviso:", "arquivo(s) não puderam ser lidos:": "archivo(s) no se pudieron leer:",
        "Simulação concluída.": "Simulación completada.", "Concluído:": "Completado:", "repetida(s) movida(s) para": "duplicado(s) movido(s) a",
        "exige uma opção --converter-*.": "requiere una opción --convert-*.",
    },
}


def localized_print(language: str, *values: object, **kwargs: object) -> None:
    text = " ".join(str(value) for value in values)
    for source, translation in OUTPUT_TRANSLATIONS.get(language, {}).items():
        text = text.replace(source, translation)
    print(text, **kwargs)


def run_conversions(args: argparse.Namespace, pasta: Path) -> tuple[int, int, list[str]]:
    imagens = args.convert_images or args.convert_all
    videos = args.convert_videos or args.convert_all
    if not imagens and not videos:
        return 0, 0, []

    destino = pasta / args.converted_folder
    destino.mkdir(parents=True, exist_ok=True)
    feitas_imagens = feitas_videos = 0
    falhas: list[str] = []
    entradas = sorted((p for p in pasta.iterdir() if p.is_file()), key=lambda p: p.name.casefold())

    if imagens:
        for origem in (p for p in entradas if p.suffix.lower() in IMAGE_EXTENSIONS):
            try:
                alvo = convert_image(origem, destino, args.jpg_quality)
                feitas_imagens += 1
                localized_print(args.language, f"  imagem: {origem.name} -> {alvo.name}")
            except Exception as erro:
                falhas.append(f"{origem.name}: {erro}")

    if videos:
        for origem in (p for p in entradas if p.suffix.lower() in VIDEO_EXTENSIONS):
            try:
                alvo = convert_video(origem, destino, args.video_quality)
                feitas_videos += 1
                localized_print(args.language, f"  vídeo: {origem.name} -> {alvo.name}")
            except Exception as erro:
                falhas.append(f"{origem.name}: {erro}")
    return feitas_imagens, feitas_videos, falhas


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    pasta = args.folder.expanduser().resolve()
    if not pasta.is_dir():
        localized_print(args.language, f"Pasta inexistente: {pasta}", file=sys.stderr)
        return 2

    if not 1 <= args.jpg_quality <= 100:
        localized_print(args.language, "--qualidade-jpg deve estar entre 1 e 100.", file=sys.stderr)
        return 2
    if not 0 <= args.video_quality <= 51:
        localized_print(args.language, "--qualidade-video deve estar entre 0 e 51.", file=sys.stderr)
        return 2

    quer_converter = args.convert_images or args.convert_videos or args.convert_all
    if args.convert_only and not quer_converter:
        localized_print(args.language, "--somente-converter exige uma opção --converter-*.", file=sys.stderr)
        return 2
    if quer_converter and not args.apply:
        tipos = []
        if args.convert_images or args.convert_all:
            tipos.append("imagens para JPG")
        if args.convert_videos or args.convert_all:
            tipos.append("vídeos para MP4")
        localized_print(args.language, f"Conversão solicitada: {' e '.join(tipos)}.")
        localized_print(args.language, "Simulação: os originais seriam preservados e os resultados iriam para "
              f"{pasta / args.converted_folder}.")

    if quer_converter and args.apply:
        localized_print(args.language, f"Convertendo arquivos para {pasta / args.converted_folder}...")
        n_imagens, n_videos, falhas_conversao = run_conversions(args, pasta)
        localized_print(args.language, f"Conversões concluídas: {n_imagens} imagem(ns), {n_videos} vídeo(s).")
        if falhas_conversao:
            localized_print(args.language, f"Falharam {len(falhas_conversao)} conversão(ões):")
            for falha in falhas_conversao:
                localized_print(args.language, f"  {falha}")

    if args.convert_only:
        if not args.apply:
            localized_print(args.language, "Use --aplicar para realizar as conversões.")
        return 0

    caminhos = photos_in_folder(pasta)
    if not caminhos:
        localized_print(args.language, "Nenhuma imagem compatível encontrada.")
        return 0

    if args.skip_duplicates:
        operacoes = []
        if args.rename_photos:
            operacoes.append("rename_photos as imagens")
        if args.make_zip:
            operacoes.append(f"criar {args.zip_name}")
        if not args.apply:
            if operacoes:
                localized_print(args.language, "Simulação: " + " e ".join(operacoes) + ".")
                localized_print(args.language, "Use --aplicar para realizar as alterações.")
            return 0
        restantes = caminhos
        if args.rename_photos:
            restantes = rename_photos(restantes)
            localized_print(args.language, f"Renomeadas {len(restantes)} imagens.")
        if args.make_zip:
            create_zip(restantes, pasta / args.zip_name)
            localized_print(args.language, f"ZIP criado: {pasta / args.zip_name}")
        return 0

    localized_print(args.language, f"Analisando {len(caminhos)} imagens em {pasta}...")
    fotos: list[Photo] = []
    falhas: list[tuple[Path, str]] = []
    for numero, caminho in enumerate(caminhos, 1):
        try:
            fotos.append(analyze(caminho))
        except (OSError, UnidentifiedImageError) as erro:
            falhas.append((caminho, str(erro)))
        if numero % 100 == 0:
            localized_print(args.language, f"  {numero}/{len(caminhos)} processadas")

    grupos = group_duplicates(fotos)
    quantidade = sum(len(grupo) - 1 for grupo in grupos)
    localized_print(args.language, f"Encontrados {len(grupos)} grupos e {quantidade} arquivos repetidos.")
    for numero, grupo in enumerate(grupos, 1):
        ordem = sorted(grupo, key=lambda i: (fotos[i].area, fotos[i].tamanho), reverse=True)
        localized_print(args.language, f"  Grupo {numero}: manter {fotos[ordem[0]].caminho.name}")
        for indice in ordem[1:]:
            localized_print(args.language, f"    separate {fotos[indice].caminho.name}")

    if falhas:
        localized_print(args.language, f"Aviso: {len(falhas)} arquivo(s) não puderam ser lidos:")
        for caminho, erro in falhas:
            localized_print(args.language, f"  {caminho.name}: {erro}")

    if not args.apply:
        localized_print(args.language, "\nSimulação concluída. Use --aplicar para realizar as alterações.")
        return 0

    destino = pasta / args.duplicates_folder
    movidas = separate(fotos, grupos, destino)
    restantes = photos_in_folder(pasta)
    if args.rename_photos:
        restantes = rename_photos(restantes)
    if args.make_zip:
        create_zip(restantes, pasta / args.zip_name)

    localized_print(args.language, f"\nConcluído: {len(movidas)} repetida(s) movida(s) para {destino}.")
    if args.rename_photos:
        localized_print(args.language, f"Renomeadas {len(restantes)} imagens.")
    if args.make_zip:
        localized_print(args.language, f"ZIP criado: {pasta / args.zip_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
