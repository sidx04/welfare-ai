const API = "http://127.0.0.1:8000";

// -----------------------------
// Helpers
// -----------------------------

function buildProfile() {
  return {
    age: parseInt(document.getElementById("age").value),
    income: parseInt(document.getElementById("income").value),
    category: document.getElementById("category").value,
    state: document.getElementById("state").value,
    owns_house: document.getElementById("owns_house").checked,
    owns_lpg: document.getElementById("owns_lpg").checked,
    land_owned_hectares: parseFloat(document.getElementById("land").value),
    has_health_insurance: document.getElementById("insurance").checked
  };
}

function renderProposed(data) {
  return `
    <h2>${data.scheme_name}</h2>

    <div role="alert" data-variant="${data.eligible ? 'success' : 'error'}">
      <strong>${data.eligible ? "Eligible" : "Not Eligible"}</strong>
    </div>

    <h3>Explanation</h3>
    <p>${data.llm_explanation}</p>

    <details>
      <summary>Structured Explanation</summary>
      <pre>${data.structured_explanation}</pre>
    </details>

    <details>
      <summary>Rule Trace</summary>
      <pre>${JSON.stringify(data.trace, null, 2)}</pre>
    </details>
  `;
}

function renderBaseline(data) {
  return `
    <h2>${data.scheme_name} (Baseline)</h2>

    <div role="alert">
      <strong>LLM Output</strong>
    </div>

    <pre>${data.baseline_output}</pre>
  `;
}

function renderAllMatches(data) {
  const topMatches = data.matches.map((match, idx) => {
    const badge = match.status === "eligible"
      ? "✅"
      : match.status === "partially eligible"
        ? "⚠️"
        : "❌";
    const reason = match.failed_reasons.length > 0
      ? `<span>${match.failed_reasons.join("; ")}</span>`
      : "";

    return `
      <li>
        <strong>${match.scheme_name}</strong> → ${match.status} ${badge}
        <p><em>Summary:</em> ${match.llm_explanation || "(not available)"}</p>
        <details>
          <summary>View rule details</summary>
          <pre>${match.structured_explanation}</pre>
        </details>
      </li>
    `;
  }).join("");

  const categories = (group, title) => {
    const items = data.groups[group];
    if (!items || items.length === 0) {
      return `<p><em>No ${title.toLowerCase()}.</em></p>`;
    }
    return `
      <ul>
        ${items.map(item => `
          <li>
            <strong>${item.scheme_name}</strong> → ${item.status}
            ${item.failed_reasons.length > 0 ? `<div>${item.failed_reasons.join("; ")}</div>` : ""}
          </li>
        `).join("")}
      </ul>
    `;
  };

  return `
    <h2>Top Matches</h2>
    <ol>${topMatches}</ol>

    <h3>Eligible schemes</h3>
    ${categories("eligible", "Eligible")}

    <h3>Partially eligible schemes</h3>
    ${categories("partially_eligible", "Partially Eligible")}

    <h3>Not eligible schemes</h3>
    ${categories("not_eligible", "Not Eligible")}
  `;
}

async function postRequest(endpoint, payload) {
  const res = await fetch(`${API}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    throw new Error("API request failed");
  }

  return res.json();
}

function updateUI(html) {
  document.getElementById("output").innerHTML = html;
}

// -----------------------------
// Event Handlers
// -----------------------------

async function handleEvaluate(e) {
  e.preventDefault();

  try {
    updateUI("<p>Loading...</p>");

    const scheme_id = document.getElementById("scheme").value;
    const profile = buildProfile();

    const data = await postRequest("/evaluate", {
      scheme_id,
      profile
    });

    updateUI(renderProposed(data));

  } catch (err) {
    updateUI(`<p>Error: ${err.message}</p>`);
  }
}

async function handleEvaluateAll() {
  try {
    updateUI("<p>Loading...</p>");

    const profile = buildProfile();
    const data = await postRequest("/evaluate_all", { profile });

    updateUI(renderAllMatches(data));

  } catch (err) {
    updateUI(`<p>Error: ${err.message}</p>`);
  }
}

async function handleBaseline() {
  try {
    updateUI("<p>Loading...</p>");

    const scheme_id = document.getElementById("scheme").value;
    const profile = buildProfile();

    const data = await postRequest("/baseline", {
      scheme_id,
      profile
    });

    updateUI(renderBaseline(data));

  } catch (err) {
    updateUI(`<p>Error: ${err.message}</p>`);
  }
}

// -----------------------------
// Init
// -----------------------------

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("form").addEventListener("submit", handleEvaluate);
  document.getElementById("baselineBtn").addEventListener("click", handleBaseline);
  document.getElementById("evaluateAllBtn").addEventListener("click", handleEvaluateAll);
});