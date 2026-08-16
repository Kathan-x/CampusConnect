// Custom MongoDB Query Console: sends raw query text to /api/custom-query,
// renders a dark syntax-highlighted result, and confirms before write ops.

const cqCollection = document.getElementById("cqCollection");
const cqEditor = document.getElementById("cqEditor");
const cqExecuteBtn = document.getElementById("cqExecuteBtn");
const cqClearBtn = document.getElementById("cqClearBtn");
const cqExamplesBox = document.getElementById("cqExamples");
const cqHistorySection = document.getElementById("cqHistorySection");
const cqHistoryBox = document.getElementById("cqHistory");
const cqResultSection = document.getElementById("cqResultSection");
const cqStatus = document.getElementById("cqStatus");
const cqResultConsole = document.getElementById("cqResultConsole");
const cqConfirmModal = document.getElementById("cqConfirmModal");
const cqConfirmText = document.getElementById("cqConfirmText");
const cqCancelBtn = document.getElementById("cqCancelBtn");
const cqConfirmBtn = document.getElementById("cqConfirmBtn");

const CQ_TODAY = new Date().toISOString().slice(0, 10);
const CQ_EXAMPLES = [
  { label: "Technical Events", query: 'db.events.find({ category: "Technical" })' },
  { label: "Fee > ₹300", query: "db.events.find({ registration_fee: { $gt: 300 } })" },
  { label: "Open Events", query: 'db.events.find({ status: "Open" })' },
  { label: "Upcoming Events", query: `db.events.find({ date: { $gte: "${CQ_TODAY}" } })` },
  { label: "Count Registrations", query: "db.registrations.countDocuments({})" },
  {
    label: "Events by Category",
    query:
      'db.events.aggregate([\n  { $group: { _id: "$category", total: { $sum: 1 } } },\n  { $sort: { total: -1 } }\n])',
  },
];

let pendingWrite = false;

function cqTruncate(str, n) {
  return str.length > n ? str.slice(0, n) + "…" : str;
}

function renderExampleChips() {
  cqExamplesBox.innerHTML = "";
  CQ_EXAMPLES.forEach((ex) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "cq-chip";
    chip.textContent = ex.label;
    chip.title = ex.query;
    chip.addEventListener("click", () => {
      cqEditor.value = ex.query;
      cqEditor.focus();
    });
    cqExamplesBox.appendChild(chip);
  });
}

function loadHistory() {
  const hist = JSON.parse(sessionStorage.getItem("cqHistory") || "[]");
  if (!hist.length) {
    cqHistorySection.style.display = "none";
    return;
  }
  cqHistorySection.style.display = "block";
  cqHistoryBox.innerHTML = "";
  hist.forEach((q) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "cq-chip cq-chip-history";
    chip.textContent = cqTruncate(q.replace(/\s+/g, " "), 42);
    chip.title = q;
    chip.addEventListener("click", () => {
      cqEditor.value = q;
      cqEditor.focus();
    });
    cqHistoryBox.appendChild(chip);
  });
}

function pushHistory(query) {
  let hist = JSON.parse(sessionStorage.getItem("cqHistory") || "[]");
  hist = hist.filter((q) => q !== query);
  hist.unshift(query);
  hist = hist.slice(0, 6);
  sessionStorage.setItem("cqHistory", JSON.stringify(hist));
  loadHistory();
}

renderExampleChips();
loadHistory();

cqClearBtn.addEventListener("click", () => {
  cqEditor.value = "";
  cqResultSection.style.display = "none";
  cqEditor.focus();
});

cqCollection.addEventListener("change", () => {
  if (!cqEditor.value.trim()) {
    cqEditor.placeholder = `db.${cqCollection.value}.find({})`;
  }
});

cqExecuteBtn.addEventListener("click", () => runCustomQuery(false));

cqCancelBtn.addEventListener("click", () => {
  cqConfirmModal.classList.remove("show");
  pendingWrite = false;
});

cqConfirmBtn.addEventListener("click", () => {
  cqConfirmModal.classList.remove("show");
  if (pendingWrite) {
    pendingWrite = false;
    runCustomQuery(true);
  }
});

function setExecuting(isRunning) {
  cqExecuteBtn.disabled = isRunning;
  cqExecuteBtn.innerHTML = isRunning
    ? '<span class="spinner" style="width:14px;height:14px;border-width:2px;"></span>Executing...'
    : '<i class="bi bi-play-fill"></i>Execute Query';
}

function showStatus(ok, message, meta) {
  cqResultSection.style.display = "block";
  cqStatus.innerHTML = `
    <span class="${ok ? "cq-status-ok" : "cq-status-error"}"><span class="cq-status-dot"></span>${ok ? "Success" : "Query Error"}</span>
    <span class="cq-status-meta">${escapeHtml(message || "")}</span>
    ${meta ? `<span class="cq-status-meta">${escapeHtml(meta)}</span>` : ""}
  `;
}

async function runCustomQuery(confirmed) {
  const query = cqEditor.value.trim();
  if (!query) {
    cqResultConsole.innerHTML = "";
    showStatus(false, "Please enter a query to execute.");
    return;
  }

  setExecuting(true);
  try {
    const res = await fetch("/api/custom-query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, confirmed }),
    });
    const data = await res.json();

    if (data.requires_confirmation) {
      pendingWrite = true;
      cqConfirmText.textContent = data.summary;
      cqConfirmModal.classList.add("show");
      setExecuting(false);
      return;
    }

    if (!data.success) {
      cqResultConsole.innerHTML = "";
      showStatus(false, data.error || "Query failed.");
      setExecuting(false);
      return;
    }

    pushHistory(query);
    cqRenderResult(data);
  } catch (err) {
    cqResultConsole.innerHTML = "";
    showStatus(false, "Network error while executing the query.");
  }
  setExecuting(false);
}

function cqRenderResult(data) {
  const meta = `Execution time: ${data.execution_time_ms} ms`;

  if (data.result_type === "find" || data.result_type === "aggregate") {
    const noun = data.result_type === "find" ? "document" : "aggregation result";
    showStatus(true, `${data.count} ${noun}${data.count === 1 ? "" : "s"} returned`, meta);
    cqResultConsole.innerHTML = data.count
      ? cqSyntaxHighlight(data.data)
      : '<span class="cq-empty-console">No documents matched this query.</span>';
  } else if (data.result_type === "count") {
    showStatus(true, `Result: ${data.count}`, meta);
    cqResultConsole.innerHTML = cqSyntaxHighlight({ count: data.count });
  } else if (data.result_type === "update") {
    showStatus(true, `Matched ${data.matched_count}, modified ${data.modified_count}`, meta);
    cqResultConsole.innerHTML = cqSyntaxHighlight({
      matched_count: data.matched_count,
      modified_count: data.modified_count,
    });
  } else if (data.result_type === "delete") {
    showStatus(true, `Deleted ${data.deleted_count} document${data.deleted_count === 1 ? "" : "s"}`, meta);
    cqResultConsole.innerHTML = cqSyntaxHighlight({ deleted_count: data.deleted_count });
  }
}

function cqSyntaxHighlight(obj) {
  const json = escapeHtml(JSON.stringify(obj, null, 2));
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false)\b|\bnull\b|-?\d+(\.\d+)?([eE][+-]?\d+)?)/g,
    (match) => {
      let cls = "cq-num";
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? "cq-key" : "cq-str";
      } else if (/true|false/.test(match)) {
        cls = "cq-bool";
      } else if (/null/.test(match)) {
        cls = "cq-null";
      }
      return `<span class="${cls}">${match}</span>`;
    }
  );
}
