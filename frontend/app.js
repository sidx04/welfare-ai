const API = "http://127.0.0.1:8000";

// Helpers

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

function renderGapsHTML(gaps) {
  if (gaps.length === 0) {
    return "<p><em>No gaps—user is eligible!</em></p>";
  }
  
  const gapsList = gaps.map((gap, idx) => {
    const priority = gap.distance > 0.7 ? "🔴 HIGH" : gap.distance > 0.4 ? "🟡 MEDIUM" : "🟢 LOW";
    return `
      <div style="margin: 10px 0; padding: 10px; border-left: 3px solid #ccc;">
        <strong>${priority} Priority</strong>
        <p><strong>Issue:</strong> ${gap.description}</p>
        <p><strong>Current:</strong> ${gap.actual}</p>
        <p><strong>Required:</strong> ${gap.required} (${gap.operator})</p>
        <p style="color: #555;"><strong>💡 Suggestion:</strong> ${gap.suggestion}</p>
      </div>
    `;
  }).join("");
  
  return gapsList;
}

function renderWhatIfScenarios(scenarios) {
  if (scenarios.length === 0) {
    return "<p><em>No schemes affected by this change.</em></p>";
  }
  
  const scenarios_html = scenarios.map(scenario => {
    const beforeBadge = scenario.before.eligible ? "✅" : scenario.before.status === "partially eligible" ? "⚠️" : "❌";
    const afterBadge = scenario.after.eligible ? "✅" : scenario.after.status === "partially eligible" ? "⚠️" : "❌";
    
    return `
      <div style="margin: 15px 0; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
        <h4>${scenario.scheme_name}</h4>
        <p>
          <strong>Before:</strong> ${beforeBadge} ${scenario.before.status}
          <br>
          <strong>After:</strong> ${afterBadge} ${scenario.after.status}
        </p>
        ${scenario.improvements.length > 0 ? `
          <p style="color: #28a745;">
            ${scenario.improvements.join("<br>")}
          </p>
        ` : ""}
      </div>
    `;
  }).join("");
  
  return scenarios_html;
}

function renderCounterfactuals(counterfactuals) {
  if (!counterfactuals.scenarios || counterfactuals.scenarios.length === 0) {
    return "<p><em>You are already eligible!</em></p>";
  }

  const scenariosHtml = counterfactuals.scenarios.map((scenario) => {
    const chevron = scenario.feasibility_score >= 0.7 ? "📈" : scenario.feasibility_score >= 0.4 ? "→" : "📉";
    return `
      <div style="margin: 12px 0; padding: 12px; border-left: 4px solid #007bff; background: #f8f9fa;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <strong>${scenario.field}</strong>
          <span style="font-weight: bold; color: ${scenario.feasibility_score >= 0.7 ? '#28a745' : scenario.feasibility_score >= 0.4 ? '#ffc107' : '#dc3545'};">
            ${scenario.feasibility_label}
          </span>
        </div>
        <p style="margin: 8px 0 4px 0; font-size: 0.95em;">
          <strong>Current:</strong> ${
            typeof scenario.current_value === "boolean"
              ? (scenario.current_value ? "Yes" : "No")
              : (typeof scenario.current_value === "number" ? scenario.current_value.toLocaleString() : scenario.current_value || "N/A")
          }
        </p>
        <p style="margin: 4px 0 4px 0; font-size: 0.95em;">
          <strong>Target:</strong> ${
            typeof scenario.suggested_value === "boolean"
              ? (scenario.suggested_value ? "Yes" : "No")
              : (typeof scenario.suggested_value === "number" ? scenario.suggested_value.toLocaleString() : scenario.suggested_value || "N/A")
          }
        </p>
        <p style="margin: 8px 0 0 0; color: #555; font-style: italic;">
          💡 ${scenario.rationale}
        </p>
      </div>
    `;
  }).join("");

  return `
    <div style="background: #f0f7ff; padding: 15px; border-radius: 4px; border: 1px solid #b3d9ff;">
      <h4>🎯 Path to Eligibility</h4>
      <p style="color: #555; margin: 10px 0;">
        ${counterfactuals.summary}
      </p>
      ${scenariosHtml}
      ${counterfactuals.multiple_paths ? `
        <p style="margin-top: 15px; font-size: 0.9em; color: #666;">
          ℹ️ Multiple improvement paths available. Start with the <strong>most feasible</strong> option.
        </p>
      ` : ""}
    </div>
  `;
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

    ${!data.eligible ? `<details>
      <summary>💭 How to become eligible? (Click to expand)</summary>
      <div id="counterfactuals-${data.scheme_id}">
        <p><em>Loading improvement scenarios...</em></p>
      </div>
    </details>` : ""}

    ${!data.eligible ? `<details>
      <summary>🔍 What are the specific gaps? (Click to expand)</summary>
      <div id="gap-analysis-${data.scheme_id}">
        <p><em>Loading gap analysis...</em></p>
      </div>
    </details>` : ""}

    <h3>What-If Analysis</h3>
    <p><em>Explore scenarios below:</em></p>
    <div id="what-if-buttons" style="margin: 10px 0;">
      <!-- Will be populated dynamically -->
    </div>

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

    // Load counterfactuals if not eligible
    if (!data.eligible) {
      try {
        const cfData = await postRequest("/counterfactuals", {
          scheme_id: data.scheme_id,
          profile
        });
        const cfHTML = renderCounterfactuals(cfData);
        const cfContainer = document.getElementById(`counterfactuals-${data.scheme_id}`);
        if (cfContainer) {
          cfContainer.innerHTML = cfHTML;
        }
      } catch (err) {
        console.error("Counterfactuals error:", err);
      }

      // Load gap analysis if not eligible
      try {
        const gapData = await postRequest("/gap-analysis", {
          scheme_id: data.scheme_id,
          profile
        });
        const gapHTML = renderGapsHTML(gapData.gaps);
        const gapContainer = document.getElementById(`gap-analysis-${data.scheme_id}`);
        if (gapContainer) {
          gapContainer.innerHTML = gapHTML;
        }
      } catch (err) {
        console.error("Gap analysis error:", err);
      }
    }

    // Populate what-if buttons
    setupWhatIfButtons(profile);

  } catch (err) {
    updateUI(`<p>Error: ${err.message}</p>`);
  }
}

function createWhatIfButtons(profile) {
  const suggestions = [
    { label: "What if income was lower?", modifications: { income: Math.floor(profile.income * 0.7) } },
    { label: "What if I didn't own a house?", modifications: { owns_house: false } },
    { label: "What if I didn't own LPG?", modifications: { owns_lpg: false } },
    { label: "What if I had health insurance?", modifications: { has_health_insurance: true } },
  ];

  return suggestions.map((s, idx) => `
    <button type="button" class="what-if-btn" data-modifications='${encodeURIComponent(JSON.stringify(s.modifications))}'>
      ${s.label}
    </button>
  `).join("");
}

function setupWhatIfButtons(profile) {
  const whatIfContainer = document.getElementById("what-if-buttons");
  if (!whatIfContainer) return;

  whatIfContainer.innerHTML = createWhatIfButtons(profile);

  whatIfContainer.querySelectorAll(".what-if-btn").forEach(button => {
    button.addEventListener("click", async () => {
      const modifications = JSON.parse(decodeURIComponent(button.dataset.modifications));
      await handleWhatIf(profile, modifications);
    });
  });
}

async function handleWhatIf(profile, modifications) {
  try {
    updateUI("<p>Calculating what-if scenario...</p>");
    
    const data = await postRequest("/what-if", {
      profile,
      modifications
    });

    const modStr = Object.entries(modifications)
      .map(([k, v]) => `${k}=${v}`)
      .join(", ");

    const html = `
      <h2>What-If Analysis</h2>
      <p><strong>Scenario:</strong> If ${modStr}</p>
      <h3>Schemes Affected</h3>
      ${renderWhatIfScenarios(data.scenarios)}
      <button onclick="location.reload()">Back to main evaluation</button>
    `;
    updateUI(html);
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