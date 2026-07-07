from __future__ import annotations

import os
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image, UnidentifiedImageError

if TYPE_CHECKING:
    import customtkinter as ctk

try:
    import customtkinter as ctk
except ImportError:  # pragma: no cover - handled at runtime for missing dependency
    ctk = None

try:
    from tkinter import filedialog, messagebox
except ImportError:  # pragma: no cover - handled on non-Windows platforms
    filedialog = None
    messagebox = None


COMMON_EXIF_TAGS = {
    270: "Image Description",
    271: "Make",
    272: "Model",
    305: "Software",
    33434: "Exposure Time",
    33437: "F Number",
    34855: "ISO Speed Ratings",
    36867: "Date Time Original",
    36868: "Date Time Digitized",
    37377: "Shutter Speed Value",
    37378: "Aperture Value",
    37379: "Brightness Value",
    37380: "Exposure Bias Value",
    37385: "Flash",
    37386: "Focal Length",
    40961: "Color Space",
    40962: "Pixel X Dimension",
    40963: "Pixel Y Dimension",
}


def _fraction_from_value(value: Any) -> Fraction | None:
    """Best-effort conversion of a metadata value to a Fraction."""
    if isinstance(value, (tuple, list)) and len(value) == 2:
        try:
            numerator = Fraction(str(value[0]))
            denominator = Fraction(str(value[1]))
            return numerator / denominator
        except (ValueError, ZeroDivisionError):
            return None

    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        try:
            return Fraction(value.numerator, value.denominator)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    if isinstance(value, (int, float, str)):
        try:
            return Fraction(str(value))
        except ValueError:
            return None

    return None


def format_metadata_value(value: Any, label: str | None = None) -> str:
    """Convert metadata values to human-readable text."""
    if value is None:
        return "Not available"
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            return value.decode("latin-1", errors="replace")

    if label in {"Exposure Time", "Shutter Speed Value"}:
        fraction = _fraction_from_value(value)
        if fraction is not None:
            if fraction <= 0:
                return "0 s"
            fraction = fraction.limit_denominator(10000)
            if fraction < 1:
                if fraction.numerator == 1:
                    return f"1/{fraction.denominator} s"
                return f"{fraction.numerator}/{fraction.denominator} s"
            if fraction.denominator == 1:
                return f"{fraction.numerator} s"
            return f"{float(fraction):.3g} s"

    if label in {"F Number", "Aperture Value"}:
        fraction = _fraction_from_value(value)
        if fraction is not None:
            if fraction.denominator == 1:
                return f"f/{fraction.numerator}"
            return f"f/{float(fraction):.1f}"

    if label == "ISO Speed Ratings":
        try:
            return f"ISO {int(value)}"
        except (TypeError, ValueError):
            pass

    if label == "Focal Length":
        fraction = _fraction_from_value(value)
        if fraction is not None:
            fraction = fraction.limit_denominator(10000)
            if fraction.denominator == 1:
                return f"{fraction.numerator}mm"
            return f"{float(fraction):.1f}mm"

    if isinstance(value, (tuple, list)):
        return ", ".join(str(item) for item in value)
    if isinstance(value, (list, dict)):
        return str(value)
    return str(value)


def extract_exif_metadata(image_path: Path) -> dict[str, str]:
    """Extract a compact set of common EXIF fields from an image."""
    try:
        with Image.open(image_path) as image:
            exif_data = image.getexif()
            if not exif_data:
                return {}

            extracted: dict[str, str] = {}
            for tag_id, value in exif_data.items():
                if tag_id not in COMMON_EXIF_TAGS:
                    continue

                label = COMMON_EXIF_TAGS[tag_id]
                extracted[label] = format_metadata_value(value, label)

            if exif_data.get_ifd(0x8769):
                for tag_id, value in exif_data.get_ifd(0x8769).items():
                    if tag_id not in COMMON_EXIF_TAGS:
                        continue

                    label = COMMON_EXIF_TAGS[tag_id]
                    extracted[label] = format_metadata_value(value, label)

            if not extracted:
                return {}
            return extracted
    except (FileNotFoundError, UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Unable to read image metadata: {exc}") from exc


def collect_metadata_sections(image_path: Path) -> dict[str, dict[str, str]]:
    """Return image details and EXIF metadata grouped into sections."""
    try:
        with Image.open(image_path) as image:
            width, height = image.size
            image_format = image.format or "Unknown"
            sections: dict[str, dict[str, str]] = {
                "Image info": {
                    "File": image_path.name,
                    "Path": str(image_path),
                    "Size": f"{width}x{height}px",
                    "Format": image_format,
                },
                "EXIF": {},
            }

            exif_metadata = extract_exif_metadata(image_path)
            if exif_metadata:
                sections["EXIF"] = exif_metadata
            else:
                sections["EXIF"] = {"Status": "No EXIF metadata found for this image."}

            return sections
    except (FileNotFoundError, UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Unable to process image: {exc}") from exc


def build_metadata_summary(image_path: Path) -> str:
    """Create a user-friendly summary of an image and its metadata."""
    sections = collect_metadata_sections(image_path)
    lines: list[str] = []

    for section_name, entries in sections.items():
        lines.append(section_name)
        lines.append("-" * len(section_name))
        for label, value in entries.items():
            lines.append(f"{label}: {value}")
        lines.append("")

    return "\n".join(lines).rstrip()


class MetadataAnalyzerApp:
    """Simple desktop GUI for reading image metadata."""

    def __init__(self, root: "ctk.CTk") -> None:
        self.root = root
        self.root.title("Photo Metadata Analyzer")
        self.root.geometry("780x520")
        self.root.minsize(680, 440)
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self._build_ui()

    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.root)
        header.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header,
            text="Photo Metadata Analyzer",
            font=("Segoe UI", 22, "bold"),
        )
        title_label.grid(row=0, column=0, sticky="w")

        description_label = ctk.CTkLabel(
            header,
            text="Select an image to inspect common EXIF metadata fields.",
            font=("Segoe UI", 12),
        )
        description_label.grid(row=1, column=0, sticky="w", pady=(4, 10))

        button_row = ctk.CTkFrame(header)
        button_row.grid(row=2, column=0, sticky="w")
        self.select_button = ctk.CTkButton(
            button_row,
            text="Select Image",
            command=self.select_image,
        )
        self.select_button.pack(side="left")

        self.status_label = ctk.CTkLabel(
            button_row,
            text="No image selected yet.",
            font=("Segoe UI", 11),
            anchor="w",
        )
        self.status_label.pack(side="left", padx=(12, 0))

        results_frame = ctk.CTkFrame(self.root)
        results_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)

        self.results_container = ctk.CTkScrollableFrame(results_frame)
        self.results_container.grid(row=0, column=0, sticky="nsew")
        self.results_container.grid_columnconfigure(0, weight=1)

        self.results_content = ctk.CTkFrame(self.results_container)
        self.results_content.grid(row=0, column=0, sticky="ew")
        self.results_content.grid_columnconfigure(0, weight=1)

        self.render_placeholder()

    def render_placeholder(self) -> None:
        for widget in self.results_content.winfo_children():
            widget.destroy()

        placeholder_card = ctk.CTkFrame(self.results_content, corner_radius=12)
        placeholder_card.grid(row=0, column=0, sticky="ew", pady=8)
        placeholder_card.grid_columnconfigure(0, weight=1)

        placeholder = ctk.CTkLabel(
            placeholder_card,
            text="Choose an image to begin.\nThe metadata will appear here in a cleaner summary view.",
            font=("Segoe UI", 13),
            justify="left",
            anchor="w",
        )
        placeholder.grid(row=0, column=0, sticky="w", padx=16, pady=16)

    def render_sections(self, sections: dict[str, dict[str, str]]) -> None:
        for widget in self.results_content.winfo_children():
            widget.destroy()

        row = 0
        for section_name, entries in sections.items():
            card = ctk.CTkFrame(self.results_content, corner_radius=12)
            card.grid(row=row, column=0, sticky="ew", pady=(0, 10))
            card.grid_columnconfigure(0, weight=1)

            header = ctk.CTkLabel(
                card,
                text=section_name,
                font=("Segoe UI", 15, "bold"),
                anchor="w",
            )
            header.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 8))

            body_frame = ctk.CTkFrame(card, fg_color="transparent")
            body_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
            body_frame.grid_columnconfigure(1, weight=1)

            for index, (label, value) in enumerate(entries.items()):
                name_label = ctk.CTkLabel(
                    body_frame,
                    text=f"{label}:",
                    font=("Segoe UI", 12, "bold"),
                    anchor="w",
                )
                name_label.grid(row=index, column=0, sticky="nw", padx=(0, 10), pady=(0, 4))

                value_label = ctk.CTkLabel(
                    body_frame,
                    text=value,
                    font=("Segoe UI", 12),
                    anchor="w",
                    justify="left",
                    wraplength=560,
                )
                value_label.grid(row=index, column=1, sticky="ew", pady=(0, 4))

            row += 1

    def select_image(self) -> None:
        if filedialog is None:
            messagebox.showerror("Missing dependency", "tkinter is not available on this system.")
            return

        file_path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.tiff *.tif *.bmp *.webp"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        self.status_label.configure(text=os.path.basename(file_path))
        try:
            sections = collect_metadata_sections(Path(file_path))
        except ValueError as exc:
            self.render_placeholder()
            error_label = ctk.CTkLabel(
                self.results_content,
                text=f"Error\n{exc}",
                font=("Segoe UI", 13),
                justify="left",
                anchor="w",
            )
            error_label.grid(row=0, column=0, sticky="w", pady=10)
            return

        self.render_sections(sections)


def main() -> None:
    if ctk is None:
        raise RuntimeError("customtkinter is required to run the desktop application.")

    app = ctk.CTk()
    MetadataAnalyzerApp(app)
    app.mainloop()


if __name__ == "__main__":
    main()
