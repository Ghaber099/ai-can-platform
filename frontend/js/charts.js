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

    chartDatasets.push({
      label: ds.name + (isBest ? " ⭐ BEST" : ""),
      data: ds.values,
      borderWidth: isBest ? 4 : 2,
      fill: false,
      tension: 0.25
    });

    const anomalyIndexes = anomalyMap[ds.name] || [];

    if (anomalyIndexes.length > 0) {
      chartDatasets.push({
        label: ds.name + " ⚠ anomalies",
        data: ds.values.map((value, index) =>
          anomalyIndexes.includes(index) ? value : null
        ),
        pointRadius: 7,
        pointHoverRadius: 9,
        showLine: false
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
      plugins: {
        legend: {
          display: true,
          labels: {
            color: "#dbeafe"
          }
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
        y: {
          ticks: {
            color: "#8da2bf"
          },
          grid: {
            color: "rgba(148, 163, 184, 0.12)"
          },
          title: {
            display: true,
            text: "Signal Values",
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