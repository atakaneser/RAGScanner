"""Conservative source-language inference tests."""

from ragscanner.reporting.language import infer_report_language


def test_declared_supported_language_wins() -> None:
    assert infer_report_language([("text", "tr-TR")], fallback="en") == "tr"


def test_turkish_source_text_is_detected() -> None:
    text = (
        "Bu belge ile VPN bağlantısı için yapılması gereken adımlar açıklanır. "
        "Bir kullanıcı uygulama üzerinden giriş yaptıktan sonra kodu ilgili alana girer "
        "ve işlem olarak kaydedilir."
    )
    assert infer_report_language([(text, None)], fallback="en") == "tr"


def test_ambiguous_text_preserves_explicit_fallback() -> None:
    assert infer_report_language([("VPN MFA 123", None)], fallback="fr") == "fr"
