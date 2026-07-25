function openRestoreView() {
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active-view", view.id === "restore-view");
  });
  document.querySelectorAll(".sidebar nav a").forEach((link) => {
    link.classList.toggle("active", link.dataset.view === "restore");
  });
  window.location.hash = "restore";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function bindRestoreNavigation() {
  document.querySelectorAll('[data-view="restore"]').forEach((element) => {
    element.addEventListener("click", (event) => {
      event.preventDefault();
      openRestoreView();
    });
  });
}

function bindRestoreForm() {
  const form = document.querySelector("#restore-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = document.querySelector("#submit-restore");
    const message = document.querySelector("#restore-message");
    const report = document.querySelector("#restore-report");
    const password = document.querySelector("#restore-password").value;

    report.classList.add("hidden");
    button.disabled = true;
    button.textContent = "Vérification en cours…";
    message.textContent = "Contrôle de l’intégrité puis restauration…";
    message.className = "message";

    const payload = {
      archive_path: document.querySelector("#restore-archive").value.trim(),
      destination_directory: document.querySelector("#restore-destination").value.trim(),
      overwrite: document.querySelector("#restore-overwrite").checked,
      password: password || null,
    };

    try {
      const response = await fetch("/api/v1/restore/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error?.message ?? "La restauration a échoué.");
      }
      if (!data.success) {
        throw new Error(data.error ?? "La restauration n’a pas pu être réalisée.");
      }

      document.querySelector("#restore-report-destination").textContent =
        data.destination_directory;
      document.querySelector("#restore-report-files").textContent =
        data.restore_report?.restored_files ?? 0;
      document.querySelector("#restore-report-skipped").textContent =
        data.restore_report?.skipped_files ?? 0;
      document.querySelector("#restore-report-integrity").textContent =
        data.integrity_report?.valid ? "Validée" : "Échec";
      report.classList.remove("hidden");
      message.textContent = "La restauration est terminée avec succès.";
      message.className = "message success";
    } catch (error) {
      message.textContent = error.message;
      message.className = "message error";
    } finally {
      button.disabled = false;
      button.textContent = "Vérifier et restaurer";
    }
  });
}

bindRestoreNavigation();
bindRestoreForm();
if (window.location.hash === "#restore") openRestoreView();