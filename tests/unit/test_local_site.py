from ragscanner.local_site import (
    DASHBOARD_BIND_HOST,
    DASHBOARD_PORT,
    dashboard_url,
    remove_legacy_hostname,
)


def test_legacy_hostname_cleanup_only_removes_the_product_owned_line(tmp_path) -> None:  # type: ignore[no-untyped-def]
    hosts = tmp_path / "hosts"
    hosts.write_text(
        "127.0.0.1 localhost\n"
        "127.0.0.1 local.ragscanner.com # RAGScanner local dashboard\n"
        "127.0.0.1 unrelated.local # keep\n",
        encoding="utf-8",
    )

    assert remove_legacy_hostname(hosts)
    assert not remove_legacy_hostname(hosts)

    content = hosts.read_text(encoding="utf-8")
    assert "local.ragscanner.com" not in content
    assert "unrelated.local" in content


def test_dashboard_has_one_fixed_loopback_address() -> None:
    assert DASHBOARD_BIND_HOST == "127.0.0.1"
    assert DASHBOARD_PORT == 8765
    assert dashboard_url() == "http://localhost:8765"
