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


def test_compose_supports_ecs_public_urls_without_exposing_internal_services():
    compose = (ROOT_DIR / "docker-compose.yml").read_text(encoding="utf-8")

    assert "FRONTEND_URL: ${FRONTEND_URL:-http://localhost:3000}" in compose
    assert "BACKEND_URL: ${BACKEND_URL:-http://localhost:8000}" in compose
    assert "NEXT_PUBLIC_API_BASE_URL: ${NEXT_PUBLIC_API_BASE_URL:-http://localhost:8000}" in compose

    assert '"${POSTGRES_HOST_BIND:-127.0.0.1}:${POSTGRES_HOST_PORT:-15432}:5432"' in compose
    assert '"${REDIS_HOST_BIND:-127.0.0.1}:${REDIS_HOST_PORT:-6379}:6379"' in compose
    assert '"${MINIO_API_HOST_BIND:-127.0.0.1}:${MINIO_API_HOST_PORT:-9000}:9000"' in compose
    assert '"${MINIO_CONSOLE_HOST_BIND:-127.0.0.1}:${MINIO_CONSOLE_HOST_PORT:-9001}:9001"' in compose


def test_frontend_dockerfile_injects_public_api_base_url_at_build_time():
    dockerfile = (ROOT_DIR / "frontend" / "Dockerfile").read_text(encoding="utf-8")

    assert "ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" in dockerfile
    assert "ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}" in dockerfile
    assert dockerfile.index("ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}") < dockerfile.index(
        "RUN npm run build"
    )


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
