(() => {
  const KEY = "morgentidende-theme";
  let saved = null;
  try { saved = localStorage.getItem(KEY); } catch (_) {}
  const systemDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  const initial = saved === "dark" || saved === "light" ? saved : (systemDark ? "dark" : "light");
  document.documentElement.dataset.theme = initial;

  const sync = () => {
    const button = document.querySelector(".theme-toggle");
    if (!button) return;
    const dark = document.documentElement.dataset.theme === "dark";
    button.setAttribute("aria-checked", String(dark));
    const label = button.querySelector(".theme-toggle__label");
    if (label) label.textContent = dark ? "Lys" : "Mørk";
  };

  const ready = () => {
    sync();
    const button = document.querySelector(".theme-toggle");
    if (!button) return;
    button.addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem(KEY, next); } catch (_) {}
      sync();
    });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready, { once: true });
  else ready();
})();
