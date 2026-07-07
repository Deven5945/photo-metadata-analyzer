import tempfile
import unittest
from pathlib import Path

from PIL import Image
import piexif

from main import (
    build_metadata_summary,
    collect_metadata_sections,
    extract_exif_metadata,
    format_metadata_value,
)


class MetadataAnalyzerTests(unittest.TestCase):
    def test_returns_empty_metadata_for_image_without_exif(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "no_exif.png"
            Image.new("RGB", (12, 12), color=(255, 0, 0)).save(image_path)

            metadata = extract_exif_metadata(image_path)
            summary = build_metadata_summary(image_path)

            self.assertEqual(metadata, {})
            self.assertIn("No EXIF metadata found", summary)

    def test_extracts_common_exif_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "with_exif.jpg"
            Image.new("RGB", (16, 16), color=(10, 20, 30)).save(image_path)

            exif_dict = {
                "0th": {
                    270: "Sample image",
                    271: "Camera Brand",
                    272: "Model X",
                }
            }
            piexif.insert(piexif.dump(exif_dict), str(image_path))

            metadata = extract_exif_metadata(image_path)

            self.assertEqual(metadata["Image Description"], "Sample image")
            self.assertEqual(metadata["Make"], "Camera Brand")
            self.assertEqual(metadata["Model"], "Model X")

    def test_collects_structured_metadata_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "structured.jpg"
            Image.new("RGB", (8, 8), color=(1, 2, 3)).save(image_path)

            sections = collect_metadata_sections(image_path)

            self.assertIn("Image info", sections)
            self.assertIn("File", sections["Image info"])
            self.assertIn("EXIF", sections)
            self.assertIn("Status", sections["EXIF"])

    def test_formats_exposure_and_aperture_values_for_readability(self) -> None:
        self.assertEqual(format_metadata_value((1, 1000), "Exposure Time"), "1/1000 s")
        self.assertEqual(format_metadata_value(0.0025, "Exposure Time"), "1/400 s")
        self.assertEqual(format_metadata_value((28, 10), "F Number"), "f/2.8")
        self.assertEqual(format_metadata_value(5.6, "F Number"), "f/5.6")
        self.assertEqual(format_metadata_value((56, 10), "Aperture Value"), "f/5.6")
        self.assertEqual(format_metadata_value(200, "ISO Speed Ratings"), "ISO 200")
        self.assertEqual(format_metadata_value((35, 1), "Focal Length"), "35mm")

    def test_reads_exposure_and_camera_values_from_exif_ifd(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "subifd.jpg"
            Image.new("RGB", (8, 8), color=(1, 2, 3)).save(image_path)

            exif_dict = {
                "Exif": {
                    piexif.ExifIFD.ExposureTime: (1, 125),
                    piexif.ExifIFD.FNumber: (28, 10),
                    piexif.ExifIFD.ISOSpeedRatings: 400,
                    piexif.ExifIFD.FocalLength: (35, 1),
                }
            }
            piexif.insert(piexif.dump(exif_dict), str(image_path))

            metadata = extract_exif_metadata(image_path)

            self.assertIn("Exposure Time", metadata)
            self.assertIn("F Number", metadata)
            self.assertIn("ISO Speed Ratings", metadata)
            self.assertIn("Focal Length", metadata)


if __name__ == "__main__":
    unittest.main()
