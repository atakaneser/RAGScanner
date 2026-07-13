# ADR-0012: Static scan ve active black-box scan ayrımı

- Status: Accepted
- Date: 2026-07-12

## Bağlam

Belge içindeki zararlı talimatı bulmak ile çalışan uygulamanın o talimata nasıl cevap verdiğini sınamak farklı veri, izin ve kanıt modelleridir.

## Karar

`static` mode yalnız SourceConnector’dan gelen document/chunk/metadata üzerinde analiz yapar. `active` mode yalnız TargetAdapter üzerinden yetkili endpoint’e test gönderir. Scan provenance hangi modların çalıştığını ayrı gösterir; bir mod diğerinin coverage’ını doldurmaz.

Bir endpoint yalnız retrieval yaptığı capability/fixture ile doğrulandığında RAG target’tır. OpenAI/Hugging Face/LLM kullanımı tek başına RAG kanıtı değildir.

## Sonuçlar

Static sonuç source location’a, active sonuç test case/request/response evidence’a bağlanır. Ortak Finding sözleşmesi kullanılabilir fakat occurrence evidence ve coverage mode-specific kalır.

