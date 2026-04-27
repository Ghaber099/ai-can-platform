async function uploadDbcFile() {
  const input = document.getElementById("dbcFileInput");
  const file = input.files[0];

  if (!file) {
    alert("Please select a DBC file");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  const status = document.getElementById("dbcStatus");

  try {
    status.innerText = "Uploading DBC...";

    const response = await fetch(`${API_BASE}/dbc/upload`, {
      method: "POST",
      body: formData
    });

    const result = await response.json();

    if (!response.ok || result.error) {
      throw new Error(result.error || "DBC upload failed");
    }

    status.innerText = "DBC uploaded: " + result.filename;

    await loadDbcFiles();

  } catch (error) {
    status.innerText = "DBC Error: " + error.message;
  }
}


async function loadDbcFiles() {
  const select = document.getElementById("dbcSelect");

  try {
    const res = await fetch(`${API_BASE}/dbc/list`);
    const data = await res.json();

    select.innerHTML = `<option value="">No DBC (AI only)</option>`;

    if (!data.dbc_files || data.dbc_files.length === 0) {
      return;
    }

    data.dbc_files.forEach(file => {
      const option = document.createElement("option");
      option.value = file;
      option.textContent = file;
      select.appendChild(option);
    });

  } catch (error) {
    console.error("DBC list error:", error);
  }
}