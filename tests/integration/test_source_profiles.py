from pathlib import Path

import pytest
from ragscanner.application import resolve_secret_reference
from ragscanner.storage import (
    DuplicateSourceError,
    MachineSecretStore,
    SourceProfile,
    SQLiteSourceProfileRepository,
)


def test_source_profiles_and_setup_preferences_are_durable_and_secret_free(tmp_path: Path) -> None:
    database = tmp_path / "history.sqlite3"
    repository = SQLiteSourceProfileRepository(database)
    try:
        profile = repository.save(
            SourceProfile(
                name="Local OpenWebUI",
                kind="openwebui",
                base_url="http://127.0.0.1:3000",
                credential_ref="env:OPENWEBUI_API_KEY",
                discovery_origin="docker",
                capability_status="scan_ready",
            )
        )
        repository.set_setting("interface_mode", "web")
        assert repository.get(profile.id) == profile
        assert repository.list() == [profile]
        assert repository.setting("interface_mode") == "web"
        assert repository.delete(profile.id)
        assert not repository.delete(profile.id)
    finally:
        repository.close()

    payload = database.read_bytes()
    assert b"synthetic-secret-value" not in payload


def test_source_profile_rejects_secret_values_and_incomplete_locations() -> None:
    with pytest.raises(ValueError, match="not the API key itself"):
        SourceProfile(
            name="Unsafe",
            kind="openwebui",
            base_url="http://127.0.0.1:3000",
            credential_ref="synthetic-secret-value",
        )
    with pytest.raises(ValueError, match="filesystem profiles require"):
        SourceProfile(name="Missing", kind="filesystem")


@pytest.mark.parametrize(
    "reference",
    ["env:", "env:INVALID-NAME", "keychain:OPENWEBUI_API_KEY", "synthetic-secret-value"],
)
def test_source_profile_accepts_only_well_formed_environment_references(reference: str) -> None:
    with pytest.raises(ValueError, match="environment-variable reference"):
        SourceProfile(
            name="Unsafe",
            kind="openwebui",
            base_url="http://127.0.0.1:3000",
            credential_ref=reference,
        )


def test_machine_secret_reference_survives_repository_restart_without_entering_sqlite(
    tmp_path: Path,
) -> None:
    database = tmp_path / "history.sqlite3"
    store = MachineSecretStore(tmp_path)
    reference = store.save("source-synthetic", "synthetic-persisted-credential")
    repository = SQLiteSourceProfileRepository(database)
    try:
        saved = repository.save(
            SourceProfile(
                name="Persistent OpenWebUI",
                kind="openwebui",
                base_url="http://127.0.0.1:3000",
                credential_ref=reference,
            )
        )
    finally:
        repository.close()

    reopened = SQLiteSourceProfileRepository(database)
    try:
        assert reopened.get(saved.id) is not None
        assert resolve_secret_reference(reference) == "synthetic-persisted-credential"
    finally:
        reopened.close()

    assert b"synthetic-persisted-credential" not in database.read_bytes()
    assert store.delete(reference)


def test_duplicate_source_locations_are_rejected_after_normalization(tmp_path: Path) -> None:
    repository = SQLiteSourceProfileRepository(tmp_path / "history.sqlite3")
    try:
        repository.save(
            SourceProfile(name="First", kind="openwebui", base_url="http://LOCALHOST:3000/")
        )
        with pytest.raises(DuplicateSourceError, match="already connected"):
            repository.save(
                SourceProfile(name="Second", kind="openwebui", base_url="http://localhost:3000")
            )
    finally:
        repository.close()
