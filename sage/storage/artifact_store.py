from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    uri: str
    version: str
    path: Path
    size_bytes: int
    sha256: str


class ArtifactStore:
    """
    Local-first immutable artifact store.

    Logical URI:
        artifact://research/doc1.pdf

    Physical storage:
        <root>/research/doc1/<sha256>.blob
        <root>/research/doc1/LATEST
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(uri: str) -> str:
        if not uri.startswith("artifact://"):
            raise ValueError("ArtifactStore requires artifact:// URI")
        key = uri[len("artifact://"):].strip("/")
        if not key or ".." in Path(key).parts:
            raise ValueError(f"Unsafe artifact URI: {uri}")
        return key

    @staticmethod
    def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(chunk_size):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
        tmp_path = Path(tmp)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def put_file(self, uri: str, source: str | Path) -> ArtifactRef:
        src = Path(source)
        if not src.is_file():
            raise FileNotFoundError(src)

        key = self._key(uri)
        digest = self._sha256_file(src)
        size = src.stat().st_size

        folder = self.root / key
        folder.mkdir(parents=True, exist_ok=True)
        blob = folder / f"{digest}.blob"
        latest = folder / "LATEST"

        if not blob.exists():
            fd, tmp = tempfile.mkstemp(
                prefix=f".{digest}.",
                suffix=".tmp",
                dir=str(folder),
            )
            tmp_path = Path(tmp)
            try:
                with os.fdopen(fd, "wb") as out, src.open("rb") as inp:
                    while chunk := inp.read(1024 * 1024):
                        out.write(chunk)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(tmp_path, blob)
            finally:
                tmp_path.unlink(missing_ok=True)

        self._atomic_write(latest, digest.encode("ascii"))
        return ArtifactRef(uri, digest, blob, size, digest)

    def get(self, uri: str) -> ArtifactRef:
        folder = self.root / self._key(uri)
        latest = folder / "LATEST"
        if not latest.exists():
            raise KeyError(uri)

        version = latest.read_text(encoding="ascii").strip()
        blob = folder / f"{version}.blob"
        if not blob.exists():
            raise RuntimeError(
                f"Artifact integrity error: {uri} -> missing {version}"
            )

        return ArtifactRef(
            uri=uri,
            version=version,
            path=blob,
            size_bytes=blob.stat().st_size,
            sha256=version,
        )