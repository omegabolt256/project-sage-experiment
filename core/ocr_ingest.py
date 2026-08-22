from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pypdfium2
import pytesseract

from core.evidence_store import EvidenceStore


DEFAULT_WINDOWS_TESSERACT = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


class OCRIngestor:
    """
    Render PDF pages with PDFium and extract text with Tesseract.
    """

    def __init__(self, evidence: EvidenceStore) -> None:
        self.evidence = evidence
        self.tesseract_cmd = self._resolve_tesseract()

        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    @staticmethod
    def _resolve_tesseract() -> str:
        configured = os.getenv("TESSERACT_CMD", "").strip()

        if configured and Path(configured).is_file():
            return configured

        if DEFAULT_WINDOWS_TESSERACT.is_file():
            return str(DEFAULT_WINDOWS_TESSERACT)

        raise RuntimeError(
            "Tesseract executable not found. "
            "Set TESSERACT_CMD or install Tesseract at "
            f"{DEFAULT_WINDOWS_TESSERACT}."
        )

    def ingest(
        self,
        conversation_id: str,
        source: str,
        title: str = "",
    ) -> dict[str, Any]:
        source_path = Path(source)

        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        if source_path.suffix.lower() != ".pdf":
            raise ValueError(
                "OCRIngestor currently supports PDF files only."
            )

        pdf = pypdfium2.PdfDocument(str(source_path))

        page_count = len(pdf)

        pages: list[str] = []

        try:
            for page_number, page in enumerate(pdf, start=1):
                bitmap = page.render(scale=2.0)
                image = bitmap.to_pil()

                text = pytesseract.image_to_string(
                    image,
                    config="--psm 3",
                ).strip()

                if text:
                    pages.append(
                        f"## Page {page_number}\n\n{text}"
                    )
        finally:
            pdf.close()

        markdown = "\n\n".join(pages)

        if not title:
            title = source_path.name

        metadata: dict[str, Any] = {
            "ingestion_method": "tesseract_ocr",
            "source": source,
            "source_exists_locally": True,
            "document_type": ".pdf",
            "page_count": page_count,
            "pages_with_text": len(pages),
            "ocr_engine": "tesseract",
            "tesseract_cmd": self.tesseract_cmd,
        }

        evidence_id = self.evidence.add(
            conversation_id=conversation_id,
            source_type="document",
            title=title,
            url="",
            content=markdown,
            metadata=metadata,
        )

        return {
            "evidence_id": evidence_id,
            "source": source,
            "title": title,
            "content": markdown,
            "metadata": metadata,
        }
