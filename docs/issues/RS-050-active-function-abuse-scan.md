# RS-050: Active tool and function abuse scan

**Objective:** Tool enumeration, unauthorized invocation ve privilege-escalation riskini side effect oluşturmadan değerlendirmek.  
**Rationale:** Agentic RAG sistemlerinde en yüksek etkili risklerden biri tool abuse’dur.  
**Dependencies:** RS-046/047/052; OD-026.  
**Scope:** Capability-aware dry-run/no-op payload, tool exposure, authorization refusal ve synthetic canary tool.  
**Out of scope:** Email gönderme, dosya silme, shell çalıştırma veya gerçek mutation.  
**Implementation guidance:** TargetAdapter side-effect capability ve explicit safe test hook gerektir.  
**Security considerations:** Varsayılan profile mutation yapamaz; destructive test ayrı gelecek ve bu issue kapsamında değildir.  
**Acceptance criteria:** Fake unsafe/safe target ayrılır; gerçek yan etki üreten test yoktur.  
**Tests:** Tool refusal, enumeration, fake no-op call, permission error ve malformed tool response.  
**Documentation changes:** Tool testing safety policy.  
**Completion checklist:** [ ] No-op design [ ] No mutation [ ] Contract tests [ ] Audit metadata [ ] Docs updated

