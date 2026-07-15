(() => {
  const body = document.body;
  const tabs = [...document.querySelectorAll("[data-source]")];
  const forms = [...document.querySelectorAll("[data-form]")];
  const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
  const discoveryStatus = document.querySelector("[data-discovery-status]");
  const discoveryResults = document.querySelector("[data-discovery-results]");
  const openWebUiUrl = document.querySelector("[data-openwebui-url]");
  const credentialRef = document.querySelector('input[name="credential_ref"]');
  const knowledgeSelect = document.querySelector("[data-knowledge-bases]");
  const knowledgeId = document.querySelector("[data-knowledge-id]");

  const setStatus = (message) => {
    if (discoveryStatus) discoveryStatus.textContent = message;
  };
  const postForm = async (url, values) => {
    const data = new FormData();
    data.append("csrf_token", csrfToken || "");
    Object.entries(values).forEach(([key, value]) => data.append(key, value));
    const response = await fetch(url, { method: "POST", body: data, credentials: "same-origin" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "The request could not be completed.");
    return payload;
  };
  document.querySelector("[data-open-drawer]")?.addEventListener("click", () => {
    body.classList.remove("drawer-collapsed");
  });
  document.querySelector("[data-close-drawer]")?.addEventListener("click", () => {
    body.classList.add("drawer-collapsed");
  });
  tabs.forEach((tab) => tab.addEventListener("click", () => {
    const selected = tab.dataset.source;
    tabs.forEach((item) => item.classList.toggle("active", item === tab));
    forms.forEach((form) => form.classList.toggle("hidden", form.dataset.form !== selected));
  }));
  document.querySelector("[data-discover-environments]")?.addEventListener("click", async () => {
    const consent = document.querySelector("[data-metadata-consent]")?.checked;
    if (!consent) {
      setStatus("Select consent before discovering local environments.");
      return;
    }
    setStatus("Discovering local RAG environments…");
    if (discoveryResults) discoveryResults.replaceChildren();
    try {
      const payload = await postForm("/dashboard/discovery/environments", { metadata_consent: "true" });
      const environments = payload.environments || [];
      if (!environments.length) {
        setStatus("No local RAG environment candidate was found.");
        return;
      }
      setStatus(`${environments.length} local environment candidate(s) found.`);
      environments.forEach((environment) => {
        const item = document.createElement("li");
        const suffix = environment.metadata_inventory_supported
          ? "Knowledge-base discovery is available."
          : "Detection only; this connector is not available yet.";
        item.textContent = `${environment.platform} · ${environment.base_url} · ${environment.status}${environment.runtime ? ` via ${environment.runtime}` : ""}. ${suffix}`;
        discoveryResults?.append(item);
        if (environment.platform === "openwebui" && environment.status === "reachable" && openWebUiUrl && !openWebUiUrl.value) {
          openWebUiUrl.value = environment.base_url;
        }
      });
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Discovery failed.");
    }
  });
  document.querySelector("[data-load-knowledge-bases]")?.addEventListener("click", async () => {
    if (!openWebUiUrl?.value || !credentialRef?.value) {
      setStatus("Enter an OpenWebUI URL and an environment credential reference first.");
      return;
    }
    setStatus("Loading accessible OpenWebUI knowledge bases…");
    try {
      const payload = await postForm("/dashboard/discovery/openwebui/knowledge-bases", {
        base_url: openWebUiUrl.value,
        credential_ref: credentialRef.value,
      });
      const knowledgeBases = payload.knowledge_bases || [];
      if (knowledgeSelect) {
        knowledgeSelect.replaceChildren(new Option("Select a knowledge base", ""));
        knowledgeBases.forEach((knowledgeBase) => {
          knowledgeSelect.add(new Option(`${knowledgeBase.name} (${knowledgeBase.id})`, knowledgeBase.id));
        });
      }
      setStatus(knowledgeBases.length ? `${knowledgeBases.length} knowledge base(s) loaded.` : "No accessible knowledge bases were returned.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Knowledge-base discovery failed.");
    }
  });
  knowledgeSelect?.addEventListener("change", () => {
    if (knowledgeId) knowledgeId.value = knowledgeSelect.value;
  });
})();
