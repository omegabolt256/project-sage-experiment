from __future__ import annotations

from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter

from core.evidence_store import EvidenceStore


class DoclingIngestor:
    """
    Convert documents with Docling and persist the extracted content
    into Sage's existing EvidenceStore.
    """

    def __init__(self, evidence: EvidenceStore) -> None:
        self.evidence = evidence
        self.converter = DocumentConverter()

    def ingest(
        self,
        conversation_id: str,
        source: str,
        title: str = "",
    ) -> dict[str, Any]:
        """
        Convert a local file or supported URL with Docling and store
        the resulting Markdown as evidence.
        """

        source_path = Path(source)

        result = self.converter.convert(source)

        document = result.document

        markdown = document.export_to_markdown()

        if not title:
            if source_path.exists():
                title = source_path.name
            else:
                title = source

        metadata: dict[str, Any] = {
            "ingestion_method": "docling",
            "source": source,
            "source_exists_locally": source_path.exists(),
            "document_type": source_path.suffix.lower()
            if source_path.exists()
            else "",
        }

        evidence_id = self.evidence.add(
            conversation_id=conversation_id,
            source_type="document",
            title=title,
            url=source if source.startswith(("http://", "https://")) else "",
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
