(() => {
  const body = document.body;
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
    if (!response.ok) throw new Error(payload.error || "The request could not be completed.");
    return payload;
  };

  document.querySelector("[data-open-drawer]")?.addEventListener("click", () => body.classList.remove("drawer-collapsed"));
  document.querySelector("[data-close-drawer]")?.addEventListener("click", () => body.classList.add("drawer-collapsed"));
  const tabs = [...document.querySelectorAll("[data-source]")];
  const forms = [...document.querySelectorAll("[data-form]")];
  tabs.forEach((tab) => tab.addEventListener("click", () => {
    tabs.forEach((item) => item.classList.toggle("active", item === tab));
    forms.forEach((form) => form.classList.toggle("hidden", form.dataset.form !== tab.dataset.source));
  }));
  const profilePicker = document.querySelector("[data-profile-picker]");
  profilePicker?.addEventListener("change", () => {
    const option = profilePicker.selectedOptions[0];
    if (!option?.value) return;
    const kind = option.dataset.kind;
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
      const use = document.createElement("button"); use.type = "button"; use.className = "secondary small"; use.textContent = setupMode ? "Select" : "Use details";
      use.addEventListener("click", () => setupMode ? populateSetupForm(environment) : populateSourceForm(environment));
      row.append(name, address, runtime, capability, use); node.append(row);
    }));
  };
  const discover = async (setupMode) => {
    setStatus("Scanning bounded local service metadata…");
    try {
      const payload = await postForm(setupMode ? "/setup/discovery" : "/dashboard/discovery/environments", setupMode ? {} : { metadata_consent: "true" });
      const environments = payload.environments || [];
      setStatus(environments.length ? `${environments.length} environment candidate(s) found.` : "No supported local environment candidate was found.");
      renderEnvironments(environments, setupMode);
    } catch (error) { setStatus(error instanceof Error ? error.message : "Discovery failed."); }
  };
  document.querySelector("[data-discover-environments]")?.addEventListener("click", () => discover(false));
  document.querySelector("[data-setup-discovery]")?.addEventListener("click", () => discover(true));

  const openWebUiUrl = document.querySelector("[data-openwebui-url]");
  const credentialRef = document.querySelector('form[data-form="openwebui"] input[name="credential_ref"]');
  const knowledgeSelect = document.querySelector("[data-knowledge-bases]");
  const knowledgeId = document.querySelector("[data-knowledge-id]");
  document.querySelector("[data-load-knowledge-bases]")?.addEventListener("click", async () => {
    if (!openWebUiUrl?.value || !credentialRef?.value) { setStatus("Enter an OpenWebUI URL and credential reference first."); return; }
    setStatus("Loading accessible OpenWebUI knowledge bases…");
    try {
      const payload = await postForm("/dashboard/discovery/openwebui/knowledge-bases", { base_url: openWebUiUrl.value, credential_ref: credentialRef.value });
      knowledgeSelect.replaceChildren(new Option("Select a knowledge base", ""));
      (payload.knowledge_bases || []).forEach((item) => knowledgeSelect.add(new Option(`${item.name} (${item.id})`, item.id)));
      setStatus(`${(payload.knowledge_bases || []).length} knowledge base(s) loaded.`);
    } catch (error) { setStatus(error instanceof Error ? error.message : "Knowledge-base discovery failed."); }
  });
  knowledgeSelect?.addEventListener("change", () => { if (knowledgeId) knowledgeId.value = knowledgeSelect.value; });

  const sourceFields = document.querySelector("[data-source-fields]");
  document.querySelectorAll('input[name="source_mode"]').forEach((radio) => radio.addEventListener("change", () => {
    if (sourceFields) sourceFields.classList.toggle("hidden", radio.checked && radio.value === "temporary_folder");
  }));

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
