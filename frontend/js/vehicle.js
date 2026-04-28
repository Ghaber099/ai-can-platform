const API_BASE = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const customerLicense = params.get("customer");

  if (customerLicense) {
    const input = document.getElementById("ownerLicense");

    if (input) {
      input.value = customerLicense;
      input.readOnly = true;
    }
  }
});

async function saveVehicle() {
  const vehicle = {
    ownerLicense: document.getElementById("ownerLicense").value.trim(),
    vin: document.getElementById("vin").value.trim(),
    plate: document.getElementById("plate").value.trim(),
    make: document.getElementById("make").value.trim(),
    model: document.getElementById("model").value.trim(),
    year: document.getElementById("year").value.trim(),
    color: document.getElementById("color").value.trim(),
    ecu: document.getElementById("ecu").value.trim(),
    engine: document.getElementById("engine").value.trim(),
    notes: document.getElementById("vehicleNotes").value.trim()
  };

  if (!vehicle.vin && !vehicle.plate) {
    alert("VIN or Plate Number required");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/vehicle/save`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(vehicle)
    });

    const result = await res.json();

    if (!res.ok || result.error) {
      throw new Error(result.error || "Save failed");
    }

    if (vehicle.ownerLicense) {
      const linkRes = await fetch(`${API_BASE}/customer-vehicle/link`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          customer_license: vehicle.ownerLicense,
          vehicle_id: result.vehicle_id,
          relationship_type: "owner"
        })
      });

      const linkResult = await linkRes.json();

      if (!linkRes.ok || linkResult.error) {
        throw new Error(linkResult.error || "Vehicle saved but customer link failed");
      }
    }

    document.getElementById("vehicleStatus").innerText =
      "Vehicle saved and linked successfully. ID: " + result.vehicle_id;

  } catch (error) {
    document.getElementById("vehicleStatus").innerText =
      "Error: " + error.message;
  }
}

async function findVehicle() {
  const query = document.getElementById("searchVin").value.trim();

  if (!query) {
    alert("Enter VIN, plate, make, model, or year");
    return;
  }

  try {
    const res = await fetch(
      `${API_BASE}/vehicles/search?q=${encodeURIComponent(query)}`
    );

    const data = await res.json();
    const box = document.getElementById("vehicleSearchResult");

    if (!data.vehicles || data.vehicles.length === 0) {
      box.innerHTML = "Vehicle not found.";
      return;
    }

    const vehicle = data.vehicles[0];

    box.innerHTML = `
      <div class="vehicle-result-card" onclick="openVehicleDetail('${vehicle.id}')">
        <h3>${vehicle.make || "Unknown"} ${vehicle.model || ""}</h3>
        <p>Year: ${vehicle.year || "-"}</p>
        <p>VIN: ${vehicle.vin || "-"}</p>
        <p>Plate: ${vehicle.plate || "-"}</p>
        <small>Click to open full history</small>
      </div>
    `;

  } catch (error) {
    document.getElementById("vehicleSearchResult").innerText =
      "Error: " + error.message;
  }
}

function openVehicleDetail(vehicleId) {
  window.open(
    `vehicle_detail.html?vehicle=${encodeURIComponent(vehicleId)}`,
    "_blank",
    "width=1200,height=850"
  );
}

function openAllVehicles() {
  window.open("vehicles_list.html", "_blank", "width=1200,height=850");
}