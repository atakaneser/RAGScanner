"""Localization for deterministic report text owned by RAGScanner."""

from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)

RuleFields = dict[str, str]
RuleLocales = dict[str, RuleFields]

_QUALITY_IMPACT_EN = (
    "Poor chunk quality can reduce retrieval precision, waste context, or hide source structure."
)
_QUALITY_IMPACT_TR = (
    "Düşük parça kalitesi getirim doğruluğunu azaltabilir, bağlamı israf edebilir "
    "veya kaynak yapısını gizleyebilir."
)

_CHUNK_TITLES: Final[dict[str, tuple[str, str]]] = {
    "APPROXIMATE-MAPPING": ("Approximate Mapping", "Yaklaşık Konum Eşlemesi"),
    "BOILERPLATE-DOMINATED-CHUNK": (
        "Boilerplate Dominated Chunk",
        "Şablon Metnin Baskın Olduğu Parça",
    ),
    "CODE-BLOCK-SPLIT": ("Code Block Split", "Kod Bloğunda Bölünme"),
    "EMPTY-CHUNK": ("Empty Chunk", "Boş Parça"),
    "EXCESSIVE-CHUNK-COUNT": ("Excessive Chunk Count", "Aşırı Parça Sayısı"),
    "EXCESSIVE-CONTROL-MARKERS": (
        "Excessive Control Markers",
        "Aşırı Kontrol İşareti",
    ),
    "EXCESSIVE-OVERLAP": ("Excessive Overlap", "Aşırı Örtüşme"),
    "EXTREME-SIZE-OUTLIER": ("Extreme Size Outlier", "Aşırı Boyut Aykırılığı"),
    "FORCED-SPLIT": ("Forced Split", "Zorunlu Bölünme"),
    "GARBLED-EXTRACTION": ("Garbled Extraction", "Bozuk Metin Çıkarımı"),
    "HIGHLY-REPETITIVE-TOKENS": (
        "Highly Repetitive Tokens",
        "Aşırı Tekrarlanan Belirteçler",
    ),
    "LIST-SPLIT": ("List Split", "Listede Bölünme"),
    "LOW-INFORMATION-DENSITY": ("Low Information Density", "Düşük Bilgi Yoğunluğu"),
    "LOW-PRINTABLE-RATIO": (
        "Low Printable Ratio",
        "Düşük Yazdırılabilir Karakter Oranı",
    ),
    "MIDDLE-SENTENCE-END": ("Middle Sentence End", "Cümlenin Ortasında Bitiş"),
    "MIDDLE-SENTENCE-START": ("Middle Sentence Start", "Cümlenin Ortasında Başlangıç"),
    "NEAR-CHARACTER-LIMIT": ("Near Character Limit", "Karakter Sınırına Yakın"),
    "NEAR-IDENTICAL-NEIGHBOR-CHUNKS": (
        "Near Identical Neighbor Chunks",
        "Neredeyse Aynı Komşu Parçalar",
    ),
    "NUMERIC-ONLY-CHUNK": ("Numeric Only Chunk", "Yalnızca Sayı İçeren Parça"),
    "OVERSIZED-CHUNK": ("Oversized Chunk", "Aşırı Büyük Parça"),
    "PAGE-NUMBER-ONLY-CHUNK": (
        "Page Number Only Chunk",
        "Yalnızca Sayfa Numarası İçeren Parça",
    ),
    "PUNCTUATION-ONLY-CHUNK": (
        "Punctuation Only Chunk",
        "Yalnızca Noktalama İçeren Parça",
    ),
    "REPEATED-LINE-CHUNK": ("Repeated Line Chunk", "Tekrarlanan Satır İçeren Parça"),
    "TABLE-SPLIT": ("Table Split", "Tabloda Bölünme"),
    "UNDERSIZED-CHUNK": ("Undersized Chunk", "Aşırı Küçük Parça"),
    "UNRELATED-HEADING-BRANCHES": (
        "Unrelated Heading Branches",
        "İlgisiz Başlık Dalları",
    ),
}

_RECOMMENDATIONS: Final[dict[str, tuple[str, str]]] = {
    "default": (
        "Review the chunk and adjust deterministic chunking configuration if appropriate.",
        "Parçayı inceleyin ve gerekiyorsa deterministik parçalama ayarını düzeltin.",
    ),
    "rechunk": (
        "Rechunk with safer structural boundaries and review the affected source.",
        "Daha güvenli yapısal sınırlarla yeniden parçalayın ve etkilenen kaynağı inceleyin.",
    ),
    "merge": (
        "Consider merging with a related adjacent chunk while preserving headings.",
        "Başlıkları koruyarak ilgili komşu parçayla birleştirmeyi değerlendirin.",
    ),
    "overlap": (
        "Reduce bounded overlap without crossing unrelated structural boundaries.",
        "İlgisiz yapısal sınırları aşmadan sınırlı örtüşmeyi azaltın.",
    ),
    "reparse": (
        "Reparse the source and inspect extraction/mapping warnings.",
        "Kaynağı yeniden ayrıştırın ve çıkarım/konum eşleme uyarılarını inceleyin.",
    ),
    "boilerplate": (
        "Review boilerplate policy before indexing; do not remove content automatically.",
        "İndekslemeden önce şablon metin politikasını inceleyin; içeriği otomatik kaldırmayın.",
    ),
}


def _chunk_recommendation(rule_suffix: str) -> tuple[str, str]:
    if any(value in rule_suffix for value in ("OVERSIZED", "SPLIT", "LIMIT")):
        return _RECOMMENDATIONS["rechunk"]
    if "UNDERSIZED" in rule_suffix:
        return _RECOMMENDATIONS["merge"]
    if "OVERLAP" in rule_suffix or "IDENTICAL" in rule_suffix:
        return _RECOMMENDATIONS["overlap"]
    if any(value in rule_suffix for value in ("MAPPING", "EXTRACTION", "GARBLED")):
        return _RECOMMENDATIONS["reparse"]
    if "BOILERPLATE" in rule_suffix:
        return _RECOMMENDATIONS["boilerplate"]
    return _RECOMMENDATIONS["default"]


RULE_TEXTS: dict[str, RuleLocales] = {
    "QUALITY-EXACT-DUPLICATE-DOCUMENT": {
        "en": {
            "title": "Exact normalized-content duplicate group",
            "impact": "Redundant indexed content can waste storage and bias retrieval.",
            "recommendation": (
                "Review the group and keep one canonical item; do not delete automatically."
            ),
        },
        "tr": {
            "title": "Tam normalleştirilmiş içerik yinelenen grubu",
            "impact": (
                "Gereksiz yinelenen indeks içeriği depolamayı israf edebilir ve getirimi "
                "yanlı hale getirebilir."
            ),
            "recommendation": (
                "Grubu inceleyin ve tek bir kanonik öğe bırakın; otomatik olarak silmeyin."
            ),
        },
    },
    "QUALITY-EXACT-DUPLICATE-CHUNK": {
        "en": {
            "title": "Exact normalized-content duplicate group",
            "impact": "Redundant indexed content can waste storage and bias retrieval.",
            "recommendation": (
                "Review the group and keep one canonical item; do not delete automatically."
            ),
        },
        "tr": {
            "title": "Tam normalleştirilmiş içerik yinelenen grubu",
            "impact": (
                "Gereksiz yinelenen indeks içeriği depolamayı israf edebilir ve getirimi "
                "yanlı hale getirebilir."
            ),
            "recommendation": (
                "Grubu inceleyin ve tek bir kanonik öğe bırakın; otomatik olarak silmeyin."
            ),
        },
    },
    "QUALITY-REPEATED-CHUNK-WITHIN-DOCUMENT": {
        "en": {
            "title": "Exact within-document repeated chunks",
            "impact": (
                "Same-document repetition may come from duplicate upload, synchronization replay, "
                "or chunk overlap and can bias retrieval."
            ),
            "recommendation": (
                "Check indexing history and chunk-overlap configuration before changing source content."
            ),
        },
        "tr": {
            "title": "Belge içinde tam yinelenen parçalar",
            "impact": (
                "Aynı belge içindeki tekrar; çift yükleme, senkronizasyon tekrarı veya parça "
                "örtüşmesinden kaynaklanabilir ve getirimi yanlı hale getirebilir."
            ),
            "recommendation": (
                "Kaynak içeriği değiştirmeden önce indeksleme geçmişini ve parça örtüşme "
                "ayarını kontrol edin."
            ),
        },
    },
    "QUALITY-NEAR-DUPLICATE": {
        "en": {
            "title": "Near-duplicate content group",
            "impact": (
                "Near-identical content may waste retrieval capacity or over-weight one statement."
            ),
            "recommendation": (
                "Review the group manually; similarity is not proof that an item should be deleted."
            ),
        },
        "tr": {
            "title": "Yakın yinelenen içerik grubu",
            "impact": (
                "Neredeyse aynı içerik getirim kapasitesini israf edebilir veya bir ifadeye "
                "gereğinden fazla ağırlık verebilir."
            ),
            "recommendation": (
                "Grubu elle inceleyin; benzerlik tek başına bir öğenin silinmesi gerektiğini kanıtlamaz."
            ),
        },
    },
    "QUALITY-WITHIN-DOCUMENT-NEAR-DUPLICATES": {
        "en": {
            "title": "Within-document near-duplicate chunks",
            "impact": (
                "Same-document repetition may come from duplicate upload, synchronization replay, "
                "or chunk overlap and can bias retrieval."
            ),
            "recommendation": (
                "Check indexing history and chunk-overlap configuration before changing source content."
            ),
        },
        "tr": {
            "title": "Belge içinde yakın yinelenen parçalar",
            "impact": (
                "Aynı belge içindeki tekrar; çift yükleme, senkronizasyon tekrarı veya parça "
                "örtüşmesinden kaynaklanabilir ve getirimi yanlı hale getirebilir."
            ),
            "recommendation": (
                "Kaynak içeriği değiştirmeden önce indeksleme geçmişini ve parça örtüşme "
                "ayarını kontrol edin."
            ),
        },
    },
    "STATIC-CMD-001": {
        "en": {
            "title": "Suspicious command instruction",
            "impact": "Following the instruction may cause destructive or privileged side effects.",
            "recommendation": (
                "Prevent retrieved content from authorizing shell, SQL, file, or network actions."
            ),
        },
        "tr": {
            "title": "Şüpheli komut talimatı",
            "impact": ("Talimatın izlenmesi yıkıcı veya ayrıcalıklı yan etkilere neden olabilir."),
            "recommendation": (
                "Getirilen içeriğin kabuk, SQL, dosya veya ağ işlemlerine yetki vermesini önleyin."
            ),
        },
    },
    "STATIC-ENC-001": {
        "en": {
            "title": "Encoded instruction-like payload",
            "impact": "Obfuscation may conceal an instruction attack.",
            "recommendation": (
                "Decode only for bounded inspection and preserve encoded content as untrusted data."
            ),
        },
        "tr": {
            "title": "Kodlanmış talimat benzeri içerik",
            "impact": "Gizleme, bir talimat saldırısını saklayabilir.",
            "recommendation": (
                "Yalnızca sınırlı inceleme için çözün ve kodlanmış içeriği güvenilmeyen veri olarak koruyun."
            ),
        },
    },
    "STATIC-HID-001": {
        "en": {
            "title": "Hidden or invisible instruction content",
            "impact": "Invisible instructions can evade human review.",
            "recommendation": (
                "Expose hidden text to trust-boundary checks and prevent it from becoming "
                "executable instruction context."
            ),
        },
        "tr": {
            "title": "Gizli veya görünmez talimat içeriği",
            "impact": "Görünmez talimatlar insan incelemesinden kaçabilir.",
            "recommendation": (
                "Gizli metni güven sınırı kontrollerine açın ve çalıştırılabilir talimat "
                "bağlamına dönüşmesini önleyin."
            ),
        },
    },
    "STATIC-META-001": {
        "en": {
            "title": "Instruction-like metadata poisoning",
            "impact": "Poisoned metadata may influence retrieval or model behavior.",
            "recommendation": (
                "Treat metadata as untrusted data and prevent it from entering instruction channels."
            ),
        },
        "tr": {
            "title": "Talimat benzeri metadata zehirlemesi",
            "impact": "Zehirlenmiş metadata getirimi veya model davranışını etkileyebilir.",
            "recommendation": (
                "Metadatayı güvenilmeyen veri olarak ele alın ve talimat kanallarına girmesini önleyin."
            ),
        },
    },
    "STATIC-PI-001": {
        "en": {
            "title": "Prompt injection instruction",
            "impact": "A model may follow untrusted retrieved instructions.",
            "recommendation": (
                "Keep retrieved content in a data-only trust boundary and enforce instruction priority."
            ),
        },
        "tr": {
            "title": "Prompt injection talimatı",
            "impact": "Model, getirilen güvenilmeyen talimatları izleyebilir.",
            "recommendation": (
                "Getirilen içeriği yalnızca veri kabul eden güven sınırında tutun ve talimat "
                "önceliğini uygulayın."
            ),
        },
    },
    "STATIC-PII-001": {
        "en": {
            "title": "Possible personal-data indicator",
            "impact": "Personal-data-shaped content may require policy review.",
            "recommendation": (
                "Review data minimization, access controls, retention, and masking requirements."
            ),
        },
        "tr": {
            "title": "Olası kişisel veri göstergesi",
            "impact": "Kişisel veri biçimindeki içerik politika incelemesi gerektirebilir.",
            "recommendation": (
                "Veri minimizasyonu, erişim kontrolü, saklama ve maskeleme gereksinimlerini inceleyin."
            ),
        },
    },
    "STATIC-RP-001": {
        "en": {
            "title": "Retrieval poisoning instruction",
            "impact": (
                "A poisoned document may cause relevant or authoritative evidence to be hidden from users."
            ),
            "recommendation": (
                "Remove source-suppression instructions, preserve source authority metadata, "
                "and resolve conflicting versions explicitly."
            ),
        },
        "tr": {
            "title": "Getirim zehirleme talimatı",
            "impact": (
                "Zehirlenmiş belge ilgili veya yetkili kanıtın kullanıcılardan saklanmasına yol açabilir."
            ),
            "recommendation": (
                "Kaynağı bastıran talimatları kaldırın, kaynak yetkisi metadatasını koruyun "
                "ve çelişen sürümleri açıkça çözün."
            ),
        },
    },
    "STATIC-SEC-001": {
        "en": {
            "title": "Likely secret or credential exposure",
            "impact": "Credentials in a knowledge source may be retrieved or disclosed.",
            "recommendation": (
                "Remove and rotate exposed credentials; use secure secret references instead."
            ),
        },
        "tr": {
            "title": "Olası gizli bilgi veya kimlik bilgisi sızıntısı",
            "impact": "Bilgi kaynağındaki kimlik bilgileri getirilebilir veya ifşa edilebilir.",
            "recommendation": (
                "Açığa çıkan kimlik bilgilerini kaldırıp yenileyin; bunun yerine güvenli "
                "gizli bilgi referansları kullanın."
            ),
        },
    },
    "STATIC-SP-001": {
        "en": {
            "title": "System prompt extraction request",
            "impact": "Private model instructions may be exposed.",
            "recommendation": (
                "Treat retrieved disclosure requests as untrusted data and prevent prompt serialization."
            ),
        },
        "tr": {
            "title": "Sistem promptunu çıkarma isteği",
            "impact": "Özel model talimatları açığa çıkabilir.",
            "recommendation": (
                "Getirilen ifşa isteklerini güvenilmeyen veri sayın ve prompt serileştirmesini önleyin."
            ),
        },
    },
    "STATIC-TA-001": {
        "en": {
            "title": "Tool or function abuse instruction",
            "impact": "An agent may perform unauthorized actions.",
            "recommendation": (
                "Allowlist tools and arguments and treat retrieved tool instructions as data."
            ),
        },
        "tr": {
            "title": "Araç veya fonksiyon kötüye kullanım talimatı",
            "impact": "Bir ajan yetkisiz işlemler gerçekleştirebilir.",
            "recommendation": (
                "Araç ve argümanları izin listesine alın; getirilen araç talimatlarını veri olarak ele alın."
            ),
        },
    },
    "STATIC-URL-001": {
        "en": {
            "title": "Suspicious URL property",
            "impact": "A model or tool may be directed to an unsafe destination.",
            "recommendation": (
                "Do not fetch retrieved URLs automatically; validate scheme, destination, and authorization."
            ),
        },
        "tr": {
            "title": "Şüpheli URL özelliği",
            "impact": "Bir model veya araç güvenli olmayan hedefe yönlendirilebilir.",
            "recommendation": (
                "Getirilen URL'leri otomatik açmayın; şema, hedef ve yetkiyi doğrulayın."
            ),
        },
    },
}

for _suffix, (_title_en, _title_tr) in _CHUNK_TITLES.items():
    _recommendation_en, _recommendation_tr = _chunk_recommendation(_suffix)
    RULE_TEXTS[f"QUALITY-CHUNK-{_suffix}"] = {
        "en": {
            "title": _title_en,
            "impact": _QUALITY_IMPACT_EN,
            "recommendation": _recommendation_en,
        },
        "tr": {
            "title": _title_tr,
            "impact": _QUALITY_IMPACT_TR,
            "recommendation": _recommendation_tr,
        },
    }


COVERAGE_REASONS: dict[str, dict[str, str]] = {
    "Static document and chunk rules were evaluated.": {
        "en": "Static document and chunk rules were evaluated.",
        "tr": "Statik belge ve parça kuralları değerlendirildi.",
    },
    "Static security scanning was disabled or unavailable.": {
        "en": "Static security scanning was disabled or unavailable.",
        "tr": "Statik güvenlik taraması kapalıydı veya kullanılamadı.",
    },
    "Chunk-quality heuristics were evaluated.": {
        "en": "Chunk-quality heuristics were evaluated.",
        "tr": "Parça kalitesi sezgisel kontrolleri değerlendirildi.",
    },
    "Chunk-quality scanning was disabled or unavailable.": {
        "en": "Chunk-quality scanning was disabled or unavailable.",
        "tr": "Parça kalitesi taraması kapalıydı veya kullanılamadı.",
    },
    "Repeated chunks inside the source were evaluated.": {
        "en": "Repeated chunks inside the source were evaluated.",
        "tr": "Kaynak içindeki yinelenen parçalar değerlendirildi.",
    },
    "Exact duplicate scanning was disabled or failed.": {
        "en": "Exact duplicate scanning was disabled or failed.",
        "tr": "Tam yinelenen içerik taraması kapalıydı veya başarısız oldu.",
    },
    "Lexical near-duplicate chunks inside the source were evaluated.": {
        "en": "Lexical near-duplicate chunks inside the source were evaluated.",
        "tr": "Kaynak içindeki sözcüksel yakın yinelenen parçalar değerlendirildi.",
    },
    "Near-duplicate scanning was disabled or failed.": {
        "en": "Near-duplicate scanning was disabled or failed.",
        "tr": "Yakın yinelenen içerik taraması kapalıydı veya başarısız oldu.",
    },
    "Normalized content was compared across source documents.": {
        "en": "Normalized content was compared across source documents.",
        "tr": "Normalleştirilmiş içerik kaynak belgeler arasında karşılaştırıldı.",
    },
    "Lexical similarity was compared across source documents.": {
        "en": "Lexical similarity was compared across source documents.",
        "tr": "Sözcüksel benzerlik kaynak belgeler arasında karşılaştırıldı.",
    },
    "Requires at least two source documents; this is a single-source knowledge base.": {
        "en": "Requires at least two source documents; this is a single-source knowledge base.",
        "tr": ("En az iki kaynak belge gerektirir; bu bilgi tabanı tek kaynaklıdır."),
    },
    "The corresponding scanner is not implemented in this release.": {
        "en": "The corresponding scanner is not implemented in this release.",
        "tr": "İlgili tarayıcı bu sürümde uygulanmamıştır.",
    },
}

_WARNED_MISSING: set[tuple[str, str, str]] = set()


def _localized(
    catalog: dict[str, RuleFields],
    language: str,
    field: str,
    fallback: str,
    *,
    identifier: str,
) -> str:
    requested = language if language in {"en", "tr"} else "en"
    localized = catalog.get(requested, {}).get(field)
    if localized:
        return localized
    english = catalog.get("en", {}).get(field)
    warning_key = (identifier, language, field)
    if warning_key not in _WARNED_MISSING:
        logger.warning(
            "report_translation_missing",
            extra={"rule_id": identifier, "report_language": language, "field": field},
        )
        _WARNED_MISSING.add(warning_key)
    return english or fallback


def localize_rule_field(rule_id: str, language: str, field: str, fallback: str) -> str:
    """Return localized rule text, falling back to English with a warning."""

    catalog = RULE_TEXTS.get(rule_id)
    if catalog is None:
        warning_key = (rule_id, language, field)
        if warning_key not in _WARNED_MISSING:
            logger.warning(
                "report_rule_translation_missing",
                extra={"rule_id": rule_id, "report_language": language, "field": field},
            )
            _WARNED_MISSING.add(warning_key)
        return fallback
    return _localized(catalog, language, field, fallback, identifier=rule_id)


def localize_coverage_reason(reason: str, language: str) -> str:
    """Return localized deterministic coverage text."""

    catalog = COVERAGE_REASONS.get(reason)
    if catalog is None:
        return reason
    requested = language if language in {"en", "tr"} else "en"
    localized = catalog.get(requested)
    if localized:
        return localized
    warning_key = (reason, language, "reason")
    if warning_key not in _WARNED_MISSING:
        logger.warning(
            "report_translation_missing",
            extra={"coverage_reason": reason, "report_language": language},
        )
        _WARNED_MISSING.add(warning_key)
    return catalog.get("en", reason)
