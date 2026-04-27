async function uploadFile() {
  const fileInput = document.getElementById("fileInput");
  const file = fileInput.files[0];

  if (!file) {
    alert("Please select a CAN log file");
    return;
  }

  const make = document.getElementById("make").value || "Unknown";
  const model = document.getElementById("model").value || "Unknown";
  const year = document.getElementById("year").value || "Unknown";
  const color = document.getElementById("color").value || "Unknown";

  const formData = new FormData();
  formData.append("file", file);
  formData.append("make", make);
  formData.append("model", model);
  formData.append("year", year);
  formData.append("color", color);

  const status = document.getElementById("status");

  resetUI();

  try {
    status.innerText = "Uploading CAN log...";

    const response = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData
    });

    const result = await response.json();

    if (!response.ok || result.error) {
      throw new Error(result.error || "Upload failed");
    }

    currentFilename = result.filename;

    status.innerText = "Uploaded: " + currentFilename;

    document.getElementById("vehicleInfo").innerText =
      `Vehicle: ${make} ${model} (${year}) - ${color}`;

    await loadCanIds(currentFilename);
    await loadDbcFiles();

  } catch (error) {
    status.innerText = "Error: " + error.message;
    document.getElementById("reportBox").innerText = "Upload Error: " + error.message;
  }
}


function resetUI() {
  currentFilename = "";
  allFrames = [];
  currentBestSignal = null;

  document.getElementById("reportBox").innerText = "";
  document.getElementById("frameTableBody").innerHTML = "";
  document.getElementById("frameCount").innerText = "No frames loaded";
  document.getElementById("bestSignalLabel").innerText = "Best Signal: --";

  const canSelect = document.getElementById("canSelect");
  canSelect.innerHTML = `<option value="">Upload CAN log first</option>`;
}


async function loadCanIds(filename) {
  const select = document.getElementById("canSelect");

  try {
    const response = await fetch(`${API_BASE}/can-ids/${filename}`);
    const data = await response.json();

    select.innerHTML = "";

    if (!data.can_ids || data.can_ids.length === 0) {
      select.innerHTML = `<option value="">No CAN IDs found</option>`;
      return;
    }

    data.can_ids.forEach(id => {
      const option = document.createElement("option");
      option.value = id;
      option.textContent = id;
      select.appendChild(option);
    });

  } catch (error) {
    select.innerHTML = `<option value="">Error loading CAN IDs</option>`;
    console.error(error);
  }
}