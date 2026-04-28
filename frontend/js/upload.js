async function uploadFile() {
  const fileInput = document.getElementById("fileInput");
  const status = document.getElementById("status");

  if (!fileInput || !fileInput.files.length) {
    alert("Please choose a CAN log file first.");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    status.innerText = "Uploading CAN log...";

    const res = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData
    });

    const result = await res.json();

    if (!res.ok || result.error) {
      throw new Error(result.error || "Upload failed");
    }

    window.uploadedFilename = result.filename;
    status.innerText = "Uploaded: " + result.filename;

    await loadCanIds(result.filename);

  } catch (error) {
    status.innerText = "Error: " + error.message;
  }
}

async function loadCanIds(filename) {
  try {
    const res = await fetch(`${API_BASE}/can-ids/${encodeURIComponent(filename)}`);
    const data = await res.json();

    const canIds = data.can_ids || data.canIds || [];

    document.getElementById("statCanIds").innerText = canIds.length;

    if (typeof renderCanIdCheckList === "function") {
      renderCanIdCheckList(canIds);
    }

    const canSelect = document.getElementById("canSelect");
    if (canSelect) {
      canSelect.innerHTML = "";

      if (!canIds.length) {
        canSelect.innerHTML = `<option value="">No CAN IDs found</option>`;
      } else {
        canIds.forEach(id => {
          const option = document.createElement("option");
          option.value = id;
          option.textContent = id;
          canSelect.appendChild(option);
        });
      }
    }

  } catch (error) {
    console.error("CAN ID load error:", error);
  }
}