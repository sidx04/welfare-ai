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
});