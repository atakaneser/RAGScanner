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
    if (!response.ok) {
      const message = payload.error || t("The request could not be completed.");
      throw new Error(payload.code ? `[${payload.code}] ${message}` : message);
    }
    return payload;
  };
  const sourceKindSelect = document.querySelector("[data-source-kind]");
  const sourceTypeGrid = document.querySelector(".source-type-grid");
  [
    { value: "website", label: "Website / Sitemap", url: "https://example.com/sitemap.xml", name: "Website knowledge" },
    { value: "sharepoint", label: "SharePoint", url: "https://example.sharepoint.com/sites/knowledge", name: "SharePoint knowledge" },
  ].forEach((definition) => {
    if (!sourceKindSelect?.querySelector(`option[value="${definition.value}"]`)) {
      const option = new Option(definition.label, definition.value);
      option.dataset.url = definition.url;
      option.dataset.name = definition.name;
      sourceKindSelect?.add(option);
    }
    if (sourceTypeGrid && !sourceTypeGrid.querySelector(`[data-source-choice="${definition.value}"]`)) {
      const button = document.createElement("button");
      button.className = "source-type";
      button.type = "button";
      button.dataset.sourceChoice = definition.value;
      const logo = document.createElement("span");
      logo.className = `source-logo logo-${definition.value}`;
      logo.ariaHidden = "true";
      const label = document.createElement("span");
      label.textContent = t(definition.label);
      button.append(logo, label);
      sourceTypeGrid.append(button);
    }
  });

  const defaultAIInventory = document.querySelector("[data-default-ai-inventory]");
  if (defaultAIInventory) {
    const settingsForm = document.querySelector("form.settings-console");
    const provider = settingsForm?.querySelector('[name="ai_provider"]');
    const model = settingsForm?.querySelector('[name="ai_model"]');
    const endpoint = settingsForm?.querySelector('[name="ai_base_url"]');
    const resultsRow = defaultAIInventory.querySelector("[data-default-ai-results-row]");
    const results = defaultAIInventory.querySelector("[data-default-ai-results]");
    const status = defaultAIInventory.querySelector("[data-default-ai-status]");
    const refreshButton = defaultAIInventory.querySelector("[data-refresh-default-ai]");
    const localDefaults = {
      ollama: "http://127.0.0.1:11434",
      "lm-studio": "http://127.0.0.1:1234",
      localai: "http://127.0.0.1:8080",
      vllm: "http://127.0.0.1:8000",
    };
    const setInventoryStatus = (message, warning = false) => {
      if (!status) return;
      status.textContent = message;
      status.classList.toggle("warning", warning);
    };
    const clearUnverifiedModel = () => {
      if (!model) return;
      model.value = "";
      model.placeholder = t("No model detected on this machine");
      model.setAttribute("aria-invalid", "true");
    };
    const refreshDefaultModels = async () => {
      const selectedProvider = provider?.value || "";
      if (!Object.hasOwn(localDefaults, selectedProvider)) {
        resultsRow?.classList.add("hidden");
        setInventoryStatus(t("Automatic discovery checks local providers only. Remote models require an explicit connection."));
        return;
      }
      if (refreshButton) refreshButton.disabled = true;
      setInventoryStatus(t("Checking the selected local AI provider…"));
      try {
        const payload = await postForm("/dashboard/discovery/ai-models", {
          provider: selectedProvider,
          base_url: endpoint?.value || localDefaults[selectedProvider],
          remote_consent: "false",
        });
        const models = payload.models || [];
        results?.replaceChildren(...models.map((name) => new Option(name, name)));
        resultsRow?.classList.toggle("hidden", models.length === 0);
        if (!models.length) {
          clearUnverifiedModel();
          setInventoryStatus(t("No model was found at this local endpoint. Start the provider or correct its address."), true);
          return;
        }
        const configured = model?.value || "";
        const selected = models.includes(configured) ? configured : models[0];
        if (results) results.value = selected;
        if (model) {
          model.value = selected;
          model.removeAttribute("aria-invalid");
        }
        if (configured && configured !== selected) {
          setInventoryStatus(`${t("The saved model is not installed. Selected")} ${selected}. ${t("Save settings to keep this change.")}`, true);
        } else {
          setInventoryStatus(`${models.length} ${t("model(s) found")} · ${selected}`);
        }
      } catch (error) {
        resultsRow?.classList.add("hidden");
        clearUnverifiedModel();
        const code = error instanceof Error ? error.message.match(/^\[([^\]]+)\]/)?.[1] : "";
        setInventoryStatus(`${t("Local model discovery failed")}${code ? ` · ${code}` : ""}`, true);
      } finally {
        if (refreshButton) refreshButton.disabled = false;
      }
    };
    provider?.addEventListener("change", () => {
      if (Object.hasOwn(localDefaults, provider.value) && endpoint) endpoint.value = localDefaults[provider.value];
      refreshDefaultModels();
    });
    endpoint?.addEventListener("change", refreshDefaultModels);
    results?.addEventListener("change", () => {
      if (model && results.value) {
        model.value = results.value;
        model.removeAttribute("aria-invalid");
        setInventoryStatus(`${t("Selected")} ${results.value}. ${t("Save settings to keep this change.")}`);
      }
    });
    refreshButton?.addEventListener("click", refreshDefaultModels);
    refreshDefaultModels();
  }

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
    const targetTab = kind === "filesystem" ? "local" : (["website", "sharepoint"].includes(kind) ? "website" : "openwebui");
    const selectedTab = tabs.find((tab) => tab.dataset.source === targetTab);
    selectedTab?.click();
    if (kind === "filesystem") {
      const localPath = document.querySelector("[data-local-path]");
      if (localPath) localPath.value = option.dataset.location || "";
      const sourceName = document.querySelector('form[data-form="local"] input[name="source_name"]');
      if (sourceName) sourceName.value = option.textContent?.replace(/ · .+$/, "") || "";
    } else if (["website", "sharepoint"].includes(kind)) {
      const websiteUrl = document.querySelector("[data-website-url]");
      const websiteName = document.querySelector('form[data-form="website"] input[name="source_name"]');
      const websiteCredential = document.querySelector('form[data-form="website"] input[name="credential_ref"]');
      if (websiteUrl) websiteUrl.value = option.dataset.location || "";
      if (websiteName) websiteName.value = option.textContent?.replace(/ · .+$/, "") || "";
      if (websiteCredential) websiteCredential.value = option.dataset.credential || "";
    } else {
      const url = document.querySelector("[data-openwebui-url]");
      const reference = document.querySelector('form[data-form="openwebui"] input[name="credential_ref"]');
      if (url) url.value = option.dataset.location || "";
      if (reference) reference.value = option.dataset.credential || "";
      const sourceName = document.querySelector("[data-selected-source-name]");
      if (sourceName) sourceName.value = option.textContent?.replace(/ · .+$/, "") || "";
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
    const ready = ["openwebui", "filesystem", "website", "sharepoint"].includes(option.value);
    if (sourceNote) sourceNote.innerHTML = ready
      ? `<strong>${t("Ready to scan:")}</strong> ${t(option.value === "filesystem" ? "RAGScanner can scan supported files in this path." : ["website", "sharepoint"].includes(option.value) ? "RAGScanner can scan a page, document, or same-origin sitemap." : "RAGScanner can inventory OpenWebUI knowledge bases and scan their content.")}`
      : `<strong>${t("Detected only:")}</strong> ${t("RAGScanner can remember and discover this environment, but its content connector is not available yet.")}`;
    const auth = ["openwebui", "sharepoint"].includes(option.value);
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
    const credentialRows = [...container.querySelectorAll("[data-ai-credential-row]")];
    const modelList = container.querySelector("[data-ai-model-list]");
    const modelResultsRow = container.querySelector("[data-ai-model-results-row]");
    const modelResults = container.querySelector("[data-ai-model-results]");
    const loadModels = container.querySelector("[data-load-ai-models]");
    const updateProvider = () => {
      const option = provider?.selectedOptions[0];
      if (!option) return;
      const local = option.dataset.local === "true";
      const credentialRequired = option.dataset.credentialRequired === "true";
      if (endpoint && !endpoint.dataset.edited) endpoint.value = option.dataset.url || "";
      credentialRows.forEach((row) => row.classList.toggle("hidden", !credentialRequired));
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
    modelResults?.addEventListener("change", () => {
      if (model && modelResults.value) model.value = modelResults.value;
    });
    loadModels?.addEventListener("click", async () => {
      const option = provider?.selectedOptions[0];
      const credential = container.querySelector('input[name="ai_credential_ref"]');
      const apiKey = container.querySelector('input[name="ai_api_key"]');
      const remoteConsent = consent?.querySelector('input[name="ai_remote_consent"]');
      loadModels.disabled = true;
      loadModels.textContent = t("Detecting models…");
      try {
        const payload = await postForm("/dashboard/discovery/ai-models", {
          provider: provider?.value || "",
          base_url: endpoint?.value || "",
          credential_ref: credential?.value || "",
          api_key: apiKey?.value || "",
          remote_consent: option?.dataset.local === "true" ? "false" : String(Boolean(remoteConsent?.checked)),
        });
        const models = payload.models || [];
        modelList?.replaceChildren(...models.map((name) => new Option(name, name)));
        modelResults?.replaceChildren(new Option(t("Choose a detected model"), ""), ...models.map((name) => new Option(name, name)));
        if (modelResults) modelResults.size = Math.min(Math.max(models.length + 1, 2), 7);
        modelResultsRow?.classList.toggle("hidden", models.length === 0);
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

  const jobRows = [...document.querySelectorAll("[data-job-row]")];
  const jobLogs = document.querySelector("[data-job-logs]");
  const liveStatus = document.querySelector("[data-job-live-status]");
  const renderJobLogs = (logs) => {
    if (!jobLogs) return;
    jobLogs.replaceChildren(...logs.map((log) => {
      const article = document.createElement("article"); article.className = `job-log job-log-${log.level}`; article.dataset.jobLog = log.job_id;
      const heading = document.createElement("div");
      const code = document.createElement("strong"); code.textContent = log.code;
      const id = document.createElement("code"); id.textContent = log.display_id || log.job_id.slice(0, 12);
      heading.append(code, id);
      const message = document.createElement("p"); message.textContent = t(log.message);
      const time = document.createElement("time"); time.dateTime = log.timestamp; time.dataset.localTime = ""; time.textContent = window.ragscannerFormatTime?.(log.timestamp) || log.timestamp;
      article.append(heading, message, time);
      return article;
    }));
  };
  const refreshJobs = async () => {
    try {
      const response = await fetch("/dashboard/jobs/status", { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) throw new Error("status unavailable");
      const payload = await response.json();
      (payload.jobs || []).forEach((job) => {
        const row = document.querySelector(`[data-job-row="${job.id}"]`);
        if (!row) return;
        const status = row.querySelector("[data-job-status]");
        if (status) { status.className = `state state-${job.status}`; status.textContent = job.status.replaceAll("_", " "); }
        const bar = row.querySelector("[data-job-progress-bar]"); if (bar) bar.style.width = `${job.progress}%`;
        const progress = row.querySelector("[data-job-progress]"); if (progress) progress.textContent = `${job.progress}%`;
        const attempts = row.querySelector("[data-job-attempts]"); if (attempts) attempts.textContent = `${job.attempt_count}/${job.max_attempts}`;
      });
      renderJobLogs(payload.logs || []);
      if (liveStatus) liveStatus.textContent = t("Live");
    } catch (_error) {
      if (liveStatus) liveStatus.textContent = t("Update unavailable");
    }
  };
  if (liveStatus) window.setInterval(refreshJobs, 2000);

  document.querySelectorAll(".scan-form").forEach((form) => {
    const scheduleFields = form.querySelector("[data-schedule-fields]");
    form.querySelectorAll("[data-execution-mode]").forEach((control) => control.addEventListener("change", () => {
      const recurring = form.querySelector('[name="execution_mode"]:checked')?.value === "scheduled";
      scheduleFields?.classList.toggle("hidden", !recurring);
      scheduleFields?.querySelectorAll("input,select").forEach((field) => { field.disabled = !recurring; });
    }));
    scheduleFields?.querySelectorAll("input,select").forEach((field) => { field.disabled = true; });
  });

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
  document.querySelectorAll("[data-report-delete]").forEach((control) => {
    if (control.tagName === "FORM") {
      control.addEventListener("submit", (event) => {
        if (!window.confirm(t("Delete this report permanently? This cannot be undone."))) event.preventDefault();
      });
      return;
    }
    control.addEventListener("click", () => {
      if (!window.confirm(t("Delete this report permanently? This cannot be undone."))) return;
      const form = document.createElement("form");
      form.method = "post";
      form.action = control.dataset.deleteUrl || "";
      const token = document.createElement("input");
      token.type = "hidden";
      token.name = "csrf_token";
      token.value = csrfToken;
      form.append(token);
      document.body.append(form);
      form.submit();
    });
  });
})();
