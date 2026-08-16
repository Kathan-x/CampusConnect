// MongoDB Query Center: executes queries against /api/query/<key> and renders results.

const queryCards = document.querySelectorAll(".query-card");
const runButtons = document.querySelectorAll("[data-query-btn]");
const resultPanel = document.getElementById("resultPanel");
const resultContent = document.getElementById("resultContent");
const resultTitle = document.getElementById("resultTitle");
const queryLabel = document.getElementById("queryLabel");
const searchTermInput = document.getElementById("searchTermInput");

let activeKey = null;

function setActiveCard(card) {
  queryCards.forEach((c) => c.classList.remove("active"));
  card.classList.add("active");
}

runButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const card = btn.closest(".query-card");
    setActiveCard(card);
    activeKey = card.dataset.query;

    if (card.dataset.needsTerm) {
      const term = searchTermInput.value.trim();
      if (!term) {
        showToast("Please enter an event name.", "error");
        searchTermInput.focus();
        return;
      }
      runQuery("search_by_name", { term }, "Search Event by Name");
      return;
    }
    runQuery(activeKey, {}, card.querySelector(".query-card-title").textContent);
  });
});

if (searchTermInput) {
  searchTermInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      document.querySelector('[data-query-btn="search_by_name"]').click();
    }
  });
}

async function runQuery(key, extraParams = {}, title = "Result") {
  resultPanel.style.display = "block";
  resultTitle.textContent = title;
  resultContent.innerHTML = `<div class="table-loading"><span class="spinner"></span>Running query...</div>`;
  resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });

  const params = new URLSearchParams(extraParams);
  try {
    const res = await fetch(`/api/query/${key}?${params.toString()}`);
    const data = await res.json();

    if (!data.success) {
      queryLabel.textContent = "";
      resultContent.innerHTML = `<div class="empty-state"><i class="bi bi-exclamation-circle"></i><strong>Query failed</strong><span>${escapeHtml(data.message)}</span></div>`;
      return;
    }

    queryLabel.textContent = data.query;
    renderResult(data.result);
  } catch (err) {
    resultContent.innerHTML = `<div class="empty-state"><i class="bi bi-wifi-off"></i><strong>Network error</strong><span>Could not reach the server.</span></div>`;
  }
}

function renderResult(result) {
  if (Array.isArray(result)) {
    if (result.length === 0) {
      resultContent.innerHTML = `<div class="empty-state"><i class="bi bi-inbox"></i><strong>No results found</strong><span>This query returned zero documents.</span></div>`;
      return;
    }
    const columns = Object.keys(result[0]);
    let html = `<div class="table-wrap"><table class="data-table"><thead><tr>`;
    for (const col of columns) html += `<th>${escapeHtml(col)}</th>`;
    html += `</tr></thead><tbody>`;
    for (const row of result) {
      html += "<tr>";
      for (const col of columns) html += `<td>${escapeHtml(row[col])}</td>`;
      html += "</tr>";
    }
    html += "</tbody></table></div>";
    resultContent.innerHTML = html;
  } else {
    let html = `<div class="kpi-grid" style="grid-template-columns: 1fr;">`;
    for (const [key, value] of Object.entries(result)) {
      html += `<div class="kpi-card"><div class="kpi-text"><span class="kpi-label">${escapeHtml(key)}</span><span class="kpi-value">${escapeHtml(value)}</span></div><div class="kpi-icon kpi-icon-indigo"><i class="bi bi-clipboard-data"></i></div></div>`;
    }
    html += "</div>";
    resultContent.innerHTML = html;
  }
}
