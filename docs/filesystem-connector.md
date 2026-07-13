# Local filesystem connector

`LocalFilesystemConnector`, açıkça yapılandırılmış tek bir yerel kök altında `.txt`, `.md`,
`.markdown`, `.pdf` ve `.docx` dosyalarını keşfeder ve bounded raw byte içerik döndürür. Home/current directory veya
filesystem root örtük seçilmez; root absolute olmalı ve `/`/drive root reddedilir.

## Güvenlik ve limitler

- Symlink varsayılan kapalıdır. Açıldığında target resolve edilir ve yine root altında olmalıdır.
- Path traversal, root dışı symlink, URL/shell/environment expansion reddedilir.
- Yalnız regular file okunur; FIFO, socket ve device atlanır.
- `os.open`, `fstat`, final-component `O_NOFOLLOW` desteği ve read byte sınırı kullanılır.
- Root veya dosya yarış sırasında kaybolursa structured `SourceError` döner.
- Hidden dosyalar varsayılan atlanır; file/discovery limitleri zorunludur.
- İçerik veya path hata mesajlarına/loglara kopyalanmaz.

MIME mapping sabittir. Text encoding/binary heuristic yalnız TXT/Markdown'a uygulanır; PDF/DOCX
bytes decode edilmeksizin kendi bounded parser'ına verilir. Checksum
discovery varsayılan kapalıdır; açıkça etkinleştirilirse bounded SHA-256 hesaplanır. Content
retrieval her zaman SHA-256 döndürür.

UTF-8 ve UTF-8 BOM desteklenir. `strict` varsayılandır. `fallback` yalnız açık codec listesini
dener; `replace` malformed UTF-8 için warning üretir. NUL veya yüksek control-byte oranı binary
kabul edilerek reddedilir. Ağ mount'u otomatik keşfedilmez veya özel güven varsayımı yapılmaz.

Change detection watcher değildir. Process içi opaque snapshot cursor; relative path, mtime-ns,
size ve checksum etkinse checksum karşılaştırır. Restart sonrası cursor geçersizdir. Timestamp/size
korunarak değişen içerik checksum kapalıysa kaçabilir; filesystem yarışları tamamen yok edilemez.
