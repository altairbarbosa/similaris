from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageEnhance

import photo_organizer


def sample_image(variant: int = 0) -> Image.Image:
    image = Image.new("RGB", (640, 420), (238, 242, 248))
    draw = ImageDraw.Draw(image)
    draw.rectangle((35, 40, 290, 220), fill=(25, 70, 145), outline=(5, 25, 75), width=8)
    draw.ellipse((330, 55, 555, 280), fill=(20, 205, 195), outline=(0, 75, 95), width=8)
    draw.polygon(((80, 360), (245, 245), (375, 370)), fill=(245, 150, 30))
    for index in range(8):
        x = 35 + index * 72
        draw.line((x, 15, 620 - index * 14, 395), fill=(40 + index * 18, 35, 90), width=3)
    if variant:
        draw.rectangle((410, 310, 610, 400), fill=(180, 35, 45))
        draw.line((20, 390, 620, 20), fill=(250, 250, 20), width=12)
    return image


class SimilarityPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name)
        photo_organizer._LAST_DUPLICATE_PLAN = None

    def tearDown(self) -> None:
        photo_organizer._LAST_DUPLICATE_PLAN = None
        self.temporary.cleanup()

    def save(self, name: str, image: Image.Image, **options: object) -> Path:
        path = self.folder / name
        image.save(path, **options)
        return path

    def analyze_pair(self, first: Path, second: Path) -> photo_organizer.MatchEvidence:
        return photo_organizer.compare_photos(
            photo_organizer.analyze(first), photo_organizer.analyze(second), "balanced"
        )

    def test_exact_copy_uses_sha256(self) -> None:
        original = self.save("original.png", sample_image())
        copy = self.folder / "copy.png"
        copy.write_bytes(original.read_bytes())
        evidence = self.analyze_pair(original, copy)
        self.assertTrue(evidence.duplicate)
        self.assertEqual(evidence.method, "sha256")

    def test_recompressed_photo_is_duplicate(self) -> None:
        original = self.save("original.png", sample_image())
        recompressed = self.save("compressed.jpg", sample_image(), quality=35)
        self.assertTrue(self.analyze_pair(original, recompressed).duplicate)

    def test_brightness_and_contrast_edit_is_duplicate(self) -> None:
        original_image = sample_image()
        original = self.save("original.png", original_image)
        edited = ImageEnhance.Contrast(ImageEnhance.Brightness(original_image).enhance(0.72)).enhance(1.35)
        edited_path = self.save("edited.jpg", edited, quality=68)
        self.assertTrue(self.analyze_pair(original, edited_path).duplicate)

    def test_rotated_photo_is_duplicate(self) -> None:
        original_image = sample_image()
        original = self.save("original.png", original_image)
        rotated = self.save("rotated.jpg", original_image.rotate(90, expand=True), quality=72)
        evidence = self.analyze_pair(original, rotated)
        self.assertTrue(evidence.duplicate, evidence)
        self.assertEqual(evidence.method, "geometry")

    def test_cropped_photo_is_duplicate(self) -> None:
        original_image = sample_image()
        original = self.save("original.png", original_image)
        cropped = original_image.crop((55, 35, 595, 390)).resize((640, 420))
        crop_path = self.save("cropped.jpg", cropped, quality=70)
        evidence = self.analyze_pair(original, crop_path)
        self.assertTrue(evidence.duplicate, evidence)
        self.assertEqual(evidence.method, "geometry")

    def test_different_photo_is_not_duplicate(self) -> None:
        first = self.save("first.png", sample_image())
        second = self.save("second.png", sample_image(variant=1))
        evidence = self.analyze_pair(first, second)
        self.assertFalse(evidence.duplicate, evidence)

    def test_sensitivity_profiles_change_borderline_decision(self) -> None:
        first = photo_organizer.analyze(self.save("first.png", sample_image()))
        second = photo_organizer.analyze(self.save("second.png", sample_image(variant=1)))
        conservative = photo_organizer.compare_photos(first, second, "conservative")
        balanced = photo_organizer.compare_photos(first, second, "balanced")
        sensitive = photo_organizer.compare_photos(first, second, "sensitive")
        self.assertFalse(conservative.duplicate)
        self.assertFalse(balanced.duplicate)
        self.assertTrue(sensitive.duplicate)

    def test_image_conversion_does_not_require_apply(self) -> None:
        self.save("source.png", sample_image())
        result = photo_organizer.main([
            str(self.folder), "--convert-images", "--convert-only", "--language", "en-US"
        ])
        self.assertEqual(result, 0)
        self.assertTrue((self.folder / "converted" / "source.jpg").is_file())

    def test_explicit_files_and_output_folder_limit_conversion_scope(self) -> None:
        selected = self.save("selected.png", sample_image())
        self.save("ignored.png", sample_image(variant=1))
        destination = self.folder / "chosen-output"

        result = photo_organizer.main([
            str(self.folder), "--convert-images", "--convert-only",
            "--files", str(selected), "--output-folder", str(destination),
        ])

        self.assertEqual(result, 0)
        self.assertTrue((destination / "selected.jpg").is_file())
        self.assertFalse((destination / "ignored.jpg").exists())

    def test_anchor_grouping_does_not_chain_matches(self) -> None:
        photos = [unittest.mock.Mock(area=300 - i, tamanho=100, hash_arquivo=str(i)) for i in range(3)]

        def adjacent_only(first: object, second: object, _sensitivity: str) -> bool:
            return abs(photos.index(first) - photos.index(second)) == 1

        with patch.object(photo_organizer, "are_similar", side_effect=adjacent_only):
            self.assertEqual(photo_organizer.group_duplicates(photos), [[0, 1]])

    def test_apply_reuses_simulation_and_writes_duplicate_report(self) -> None:
        original = self.save("img (4).png", sample_image())
        duplicate = self.save(
            "img (1).jpg", sample_image().resize((480, 315)), quality=55
        )

        destination = self.folder / "reviewed-duplicates"
        common_arguments = [
            str(self.folder), "--language", "pt-BR", "--files", str(original),
            str(duplicate), "--output-folder", str(destination),
        ]
        self.assertEqual(photo_organizer.main(common_arguments), 0)
        self.assertIsNotNone(photo_organizer._LAST_DUPLICATE_PLAN)

        with patch.object(
            photo_organizer, "analyze", side_effect=AssertionError("unexpected recomparison")
        ):
            self.assertEqual(photo_organizer.main(common_arguments + ["--apply"]), 0)

        moved = destination / duplicate.name
        report = destination / "report.txt"
        self.assertTrue(original.is_file())
        self.assertTrue(moved.is_file())
        self.assertTrue(report.is_file())
        contents = report.read_text(encoding="utf-8")
        self.assertTrue(contents.startswith("RELATÓRIO DE IMAGENS DUPLICADAS\n"))
        self.assertIn("Imagem separada: img (1).jpg", contents)
        self.assertIn("Imagem mantida: img (4).png", contents)
        self.assertIn("A imagem mantida possui melhor resolução.", contents)
        self.assertIn("separada 480x315 | mantida 640x420", contents)

    def test_geometric_confirmation_is_not_discarded_by_global_score(self) -> None:
        first = unittest.mock.Mock(hash_arquivo="first")
        second = unittest.mock.Mock(hash_arquivo="second")
        global_result = photo_organizer.MatchEvidence(False, 0.91, "global")
        geometric_result = photo_organizer.MatchEvidence(True, 0.82, "geometry")
        with (
            patch.object(photo_organizer, "_global_evidence", return_value=global_result),
            patch.object(photo_organizer, "_is_geometric_candidate", return_value=True),
            patch.object(photo_organizer, "_geometric_evidence", return_value=geometric_result),
        ):
            self.assertEqual(
                photo_organizer.compare_photos(first, second), geometric_result
            )

    def test_clear_negative_does_not_run_geometric_comparison(self) -> None:
        first = unittest.mock.Mock(hash_arquivo="first")
        second = unittest.mock.Mock(hash_arquivo="second")
        global_result = photo_organizer.MatchEvidence(False, 0.25, "global")
        with (
            patch.object(photo_organizer, "_global_evidence", return_value=global_result),
            patch.object(photo_organizer, "_is_geometric_candidate", return_value=False),
            patch.object(photo_organizer, "_geometric_evidence") as geometry,
        ):
            self.assertEqual(photo_organizer.compare_photos(first, second), global_result)
            geometry.assert_not_called()

    def test_enhancement_preserves_original_and_creates_scaled_png(self) -> None:
        source = self.save("source.jpg", sample_image(), quality=80)
        engine = self.folder / "realesrgan-ncnn-vulkan"
        engine.touch()
        (self.folder / "models").mkdir()

        def create_engine_output(command: list[str], **_kwargs: object) -> object:
            output = Path(command[command.index("-o") + 1])
            Image.new("RGB", (1280, 840), "white").save(output)
            return unittest.mock.Mock(returncode=0)

        with (
            patch.object(photo_organizer, "find_enhancement_engine", return_value=str(engine)),
            patch.object(photo_organizer.subprocess, "run", side_effect=create_engine_output) as run,
        ):
            target = photo_organizer.enhance_image(source, self.folder / "enhanced", 2, "photo")

        self.assertTrue(source.is_file())
        self.assertEqual(target.name, "source-2x.png")
        with Image.open(target) as enhanced:
            self.assertEqual(enhanced.size, (1280, 840))
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("-s") + 1], "2")
        self.assertEqual(command[command.index("-n") + 1], "realesrgan-x4plus")

    def test_enhancement_reports_current_file_and_real_percentage(self) -> None:
        self.save("first.png", sample_image())
        self.save("second.jpg", sample_image(variant=1), quality=80)

        def successful_enhancement(
            source: Path, destination: Path, _scale: int, _model: str, progress: object
        ) -> Path:
            progress("Real-ESRGAN em execução")
            return destination / f"{source.stem}-2x.png"

        output = io.StringIO()
        with (
            patch.object(photo_organizer, "enhance_image", side_effect=successful_enhancement),
            contextlib.redirect_stdout(output),
        ):
            result = photo_organizer.main([
                str(self.folder), "--enhance-images", "--enhance-only", "--language", "pt-BR"
            ])

        self.assertEqual(result, 0)
        details = output.getvalue()
        self.assertIn("Progresso da melhoria: 0/2 (0.0%) — processando first.png", details)
        self.assertIn("first.png: Real-ESRGAN em execução", details)
        self.assertIn("Progresso da melhoria: 2/2 (100.0%) — etapa concluída", details)

    def test_console_tools_are_hidden_on_windows(self) -> None:
        with patch.object(photo_organizer.sys, "platform", "win32"):
            self.assertEqual(
                photo_organizer.subprocess_window_options(),
                {"creationflags": 0x08000000},
            )
        with patch.object(photo_organizer.sys, "platform", "linux"):
            self.assertEqual(photo_organizer.subprocess_window_options(), {})

    def test_enhance_only_requires_enhancement_operation(self) -> None:
        self.assertEqual(
            photo_organizer.main([str(self.folder), "--enhance-only"]), 2
        )


if __name__ == "__main__":
    unittest.main()
