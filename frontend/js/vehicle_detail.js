function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

function getVehicles() {
  return JSON.parse(localStorage.getItem("vehicles") || "{}");
}

function saveVehicles(vehicles) {
  localStorage.setItem("vehicles", JSON.stringify(vehicles));
}

function getCurrentVehicleKey() {
  return getQueryParam("vehicle");
}

function loadVehicleDetail() {
  const vehicleKey = getCurrentVehicleKey();
  const vehicles = getVehicles();
  const vehicle = vehicles[vehicleKey];

  if (!vehicle) {
    document.getElementById("vehicleTitle").innerText = "Vehicle Not Found";
    document.getElementById("vehicleInfoBox").innerText =
      "No vehicle found for key: " + vehicleKey;
    return;
  }

  if (!vehicle.owners) vehicle.owners = [];
  if (!vehicle.repairs) vehicle.repairs = [];

  document.getElementById("vehicleTitle").innerText =
    `${vehicle.make || "Unknown"} ${vehicle.model || "Unknown"}`;

  document.getElementById("vehicleSubtitle").innerText =
    `VIN: ${vehicle.vin || "N/A"} | Plate: ${vehicle.plate || "N/A"}`;

  document.getElementById("vehicleInfoBox").innerText =
    JSON.stringify(vehicle, null, 2);

  renderOwners(vehicle);
  renderRepairs(vehicle);
  updateStats(vehicle);
}

function addOwner() {
  const vehicleKey = getCurrentVehicleKey();
  const vehicles = getVehicles();
  const vehicle = vehicles[vehicleKey];

  if (!vehicle) {
    alert("Vehicle not found.");
    return;
  }

  if (!vehicle.owners) vehicle.owners = [];

  const owner = {
    name: document.getElementById("ownerName").value.trim(),
    license: document.getElementById("ownerLicense").value.trim(),
    phone: document.getElementById("ownerPhone").value.trim(),
    addedAt: new Date().toLocaleString()
  };

  if (!owner.name || !owner.license) {
    alert("Owner name and license are required.");
    return;
  }

  vehicle.owners.push(owner);
  saveVehicles(vehicles);

  document.getElementById("ownerName").value = "";
  document.getElementById("ownerLicense").value = "";
  document.getElementById("ownerPhone").value = "";

  loadVehicleDetail();
}

function addRepair() {
  const vehicleKey = getCurrentVehicleKey();
  const vehicles = getVehicles();
  const vehicle = vehicles[vehicleKey];

  if (!vehicle) {
    alert("Vehicle not found.");
    return;
  }

  if (!vehicle.repairs) vehicle.repairs = [];

  const repair = {
    date: document.getElementById("repairDate").value || new Date().toISOString().slice(0, 10),
    mileage: document.getElementById("repairMileage").value.trim(),
    title: document.getElementById("repairTitle").value.trim(),
    workDone: document.getElementById("repairWork").value.trim()
  };

  if (!repair.title) {
    alert("Repair title is required.");
    return;
  }

  vehicle.repairs.push(repair);
  saveVehicles(vehicles);

  document.getElementById("repairDate").value = "";
  document.getElementById("repairMileage").value = "";
  document.getElementById("repairTitle").value = "";
  document.getElementById("repairWork").value = "";

  loadVehicleDetail();
}

function renderOwners(vehicle) {
  const table = document.getElementById("ownersTable");
  table.innerHTML = "";

  if (!vehicle.owners || vehicle.owners.length === 0) {
    table.innerHTML = `
      <tr>
        <td colspan="4">No owners added yet.</td>
      </tr>
    `;
    return;
  }

  vehicle.owners.forEach(owner => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${owner.addedAt || "-"}</td>
      <td>${owner.name || "-"}</td>
      <td>${owner.license || "-"}</td>
      <td>${owner.phone || "-"}</td>
    `;
    table.appendChild(row);
  });
}

function renderRepairs(vehicle) {
  const table = document.getElementById("repairsTable");
  table.innerHTML = "";

  if (!vehicle.repairs || vehicle.repairs.length === 0) {
    table.innerHTML = `
      <tr>
        <td colspan="4">No repair records added yet.</td>
      </tr>
    `;
    return;
  }

  vehicle.repairs.forEach(repair => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${repair.date || "-"}</td>
      <td>${repair.mileage || "-"}</td>
      <td>${repair.title || "-"}</td>
      <td>${repair.workDone || "-"}</td>
    `;
    table.appendChild(row);
  });
}

function updateStats(vehicle) {
  const owners = vehicle.owners || [];
  const repairs = vehicle.repairs || [];

  document.getElementById("totalOwners").innerText = owners.length;
  document.getElementById("totalRepairs").innerText = repairs.length;

  const lastRepair = repairs.length ? repairs[repairs.length - 1] : null;

  document.getElementById("lastMileage").innerText =
    lastRepair?.mileage || vehicle.odometer || "--";

  document.getElementById("lastVisit").innerText =
    lastRepair?.date || "--";
}

document.addEventListener("DOMContentLoaded", loadVehicleDetail);