from __future__ import annotations

import argparse
import json
import mimetypes
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile

import httpx


class SmokeError(RuntimeError):
    pass


@dataclass(frozen=True)
class PublicSampleSource:
    id: str
    label: str
    url: str
    file_name: str
    content_type: str
    provenance: str


class PublicSampleSources:
    def __init__(self, sources: Iterable[PublicSampleSource]) -> None:
        self._sources = tuple(sources)

    def __iter__(self):
        return iter(self._sources)

    def by_id(self, source_id: str) -> PublicSampleSource:
        for source in self._sources:
            if source.id == source_id:
                return source
        raise KeyError(source_id)


PUBLIC_SAMPLE_SOURCES = PublicSampleSources(
    [
        PublicSampleSource(
            id="text",
            label="Project Gutenberg Alice public-domain text",
            url="https://www.gutenberg.org/files/11/11-0.txt",
            file_name="alice-public-domain.txt",
            content_type="text/plain",
            provenance="https://www.gutenberg.org/ebooks/11",
        ),
        PublicSampleSource(
            id="image",
            label="Wikimedia Commons stop sign public-domain PNG",
            url="https://commons.wikimedia.org/wiki/Special:Redirect/file/Stop_sign.png",
            file_name="stop-sign.png",
            content_type="image/png",
            provenance="https://commons.wikimedia.org/wiki/File:Stop_sign.png",
        ),
        PublicSampleSource(
            id="audio",
            label="LibriVox public-domain short poetry MP3",
            url="https://archive.org/download/short_poetry_001_librivox/abou_hunt_py_64kb.mp3",
            file_name="abou-ben-adhem.mp3",
            content_type="audio/mpeg",
            provenance="https://archive.org/details/short_poetry_001_librivox",
        ),
        PublicSampleSource(
            id="video",
            label="Wikimedia Commons USGS volcano lava WebM",
            url="https://commons.wikimedia.org/wiki/Special:Redirect/file/Volcano_Lava_Sample.webm",
            file_name="volcano-lava-sample.webm",
            content_type="video/webm",
            provenance="https://commons.wikimedia.org/wiki/File:Volcano_Lava_Sample.webm",
        ),
    ]
)


SECRET_KEY_MARKERS = ("api_key", "apikey", "secret", "token", "password")


def main() -> int:
    args = _parse_args()
    work_dir = Path(args.work_dir)
    sources_dir = work_dir / "sources"
    results_dir = work_dir / "results"
    sources_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    errors: list[dict[str, str]] = []
    material_results: list[dict[str, Any]] = []
    sample_files: dict[str, Path] = {}

    try:
        prepared = prepare_public_samples(
            sources_dir,
            max_download_mb=args.max_download_mb,
            ffmpeg_docker_image=args.ffmpeg_docker_image,
        )
        sample_files.update(prepared)
        result_path = results_dir / f"{_timestamp()}.json"
        with httpx.Client(base_url=args.backend_url.rstrip("/"), timeout=args.timeout) as client:
            token = _bootstrap_smoke_account(client)
            headers = {"Authorization": f"Bearer {token}"}
            provider_report = redacted_provider_report(
                _request_json(client, "GET", "/api/settings/providers", headers=headers)
            )
            _assert_dashscope_ready(provider_report)
            persona = _create_smoke_persona(client, headers)

            upload_plan = [
                ("text", prepared["text"], "Public-domain text sample"),
                (
                    "image",
                    prepared["image"],
                    "A public stop-sign image from a walk with the persona; "
                    "the persona taught the user to pause, stop, and look both ways.",
                ),
                ("audio", prepared["audio"], "Public-domain spoken poetry ASR sample"),
                ("video", prepared["video_clip"], "Trimmed public-domain video sample"),
                ("pdf", prepared["pdf"], "Derived public-domain PDF text sample"),
                ("docx", prepared["docx"], "Derived public-domain DOCX text sample"),
                ("doc", prepared["doc"], "Derived public-domain DOC text sample"),
            ]
            for kind, path, description in upload_plan:
                try:
                    material_results.append(
                        upload_and_assert_material(
                            client,
                            headers,
                            persona_id=persona["id"],
                            kind=kind,
                            path=path,
                            user_description=description,
                        )
                    )
                except Exception as exc:
                    errors.append({"kind": kind, "error": str(exc)})

        record = build_result_record(
            backend_url=args.backend_url,
            sample_mode=args.sample_mode,
            provider_report=provider_report,
            sample_files=sample_files,
            material_results=material_results,
            errors=errors,
            output_path=result_path,
        )
        print(json.dumps(record, ensure_ascii=False, indent=2))
        if errors:
            return 1
        return 0
    except Exception as exc:
        result_path = results_dir / f"{_timestamp()}-failed.json"
        record = build_result_record(
            backend_url=args.backend_url,
            sample_mode=args.sample_mode,
            provider_report={},
            sample_files=sample_files,
            material_results=material_results,
            errors=[{"kind": "preflight", "error": str(exc)}],
            output_path=result_path,
        )
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run real DashScope multimodal parsing smoke with public samples."
    )
    parser.add_argument("--backend-url", default="http://localhost:8000")
    parser.add_argument("--sample-mode", choices=["public"], default="public")
    parser.add_argument("--work-dir", default=".smoke/real-multimodal")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-download-mb", type=int, default=60)
    parser.add_argument("--ffmpeg-docker-image", default="persona-memory-agent-backend:local")
    return parser.parse_args()


def prepare_public_samples(
    sources_dir: Path,
    *,
    max_download_mb: int,
    ffmpeg_docker_image: str | None = None,
) -> dict[str, Path]:
    samples: dict[str, Path] = {}
    for source in PUBLIC_SAMPLE_SOURCES:
        target = sources_dir / source.file_name
        download_file(source, target, max_download_mb=max_download_mb)
        samples[source.id] = target

    trimmed_text = sources_dir / "alice-memory-trimmed.txt"
    _write_trimmed_text_sample(samples["text"], trimmed_text)
    samples["text"] = trimmed_text

    for path in derive_document_samples(trimmed_text, sources_dir):
        samples[path.suffix.lstrip(".")] = path

    clip_path = sources_dir / "volcano-lava-smoke-clip.mp4"
    ensure_video_clip(
        samples["video"],
        clip_path,
        docker_image=ffmpeg_docker_image,
    )
    samples["video_clip"] = clip_path
    return samples


def download_file(
    source: PublicSampleSource,
    target: Path,
    *,
    max_download_mb: int,
) -> Path:
    if target.exists() and target.stat().st_size > 0:
        return target

    request = Request(source.url, headers={"User-Agent": "persona-memory-smoke/1.0"})
    try:
        with urlopen(request, timeout=60) as response:
            content_length = response.headers.get("content-length")
            if content_length:
                _assert_download_size(int(content_length), max_download_mb, source.url)
            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            with target.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    _assert_download_size(written, max_download_mb, source.url)
                    handle.write(chunk)
    except HTTPError as exc:
        body = exc.read(500).decode("utf-8", errors="ignore")
        raise SmokeError(f"download failed for {source.url}: HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise SmokeError(f"download failed for {source.url}: {exc}") from exc
    return target


def derive_document_samples(text_path: Path, output_dir: Path) -> list[Path]:
    text = text_path.read_text(encoding="utf-8", errors="ignore")
    compact_text = " ".join(text.split())[:1400] or "Alice remembered a warm family story."
    pdf_path = output_dir / "alice-derived.pdf"
    docx_path = output_dir / "alice-derived.docx"
    doc_path = output_dir / "alice-derived.doc"
    _write_simple_pdf(pdf_path, compact_text)
    _write_simple_docx(docx_path, compact_text)
    doc_path.write_text(compact_text, encoding="utf-8")
    return [pdf_path, docx_path, doc_path]


def ensure_video_clip(
    source_video: Path,
    output_path: Path,
    *,
    docker_image: str | None = None,
) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    docker = shutil.which("docker")
    if not ffmpeg and not (docker and docker_image):
        raise SmokeError("ffmpeg is required for video smoke audio extraction and key frames")
    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        _ffmpeg_trim_command(ffmpeg, docker, docker_image, source_video, output_path),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if result.returncode != 0 or not output_path.exists():
        stderr = (result.stderr or "").strip()[:1000]
        raise SmokeError(f"ffmpeg video trim failed with code {result.returncode}: {stderr}")
    return output_path


def _ffmpeg_trim_command(
    ffmpeg: str | None,
    docker: str | None,
    docker_image: str | None,
    source_video: Path,
    output_path: Path,
) -> list[str]:
    trim_args = [
        "-y",
        "-i",
        str(source_video),
        "-t",
        "12",
        "-vf",
        "scale=-2:360",
        "-r",
        "12",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "30",
        "-c:a",
        "aac",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    if ffmpeg:
        return [ffmpeg, *trim_args]
    if source_video.parent.resolve() != output_path.parent.resolve():
        raise SmokeError("docker ffmpeg fallback requires source and output in the same directory")
    return [
        docker or "docker",
        "run",
        "--rm",
        "-v",
        f"{source_video.parent.resolve()}:/work",
        docker_image or "persona-memory-agent-backend:local",
        "ffmpeg",
        *[
            "/work/" + value.name if isinstance(value, Path) else value
            for value in [
                "-y",
                "-i",
                source_video,
                "-t",
                "12",
                "-vf",
                "scale=-2:360",
                "-r",
                "12",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "30",
                "-c:a",
                "aac",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-movflags",
                "+faststart",
                output_path,
            ]
        ],
    ]


def redacted_provider_report(report: dict[str, Any]) -> dict[str, Any]:
    return _redact_secrets(report)


def build_result_record(
    *,
    backend_url: str,
    sample_mode: str,
    provider_report: dict[str, Any],
    sample_files: dict[str, Path],
    material_results: list[dict[str, Any]],
    errors: list[dict[str, str]],
    output_path: Path,
) -> dict[str, Any]:
    record = {
        "created_at": _timestamp(),
        "backend_url": backend_url,
        "sample_mode": sample_mode,
        "provider_report": redacted_provider_report(provider_report),
        "sample_sources": [asdict(source) for source in PUBLIC_SAMPLE_SOURCES],
        "samples": {
            key: {"path": str(path), "bytes": path.stat().st_size if path.exists() else 0}
            for key, path in sorted(sample_files.items())
        },
        "materials": material_results,
        "errors": errors,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def upload_and_assert_material(
    client: httpx.Client,
    headers: dict[str, str],
    *,
    persona_id: str,
    kind: str,
    path: Path,
    user_description: str,
) -> dict[str, Any]:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    with path.open("rb") as handle:
        response = client.post(
            f"/api/personas/{persona_id}/materials/upload",
            headers=headers,
            data={"importance": "important", "user_description": user_description},
            files={"files": (path.name, handle, mime_type)},
        )
    if response.status_code >= 400:
        raise SmokeError(f"upload {kind} failed: HTTP {response.status_code}: {response.text[:800]}")
    body = response.json()
    material = (body.get("items") or [None])[0]
    if not material:
        raise SmokeError(f"upload {kind} did not return a material")
    jobs = material.get("jobs") or []
    job = jobs[0] if jobs else {}
    if material.get("parse_status") != "succeeded" or job.get("status") != "succeeded":
        raise SmokeError(
            f"{kind} parse failed: material={material.get('parse_status')} "
            f"job={job.get('status')} error={job.get('error_message')}"
        )
    if job.get("provider_name") != "dashscope":
        raise SmokeError(f"{kind} used provider {job.get('provider_name')}, expected dashscope")
    if job.get("provider_type") != "third_party":
        raise SmokeError(f"{kind} used provider_type {job.get('provider_type')}, expected third_party")

    memories = _request_json(
        client,
        "GET",
        f"/api/personas/{persona_id}/memories",
        headers=headers,
    ).get("items", [])
    source_memories = [
        memory for memory in memories if memory.get("source_material_id") == material.get("id")
    ]
    if not source_memories:
        raise SmokeError(f"{kind} did not create source-backed memories")
    output = job.get("output_json") or {}
    if not output.get("parsed_chunk_id"):
        raise SmokeError(f"{kind} job did not expose parsed_chunk_id")
    if not output.get("memory_card_ids"):
        raise SmokeError(f"{kind} job did not expose memory_card_ids")

    return {
        "kind": kind,
        "path": str(path),
        "material_id": material["id"],
        "file_type": material["file_type"],
        "parse_status": material["parse_status"],
        "job_id": job.get("id"),
        "status": job.get("status"),
        "provider_name": job.get("provider_name"),
        "provider_type": job.get("provider_type"),
        "memory_count": len(source_memories),
        "parsed_chunk_id": output.get("parsed_chunk_id"),
    }


def _request_json(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    json_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = client.request(method, path, headers=headers, json=json_payload)
    if response.status_code >= 400:
        raise SmokeError(f"{method} {path} failed: HTTP {response.status_code}: {response.text[:800]}")
    return response.json()


def _bootstrap_smoke_account(client: httpx.Client) -> str:
    health = client.get("/health")
    if health.status_code >= 400:
        raise SmokeError(f"/health failed: HTTP {health.status_code}: {health.text[:500]}")
    email = f"real-multimodal-smoke-{int(time.time())}@local.test"
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "smoke-password",
            "display_name": "Real multimodal smoke",
        },
    )
    if response.status_code >= 400:
        raise SmokeError(f"register failed: HTTP {response.status_code}: {response.text[:800]}")
    return response.json()["access_token"]


def _create_smoke_persona(client: httpx.Client, headers: dict[str, str]) -> dict[str, Any]:
    return _request_json(
        client,
        "POST",
        "/api/personas",
        headers=headers,
        json_payload={
            "name": "Smoke Memory Person",
            "persona_type": "deceased_relative",
            "status": "deceased",
            "relationship_to_user": "grandmother",
            "user_nickname_by_persona": "child",
            "age": 72,
            "gender": "female",
            "language": "en",
            "short_bio": "A warm demo persona for real multimodal provider smoke.",
            "speaking_style": "Warm, concise, and grounded in uploaded material.",
            "emotional_style": "Gentle support without claiming real presence.",
            "forbidden_expressions": "Do not claim resurrection or unsupported facts.",
        },
    )


def _assert_dashscope_ready(provider_report: dict[str, Any]) -> None:
    if provider_report.get("default_llm_provider") != "dashscope":
        raise SmokeError(
            "DEFAULT_LLM_PROVIDER must be dashscope for real multimodal smoke"
        )
    dashscope = None
    for provider in provider_report.get("providers", []):
        if provider.get("id") == "dashscope":
            dashscope = provider
            break
    if not dashscope or not dashscope.get("configured"):
        raise SmokeError("DashScope provider is not configured")


def _write_trimmed_text_sample(source_path: Path, target_path: Path) -> None:
    raw = source_path.read_text(encoding="utf-8", errors="ignore")
    marker = "CHAPTER I."
    start = raw.find(marker)
    excerpt = raw[start : start + 2200] if start >= 0 else raw[:2200]
    target_path.write_text(excerpt.strip() or raw[:2200], encoding="utf-8")


def _write_simple_docx(path: Path, text: str) -> None:
    escaped = _xml_escape(text)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        f"<w:p><w:r><w:t>{escaped}</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                "</Types>"
            ),
        )
        archive.writestr("word/document.xml", document_xml)


def _write_simple_pdf(path: Path, text: str) -> None:
    safe_text = text.encode("latin-1", errors="ignore").decode("latin-1")
    lines = [line[:90] for line in _wrap_text(safe_text, width=90)[:18]]
    content_lines = ["BT", "/F1 11 Tf", "50 760 Td"]
    for index, line in enumerate(lines):
        if index:
            content_lines.append("0 -18 Td")
        content_lines.append(f"({_escape_pdf_text(line)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    path.write_bytes(bytes(output))


def _redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if any(marker in str(key).lower() for marker in SECRET_KEY_MARKERS):
                redacted[key] = "<redacted>" if item else item
            else:
                redacted[key] = _redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [_redact_secrets(item) for item in value]
    return value


def _assert_download_size(size_bytes: int, max_download_mb: int, url: str) -> None:
    max_bytes = max_download_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise SmokeError(
            f"download exceeds limit for {url}: {size_bytes} bytes > {max_bytes} bytes"
        )


def _wrap_text(text: str, *, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


if __name__ == "__main__":
    raise SystemExit(main())
