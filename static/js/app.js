// Shared helpers: toast notifications, mobile sidebar toggle, status badge class.

function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function statusBadgeClass(status) {
  return `badge badge-${(status || "").toLowerCase()}`;
}

const CATEGORY_BADGE_CLASSES = {
  Technical: "badge-cat-technical",
  Cultural: "badge-cat-cultural",
  Workshop: "badge-cat-workshop",
  Sports: "badge-cat-sports",
  Hackathon: "badge-cat-hackathon",
  Seminar: "badge-cat-seminar",
};
function categoryBadgeClass(category) {
  return `badge ${CATEGORY_BADGE_CLASSES[category] || "badge-category"}`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebarBackdrop");

  function closeSidebar() {
    sidebar.classList.remove("show");
    backdrop.classList.remove("show");
  }

  if (toggle && sidebar && backdrop) {
    toggle.addEventListener("click", () => {
      sidebar.classList.toggle("show");
      backdrop.classList.toggle("show");
    });
    backdrop.addEventListener("click", closeSidebar);
    sidebar.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeSidebar));
  }

  const fullscreenToggle = document.getElementById("fullscreenToggle");
  if (fullscreenToggle) {
    fullscreenToggle.addEventListener("click", () => {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        document.documentElement.requestFullscreen().catch(() => {
          showToast("Fullscreen is not available in this browser.", "error");
        });
      }
    });
    document.addEventListener("fullscreenchange", () => {
      const icon = fullscreenToggle.querySelector("i");
      icon.className = document.fullscreenElement ? "bi bi-fullscreen-exit" : "bi bi-arrows-fullscreen";
    });
  }

  const globalSearch = document.getElementById("globalSearch");
  if (globalSearch) {
    document.addEventListener("keydown", (e) => {
      const isShortcut = (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k";
      if (isShortcut) {
        e.preventDefault();
        globalSearch.focus();
        globalSearch.select();
      }
      if (e.key === "Escape" && document.activeElement === globalSearch) {
        globalSearch.blur();
      }
    });
  }
});
