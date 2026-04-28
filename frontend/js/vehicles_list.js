async function renderAllVehicles() {
  const search = document.getElementById("vehicleSearchBox").value.trim();

  try {
    const res = await fetch(
      `http://127.0.0.1:8000/vehicles/search?q=${encodeURIComponent(search)}`
    );

    const data = await res.json();
    const tableBody = document.getElementById("vehicleList");

    tableBody.innerHTML = "";

    if (!data.vehicles || data.vehicles.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="8">No vehicles found.</td>
        </tr>
      `;
      return;
    }

    data.vehicles.forEach(vehicle => {
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
          <button class="primary-btn" onclick="openVehicleDetail(${vehicle.id})">
            Open
          </button>
        </td>
      `;

      tableBody.appendChild(row);
    });

  } catch (error) {
    console.error(error);
  }
}

function openVehicleDetail(vehicleId) {
  window.open(
    `vehicle_detail.html?vehicle=${encodeURIComponent(vehicleId)}`,
    "_blank",
    "width=1200,height=850"
  );
}

document.addEventListener("DOMContentLoaded", renderAllVehicles);