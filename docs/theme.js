(() => {
  const KEY = "morgentidende-theme";
  let saved = null;
  try { saved = localStorage.getItem(KEY); } catch (_) {}
  const systemDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  const initial = saved === "dark" || saved === "light" ? saved : (systemDark ? "dark" : "light");
  document.documentElement.dataset.theme = initial;

  const rootPrefix = location.pathname.includes("/artikler/") ? "../" : "./";
  const css = document.createElement("link");
  css.rel = "stylesheet";
  css.href = `${rootPrefix}account-ui.css?v=1`;
  document.head.appendChild(css);

  const sync = () => {
    const button = document.querySelector(".theme-toggle");
    if (!button) return;
    const dark = document.documentElement.dataset.theme === "dark";
    button.setAttribute("aria-checked", String(dark));
    const label = button.querySelector(".theme-toggle__label");
    if (label) label.textContent = dark ? "Lys" : "Mørk";
  };

  const addAccountLink = () => {
    const masthead = document.querySelector(".masthead-inner");
    if (!masthead || masthead.querySelector(".account-link")) return;
    const link = document.createElement("a");
    link.className = "account-link";
    link.href = `${rootPrefix}login.html`;
    link.setAttribute("aria-label", "Log ind");
    link.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"></circle><path d="M4.5 20c.8-4.1 3.3-6 7.5-6s6.7 1.9 7.5 6"></path></svg><span>Log ind</span>';
    masthead.appendChild(link);
  };

  const trackArticleView = () => {
    if (!document.body.classList.contains("article-page")) return;
    const match = location.pathname.match(/\/artikler\/([a-z0-9-]+)\.html$/i);
    if (!match) return;
    const payload = JSON.stringify({
      slug: match[1],
      title: (document.querySelector("h1")?.textContent || "").trim(),
      category: (document.querySelector(".section-label")?.textContent || "").trim(),
      referrer: document.referrer || "",
    });
    const endpoint = "https://morgentidende-app.nicolaipetersen108.workers.dev/api/analytics/pageview";
    try {
      fetch(endpoint, { method: "POST", mode: "cors", keepalive: true, credentials: "omit", headers: { "content-type": "application/json" }, body: payload }).catch(() => {});
    } catch (_) {}
  };

  const ready = () => {
    sync();
    addAccountLink();
    trackArticleView();
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
