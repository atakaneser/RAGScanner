from ragscanner.local_auth import LocalAdministratorStore


def test_local_administrator_uses_a_non_reversible_password_hash(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = LocalAdministratorStore(tmp_path)

    created = store.create("host-admin", "a long local-only password")

    assert created.username == "host-admin"
    assert store.verify("host-admin", "a long local-only password")
    assert not store.verify("host-admin", "incorrect password")
    saved = (tmp_path / "local-administrator.json").read_text(encoding="utf-8")
    assert "a long local-only password" not in saved
