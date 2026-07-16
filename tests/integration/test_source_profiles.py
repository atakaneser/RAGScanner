from pathlib import Path

import pytest
from ragscanner.storage import SourceProfile, SQLiteSourceProfileRepository


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
    assert b"OPENWEBUI_API_KEY" in payload
    assert b"synthetic-secret-value" not in payload


def test_source_profile_rejects_secret_values_and_incomplete_locations() -> None:
    with pytest.raises(ValueError, match="credential references must use env"):
        SourceProfile(
            name="Unsafe",
            kind="openwebui",
            base_url="http://127.0.0.1:3000",
            credential_ref="synthetic-secret-value",
        )
    with pytest.raises(ValueError, match="filesystem profiles require"):
        SourceProfile(name="Missing", kind="filesystem")
