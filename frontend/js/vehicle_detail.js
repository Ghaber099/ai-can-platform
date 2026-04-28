const API_BASE = "http://127.0.0.1:8000";

function getQueryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

function getCurrentVehicleId() {
  return getQueryParam("vehicle");
}

async function loadVehicleDetail() {
  const vehicleId = getCurrentVehicleId();

  if (!vehicleId) {
    showVehicleError("Vehicle Not Found", "No vehicle ID found in URL.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/vehicles/search?q=`);
    const data = await res.json();

    const vehicle = (data.vehicles || []).find(
      v => String(v.id) === String(vehicleId)
    );

    if (!vehicle) {
      showVehicleError("Vehicle Not Found", "No vehicle found with ID: " + vehicleId);
      return;
    }

    document.getElementById("vehicleTitle").innerText =
      `${vehicle.make || "Unknown"} ${vehicle.model || ""}`;

    document.getElementById("vehicleSubtitle").innerText =
      `VIN: ${vehicle.vin || "-"} | Plate: ${vehicle.plate || "-"}`;

    renderVehicleInfo(vehicle);

    await loadLinkedCustomers(vehicleId);
    await loadRepairs(vehicleId);

  } catch (error) {
    showVehicleError("Vehicle Error", error.message);
  }
}

function renderVehicleInfo(vehicle) {
  document.getElementById("vehicleInfoBox").innerHTML = `
    <div class="info-item"><span>Make</span><strong>${vehicle.make || "-"}</strong></div>
    <div class="info-item"><span>Model</span><strong>${vehicle.model || "-"}</strong></div>
    <div class="info-item"><span>Year</span><strong>${vehicle.year || "-"}</strong></div>
    <div class="info-item"><span>Color</span><strong>${vehicle.color || "-"}</strong></div>
    <div class="info-item"><span>VIN</span><strong>${vehicle.vin || "-"}</strong></div>
    <div class="info-item"><span>Plate</span><strong>${vehicle.plate || "-"}</strong></div>
    <div class="info-item"><span>ECU</span><strong>${vehicle.ecu || "-"}</strong></div>
    <div class="info-item"><span>Engine</span><strong>${vehicle.engine || "-"}</strong></div>
  `;
}

function showVehicleError(title, message) {
  document.getElementById("vehicleTitle").innerText = title;
  document.getElementById("vehicleInfoBox").innerText = message;
}

async function loadLinkedCustomers(vehicleId) {
  try {
    const res = await fetch(`${API_BASE}/customers/vehicle/${vehicleId}`);
    const data = await res.json();

    const customers = data.customers || [];

    renderOwners(customers);
    document.getElementById("totalOwners").innerText = customers.length;

  } catch (error) {
    renderOwners([]);
    document.getElementById("totalOwners").innerText = "0";
  }
}

function renderOwners(customers) {
  const table = document.getElementById("ownersTable");
  table.innerHTML = "";

  if (!customers.length) {
    table.innerHTML = `
      <tr>
        <td colspan="5">No customers linked yet.</td>
      </tr>
    `;
    return;
  }

  customers.forEach(customer => {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${customer.created_at || "-"}</td>
      <td>${customer.name || "-"}</td>
      <td>${customer.license || "-"}</td>
      <td>${customer.phone || "-"}</td>
      <td>
        <button class="primary-btn" onclick="openCustomerDetail('${customer.license}')">
          Open
        </button>
      </td>
    `;

    table.appendChild(row);
  });
}

function openCustomerDetail(license) {
  window.open(
    `customer_detail.html?license=${encodeURIComponent(license)}`,
    "_blank",
    "width=1200,height=850"
  );
}

async function addRepair() {
  const vehicleId = getCurrentVehicleId();

  const data = {
    vehicle_id: Number(vehicleId),
    date: document.getElementById("repairDate").value || new Date().toISOString().slice(0, 10),
    mileage: document.getElementById("repairMileage").value.trim(),
    title: document.getElementById("repairTitle").value.trim(),
    work_done: document.getElementById("repairWork").value.trim()
  };

  if (!data.title) {
    alert("Repair title is required.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/repair/save`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(data)
    });

    const result = await res.json();

    if (!res.ok || result.error) {
      throw new Error(result.error || "Repair save failed");
    }

    document.getElementById("repairDate").value = "";
    document.getElementById("repairMileage").value = "";
    document.getElementById("repairTitle").value = "";
    document.getElementById("repairWork").value = "";

    await loadRepairs(vehicleId);

  } catch (error) {
    alert("Repair save failed: " + error.message);
  }
}

async function loadRepairs(vehicleId) {
  try {
    const res = await fetch(`${API_BASE}/repairs/vehicle/${vehicleId}`);
    const data = await res.json();

    const repairs = data.repairs || [];

    renderRepairs(repairs);
    updateRepairStats(repairs);

  } catch (error) {
    renderRepairs([]);
    updateRepairStats([]);
  }
}

function renderRepairs(repairs) {
  const table = document.getElementById("repairsTable");
  table.innerHTML = "";

  if (!repairs.length) {
    table.innerHTML = `
      <tr>
        <td colspan="4">No repair records added yet.</td>
      </tr>
    `;
    return;
  }

  repairs.forEach(repair => {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${repair.date || "-"}</td>
      <td>${repair.mileage || "-"}</td>
      <td>${repair.title || "-"}</td>
      <td>${repair.work_done || "-"}</td>
    `;

    table.appendChild(row);
  });
}

function updateRepairStats(repairs) {
  document.getElementById("totalRepairs").innerText = repairs.length;

  const lastRepair = repairs[0];

  document.getElementById("lastMileage").innerText =
    lastRepair?.mileage || "--";

  document.getElementById("lastVisit").innerText =
    lastRepair?.date || "--";
}




document.addEventListener("DOMContentLoaded", loadVehicleDetail);