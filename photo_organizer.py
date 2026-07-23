#!/usr/bin/env python3
"""Find duplicate photos, organize images, and convert media."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

try:
    from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError
    import cv2
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
WINDOWS_CREATE_NO_WINDOW = 0x08000000


def subprocess_window_options() -> dict[str, int]:
    """Prevent bundled console tools from opening a terminal on Windows."""
    return {"creationflags": WINDOWS_CREATE_NO_WINDOW} if sys.platform == "win32" else {}


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
    grayscale: object
    color_histogram: object
    keypoints: object
    descriptors: object

    @property
    def area(self) -> int:
        return self.largura * self.altura


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find visually duplicate photos and organize a folder."
    )
    parser.add_argument("folder", nargs="?", default=".", type=Path)
    parser.add_argument("--files", nargs="+", type=Path, default=None)
    parser.add_argument("--output-folder", type=Path, default=None)
    parser.add_argument("--apply", "--aplicar", action="store_true", help="modify files")
    parser.add_argument("--skip-duplicates", "--nao-separar", action="store_true")
    parser.add_argument("--rename", "--renomear", action="store_true", dest="rename_photos")
    parser.add_argument("--duplicates-folder", "--destino", default="duplicates")
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
    parser.add_argument("--enhance-images", action="store_true", dest="enhance_images")
    parser.add_argument("--enhance-only", action="store_true", dest="enhance_only")
    parser.add_argument("--enhanced-folder", default="enhanced")
    parser.add_argument("--enhancement-scale", type=int, choices=(2, 3, 4), default=2)
    parser.add_argument(
        "--enhancement-model", choices=("photo", "illustration"), default="photo"
    )
    parser.add_argument(
        "--jpg-quality", "--qualidade-jpg", type=int, default=92, metavar="1-100",
    )
    parser.add_argument(
        "--video-quality", "--qualidade-video", type=int, default=20, metavar="CRF",
    )
    parser.add_argument("--language", choices=("pt-BR", "en-US", "es-ES"), default="en-US")
    parser.add_argument(
        "--sensitivity", choices=("conservative", "balanced", "sensitive"),
        default="balanced", help="duplicate detection sensitivity",
    )
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
        rgb_array = np.asarray(imagem, dtype=np.uint8)
        grayscale = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2GRAY)
        orb = cv2.ORB_create(nfeatures=1200, scaleFactor=1.2, nlevels=8, fastThreshold=12)
        keypoints, descriptors = orb.detectAndCompute(grayscale, None)
        hsv = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2HSV)
        color_histogram = cv2.calcHist([hsv], [0, 1], None, [24, 16], [0, 180, 0, 256])
        cv2.normalize(color_histogram, color_histogram)
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
            grayscale=grayscale,
            color_histogram=color_histogram.flatten().astype(np.float32),
            keypoints=tuple(keypoints),
            descriptors=descriptors,
        )


@dataclass(frozen=True)
class MatchEvidence:
    duplicate: bool
    confidence: float
    method: str
    inliers: int = 0
    overlap: float = 0.0
    changed_fraction: float = 0.0


@dataclass(frozen=True)
class PlannedPhoto:
    path: Path
    width: int
    height: int
    size: int
    modified_ns: int

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass(frozen=True)
class DuplicatePlan:
    folder: Path
    sensitivity: str
    fingerprint: tuple[tuple[str, int, int], ...]
    groups: tuple[tuple[PlannedPhoto, ...], ...]


@dataclass(frozen=True)
class SeparationRecord:
    moved: Path
    kept: Path
    moved_resolution: tuple[int, int]
    kept_resolution: tuple[int, int]


_LAST_DUPLICATE_PLAN: DuplicatePlan | None = None


SENSITIVITY = {
    "conservative": {"hash": 0.94, "geometry": 0.88, "inlier_ratio": 0.48, "inliers": 16, "changed": 0.035},
    "balanced": {"hash": 0.90, "geometry": 0.80, "inlier_ratio": 0.36, "inliers": 11, "changed": 0.055},
    "sensitive": {"hash": 0.86, "geometry": 0.72, "inlier_ratio": 0.27, "inliers": 8, "changed": 0.10},
}


def _normalized_correlation(first: np.ndarray, second: np.ndarray) -> float:
    first_values = first.astype(np.float32).reshape(-1)
    second_values = second.astype(np.float32).reshape(-1)
    first_values -= first_values.mean()
    second_values -= second_values.mean()
    denominator = float(np.linalg.norm(first_values) * np.linalg.norm(second_values))
    return float(np.dot(first_values, second_values) / denominator) if denominator else 0.0


def _structural_similarity(first: np.ndarray, second: np.ndarray, mask: np.ndarray) -> float:
    valid = mask > 0
    if int(valid.sum()) < 256:
        return 0.0
    x = first[valid].astype(np.float64)
    y = second[valid].astype(np.float64)
    mean_x, mean_y = x.mean(), y.mean()
    variance_x, variance_y = x.var(), y.var()
    covariance = ((x - mean_x) * (y - mean_y)).mean()
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    return float(
        ((2 * mean_x * mean_y + c1) * (2 * covariance + c2))
        / ((mean_x**2 + mean_y**2 + c1) * (variance_x + variance_y + c2))
    )


def _global_evidence(a: Photo, b: Photo, sensitivity: str) -> MatchEvidence:
    proporcao_a = a.largura / a.altura
    proporcao_b = b.largura / b.altura
    aspect_delta = abs(proporcao_a - proporcao_b) / max(proporcao_a, proporcao_b)

    pd = a.phash - b.phash
    dd = a.dhash - b.dhash
    ad = a.ahash - b.ahash
    correlacao_cinza = float(
        np.dot(a.cinza.astype(np.float32), b.cinza.astype(np.float32)) / 4096
    )
    correlacao_bordas = float(
        np.dot(a.bordas.astype(np.float32), b.bordas.astype(np.float32)) / 4096
    )
    histogram = float(cv2.compareHist(a.color_histogram, b.color_histogram, cv2.HISTCMP_CORREL))
    hash_score = max(0.0, 1.0 - (pd / 256.0))
    global_score = (
        0.34 * hash_score + 0.26 * max(0.0, correlacao_cinza)
        + 0.25 * max(0.0, correlacao_bordas) + 0.15 * max(0.0, histogram)
    )

    # O primeiro limite encontra recompressões quase idênticas. O segundo é
    # tolerante a cor, brilho, contraste e filtros, mas exige bordas coincidentes
    # para não confundir fotografias consecutivas com poses diferentes.
    almost_identical = (
        aspect_delta <= 0.015 and pd <= 10 and dd <= 20 and ad <= 8
        and correlacao_cinza >= 0.94
    )
    threshold = SENSITIVITY[sensitivity]["hash"]
    duplicate = almost_identical or (aspect_delta <= 0.03 and global_score >= threshold)
    return MatchEvidence(duplicate, min(1.0, global_score), "global")


def _is_geometric_candidate(a: Photo, b: Photo) -> bool:
    """Cheap, permissive gate that keeps expensive feature matching off clear negatives."""
    hash_similarity = 1.0 - ((a.phash - b.phash) / 256.0)
    histogram_similarity = float(
        cv2.compareHist(a.color_histogram, b.color_histogram, cv2.HISTCMP_CORREL)
    )
    aspect_a = a.largura / a.altura
    aspect_b = b.largura / b.altura
    same_orientation = abs(aspect_a - aspect_b) / max(aspect_a, aspect_b) <= 0.35
    rotated_orientation = abs(aspect_a - (1.0 / aspect_b)) / max(aspect_a, 1.0 / aspect_b) <= 0.35

    gray_a = a.cinza.astype(np.float32).reshape(64, 64)
    gray_b = b.cinza.astype(np.float32).reshape(64, 64)
    edge_a = a.bordas.astype(np.float32).reshape(64, 64)
    edge_b = b.bordas.astype(np.float32).reshape(64, 64)
    gray_correlation = max(
        float(np.dot(gray_a.reshape(-1), np.rot90(gray_b, turns).reshape(-1)) / 4096)
        for turns in range(4)
    )
    edge_correlation = max(
        float(np.dot(edge_a.reshape(-1), np.rot90(edge_b, turns).reshape(-1)) / 4096)
        for turns in range(4)
    )

    # Rotation-aware low-resolution structure keeps transformed copies while
    # preventing visually related photo sessions from reaching ORB matching.
    return (
        hash_similarity >= 0.62
        or gray_correlation >= 0.55
        or edge_correlation >= 0.43
        or histogram_similarity >= 0.94
        or (
            (same_orientation or rotated_orientation)
            and histogram_similarity >= 0.90
            and (gray_correlation >= 0.40 or edge_correlation >= 0.38)
        )
    )


def _symmetric_ratio_matches(a: Photo, b: Photo) -> list[object]:
    """Return Lowe-ratio matches that also agree in the reverse direction."""
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    forward_pairs = matcher.knnMatch(a.descriptors, b.descriptors, k=2)
    reverse_pairs = matcher.knnMatch(b.descriptors, a.descriptors, k=2)
    forward = {
        match.queryIdx: match
        for pair in forward_pairs if len(pair) == 2
        for match in pair[:1] if match.distance < 0.78 * pair[1].distance
    }
    reverse = {
        match.queryIdx: match
        for pair in reverse_pairs if len(pair) == 2
        for match in pair[:1] if match.distance < 0.78 * pair[1].distance
    }
    return [
        match for query_index, match in forward.items()
        if match.trainIdx in reverse and reverse[match.trainIdx].trainIdx == query_index
    ]


def _geometric_evidence(a: Photo, b: Photo, sensitivity: str) -> MatchEvidence:
    if a.descriptors is None or b.descriptors is None:
        return MatchEvidence(False, 0.0, "geometry")
    if len(a.keypoints) < 8 or len(b.keypoints) < 8:
        return MatchEvidence(False, 0.0, "geometry")

    good = _symmetric_ratio_matches(a, b)
    if len(good) < 8:
        return MatchEvidence(False, 0.0, "geometry")

    source_points = np.float32([b.keypoints[match.trainIdx].pt for match in good]).reshape(-1, 1, 2)
    target_points = np.float32([a.keypoints[match.queryIdx].pt for match in good]).reshape(-1, 1, 2)
    robust_method = getattr(cv2, "USAC_MAGSAC", cv2.RANSAC)
    homography, inlier_mask = cv2.findHomography(source_points, target_points, robust_method, 3.5)
    if homography is None or inlier_mask is None:
        return MatchEvidence(False, 0.0, "geometry")

    inliers = int(inlier_mask.sum())
    inlier_ratio = inliers / len(good)
    height, width = a.grayscale.shape

    # Reject degenerate or implausible projections before the expensive warp.
    source_height, source_width = b.grayscale.shape
    corners = np.float32(
        [[0, 0], [source_width - 1, 0], [source_width - 1, source_height - 1], [0, source_height - 1]]
    ).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(corners, homography).reshape(-1, 2)
    projected_area = abs(float(cv2.contourArea(projected.astype(np.float32))))
    area_ratio = projected_area / float(width * height)
    if not cv2.isContourConvex(projected.astype(np.float32)) or not 0.12 <= area_ratio <= 8.0:
        return MatchEvidence(False, 0.0, "geometry", inliers)

    aligned = cv2.warpPerspective(b.grayscale, homography, (width, height))
    source_mask = np.full(b.grayscale.shape, 255, dtype=np.uint8)
    overlap_mask = cv2.warpPerspective(source_mask, homography, (width, height))
    overlap = float(np.count_nonzero(overlap_mask)) / float(width * height)
    if overlap < 0.28:
        return MatchEvidence(False, 0.0, "geometry", inliers, overlap)

    structural = _structural_similarity(a.grayscale, aligned, overlap_mask)
    valid = overlap_mask > 0
    correlation = _normalized_correlation(a.grayscale[valid], aligned[valid])
    first_values = a.grayscale[valid].astype(np.float32)
    second_values = aligned[valid].astype(np.float32)
    first_values = (first_values - first_values.mean()) / (first_values.std() + 1e-6)
    second_values = (second_values - second_values.mean()) / (second_values.std() + 1e-6)
    changed_fraction = float(np.mean(np.abs(first_values - second_values) > 0.5))
    geometry_score = (
        0.38 * min(1.0, inlier_ratio / 0.65)
        + 0.25 * max(0.0, structural)
        + 0.25 * max(0.0, correlation)
        + 0.12 * min(1.0, overlap / 0.75)
    ) * max(0.0, 1.0 - changed_fraction)
    limits = SENSITIVITY[sensitivity]
    duplicate = (
        inliers >= limits["inliers"] and inlier_ratio >= limits["inlier_ratio"]
        and geometry_score >= limits["geometry"] and changed_fraction <= limits["changed"]
    )
    return MatchEvidence(
        duplicate, min(1.0, geometry_score), "geometry", inliers, overlap, changed_fraction
    )


def compare_photos(a: Photo, b: Photo, sensitivity: str = "balanced") -> MatchEvidence:
    if a.hash_arquivo == b.hash_arquivo:
        return MatchEvidence(True, 1.0, "sha256")
    global_result = _global_evidence(a, b, sensitivity)
    if global_result.duplicate:
        return global_result
    if not _is_geometric_candidate(a, b):
        return global_result
    geometric_result = _geometric_evidence(a, b, sensitivity)
    # A valid geometric confirmation must never be discarded merely because two
    # unrelated confidence scales happen to have different numeric values.
    if geometric_result.duplicate:
        return geometric_result
    return geometric_result if geometric_result.confidence >= global_result.confidence else global_result


def are_similar(a: Photo, b: Photo, sensitivity: str = "balanced") -> bool:
    return compare_photos(a, b, sensitivity).duplicate


def group_duplicates(
    fotos: list[Photo], sensitivity: str = "balanced",
    progress: Callable[[int, int], None] | None = None,
) -> list[list[int]]:
    # The highest-quality image is the anchor. Candidates must match the anchor,
    # which prevents A~B~C transitive chains from merging unrelated endpoints.
    ordered = sorted(range(len(fotos)), key=lambda i: (fotos[i].area, fotos[i].tamanho), reverse=True)
    groups: list[list[int]] = []
    comparisons = 0
    maximum_comparisons = len(fotos) * (len(fotos) - 1) // 2
    for index in ordered:
        for group in groups:
            comparisons += 1
            if are_similar(fotos[group[0]], fotos[index], sensitivity):
                group.append(index)
                break
            if progress and comparisons % 2500 == 0:
                progress(comparisons, maximum_comparisons)
        else:
            groups.append([index])
    if progress:
        progress(comparisons, maximum_comparisons)
    return [group for group in groups if len(group) > 1]


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


def photo_fingerprint(paths: list[Path]) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        (str(path.resolve()), metadata.st_size, metadata.st_mtime_ns)
        for path in paths for metadata in (path.stat(),)
    )


def build_duplicate_plan(
    folder: Path, sensitivity: str, photos: list[Photo], groups: list[list[int]],
    paths: list[Path],
) -> DuplicatePlan:
    planned_groups = []
    for group in groups:
        ordered = sorted(group, key=lambda i: (photos[i].area, photos[i].tamanho), reverse=True)
        planned_groups.append(tuple(
            PlannedPhoto(
                photos[index].caminho, photos[index].largura, photos[index].altura,
                photos[index].tamanho, photos[index].caminho.stat().st_mtime_ns,
            )
            for index in ordered
        ))
    return DuplicatePlan(
        folder, sensitivity, photo_fingerprint(paths), tuple(planned_groups)
    )


def plan_is_current(
    plan: DuplicatePlan | None, folder: Path, sensitivity: str, paths: list[Path]
) -> bool:
    if plan is None or plan.folder != folder or plan.sensitivity != sensitivity:
        return False
    try:
        return plan.fingerprint == photo_fingerprint(paths)
    except OSError:
        return False


def apply_duplicate_plan(plan: DuplicatePlan, destination: Path) -> list[SeparationRecord]:
    destination.mkdir(parents=True, exist_ok=True)
    records: list[SeparationRecord] = []
    for group in plan.groups:
        kept = group[0]
        for duplicate in group[1:]:
            target = available_path(destination / duplicate.path.name)
            shutil.move(duplicate.path, target)
            records.append(SeparationRecord(
                target, kept.path, (duplicate.width, duplicate.height),
                (kept.width, kept.height),
            ))
    return records


def write_duplicate_report(
    destination: Path, records: list[SeparationRecord], language: str
) -> Path:
    labels = {
        "pt-BR": (
            "RELATÓRIO DE IMAGENS DUPLICADAS", "Imagem separada", "Imagem mantida",
            "Resoluções", "separada", "mantida", "Motivo",
            "A imagem mantida possui melhor resolução.",
        ),
        "en-US": (
            "DUPLICATE IMAGE REPORT", "Separated image", "Kept image",
            "Resolutions", "separated", "kept", "Reason",
            "The kept image has the better resolution.",
        ),
        "es-ES": (
            "INFORME DE IMÁGENES DUPLICADAS", "Imagen separada", "Imagen conservada",
            "Resoluciones", "separada", "conservada", "Motivo",
            "La imagen conservada tiene mejor resolución.",
        ),
    }
    title, moved_label, kept_label, sizes_label, moved_size_label, kept_size_label, reason_label, reason = labels[language]
    lines = [title, "=" * len(title), ""]
    for record in records:
        moved_size = f"{record.moved_resolution[0]}x{record.moved_resolution[1]}"
        kept_size = f"{record.kept_resolution[0]}x{record.kept_resolution[1]}"
        lines.extend((
            f"{moved_label}: {record.moved.name}",
            f"{kept_label}: {record.kept.name}",
            f"{sizes_label}: {moved_size_label} {moved_size} | {kept_size_label} {kept_size}",
            f"{reason_label}: {reason}", "", "-" * 60, "",
        ))
    report = destination / "report.txt"
    temporary = destination / f".report.{uuid.uuid4().hex}.tmp"
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(temporary, report)
    return report


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
        subprocess.run(comando, check=True, **subprocess_window_options())
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


def find_enhancement_engine() -> str | None:
    executable_name = "realesrgan-ncnn-vulkan.exe" if os.name == "nt" else "realesrgan-ncnn-vulkan"
    found = shutil.which(executable_name)
    if found:
        return found
    resource_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidates = (
        resource_dir / executable_name,
        Path(sys.executable).resolve().parent / executable_name,
        Path(__file__).resolve().parent / executable_name,
    )
    return next((str(candidate) for candidate in candidates if candidate.is_file()), None)


def enhance_image(
    source: Path, destination: Path, scale: int, model: str,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Upscale one image locally with the bundled Real-ESRGAN NCNN/Vulkan engine."""
    engine = find_enhancement_engine()
    if not engine:
        raise RuntimeError("Real-ESRGAN enhancement engine was not found")

    destination.mkdir(parents=True, exist_ok=True)
    target = available_path(destination / f"{source.stem}-{scale}x.png")
    model_name = "realesrgan-x4plus" if model == "photo" else "realesrgan-x4plus-anime"
    model_directory = Path(engine).resolve().parent / "models"
    if not model_directory.is_dir():
        raise RuntimeError("Real-ESRGAN model files were not found")
    with tempfile.TemporaryDirectory(prefix="similaris-enhance-") as temporary_folder:
        normalized = Path(temporary_folder) / "input.png"
        temporary_output = Path(temporary_folder) / "output.png"
        if progress:
            progress("preparando a imagem")
        with Image.open(source) as image:
            ImageOps.exif_transpose(image).save(normalized, format="PNG")
        command = [
            engine, "-i", str(normalized), "-o", str(temporary_output),
            "-s", str(scale), "-n", model_name, "-m", str(model_directory), "-f", "png",
        ]
        try:
            if progress:
                progress("Real-ESRGAN em execução")
            subprocess.run(
                command, check=True, capture_output=True, text=True,
                **subprocess_window_options(),
            )
        except subprocess.CalledProcessError as error:
            details = (error.stderr or error.stdout or "").strip()
            raise RuntimeError(
                "Real-ESRGAN failed. Verify that a Vulkan-compatible GPU and driver are available"
                + (f": {details}" if details else "")
            ) from error
        if not temporary_output.is_file():
            raise RuntimeError("Real-ESRGAN completed without creating an output image")
        if progress:
            progress("validando o resultado")
        with Image.open(normalized) as input_image, Image.open(temporary_output) as output_image:
            expected_size = (input_image.width * scale, input_image.height * scale)
            if output_image.size != expected_size:
                raise RuntimeError(
                    f"Real-ESRGAN returned {output_image.size}; expected {expected_size}"
                )
        os.replace(temporary_output, target)
        if progress:
            progress("arquivo salvo")
    return target


def run_enhancement(
    args: argparse.Namespace, folder: Path, selected_files: list[Path] | None = None,
    output_folder: Path | None = None,
) -> tuple[int, list[str]]:
    if not args.enhance_images:
        return 0, []
    destination = output_folder or (folder / args.enhanced_folder)
    completed = 0
    failures: list[str] = []
    sources = selected_files if selected_files is not None else photos_in_folder(folder)
    sources = [source for source in sources if source.suffix.lower() in IMAGE_EXTENSIONS]
    total = len(sources)
    for index, source in enumerate(sources, 1):
        initial_percent = (completed * 100 / total) if total else 100
        localized_print(
            args.language,
            f"Progresso da melhoria: {completed}/{total} ({initial_percent:.1f}%) — processando {source.name}",
        )
        try:
            target = enhance_image(
                source, destination, args.enhancement_scale, args.enhancement_model,
                lambda phase: localized_print(args.language, f"    {source.name}: {phase}"),
            )
            completed += 1
            localized_print(args.language, f"  imagem melhorada: {source.name} -> {target.name}")
        except Exception as error:
            failures.append(f"{source.name}: {error}")
            localized_print(args.language, f"    falha em {source.name}: {error}")
        finished_percent = (index * 100 / total) if total else 100
        localized_print(
            args.language,
            f"Progresso da melhoria: {index}/{total} ({finished_percent:.1f}%) — etapa concluída",
        )
    return completed, failures


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
        "Renomeadas": "Renamed", "imagens.": "images.", "Analisando": "Analyzing",
        "imagens em": "images in", "processadas": "processed", "Encontrados": "Found", "grupos e": "groups and",
        "arquivos repetidos.": "duplicate files.", "Grupo": "Group", "manter": "keep", "separar": "separate",
        "Aviso:": "Warning:", "arquivo(s) não puderam ser lidos:": "file(s) could not be read:",
        "Simulação concluída.": "Simulation completed.", "Concluído:": "Completed:", "repetida(s) movida(s) para": "duplicate(s) moved to",
        "exige uma opção --converter-*.": "requires a --convert-* option.",
        "Reutilizando o resultado da última simulação; nenhuma nova comparação é necessária.": "Reusing the last simulation result; no new comparison is required.",
        "Relatório criado em": "Report created at",
        "Comparando imagens:": "Comparing images:", "pares verificados": "pairs checked",
        "Melhorando imagens para": "Enhancing images into", "Melhoria concluída:": "Enhancement completed:",
        "imagem(ns) melhorada(s).": "enhanced image(s).", "  imagem melhorada:": "  enhanced image:",
        "Progresso da melhoria:": "Enhancement progress:", "processando": "processing",
        "preparando a imagem": "preparing image", "Real-ESRGAN em execução": "Real-ESRGAN is running",
        "validando o resultado": "validating result", "arquivo salvo": "file saved",
        "etapa concluída": "step completed", "falha em": "failed on",
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
        "Renomeadas": "Renombradas", "imagens.": "imágenes.", "Analisando": "Analizando",
        "imagens em": "imágenes en", "processadas": "procesadas", "Encontrados": "Encontrados", "grupos e": "grupos y",
        "arquivos repetidos.": "archivos duplicados.", "Grupo": "Grupo", "manter": "conservar", "separar": "separar",
        "Aviso:": "Aviso:", "arquivo(s) não puderam ser lidos:": "archivo(s) no se pudieron leer:",
        "Simulação concluída.": "Simulación completada.", "Concluído:": "Completado:", "repetida(s) movida(s) para": "duplicado(s) movido(s) a",
        "exige uma opção --converter-*.": "requiere una opción --convert-*.",
        "Reutilizando o resultado da última simulação; nenhuma nova comparação é necessária.": "Reutilizando el resultado de la última simulación; no se requiere una nueva comparación.",
        "Relatório criado em": "Informe creado en",
        "Comparando imagens:": "Comparando imágenes:", "pares verificados": "pares comprobados",
        "Melhorando imagens para": "Mejorando imágenes en", "Melhoria concluída:": "Mejora completada:",
        "imagem(ns) melhorada(s).": "imagen(es) mejorada(s).", "  imagem melhorada:": "  imagen mejorada:",
        "Progresso da melhoria:": "Progreso de mejora:", "processando": "procesando",
        "preparando a imagem": "preparando imagen", "Real-ESRGAN em execução": "Real-ESRGAN está en ejecución",
        "validando o resultado": "validando resultado", "arquivo salvo": "archivo guardado",
        "etapa concluída": "etapa completada", "falha em": "falló en",
    },
}


def localized_print(language: str, *values: object, **kwargs: object) -> None:
    text = " ".join(str(value) for value in values)
    for source, translation in OUTPUT_TRANSLATIONS.get(language, {}).items():
        text = text.replace(source, translation)
    print(text, **kwargs)


def run_conversions(
    args: argparse.Namespace, pasta: Path, selected_files: list[Path] | None = None,
    output_folder: Path | None = None,
) -> tuple[int, int, list[str]]:
    imagens = args.convert_images or args.convert_all
    videos = args.convert_videos or args.convert_all
    if not imagens and not videos:
        return 0, 0, []

    destino = output_folder or (pasta / args.converted_folder)
    destino.mkdir(parents=True, exist_ok=True)
    feitas_imagens = feitas_videos = 0
    falhas: list[str] = []
    entradas = selected_files if selected_files is not None else [p for p in pasta.iterdir() if p.is_file()]
    entradas = sorted(entradas, key=lambda p: p.name.casefold())

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
    global _LAST_DUPLICATE_PLAN
    args = parse_arguments(argv)
    pasta = args.folder.expanduser().resolve()
    selected_files = (
        [path.expanduser().resolve() for path in args.files] if args.files else None
    )
    output_folder = args.output_folder.expanduser().resolve() if args.output_folder else None
    if not pasta.is_dir():
        localized_print(args.language, f"Pasta inexistente: {pasta}", file=sys.stderr)
        return 2
    if selected_files is not None:
        missing = [path for path in selected_files if not path.is_file()]
        if missing:
            localized_print(args.language, f"Arquivo inexistente: {missing[0]}", file=sys.stderr)
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
    if args.enhance_only and not args.enhance_images:
        localized_print(args.language, "--enhance-only requires --enhance-images.", file=sys.stderr)
        return 2
    if quer_converter:
        conversion_destination = output_folder or (pasta / args.converted_folder)
        localized_print(args.language, f"Convertendo arquivos para {conversion_destination}...")
        n_imagens, n_videos, falhas_conversao = run_conversions(
            args, pasta, selected_files, conversion_destination
        )
        localized_print(args.language, f"Conversões concluídas: {n_imagens} imagem(ns), {n_videos} vídeo(s).")
        if falhas_conversao:
            localized_print(args.language, f"Falharam {len(falhas_conversao)} conversão(ões):")
            for falha in falhas_conversao:
                localized_print(args.language, f"  {falha}")

    if args.enhance_images:
        enhancement_destination = output_folder or (pasta / args.enhanced_folder)
        localized_print(args.language, f"Melhorando imagens para {enhancement_destination}...")
        enhanced_count, enhancement_failures = run_enhancement(
            args, pasta, selected_files, enhancement_destination
        )
        localized_print(args.language, f"Melhoria concluída: {enhanced_count} imagem(ns) melhorada(s).")
        if enhancement_failures:
            localized_print(args.language, f"Falharam {len(enhancement_failures)} imagem(ns):")
            for failure in enhancement_failures:
                localized_print(args.language, f"  {failure}")

    if args.convert_only or args.enhance_only:
        return 1 if (locals().get("falhas_conversao") or locals().get("enhancement_failures")) else 0

    caminhos = (
        [path for path in selected_files if path.suffix.lower() in IMAGE_EXTENSIONS]
        if selected_files is not None else photos_in_folder(pasta)
    )
    if not caminhos:
        localized_print(args.language, "Nenhuma imagem compatível encontrada.")
        return 0

    if args.skip_duplicates:
        operacoes = []
        if args.rename_photos:
            operacoes.append("rename_photos as imagens")
        if not args.apply:
            if operacoes:
                localized_print(args.language, "Simulação: " + " e ".join(operacoes) + ".")
                localized_print(args.language, "Use --aplicar para realizar as alterações.")
            return 0
        restantes = caminhos
        if args.rename_photos:
            restantes = rename_photos(restantes)
            localized_print(args.language, f"Renomeadas {len(restantes)} imagens.")
        return 0

    if args.apply and plan_is_current(_LAST_DUPLICATE_PLAN, pasta, args.sensitivity, caminhos):
        localized_print(
            args.language,
            "Reutilizando o resultado da última simulação; nenhuma nova comparação é necessária.",
        )
        destino = output_folder or (pasta / args.duplicates_folder)
        records = apply_duplicate_plan(_LAST_DUPLICATE_PLAN, destino)
        report = write_duplicate_report(destino, records, args.language)
        _LAST_DUPLICATE_PLAN = None
        restantes = [path for path in caminhos if path.exists()]
        if args.rename_photos:
            restantes = rename_photos(restantes)
        localized_print(args.language, f"Concluído: {len(records)} repetida(s) movida(s) para {destino}.")
        localized_print(args.language, f"Relatório criado em {report}.")
        if args.rename_photos:
            localized_print(args.language, f"Renomeadas {len(restantes)} imagens.")
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

    def comparison_progress(completed: int, total: int) -> None:
        percent = (completed * 100 / total) if total else 100
        localized_print(
            args.language,
            f"  Comparando imagens: {completed}/{total} pares verificados ({percent:.1f}%)",
        )

    grupos = group_duplicates(fotos, args.sensitivity, comparison_progress)
    _LAST_DUPLICATE_PLAN = build_duplicate_plan(
        pasta, args.sensitivity, fotos, grupos, caminhos
    )
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

    destino = output_folder or (pasta / args.duplicates_folder)
    records = apply_duplicate_plan(_LAST_DUPLICATE_PLAN, destino)
    report = write_duplicate_report(destino, records, args.language)
    _LAST_DUPLICATE_PLAN = None
    restantes = [path for path in caminhos if path.exists()]
    if args.rename_photos:
        restantes = rename_photos(restantes)

    localized_print(args.language, f"\nConcluído: {len(records)} repetida(s) movida(s) para {destino}.")
    localized_print(args.language, f"Relatório criado em {report}.")
    if args.rename_photos:
        localized_print(args.language, f"Renomeadas {len(restantes)} imagens.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
