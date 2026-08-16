// Events table: search / filter via /api/events, delete with confirmation modal.

const tableBody = document.getElementById("eventsTableBody");
const searchInput = document.getElementById("searchInput");
const categoryFilter = document.getElementById("categoryFilter");
const statusFilter = document.getElementById("statusFilter");
const deleteModal = document.getElementById("deleteModal");
const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");
const cancelDeleteBtn = document.getElementById("cancelDeleteBtn");

let pendingDeleteId = null;
let debounceTimer = null;

function capacityFillClass(pct) {
  if (pct >= 100) return "capacity-fill is-full";
  if (pct >= 80) return "capacity-fill is-high";
  return "capacity-fill";
}

async function loadEvents() {
  tableBody.innerHTML = `<tr><td colspan="9"><div class="table-loading"><span class="spinner"></span>Loading events...</div></td></tr>`;
  const params = new URLSearchParams({
    search: searchInput.value.trim(),
    category: categoryFilter.value,
    status: statusFilter.value,
  });
  try {
    const res = await fetch(`/api/events?${params.toString()}`);
    const events = await res.json();
    renderEvents(events);
  } catch (err) {
    tableBody.innerHTML = `<tr><td colspan="9"><div class="empty-state"><i class="bi bi-wifi-off"></i><strong>Could not load events</strong><span>Check your connection and try again.</span></div></td></tr>`;
  }
}

function renderEvents(events) {
  if (!events.length) {
    tableBody.innerHTML = `<tr><td colspan="9"><div class="empty-state"><i class="bi bi-calendar-x"></i><strong>No events found</strong><span>Try adjusting your search or filters.</span></div></td></tr>`;
    return;
  }
  tableBody.innerHTML = "";
  for (const e of events) {
    const registered = e.registered_count ?? 0;
    const pct = e.max_participants ? Math.min(100, Math.round((registered / e.max_participants) * 100)) : 0;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="cell-id">${escapeHtml(e.event_id)}</td>
      <td class="cell-primary">${escapeHtml(e.event_name)}</td>
      <td><span class="${categoryBadgeClass(e.category)}">${escapeHtml(e.category)}</span></td>
      <td class="cell-muted">${escapeHtml(e.date)}</td>
      <td class="cell-muted">${escapeHtml(e.venue)}</td>
      <td>
        <div class="capacity-cell">
          <span class="capacity-numbers">${registered} / ${e.max_participants}</span>
          <div class="capacity-track"><div class="${capacityFillClass(pct)}" style="width:${pct}%;"></div></div>
        </div>
      </td>
      <td class="cell-muted">&#8377;${e.registration_fee}</td>
      <td><span class="${statusBadgeClass(e.status)}">${escapeHtml(e.status)}</span></td>
      <td class="actions-col">
        <div class="row-actions">
          <a class="icon-btn icon-btn-edit" title="Edit event" href="/events/edit/${encodeURIComponent(e.event_id)}"><i class="bi bi-pencil"></i></a>
          <button class="icon-btn icon-btn-delete" title="Delete event" data-delete-id="${e.event_id}" data-delete-name="${escapeHtml(e.event_name)}"><i class="bi bi-trash3"></i></button>
        </div>
      </td>`;
    tableBody.appendChild(tr);
  }
}

tableBody.addEventListener("click", (ev) => {
  const btn = ev.target.closest("[data-delete-id]");
  if (!btn) return;
  pendingDeleteId = btn.dataset.deleteId;
  document.getElementById("deleteModalText").textContent =
    `Are you sure you want to delete "${btn.dataset.deleteName}"? This action cannot be undone.`;
  deleteModal.classList.add("show");
});

cancelDeleteBtn.addEventListener("click", () => {
  deleteModal.classList.remove("show");
  pendingDeleteId = null;
});

confirmDeleteBtn.addEventListener("click", async () => {
  if (!pendingDeleteId) return;
  try {
    const res = await fetch(`/events/delete/${encodeURIComponent(pendingDeleteId)}`, { method: "POST" });
    const data = await res.json();
    showToast(data.message, data.success ? "success" : "error");
    if (data.success) loadEvents();
  } catch (err) {
    showToast("Network error while deleting event.", "error");
  }
  deleteModal.classList.remove("show");
  pendingDeleteId = null;
});

searchInput.addEventListener("input", () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(loadEvents, 300);
});
categoryFilter.addEventListener("change", loadEvents);
statusFilter.addEventListener("change", loadEvents);

loadEvents();
