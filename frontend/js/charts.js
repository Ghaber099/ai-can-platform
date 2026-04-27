function getSignalLabel(name) {
  if (name.startsWith("byte_")) {
    return name + " (1-byte)";
  }

  if (name.startsWith("signal_")) {
    return name.replace("signal_", "bytes_") + " (2-byte)";
  }

  return name;
}

function drawChartMulti(datasets, bestSignal, anomalyMap = {}) {
  const ctx = document.getElementById("signalChart").getContext("2d");

  if (chart) {
    chart.destroy();
  }

  if (!datasets || datasets.length === 0) {
    chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: []
      }
    });
    return;
  }

  const chartDatasets = [];

  datasets.forEach((ds) => {
    const isBest = ds.name === bestSignal;
    const isByte = ds.name.startsWith("byte_");

    chartDatasets.push({
      label: getSignalLabel(ds.name) + (isBest ? " ⭐ BEST" : ""),
      data: ds.values,
      borderWidth: isBest ? 4 : isByte ? 2 : 3,
      fill: false,
      tension: isByte ? 0 : 0.25,
      stepped: isByte,
      pointRadius: isByte ? 3 : 2,
      yAxisID: isByte ? "yByte" : "ySignal"
    });

    const anomalyIndexes = anomalyMap[ds.name] || [];

    if (anomalyIndexes.length > 0) {
      chartDatasets.push({
        label: getSignalLabel(ds.name) + " ⚠ anomalies",
        data: ds.values.map((value, index) =>
          anomalyIndexes.includes(index) ? value : null
        ),
        pointRadius: 7,
        pointHoverRadius: 9,
        showLine: false,
        yAxisID: isByte ? "yByte" : "ySignal"
      });
    }
  });

  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: datasets[0].values.map((_, index) => index),
      datasets: chartDatasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: {
          display: true,
          labels: {
            color: "#dbeafe"
          }
        },
        tooltip: {
          enabled: true
        }
      },
      scales: {
        x: {
          ticks: {
            color: "#8da2bf"
          },
          grid: {
            color: "rgba(148, 163, 184, 0.12)"
          },
          title: {
            display: true,
            text: "Frame Index",
            color: "#8da2bf"
          }
        },
        ySignal: {
          position: "left",
          ticks: {
            color: "#8da2bf"
          },
          grid: {
            color: "rgba(148, 163, 184, 0.12)"
          },
          title: {
            display: true,
            text: "2-Byte Signal Value",
            color: "#8da2bf"
          }
        },
        yByte: {
          position: "right",
          min: 0,
          max: 255,
          ticks: {
            color: "#8da2bf"
          },
          grid: {
            drawOnChartArea: false
          },
          title: {
            display: true,
            text: "1-Byte Value",
            color: "#8da2bf"
          }
        }
      }
    }
  });
}

function downloadChart() {
  if (!chart) {
    alert("No chart to download");
    return;
  }

  const link = document.createElement("a");
  link.href = chart.toBase64Image();
  link.download = "signal_graph.png";
  link.click();
}