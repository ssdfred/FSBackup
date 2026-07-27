(() => {
  const originalFetch = window.fetch.bind(window);
  const guardedEndpoints = new Set([
    "/api/v1/sources/diagnostic",
    "/api/v1/sources/exclusions/suggestions",
  ]);
  const requestVersions = new Map();

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
    const version = (requestVersions.get(url.pathname) ?? 0) + 1;
    requestVersions.set(url.pathname, version);
    const response = await originalFetch(input, options);

    const obsolete =
      requestVersions.get(url.pathname) !== version ||
      !source ||
      source !== selectedSource();
    if (!obsolete) return response;

    // Une ancienne analyse ne doit jamais écraser l’état du lecteur courant.
    return new Promise(() => {});
  };
})();
