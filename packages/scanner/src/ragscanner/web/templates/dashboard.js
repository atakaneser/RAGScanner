(() => {
  const body = document.body;
  const tabs = [...document.querySelectorAll("[data-source]")];
  const forms = [...document.querySelectorAll("[data-form]")];
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
})();
