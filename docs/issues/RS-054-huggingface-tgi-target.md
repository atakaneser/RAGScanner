# RS-054: Hugging Face TGI target adapter

**Objective:** TGI/OpenAI Messages uyumluluğunu capability fixture ile doğrulamak ve HF-specific farkları adapte etmek.  
**Rationale:** Yalnız `transformers` import etmek Hugging Face desteği değildir.  
**Dependencies:** RS-053.  
**Scope:** TGI version/capability, model/endpoint config, response mapping ve official fixture documentation.  
**Out of scope:** Model download, arbitrary `trust_remote_code`, HF’yi document source saymak.  
**Implementation guidance:** Generic adapter’ı yeniden kullan; yalnız kanıtlanmış farkları ekle.  
**Security considerations:** Token redaction, endpoint privacy, remote-code/model supply chain uyarıları.  
**Acceptance criteria:** Mock TGI fixtures geçer; supported TGI version/mode açıklanır; fallback sessiz değildir.  
**Tests:** Chat success, unsupported schema, auth, timeout, streaming ve version capability.  
**Documentation changes:** Hugging Face target/model distinction.  
**Completion checklist:** [ ] Official schema fixture [ ] Version matrix [ ] No remote code [ ] Tests [ ] Docs updated

