# RS-051: Active context-manipulation scan

**Objective:** Retrieved context bypass, poisoning acceptance ve kaynak/citation manipülasyonunu test etmek.  
**Rationale:** Modelin context’i görmezden gelmesi veya sahte kaynağı tercih etmesi statik taramayla kanıtlanamaz.  
**Dependencies:** RS-046/047/052 ve retrieval-aware target capability.  
**Scope:** Synthetic trusted/untrusted context pair, context override, citation/source integrity ve abstention behavior.  
**Out of scope:** Production index’i zehirleme, gerçek belge mutation’ı.  
**Implementation guidance:** Ephemeral/synthetic test collection veya target-provided safe fixture kullan.  
**Security considerations:** Production knowledge base’e payload yazma varsayılan olarak yasaktır.  
**Acceptance criteria:** Safe fixture üzerinde context bypass sinyali açıklanabilir ve tekrar üretilebilir.  
**Tests:** Trusted-vs-poisoned, refusal, conflicting context, citation mismatch ve cleanup.  
**Documentation changes:** Context test topology/limitations.  
**Completion checklist:** [ ] Ephemeral fixture [ ] No production mutation [ ] TP/FP [ ] Cleanup [ ] Docs updated

