from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile


@dataclass(frozen=True)
class ExtractedText:
    text: str
    metadata: dict[str, object]


def extract_text_from_material_path(
    path: str | Path,
    *,
    file_name: str | None,
    mime_type: str | None,
) -> ExtractedText:
    file_path = Path(path)
    suffix = Path(file_name or file_path.name).suffix.lower()
    source_location = f"text:{file_name or file_path.name}"
    if suffix == ".pdf" or mime_type == "application/pdf":
        text, metadata = _extract_pdf(file_path)
    elif suffix == ".docx" or _is_docx_mime(mime_type):
        text, metadata = _extract_docx(file_path)
    elif suffix == ".doc" or _is_doc_mime(mime_type):
        text, metadata = _extract_doc(file_path)
    else:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        metadata = {"extractor": "plain_text"}
    cleaned_text = _clean_text(text)
    return ExtractedText(
        text=cleaned_text,
        metadata={
            **metadata,
            "source_location": source_location,
            "file_name": file_name or file_path.name,
            "mime_type": mime_type,
            "has_text": bool(cleaned_text),
        },
    )


def _extract_pdf(path: Path) -> tuple[str, dict[str, object]]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return (
            path.read_text(encoding="utf-8", errors="ignore"),
            {
                "extractor": "pdf_best_effort",
                "warning": "pypdf is not installed; used best-effort text decode",
            },
        )

    reader = PdfReader(str(path))
    page_texts: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            page_texts.append(f"[page {index}]\n{text}")
    return (
        "\n\n".join(page_texts),
        {"extractor": "pypdf", "page_count": len(reader.pages)},
    )


def _extract_docx(path: Path) -> tuple[str, dict[str, object]]:
    try:
        with ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
    except (BadZipFile, KeyError):
        return (
            path.read_text(encoding="utf-8", errors="ignore"),
            {
                "extractor": "docx_best_effort",
                "warning": "docx package did not contain word/document.xml",
            },
        )

    root = ET.fromstring(document_xml)
    paragraphs: list[str] = []
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    for paragraph in root.iter(f"{namespace}p"):
        parts = [node.text or "" for node in paragraph.iter(f"{namespace}t")]
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs), {"extractor": "docx"}


def _extract_doc(path: Path) -> tuple[str, dict[str, object]]:
    antiword = shutil.which("antiword")
    if antiword:
        result = subprocess.run(
            [antiword, str(path)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout, {"extractor": "antiword"}

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [
                    soffice,
                    "--headless",
                    "--convert-to",
                    "txt:Text",
                    "--outdir",
                    tmp_dir,
                    str(path),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
            converted = Path(tmp_dir) / f"{path.stem}.txt"
            if result.returncode == 0 and converted.exists():
                return converted.read_text(encoding="utf-8", errors="ignore"), {
                    "extractor": "libreoffice"
                }

    return (
        path.read_text(encoding="utf-8", errors="ignore"),
        {
            "extractor": "doc_best_effort",
            "warning": "antiword/libreoffice not available; used best-effort text decode",
        },
    )


def _is_docx_mime(mime_type: str | None) -> bool:
    return (
        mime_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def _is_doc_mime(mime_type: str | None) -> bool:
    return mime_type in {
        "application/msword",
        "application/vnd.ms-word",
    }


def _clean_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()
