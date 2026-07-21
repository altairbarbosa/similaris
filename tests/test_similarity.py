from __future__ import annotations

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

    def tearDown(self) -> None:
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

    def test_anchor_grouping_does_not_chain_matches(self) -> None:
        photos = [unittest.mock.Mock(area=300 - i, tamanho=100, hash_arquivo=str(i)) for i in range(3)]

        def adjacent_only(first: object, second: object, _sensitivity: str) -> bool:
            return abs(photos.index(first) - photos.index(second)) == 1

        with patch.object(photo_organizer, "are_similar", side_effect=adjacent_only):
            self.assertEqual(photo_organizer.group_duplicates(photos), [[0, 1]])

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


if __name__ == "__main__":
    unittest.main()
