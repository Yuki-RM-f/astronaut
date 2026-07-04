from pathlib import Path


def test_initial_migration_uses_explicit_table_operations():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0001_initial_schema.py"
    )
    source = migration_path.read_text(encoding="utf-8")

    assert "Base.metadata" not in source
    assert "op.create_table(" in source
    assert "op.drop_table(" in source
