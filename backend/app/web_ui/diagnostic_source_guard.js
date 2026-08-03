(() => {
  const originalFetch = window.fetch.bind(window);
  const guardedEndpoints = new Set([
    "/api/v1/sources/diagnostic",
    "/api/v1/sources/exclusions/suggestions",
  ]);

  function normalizeSource(value) {
    return String(value ?? "")
      .trim()
      .replaceAll("/", "\\")
      .replace(/\\+$/g, "")
      .toLowerCase();
  }

  function selectedSource() {
    if (document.querySelector("#source-mode")?.value !== "windows_disk") return "";
    return normalizeSource(document.querySelector("#source-root")?.value);
  }

  function requestSource(options) {
    try {
      return normalizeSource(JSON.parse(options?.body ?? "{}").source_root);
    } catch (_error) {
      return "";
    }
  }

  window.fetch = async (input, options = {}) => {
    const url = new URL(typeof input === "string" ? input : input.url, window.location.href);
    if (!guardedEndpoints.has(url.pathname)) return originalFetch(input, options);

    const source = requestSource(options);
    const response = await originalFetch(input, options);

    if (source && source === selectedSource()) return response;

    // Une réponse d’un ancien lecteur ne doit jamais remplacer l’état courant.
    // Les appels simultanés du diagnostic et de la capacité pour le même lecteur
    // restent tous deux valides.
    return new Promise(() => {});
  };
})();
