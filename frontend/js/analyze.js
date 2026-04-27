async function loadReport() {
  if (!currentFilename) {
    alert("Please upload a CAN log first");
    return;
  }

  const canId = document.getElementById("canSelect").value;
  const dbc = document.getElementById("dbcSelect").value;

  if (!canId) {
    alert("Please select a CAN ID");
    return;
  }

  try {
    document.getElementById("reportBox").innerText = "Running analysis...";

    const dbcQuery = dbc ? `?dbc=${encodeURIComponent(dbc)}` : "";

    const reportTextRes = await fetch(
      `${API_BASE}/report-text/${encodeURIComponent(currentFilename)}/${encodeURIComponent(canId)}`
    );

    const reportText = await reportTextRes.text();

    const reportJsonRes = await fetch(
      `${API_BASE}/report/${encodeURIComponent(currentFilename)}/${encodeURIComponent(canId)}${dbcQuery}`
    );

    const reportJson = await reportJsonRes.json();

    if (!reportJsonRes.ok || reportJson.error) {
      throw new Error(reportJson.error || "Analysis failed");
    }

    showReport(reportText, reportJson);
    updateStats(reportJson);
    updateBestSignal(reportJson);
    await loadSignalFrames(canId, reportJson);

  } catch (error) {
    document.getElementById("reportBox").innerText = "Error: " + error.message;
  }
}


function showReport(reportText, reportJson) {
  let output = reportText;

  if (reportJson.dbc_signals && Object.keys(reportJson.dbc_signals).length > 0) {
    output += "\n\n==============================";
    output += "\nDBC DECODED SIGNALS";
    output += "\n==============================\n";

    Object.entries(reportJson.dbc_signals).forEach(([signalName, values]) => {
      output += `\n${signalName}: ${values.slice(0, 12).join(", ")}`;
    });
  }

  document.getElementById("reportBox").innerText = output;
}


function updateStats(reportJson) {
  document.getElementById("statFrames").innerText = reportJson.total_frames || "--";

  document.getElementById("statBestSignal").innerText =
    reportJson.signal16_report?.[0]?.signal || "--";

  let anomalyCount = 0;

  if (reportJson.signal16_report) {
    reportJson.signal16_report.forEach(signal => {
      anomalyCount += signal.anomalies ? signal.anomalies.length : 0;
    });
  }

  document.getElementById("statAnomalies").innerText = anomalyCount;

  const canSelect = document.getElementById("canSelect");
  document.getElementById("statCanIds").innerText = canSelect.options.length || "--";
}


function updateBestSignal(reportJson) {
  currentBestSignal = null;
  let correlatedSignal = null;

  if (reportJson.signal16_report && reportJson.signal16_report.length > 0) {
    currentBestSignal = reportJson.signal16_report[0].signal;

    if (reportJson.correlations && reportJson.correlations.length > 0) {
      const bestCorrelation = reportJson.correlations
        .filter(correlation => correlation.pair && correlation.pair.includes(currentBestSignal))
        .sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation))[0];

      if (bestCorrelation && Math.abs(bestCorrelation.correlation) > 0.5) {
        const parts = bestCorrelation.pair.split(" ↔ ");
        correlatedSignal = parts[0] === currentBestSignal ? parts[1] : parts[0];
      }
    }

    document.getElementById("bestSignalLabel").innerText =
      "Best Signal: " +
      currentBestSignal +
      (correlatedSignal ? " | Correlated: " + correlatedSignal + " 🔗" : "") +
      " ⭐";
  }

  return correlatedSignal;
}


async function loadSignalFrames(canId, reportJson) {
  const signalResponse = await fetch(
    `${API_BASE}/signal-data/${encodeURIComponent(currentFilename)}/${encodeURIComponent(canId)}`
  );

  const signalData = await signalResponse.json();

  if (!signalResponse.ok || signalData.error) {
    throw new Error(signalData.error || "Signal data failed");
  }

  if (!signalData.frames || signalData.frames.length === 0) {
    allFrames = [];
    renderTable([]);
    drawChartMulti([], currentBestSignal, {});
    return;
  }

  allFrames = signalData.frames;
  renderTable(allFrames);

  const anomalyMap = {};
  if (reportJson.signal16_report) {
    reportJson.signal16_report.forEach(signal => {
      anomalyMap[signal.signal] = signal.anomalies || [];
    });
  }

  const correlatedSignal = updateBestSignal(reportJson);
  const selectedSignals = getSelectedSignals();

  let graphSignals = [];

  if (currentBestSignal) {
    graphSignals.push(currentBestSignal);
  }

  if (correlatedSignal && !graphSignals.includes(correlatedSignal)) {
    graphSignals.push(correlatedSignal);
  }

  selectedSignals.forEach(signal => {
    if (!graphSignals.includes(signal)) {
      graphSignals.push(signal);
    }
  });

  if (graphSignals.length === 0) {
    graphSignals = ["signal_0_1"];
  }

  selectSignalsInDropdown(graphSignals);

  const datasets = graphSignals.map(signal => ({
    name: signal,
    values: allFrames.map(frame => Number(frame[signal] ?? 0))
  }));

  drawChartMulti(datasets, currentBestSignal, anomalyMap);
}


function getSelectedSignals() {
  const selectedOptions = Array.from(document.getElementById("signalSelect").selectedOptions);
  return selectedOptions.map(option => option.value);
}


function selectSignalsInDropdown(signals) {
  const options = document.getElementById("signalSelect").options;

  Array.from(options).forEach(option => {
    option.selected = signals.includes(option.value);
  });
}


function filterTable() {
  const search = document.getElementById("tableSearch").value.toLowerCase().trim();

  if (!search) {
    renderTable(allFrames);
    return;
  }

  const filtered = allFrames.filter(frame => {
    const dataString = Array.isArray(frame.data) ? frame.data.join(" ").toLowerCase() : "";
    const canIdString = String(frame.can_id || "").toLowerCase();
    const timestampString = String(frame.timestamp || "").toLowerCase();

    return (
      dataString.includes(search) ||
      canIdString.includes(search) ||
      timestampString.includes(search)
    );
  });

  renderTable(filtered);
}


function renderTable(frames) {
  const tableBody = document.getElementById("frameTableBody");
  tableBody.innerHTML = "";

  document.getElementById("frameCount").innerText =
    `Showing first ${Math.min(frames.length, 50)} of ${frames.length} frames`;

  frames.slice(0, 50).forEach(frame => {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${frame.frame_index ?? "-"}</td>
      <td>${frame.timestamp ?? "-"}</td>
      <td>${frame.can_id ?? "-"}</td>
      <td>${frame.dlc ?? "-"}</td>
      <td>${formatDataBytes(frame.data || [])}</td>
    `;

    tableBody.appendChild(row);
  });
}


function formatDataBytes(data) {
  if (!Array.isArray(data)) {
    return "";
  }

  return data.map((byte, index) => {
    const isChanging = allFrames.some(frame =>
      Array.isArray(frame.data) && frame.data[index] !== byte
    );

    const changeClass = isChanging ? "byte-changing" : "byte-constant";

    return `<span class="byte byte-${index} ${changeClass}">${byte}</span>`;
  }).join(" ");
}


function downloadReport() {
  const reportText = document.getElementById("reportBox").innerText;

  if (!reportText || reportText.includes("Upload a CAN log")) {
    alert("No report to download");
    return;
  }

  const blob = new Blob([reportText], { type: "text/plain" });
  const link = document.createElement("a");

  link.href = URL.createObjectURL(blob);
  link.download = "can_analysis_report.txt";
  link.click();

  URL.revokeObjectURL(link.href);
}