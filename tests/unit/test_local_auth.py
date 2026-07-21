from ragscanner.local_auth import LocalAdministratorStore


def test_local_administrator_uses_a_non_reversible_password_hash(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = LocalAdministratorStore(tmp_path)

    created = store.create("host-admin", "a long local-only password")

    assert created.username == "host-admin"
    assert store.verify("host-admin", "a long local-only password")
    assert not store.verify("host-admin", "incorrect password")
    saved = (tmp_path / "local-administrator.json").read_text(encoding="utf-8")
    assert "a long local-only password" not in saved


def test_password_change_rotates_sessions_and_replaces_password_atomically(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = LocalAdministratorStore(tmp_path)
    store.create("host-admin", "a long local-only password")
    old_session = store.issue_session("host-admin")

    changed = store.change_password("a long local-only password", "a different long local password")

    assert changed.username == "host-admin"
    assert not store.verify("host-admin", "a long local-only password")
    assert store.verify("host-admin", "a different long local password")
    assert not store.valid_session(old_session)
    assert store.valid_session(store.issue_session("host-admin"))
    assert list(tmp_path.glob("*.tmp")) == []


def test_password_change_rejects_invalid_current_weak_and_reused_passwords(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = LocalAdministratorStore(tmp_path)
    password = "a long local-only password"  # noqa: S105 - synthetic test value
    store.create("host-admin", password)

    for current, replacement, error in (
        ("incorrect password", "a different long local password", PermissionError),
        (password, "too short", ValueError),
        (password, password, ValueError),
    ):
        try:
            store.change_password(current, replacement)
        except error:
            pass
        else:
            raise AssertionError(f"expected {error.__name__}")

    assert store.verify("host-admin", password)
