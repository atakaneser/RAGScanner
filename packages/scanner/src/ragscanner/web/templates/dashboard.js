(() => {
  const body = document.body;
  const t = window.ragscannerTranslate || ((value) => value);
  const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || "";
  const statusNodes = [...document.querySelectorAll("[data-discovery-status]")];
  const resultNodes = [...document.querySelectorAll("[data-discovery-results]")];
  const setStatus = (message) => statusNodes.forEach((node) => { node.textContent = message; });
  const postForm = async (url, values = {}) => {
    const data = new FormData();
    data.append("csrf_token", csrfToken);
    Object.entries(values).forEach(([key, value]) => data.append(key, value));
    const response = await fetch(url, { method: "POST", body: data, credentials: "same-origin" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || t("The request could not be completed."));
    return payload;
  };

  document.querySelectorAll("[data-open-drawer]").forEach((button) => button.addEventListener("click", () => body.classList.remove("drawer-collapsed")));
  document.querySelector("[data-close-drawer]")?.addEventListener("click", () => body.classList.add("drawer-collapsed"));
  const tabs = [...document.querySelectorAll("[data-source]")];
  const forms = [...document.querySelectorAll("[data-form]")];
  tabs.forEach((tab) => tab.addEventListener("click", () => {
    tabs.forEach((item) => item.classList.toggle("active", item === tab));
    forms.forEach((form) => form.classList.toggle("hidden", form.dataset.form !== tab.dataset.source));
  }));
  const profilePicker = document.querySelector("[data-profile-picker]");
  const connectionPanel = document.querySelector("[data-connection-panel]");
  const connectionStatus = document.querySelector("[data-connection-status]");
  const connectionProfile = document.querySelector("[data-connection-profile]");
  const connectionApiKey = document.querySelector("[data-connection-api-key]");
  const connectionCredentialRef = document.querySelector("[data-connection-credential-ref]");
  const setConnectionState = (option) => {
    const needsConnection = option?.dataset.status === "connection_required";
    const detectionOnly = option?.dataset.status === "metadata_only";
    connectionPanel?.classList.toggle("hidden", !needsConnection && !detectionOnly);
    if (connectionProfile) connectionProfile.value = option?.value || "";
    if (connectionStatus) connectionStatus.textContent = detectionOnly
      ? t("This environment was detected, but its content connector is not available yet. No API key is needed.")
      : "";
    connectionApiKey?.closest("label")?.classList.toggle("hidden", detectionOnly);
    connectionCredentialRef?.closest("details")?.classList.toggle("hidden", detectionOnly);
    const connectButton = document.querySelector("[data-connect-and-continue]");
    connectButton?.classList.toggle("hidden", detectionOnly);
  };
  profilePicker?.addEventListener("change", () => {
    const option = profilePicker.selectedOptions[0];
    setConnectionState(option);
    if (!option?.value) return;
    const kind = option.dataset.kind;
    if (option.dataset.status === "metadata_only") return;
    const selectedTab = tabs.find((tab) => tab.dataset.source === (kind === "filesystem" ? "local" : "openwebui"));
    selectedTab?.click();
    if (kind === "filesystem") {
      const localPath = document.querySelector("[data-local-path]");
      if (localPath) localPath.value = option.dataset.location || "";
    } else {
      const url = document.querySelector("[data-openwebui-url]");
      const reference = document.querySelector('form[data-form="openwebui"] input[name="credential_ref"]');
      if (url) url.value = option.dataset.location || "";
      if (reference) reference.value = option.dataset.credential || "";
    }
  });
  document.querySelectorAll("[data-connect-profile]").forEach((button) => button.addEventListener("click", () => {
    body.classList.remove("drawer-collapsed");
    if (profilePicker) {
      profilePicker.value = button.dataset.connectProfile || "";
      profilePicker.dispatchEvent(new Event("change"));
    }
  }));
  document.querySelector("[data-connect-and-continue]")?.addEventListener("click", async () => {
    if (!connectionProfile?.value) return;
    if (connectionStatus) connectionStatus.textContent = t("Testing the connection…");
    try {
      const payload = await postForm(`/dashboard/sources/${connectionProfile.value}/connect`, {
        api_key: connectionApiKey?.value || "",
        credential_ref: connectionCredentialRef?.value || "",
      });
      const option = [...profilePicker.options].find((item) => item.value === connectionProfile.value);
      if (option) {
        option.dataset.status = "scan_ready";
        option.dataset.credential = payload.credential_ref || "";
        option.textContent = option.textContent.replace(/ · .+$/, ` · ${t("Ready")}`);
      }
      const reference = document.querySelector('form[data-form="openwebui"] input[name="credential_ref"]');
      if (reference) reference.value = payload.credential_ref || "";
      knowledgeSelect?.replaceChildren(new Option(t("Select a knowledge base"), ""));
      (payload.knowledge_bases || []).forEach((item) => knowledgeSelect?.add(new Option(`${item.name} (${item.id})`, item.id)));
      connectionPanel?.classList.add("hidden");
      tabs.find((tab) => tab.dataset.source === "openwebui")?.click();
      setStatus(`${(payload.knowledge_bases || []).length} ${t("knowledge base(s) loaded.")}`);
    } catch (error) {
      if (connectionStatus) connectionStatus.textContent = error instanceof Error ? error.message : t("Connection failed.");
    }
  });

  const populateSourceForm = (environment) => {
    const form = document.querySelector(".settings-form");
    if (!form) return;
    form.querySelector('[name="name"]').value = environment.platform;
    const kind = [...form.querySelector('[name="kind"]').options].some((option) => option.value === environment.platform) ? environment.platform : "generic";
    form.querySelector('[name="kind"]').value = kind;
    form.querySelector('[name="location"]').value = environment.base_url;
    form.querySelector('[name="discovery_origin"]').value = environment.runtime || "localhost";
    form.scrollIntoView({ behavior: "smooth", block: "center" });
  };
  const populateSetupForm = (environment) => {
    const name = document.querySelector('[name="source_name"]');
    const location = document.querySelector('[name="source_location"]');
    if (name) name.value = environment.platform;
    if (location) location.value = environment.base_url;
  };
  const renderEnvironments = (environments, setupMode) => {
    resultNodes.forEach((node) => node.replaceChildren());
    environments.forEach((environment) => resultNodes.forEach((node) => {
      const row = document.createElement("div");
      row.className = "environment-row";
      const name = document.createElement("strong"); name.textContent = environment.platform;
      const address = document.createElement("code"); address.textContent = environment.base_url;
      const runtime = document.createElement("small"); runtime.textContent = environment.runtime || "localhost";
      const capability = document.createElement("span"); capability.className = `capability capability-${environment.capability_status}`; capability.textContent = environment.capability_status.replaceAll("_", " ");
      const use = document.createElement("button"); use.type = "button"; use.className = "secondary small"; use.textContent = t(setupMode ? "Select" : "Use details");
      use.addEventListener("click", () => setupMode ? populateSetupForm(environment) : populateSourceForm(environment));
      row.append(name, address, runtime, capability, use); node.append(row);
    }));
  };
  const discover = async (setupMode) => {
    setStatus(t("Scanning bounded local service metadata…"));
    try {
      const payload = await postForm(setupMode ? "/setup/discovery" : "/dashboard/discovery/environments", setupMode ? {} : { metadata_consent: "true" });
      const environments = payload.environments || [];
      setStatus(environments.length ? `${environments.length} ${t("environment candidate(s) found.")}` : t("No supported local environment candidate was found."));
      renderEnvironments(environments, setupMode);
    } catch (error) { setStatus(error instanceof Error ? error.message : t("Discovery failed.")); }
  };
  document.querySelector("[data-discover-environments]")?.addEventListener("click", () => discover(false));
  document.querySelector("[data-setup-discovery]")?.addEventListener("click", () => discover(true));

  const sourceBuilder = document.querySelector("[data-source-builder]");
  document.querySelector("[data-show-source-form]")?.addEventListener("click", () => sourceBuilder?.scrollIntoView({ behavior: "smooth", block: "start" }));
  document.querySelector("[data-cancel-source]")?.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  const sourceKind = document.querySelector("[data-source-kind]");
  const sourceForm = document.querySelector(".source-settings-form");
  const sourceNote = document.querySelector("[data-connector-note]");
  const updateSourceDefaults = () => {
    const option = sourceKind?.selectedOptions[0];
    if (!option || !sourceForm) return;
    const name = sourceForm.querySelector('[name="name"]');
    const location = sourceForm.querySelector('[name="location"]');
    if (name) name.value = option.dataset.name || "";
    if (location) location.value = option.dataset.url || "";
    const ready = ["openwebui", "filesystem"].includes(option.value);
    if (sourceNote) sourceNote.innerHTML = ready
      ? `<strong>${t("Ready to scan:")}</strong> ${t(option.value === "filesystem" ? "RAGScanner can scan supported files in this path." : "RAGScanner can inventory OpenWebUI knowledge bases and scan their content.")}`
      : `<strong>${t("Detected only:")}</strong> ${t("RAGScanner can remember and discover this environment, but its content connector is not available yet.")}`;
    const auth = option.value === "openwebui";
    sourceForm.querySelector(".auth-choice")?.classList.toggle("hidden", !auth);
    sourceForm.querySelector("[data-api-key-row]")?.classList.toggle("hidden", !auth);
    sourceForm.querySelector("[data-credential-ref-row]")?.classList.add("hidden");
    const apiRadio = sourceForm.querySelector('input[name="auth_mode"][value="api_key"]');
    if (apiRadio) apiRadio.checked = auth;
  };
  sourceKind?.addEventListener("change", updateSourceDefaults);
  document.querySelectorAll("[data-source-choice]").forEach((button) => button.addEventListener("click", () => {
    if (!sourceKind) return;
    sourceKind.value = button.dataset.sourceChoice || "custom";
    document.querySelectorAll("[data-source-choice]").forEach((item) => item.classList.toggle("selected", item === button));
    updateSourceDefaults();
  }));
  sourceForm?.querySelectorAll('input[name="auth_mode"]').forEach((radio) => radio.addEventListener("change", () => {
    const mode = sourceForm.querySelector('input[name="auth_mode"]:checked')?.value;
    const apiRow = sourceForm.querySelector("[data-api-key-row]");
    const envRow = sourceForm.querySelector("[data-credential-ref-row]");
    apiRow?.classList.toggle("hidden", mode !== "api_key");
    envRow?.classList.toggle("hidden", mode !== "environment");
    apiRow?.querySelector("input")?.toggleAttribute("disabled", mode !== "api_key");
    envRow?.querySelector("input")?.toggleAttribute("disabled", mode !== "environment");
  }));

  const openWebUiUrl = document.querySelector("[data-openwebui-url]");
  const credentialRef = document.querySelector('form[data-form="openwebui"] input[name="credential_ref"]');
  const knowledgeSelect = document.querySelector("[data-knowledge-bases]");
  const knowledgeId = document.querySelector("[data-knowledge-id]");
  document.querySelector("[data-load-knowledge-bases]")?.addEventListener("click", async () => {
    if (!openWebUiUrl?.value || !credentialRef?.value) { setStatus(t("Enter an OpenWebUI URL and credential reference first.")); return; }
    setStatus(t("Loading accessible OpenWebUI knowledge bases…"));
    try {
      const payload = await postForm("/dashboard/discovery/openwebui/knowledge-bases", { base_url: openWebUiUrl.value, credential_ref: credentialRef.value });
      knowledgeSelect.replaceChildren(new Option(t("Select a knowledge base"), ""));
      (payload.knowledge_bases || []).forEach((item) => knowledgeSelect.add(new Option(`${item.name} (${item.id})`, item.id)));
      setStatus(`${(payload.knowledge_bases || []).length} ${t("knowledge base(s) loaded.")}`);
    } catch (error) { setStatus(error instanceof Error ? error.message : t("Knowledge-base discovery failed.")); }
  });
  knowledgeSelect?.addEventListener("change", () => { if (knowledgeId) knowledgeId.value = knowledgeSelect.value; });

  document.querySelectorAll("[data-ai-options]").forEach((container) => {
    const toggle = container.querySelector("[data-ai-toggle]");
    const fields = container.querySelector("[data-ai-fields]");
    const provider = container.querySelector("[data-ai-provider]");
    const endpoint = container.querySelector("[data-ai-url]");
    const model = container.querySelector("[data-ai-model]");
    const privacy = container.querySelector("[data-ai-privacy]");
    const consent = container.querySelector("[data-ai-consent]");
    const credentialRow = container.querySelector("[data-ai-credential-row]");
    const modelList = container.querySelector("[data-ai-model-list]");
    const loadModels = container.querySelector("[data-load-ai-models]");
    const updateProvider = () => {
      const option = provider?.selectedOptions[0];
      if (!option) return;
      const local = option.dataset.local === "true";
      const credentialRequired = option.dataset.credentialRequired === "true";
      if (endpoint && !endpoint.dataset.edited) endpoint.value = option.dataset.url || "";
      credentialRow?.classList.toggle("hidden", !credentialRequired);
      consent?.classList.toggle("hidden", local);
      privacy.textContent = local
        ? t("Local providers keep the bounded, redacted analysis context on this machine.")
        : t("Remote providers receive only a bounded, redacted findings summary—never raw documents or finding evidence.");
      const defaults = { ollama: "llama3.1:8b", "lm-studio": "local-model", localai: "local-model", vllm: "local-model", openai: "gpt-4.1-mini", openrouter: "openai/gpt-4.1-mini", "nvidia-nim": "meta/llama-3.1-70b-instruct", anthropic: "claude-sonnet-4-20250514", "google-gemini": "gemini-2.5-flash", groq: "llama-3.3-70b-versatile", mistral: "mistral-small-latest", together: "meta-llama/Llama-3.3-70B-Instruct-Turbo" };
      if (model && !model.dataset.edited) model.value = defaults[option.value] || "";
    };
    toggle?.addEventListener("change", () => {
      fields?.classList.toggle("hidden", !toggle.checked);
      fields?.querySelectorAll("input,select").forEach((control) => { control.disabled = !toggle.checked; });
      if (toggle.checked) updateProvider();
    });
    provider?.addEventListener("change", updateProvider);
    loadModels?.addEventListener("click", async () => {
      const option = provider?.selectedOptions[0];
      const credential = credentialRow?.querySelector('input[name="ai_credential_ref"]');
      const remoteConsent = consent?.querySelector('input[name="ai_remote_consent"]');
      loadModels.disabled = true;
      loadModels.textContent = t("Detecting models…");
      try {
        const payload = await postForm("/dashboard/discovery/ai-models", {
          provider: provider?.value || "",
          base_url: endpoint?.value || "",
          credential_ref: credential?.value || "",
          remote_consent: option?.dataset.local === "true" ? "false" : String(Boolean(remoteConsent?.checked)),
        });
        modelList?.replaceChildren(...(payload.models || []).map((name) => new Option(name, name)));
        if (model && payload.models?.length) model.value = payload.models[0];
        loadModels.textContent = payload.models?.length ? `${payload.models.length} ${t("model(s) found")}` : t("No models found");
      } catch (error) {
        loadModels.textContent = error instanceof Error ? error.message : t("Model discovery failed");
      } finally {
        loadModels.disabled = false;
      }
    });
    endpoint?.addEventListener("input", () => { endpoint.dataset.edited = "true"; });
    model?.addEventListener("input", () => { model.dataset.edited = "true"; });
    fields?.querySelectorAll("input,select").forEach((control) => { control.disabled = true; });
  });

  const sourceFields = document.querySelector("[data-source-fields]");
  const updateSetupSource = () => {
    const mode = document.querySelector('input[name="source_mode"]:checked')?.value;
    sourceFields?.classList.toggle("hidden", mode === "temporary_folder");
    const credentialField = sourceFields?.querySelector(".credential-field");
    const advancedCredential = sourceFields?.querySelector(".advanced-fields");
    credentialField?.classList.toggle("hidden", mode !== "openwebui");
    advancedCredential?.classList.toggle("hidden", mode !== "openwebui");
  };
  document.querySelectorAll('input[name="source_mode"]').forEach((radio) => radio.addEventListener("change", updateSetupSource));
  updateSetupSource();

  const compareForm = document.querySelector("[data-compare-form]");
  const choices = [...document.querySelectorAll("[data-report-choice]")];
  const compareButton = document.querySelector("[data-compare-button]");
  const updateCompare = () => {
    const selected = choices.filter((choice) => choice.checked);
    choices.filter((choice) => !choice.checked).forEach((choice) => { choice.disabled = selected.length >= 2; });
    if (compareButton) compareButton.disabled = selected.length !== 2;
  };
  choices.forEach((choice) => choice.addEventListener("change", updateCompare));
  compareForm?.addEventListener("submit", (event) => {
    const selected = choices.filter((choice) => choice.checked);
    if (selected.length !== 2) { event.preventDefault(); return; }
    selected.forEach((choice, index) => { choice.name = index === 0 ? "baseline" : "candidate"; });
  });
})();
