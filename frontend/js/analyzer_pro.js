let selectedCanIds = new Set();
let loadedCanIds = [];
let latestReportText = "";
let tableFrames = [];
let latestDatasets = [];
let currentSelectedSignal = "";

function safeText(id, value) {
  const el = document.getElementById(id);
  if (el) el.innerText = value;
}

function safeHTML(id, value) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = value;
}

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function getCheckedValues(selector) {
  return Array.from(document.querySelectorAll(`${selector} input:checked`))
    .map(input => input.value);
}

/* =========================
   CAN ID FILTERS
========================= */

function renderCanIdCheckList(canIds) {
  loadedCanIds = canIds || [];
  selectedCanIds.clear();

  safeText("selectedCanCount", "0");
  safeText("statCanIds", loadedCanIds.length || "--");

  const box = document.getElementById("canIdCheckList");
  if (!box) return;

  if (!loadedCanIds.length) {
    box.innerHTML = `<div class="empty-state">No CAN IDs found.</div>`;
    return;
  }

  box.innerHTML = loadedCanIds.map(id => `
    <label>
      <input type="checkbox" value="${escapeHTML(id)}" onchange="toggleCanId('${escapeHTML(id)}', this.checked)" />
      <span>${escapeHTML(id)}</span>
    </label>
  `).join("");
}

function toggleCanId(id, checked) {
  checked ? selectedCanIds.add(id) : selectedCanIds.delete(id);
  safeText("selectedCanCount", selectedCanIds.size);
}

function selectAllCanIds() {
  selectedCanIds = new Set(loadedCanIds);
  document.querySelectorAll("#canIdCheckList input").forEach(input => input.checked = true);
  safeText("selectedCanCount", selectedCanIds.size);
}

function clearAllCanIds() {
  selectedCanIds.clear();
  document.querySelectorAll("#canIdCheckList input").forEach(input => input.checked = false);
  safeText("selectedCanCount", "0");
}

function selectAllBytes() {
  document.querySelectorAll("#byteCheckList input").forEach(input => input.checked = true);
}

function clearAllBytes() {
  document.querySelectorAll("#byteCheckList input").forEach(input => input.checked = false);
}

function selectAllPairs() {
  document.querySelectorAll("#pairCheckList input").forEach(input => input.checked = true);
}

function clearAllPairs() {
  document.querySelectorAll("#pairCheckList input").forEach(input => input.checked = false);
}

/* =========================
   SIGNAL VALUES
========================= */

function getSignalValue(frame, signalName) {
  if (frame[signalName] !== undefined && frame[signalName] !== null) {
    return Number(frame[signalName]);
  }

  const data = Array.isArray(frame.data)
    ? frame.data.map(byte => parseInt(byte, 16))
    : [];

  if (signalName.startsWith("byte_")) {
    const index = Number(signalName.replace("byte_", ""));
    return data[index];
  }

  if (signalName === "signal_0_1") return ((data[0] || 0) << 8) + (data[1] || 0);
  if (signalName === "signal_2_3") return ((data[2] || 0) << 8) + (data[3] || 0);
  if (signalName === "signal_4_5") return ((data[4] || 0) << 8) + (data[5] || 0);
  if (signalName === "signal_6_7") return ((data[6] || 0) << 8) + (data[7] || 0);

  return null;
}

function buildDatasets(frames, canId, signals) {
  const datasets = [];

  signals.forEach(signalName => {
    const values = frames
      .map(frame => getSignalValue(frame, signalName))
      .filter(v => v !== undefined && v !== null && !Number.isNaN(v));

    if (values.length) {
      datasets.push({
        name: `${canId} ${signalName}`,
        signalName,
        canId,
        values
      });
    }
  });

  return datasets;
}

function populateSignalSelect(datasets) {
  const select = document.getElementById("signalSelect");
  if (!select) return;

  select.innerHTML = `<option value="">Auto select signal</option>`;

  datasets.forEach((ds, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = ds.name;
    select.appendChild(option);
  });
}

function redrawSelectedSignal() {
  const select = document.getElementById("signalSelect");

  if (!select || !latestDatasets.length) {
    return;
  }

  const index = select.value;

  if (index === "") {
    drawSignalDatasets(latestDatasets);
    return;
  }

  const ds = latestDatasets[Number(index)];
  if (!ds) return;

  drawSignalDatasets([ds]);
  safeText("bestSignalLabel", `Selected: ${ds.name}`);
}

function drawSignalDatasets(datasets) {
  if (typeof drawChartMulti === "function") {
    drawChartMulti(
      datasets.map(ds => ({ name: ds.name, values: ds.values })),
      datasets[0]?.name || null,
      {}
    );
  }

  safeText("bestSignalLabel", datasets[0]?.name ? `Signal: ${datasets[0].name}` : "No signal selected");
}

/* =========================
   REPORT PARSING FOR UI
========================= */

function extractValue(report, regex, fallback = "--") {
  const match = report.match(regex);
  return match ? match[1].trim() : fallback;
}

function detectSecurityStatus(report) {
  const text = report.toLowerCase();

  if (
    text.includes("attack simulation") ||
    text.includes("possible attack") ||
    text.includes("integrity anomalies") ||
    text.includes("checksum fail")
  ) {
    return {
      level: "CRITICAL",
      detail: "Possible CAN injection / integrity violation detected.",
      className: "critical"
    };
  }

  if (
    text.includes("counter anomalies") ||
    text.includes("checksum") ||
    text.includes("validation byte")
  ) {
    return {
      level: "MONITORED",
      detail: "Integrity fields detected. No critical attack confirmed.",
      className: "warning"
    };
  }

  return {
    level: "SAFE",
    detail: "No major security issue detected.",
    className: "safe"
  };
}

function updateSecurityUI(report) {
  const status = detectSecurityStatus(report);

  safeText("securityStatus", status.level);
  safeText("securityDetail", status.detail);

  const card = document.getElementById("securityCard");
  if (card) {
    card.classList.remove("safe", "warning", "critical");
    card.classList.add(status.className);
  }

  const banner = document.getElementById("alertBanner");
  if (banner) {
    if (status.level === "CRITICAL") {
      banner.classList.remove("hidden");
      banner.innerText = "🚨 Possible CAN Injection / Integrity Violation Detected";
    } else {
      banner.classList.add("hidden");
    }
  }

  safeHTML("securityPanel", `
    <div class="status-pill ${status.className}">${status.level}</div>
    <p>${escapeHTML(status.detail)}</p>
    <ul>
      <li>Attack keywords: ${report.toLowerCase().includes("attack") ? "Detected" : "Not detected"}</li>
      <li>Checksum: ${report.toLowerCase().includes("checksum") ? "Detected" : "Not detected"}</li>
      <li>Counter anomalies: ${report.toLowerCase().includes("counter anomalies") ? "Checked" : "Not reported"}</li>
    </ul>
  `);
}

function updateIntelligenceUI(report) {
  const messageType = extractValue(report, /Message Type:\s*(.+)/i);
  const frameIntel = extractValue(report, /Overall Frame Intelligence:\s*(.+)/i);
  const temporalReliability = extractValue(report, /Temporal reliability:\s*(.+)/i);

  safeText("messageTypeCard", messageType);
  safeText("frameIntelCard", frameIntel);
  safeText("temporalReliabilityCard", temporalReliability);

  const frameMeaning = extractValue(report, /Frame Meaning:\s*(.+)/i, "Not available");
  const primary = extractValue(report, /Primary Signal:\s*\n\s*(.+)/i, "Not available");
  const secondary = extractValue(report, /Secondary Signal:\s*\n\s*(.+)/i, "Not available");

  safeHTML("frameIntelPanel", `
    <div class="mini-kv"><span>Message Type</span><strong>${escapeHTML(messageType)}</strong></div>
    <div class="mini-kv"><span>Frame Meaning</span><strong>${escapeHTML(frameMeaning)}</strong></div>
    <div class="mini-kv"><span>Primary</span><strong>${escapeHTML(primary)}</strong></div>
    <div class="mini-kv"><span>Secondary</span><strong>${escapeHTML(secondary)}</strong></div>
  `);
}

function extractSection(report, title) {
  const escapedTitle = title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`${escapedTitle}\\n[-]+\\n([\\s\\S]*?)(\\n\\n[A-Z /]+\\n[-]+|$)`, "i");
  const match = report.match(regex);
  return match ? match[1].trim() : "";
}

function updateSmartPanels(report) {
  const temporal = extractSection(report, "TEMPORAL BEHAVIOR INTELLIGENCE");
  const correlation = extractSection(report, "SIGNAL CORRELATION ANALYSIS");
  const attack = extractSection(report, "ATTACK / VALIDATION ANALYSIS");

  safeHTML("temporalPanel", temporal
    ? `<pre>${escapeHTML(temporal)}</pre>`
    : "No temporal intelligence available."
  );

  safeHTML("correlationPanel", correlation
    ? `<pre>${escapeHTML(correlation)}</pre>`
    : "No correlation intelligence available."
  );

  if (attack) {
    safeHTML("securityPanel", `
      ${document.getElementById("securityPanel")?.innerHTML || ""}
      <hr />
      <pre>${escapeHTML(attack)}</pre>
    `);
  }
}

function updateAnalyzerStats(ids, datasets, report) {
  safeText("statCanIds", loadedCanIds.length || "--");
  safeText("selectedCanCount", ids.length);
  safeText("statFrames", tableFrames.length || "--");

  const anomalyCount = (report.match(/anomal|attack|fail|suspicious/gi) || []).length;
  safeText("statAnomalies", anomalyCount || "0");

  updateSecurityUI(report);
  updateIntelligenceUI(report);
  updateSmartPanels(report);
}

/* =========================
   MAIN ANALYSIS
========================= */

async function runSelectedAnalyzer() {
  const filename = window.uploadedFilename;

  tableFrames = [];
  latestDatasets = [];

  if (!filename) {
    alert("Upload CAN log first.");
    return;
  }

  const ids = Array.from(selectedCanIds);

  if (!ids.length) {
    alert("Select at least one CAN ID.");
    return;
  }

  const signals = [
    ...getCheckedValues("#byteCheckList"),
    ...getCheckedValues("#pairCheckList")
  ];

  if (!signals.length) {
    alert("Select at least one byte or byte pair.");
    return;
  }

  safeText("reportBox", "Running AI CAN analysis...");
  safeText("frameCount", "Loading frames...");

  let fullReport = "";

  for (const canId of ids) {
    fullReport += `\n====================================\n`;
    fullReport += `CAN ID: ${canId}\n`;
    fullReport += `Selected Signals: ${signals.join(", ")}\n`;
    fullReport += `====================================\n\n`;

    try {
      const dbc = document.getElementById("dbcSelect")?.value || "";
      const reportUrl =
        `${API_BASE}/report-text/${encodeURIComponent(filename)}/${encodeURIComponent(canId)}${dbc ? `?dbc=${encodeURIComponent(dbc)}` : ""}`;

      const reportRes = await fetch(reportUrl);
      const reportText = await reportRes.text();

      fullReport += reportText + "\n\n";

      const signalRes = await fetch(
        `${API_BASE}/signal-data/${encodeURIComponent(filename)}/${encodeURIComponent(canId)}`
      );

      const signalData = await signalRes.json();

      const frames = Array.isArray(signalData.frames)
        ? signalData.frames
        : Array.isArray(signalData.data)
          ? signalData.data
          : [];

      tableFrames = tableFrames.concat(frames);
      latestDatasets = latestDatasets.concat(buildDatasets(frames, canId, signals));

    } catch (error) {
      fullReport += `Error analyzing ${canId}: ${error.message}\n\n`;
    }
  }

  latestReportText = fullReport.trim();

  safeText("reportBox", latestReportText || "No report generated.");

  renderFrameTable(tableFrames);
  populateSignalSelect(latestDatasets);
  updateAnalyzerStats(ids, latestDatasets, latestReportText);

  if (latestDatasets.length) {
    drawSignalDatasets(latestDatasets.slice(0, 4));
  }
}

/* =========================
   FRAME TABLE
========================= */

function filterTable() {
  const input = document.getElementById("tableSearch");
  const query = (input?.value || "").toLowerCase();

  document.querySelectorAll("#frameTableBody tr").forEach(row => {
    row.style.display = row.innerText.toLowerCase().includes(query) ? "" : "none";
  });
}

function renderFrameTable(frames) {
  const tableBody = document.getElementById("frameTableBody");
  const frameCount = document.getElementById("frameCount");

  if (!tableBody) return;

  tableBody.innerHTML = "";

  if (!frames || frames.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="7">No frames found</td></tr>`;
    if (frameCount) frameCount.innerText = "No frames loaded";
    return;
  }

  if (frameCount) {
    frameCount.innerText = `Showing first ${Math.min(frames.length, 150)} of ${frames.length} frames`;
  }

  frames.slice(0, 150).forEach((frame, index) => {
    const row = document.createElement("tr");

    const data = Array.isArray(frame.data)
      ? frame.data.map((b, i) => `<span class="byte byte-${i}">${escapeHTML(b)}</span>`).join(" ")
      : escapeHTML(frame.data || "");

    row.innerHTML = `
      <td>${frame.frame_index ?? frame.line ?? index + 1}</td>
      <td>${frame.timestamp ?? ""}</td>
      <td>${frame.can_id ?? ""}</td>
      <td>${frame.dlc ?? ""}</td>
      <td>${data}</td>
      <td>${frame.signal_0_1 ?? "--"}</td>
      <td>${frame.signal_2_3 ?? "--"}</td>
    `;

    tableBody.appendChild(row);
  });
}

/* =========================
   DOWNLOAD
========================= */

function downloadReport() {
  const report =
    latestReportText ||
    document.getElementById("reportBox")?.innerText ||
    "";

  if (!report.trim() || report.includes("Upload a CAN log")) {
    alert("No report available yet.");
    return;
  }

  const blob = new Blob([report], { type: "text/plain" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = "autoscope_can_analysis_report.txt";
  link.click();

  URL.revokeObjectURL(url);
}

/* =========================
   TAB SUPPORT
========================= */

function switchTab(tab) {
  document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".tabs button").forEach(b => b.classList.remove("active"));

  const panel = document.getElementById(tab);
  if (panel) panel.classList.add("active");

  if (event?.target) event.target.classList.add("active");
}