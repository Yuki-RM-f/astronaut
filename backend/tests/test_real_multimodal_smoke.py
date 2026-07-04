import json
import subprocess
from pathlib import Path

import pytest

from scripts.real_multimodal_smoke import (
    PUBLIC_SAMPLE_SOURCES,
    SmokeError,
    build_result_record,
    derive_document_samples,
    ensure_video_clip,
    redacted_provider_report,
)


def test_public_sample_manifest_uses_expected_sources():
    source_ids = {source.id for source in PUBLIC_SAMPLE_SOURCES}

    assert {"text", "image", "audio", "video"} <= source_ids
    assert PUBLIC_SAMPLE_SOURCES.by_id("text").url.startswith(
        "https://www.gutenberg.org/"
    )
    assert "commons.wikimedia.org" in PUBLIC_SAMPLE_SOURCES.by_id("image").url
    assert "archive.org" in PUBLIC_SAMPLE_SOURCES.by_id("audio").url
    assert "commons.wikimedia.org" in PUBLIC_SAMPLE_SOURCES.by_id("video").url


def test_provider_report_redacts_secret_like_values():
    report = redacted_provider_report(
        {
            "providers": [
                {
                    "id": "dashscope",
                    "configured": True,
                    "settings": {
                        "api_key": "sk-secret",
                        "compat_base_url": "https://example.test/v1",
                    },
                }
            ]
        }
    )

    serialized = json.dumps(report, ensure_ascii=False)
    assert "sk-secret" not in serialized
    assert report["providers"][0]["settings"]["api_key"] == "<redacted>"
    assert report["providers"][0]["settings"]["compat_base_url"] == "https://example.test/v1"


def test_derive_document_samples_creates_local_text_documents(tmp_path):
    text_path = tmp_path / "alice.txt"
    text_path.write_text(
        "Alice remembered her sister. Grandmother said take your time.",
        encoding="utf-8",
    )

    derived = derive_document_samples(text_path, tmp_path)

    assert {path.suffix for path in derived} == {".pdf", ".docx", ".doc"}
    for path in derived:
        assert path.exists()
        assert path.stat().st_size > 0


def test_ensure_video_clip_requires_ffmpeg_for_video_smoke(tmp_path, monkeypatch):
    video_path = tmp_path / "sample.webm"
    video_path.write_bytes(b"not a real video")
    monkeypatch.setattr("scripts.real_multimodal_smoke.shutil.which", lambda _: None)

    with pytest.raises(SmokeError, match="ffmpeg"):
        ensure_video_clip(video_path, tmp_path / "clip.mp4")


def test_ensure_video_clip_reports_ffmpeg_failure(tmp_path, monkeypatch):
    video_path = tmp_path / "sample.webm"
    video_path.write_bytes(b"not a real video")
    monkeypatch.setattr("scripts.real_multimodal_smoke.shutil.which", lambda _: "ffmpeg")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=1, stderr="bad video")

    monkeypatch.setattr("scripts.real_multimodal_smoke.subprocess.run", fake_run)

    with pytest.raises(SmokeError, match="bad video"):
        ensure_video_clip(video_path, tmp_path / "clip.mp4")


def test_result_record_keeps_public_artifacts_and_errors_without_secrets(tmp_path):
    result_path = tmp_path / "result.json"
    record = build_result_record(
        backend_url="http://localhost:8000",
        sample_mode="public",
        provider_report={"providers": [{"id": "dashscope", "configured": True}]},
        sample_files={"text": tmp_path / "alice.txt"},
        material_results=[
            {
                "kind": "text",
                "material_id": "mat-1",
                "job_id": "job-1",
                "status": "succeeded",
                "provider_name": "dashscope",
            }
        ],
        errors=[{"kind": "audio", "error": "HTTP 402: Payment Required"}],
        output_path=result_path,
    )

    serialized = json.dumps(record, ensure_ascii=False)
    assert record["backend_url"] == "http://localhost:8000"
    assert record["sample_mode"] == "public"
    assert record["samples"]["text"]["path"].endswith("alice.txt")
    assert record["materials"][0]["provider_name"] == "dashscope"
    assert "Payment Required" in serialized
    assert "DASHSCOPE_API_KEY" not in serialized
    assert result_path.exists()
