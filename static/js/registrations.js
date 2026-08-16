// Registrations table: search / filter via /api/registrations.

const regBody = document.getElementById("regTableBody");
const regSearch = document.getElementById("searchInput");
const eventFilter = document.getElementById("eventFilter");
const resultCount = document.getElementById("resultCount");
let regDebounce = null;

async function loadRegistrations() {
  regBody.innerHTML = `<tr><td colspan="9"><div class="table-loading"><span class="spinner"></span>Loading registrations...</div></td></tr>`;
  const params = new URLSearchParams({
    search: regSearch.value.trim(),
    event_id: eventFilter.value,
  });
  try {
    const res = await fetch(`/api/registrations?${params.toString()}`);
    const rows = await res.json();
    renderRegistrations(rows);
  } catch (err) {
    regBody.innerHTML = `<tr><td colspan="9"><div class="empty-state"><i class="bi bi-wifi-off"></i><strong>Could not load registrations</strong><span>Check your connection and try again.</span></div></td></tr>`;
  }
}

function renderRegistrations(rows) {
  resultCount.textContent = `${rows.length} registration${rows.length === 1 ? "" : "s"}`;
  if (!rows.length) {
    regBody.innerHTML = `<tr><td colspan="9"><div class="empty-state"><i class="bi bi-inbox"></i><strong>No registrations found</strong><span>Try adjusting your search or filter.</span></div></td></tr>`;
    return;
  }
  regBody.innerHTML = "";
  for (const r of rows) {
    const tr = document.createElement("tr");
    const date = r.registered_at ? new Date(r.registered_at).toLocaleDateString() : "-";
    tr.innerHTML = `
      <td class="cell-id">${escapeHtml(r.registration_id)}</td>
      <td class="cell-primary">${escapeHtml(r.student_name)}</td>
      <td class="cell-muted">${escapeHtml(r.enrollment_number)}</td>
      <td class="cell-muted">${escapeHtml(r.email)}</td>
      <td class="cell-muted">${escapeHtml(r.department)}</td>
      <td class="cell-muted">${escapeHtml(r.year)}</td>
      <td><span class="${categoryBadgeClass(r.category)}">${escapeHtml(r.event_name)}</span></td>
      <td class="cell-muted">${date}</td>
      <td class="actions-col">
        <div class="row-actions">
          <a class="icon-btn icon-btn-edit" title="Edit registration" href="/registrations/edit/${encodeURIComponent(r.registration_id)}"><i class="bi bi-pencil"></i></a>
        </div>
      </td>`;
    regBody.appendChild(tr);
  }
}

regSearch.addEventListener("input", () => {
  clearTimeout(regDebounce);
  regDebounce = setTimeout(loadRegistrations, 300);
});
eventFilter.addEventListener("change", loadRegistrations);

loadRegistrations();
