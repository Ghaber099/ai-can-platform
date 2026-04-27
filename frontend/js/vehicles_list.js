function getVehicles() {
  return JSON.parse(localStorage.getItem("vehicles") || "{}");
}

function openVehicleDetail(vehicleKey) {
  window.open(
    `vehicle_detail.html?vehicle=${encodeURIComponent(vehicleKey)}`,
    "_blank",
    "width=1200,height=850"
  );
}

function renderAllVehicles() {
  const vehicles = getVehicles();
  const tableBody = document.getElementById("vehicleList");
  const search = document.getElementById("vehicleSearchBox").value.toLowerCase().trim();

  const vehicleArray = Object.values(vehicles);

  tableBody.innerHTML = "";

  if (vehicleArray.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="8">No vehicles saved yet.</td>
      </tr>
    `;
    return;
  }

  const filtered = vehicleArray.filter(v => {
    return (
      String(v.vin || "").toLowerCase().includes(search) ||
      String(v.plate || "").toLowerCase().includes(search) ||
      String(v.make || "").toLowerCase().includes(search) ||
      String(v.model || "").toLowerCase().includes(search) ||
      String(v.year || "").toLowerCase().includes(search)
    );
  });

  if (filtered.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="8">No matching vehicles found.</td>
      </tr>
    `;
    return;
  }

  filtered.forEach(vehicle => {
    const key = vehicle.vin || vehicle.plate;

    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${vehicle.make || "-"}</td>
      <td>${vehicle.model || "-"}</td>
      <td>${vehicle.year || "-"}</td>
      <td>${vehicle.color || "-"}</td>
      <td>${vehicle.vin || "-"}</td>
      <td>${vehicle.plate || "-"}</td>
      <td>${vehicle.ecu || "-"}</td>
      <td>
        <button class="primary-btn" onclick="openVehicleDetail('${key}')">
          Open
        </button>
      </td>
    `;

    tableBody.appendChild(row);
  });
}

document.addEventListener("DOMContentLoaded", renderAllVehicles);