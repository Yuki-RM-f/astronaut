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


def test_memory_audit_v2_migration_uses_incremental_explicit_operations():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0006_memory_audit_v2_persona_engine.py"
    )
    source = migration_path.read_text(encoding="utf-8")

    assert "Base.metadata" not in source
    assert 'op.add_column("audit_logs"' in source
    assert 'op.add_column("persona_profiles"' in source
    assert 'op.create_table("memory_conflicts"' in source
    assert "op.drop_table(\"memory_conflicts\")" in source
