import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def test_backend_container_entrypoint_runs_migrations_before_uvicorn():
    entrypoint_path = ROOT_DIR / "backend" / "docker-entrypoint.sh"
    dockerfile = (ROOT_DIR / "backend" / "Dockerfile").read_text(encoding="utf-8")

    assert entrypoint_path.exists()
    entrypoint = entrypoint_path.read_text(encoding="utf-8")

    assert "alembic upgrade head" in entrypoint
    assert "exec uvicorn app.main:app" in entrypoint
    assert 'CMD ["./docker-entrypoint.sh"]' in dockerfile


def test_backend_app_imports_from_clean_process():
    result = subprocess.run(
        [sys.executable, "-c", "from app.main import app; print(app.title)"],
        cwd=ROOT_DIR / "backend",
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_dockerignore_files_exclude_generated_host_state():
    backend_ignore = (ROOT_DIR / "backend" / ".dockerignore").read_text(encoding="utf-8")
    frontend_ignore = (ROOT_DIR / "frontend" / ".dockerignore").read_text(encoding="utf-8")

    assert "__pycache__/" in backend_ignore
    assert "*.py[cod]" in backend_ignore
    assert ".pytest_cache/" in backend_ignore
    assert ".env*" in backend_ignore

    assert "node_modules/" in frontend_ignore
    assert ".next/" in frontend_ignore
    assert "next-env.d.ts" in frontend_ignore
    assert ".env*" in frontend_ignore
