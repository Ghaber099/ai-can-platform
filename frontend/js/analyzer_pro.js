let selectedCanIds = new Set();
let loadedCanIds = [];
let latestReportText = "";

function renderCanIdCheckList(canIds) {
  loadedCanIds = canIds || [];
  selectedCanIds.clear();

  const box = document.getElementById("canIdCheckList");
  const countBox = document.getElementById("selectedCanCount");

  if (countBox) countBox.innerText = "0";

  if (!box) return;

  if (!loadedCanIds.length) {
    box.innerHTML = "No CAN IDs found.";
    return;
  }

  box.innerHTML = loadedCanIds.map(id => `
    <label>
      <input type="checkbox" value="${id}" onchange="toggleCanId('${id}', this.checked)" />
      ${id}
    </label>
  `).join("");
}

function toggleCanId(id, checked) {
  if (checked) {
    selectedCanIds.add(id);
  } else {
    selectedCanIds.delete(id);
  }

  const countBox = document.getElementById("selectedCanCount");
  if (countBox) countBox.innerText = selectedCanIds.size;
}

function selectAllCanIds() {
  selectedCanIds = new Set(loadedCanIds);

  document.querySelectorAll("#canIdCheckList input").forEach(input => {
    input.checked = true;
  });

  document.getElementById("selectedCanCount").innerText = selectedCanIds.size;
}

function clearAllCanIds() {
  selectedCanIds.clear();

  document.querySelectorAll("#canIdCheckList input").forEach(input => {
    input.checked = false;
  });

  document.getElementById("selectedCanCount").innerText = "0";
}

function selectAllBytes() {
  document.querySelectorAll("#byteCheckList input").forEach(input => {
    input.checked = true;
  });
}

function clearAllBytes() {
  document.querySelectorAll("#byteCheckList input").forEach(input => {
    input.checked = false;
  });
}

function selectAllPairs() {
  document.querySelectorAll("#pairCheckList input").forEach(input => {
    input.checked = true;
  });
}

function clearAllPairs() {
  document.querySelectorAll("#pairCheckList input").forEach(input => {
    input.checked = false;
  });
}

function getCheckedValues(selector) {
  return Array.from(document.querySelectorAll(`${selector} input:checked`))
    .map(input => input.value);
}

async function runSelectedAnalyzer() {
  const filename = window.uploadedFilename;

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

  let fullReport = "";
  let allDatasets = [];

  for (const canId of ids) {
    fullReport += `\n====================================\n`;
    fullReport += `CAN ID: ${canId}\n`;
    fullReport += `Selected Signals: ${signals.join(", ")}\n`;
    fullReport += `====================================\n\n`;

    try {
      const reportRes = await fetch(
        `${API_BASE}/report-text/${encodeURIComponent(filename)}/${encodeURIComponent(canId)}`
      );

      const reportText = await reportRes.text();
      fullReport += reportText + "\n\n";

      const signalRes = await fetch(
        `${API_BASE}/signal-data/${encodeURIComponent(filename)}/${encodeURIComponent(canId)}`
      );

      const signalData = await signalRes.json();
      const frames = signalData.frames || signalData.data || [];

      signals.forEach(signalName => {
        const values = frames
          .map(frame => frame[signalName])
          .filter(v => v !== undefined && v !== null);

        if (values.length) {
          allDatasets.push({
            name: `${canId} ${signalName}`,
            values
          });
        }
      });

    } catch (error) {
      fullReport += `Error analyzing ${canId}: ${error.message}\n\n`;
    }
  }

  latestReportText = fullReport.trim();

  document.getElementById("reportBox").innerText =
    latestReportText || "No report generated.";

  updateAnalyzerStats(ids, allDatasets, latestReportText);

  if (typeof drawChartMulti === "function") {
    drawChartMulti(allDatasets, allDatasets[0]?.name || null);
  }
}

function updateAnalyzerStats(ids, datasets, report) {
  document.getElementById("statCanIds").innerText = loadedCanIds.length || "--";
  document.getElementById("selectedCanCount").innerText = ids.length;

  const frameCount = datasets[0]?.values?.length || "--";
  document.getElementById("statFrames").innerText = frameCount;

  const anomalyCount = (report.match(/anomal/gi) || []).length;
  document.getElementById("statAnomalies").innerText = anomalyCount || "0";
}

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

function filterTable() {
  const input = document.getElementById("tableSearch");
  const query = input.value.toLowerCase();

  document.querySelectorAll("#frameTableBody tr").forEach(row => {
    row.style.display = row.innerText.toLowerCase().includes(query)
      ? ""
      : "none";
  });
}