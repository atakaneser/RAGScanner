from ragscanner.local_site import (
    LOCAL_DASHBOARD_HOST,
    dashboard_url,
    local_hostname_is_registered,
    register_local_hostname,
    unregister_local_hostname,
)


def test_local_hostname_registration_is_idempotent_and_only_removes_its_own_line(tmp_path) -> None:  # type: ignore[no-untyped-def]
    hosts = tmp_path / "hosts"
    hosts.write_text("127.0.0.1 localhost\n127.0.0.1 unrelated.local # keep\n", encoding="utf-8")

    register_local_hostname(hosts)
    register_local_hostname(hosts)

    assert local_hostname_is_registered(hosts)
    assert hosts.read_text(encoding="utf-8").count(LOCAL_DASHBOARD_HOST) == 1

    unregister_local_hostname(hosts)

    assert not local_hostname_is_registered(hosts)
    assert "unrelated.local" in hosts.read_text(encoding="utf-8")


def test_dashboard_url_is_loopback_hostname_without_external_resolution() -> None:
    assert dashboard_url() == "http://local.ragscanner.com:8000"
    assert dashboard_url(port=80) == "http://local.ragscanner.com"
