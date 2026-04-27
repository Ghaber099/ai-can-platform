function getVehicles() {
  return JSON.parse(localStorage.getItem("vehicles") || "{}");
}

function saveVehicles(data) {
  localStorage.setItem("vehicles", JSON.stringify(data));
}

function saveVehicle() {
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
    notes: document.getElementById("vehicleNotes").value.trim(),
    createdAt: new Date().toISOString()
    
  };

  if (!vehicle.vin && !vehicle.plate) {
    alert("VIN or Plate Number required");
    return;
  }

  const vehicles = getVehicles();
  const key = vehicle.vin || vehicle.plate;

  vehicles[key] = vehicle;
  saveVehicles(vehicles);

  document.getElementById("vehicleStatus").innerText =
    "Vehicle saved: " + (vehicle.vin || vehicle.plate);
}

function findVehicle() {
  const key = document.getElementById("searchVin").value.trim();

  if (!key) {
    alert("Enter VIN or Plate");
    return;
  }

  const vehicles = getVehicles();

  const vehicle = Object.values(vehicles).find(v =>
    v.vin === key || v.plate === key
  );

  const box = document.getElementById("vehicleSearchResult");

  if (!vehicle) {
    box.innerHTML = "Vehicle not found.";
    return;
  }

  const vehicleKey = vehicle.vin || vehicle.plate;

  box.innerHTML = `
    <div class="vehicle-result-card" onclick="openVehicleDetail('${vehicleKey}')">
      <h3>${vehicle.make || "Unknown"} ${vehicle.model || "Unknown"}</h3>
      <p>VIN: ${vehicle.vin || "N/A"}</p>
      <p>Plate: ${vehicle.plate || "N/A"}</p>
      <small>Click to open full history</small>
    </div>
  `;
}


function openVehicleDetail(vehicleKey) {
  window.open(
    `vehicle_detail.html?vehicle=${encodeURIComponent(vehicleKey)}`,
    "_blank",
    "width=1200,height=850"
  );
}


function renderVehicleList() {
  const vehicles = getVehicles();
  const listBox = document.getElementById("vehicleList");
  const search = document.getElementById("vehicleSearchBox").value.toLowerCase();

  const vehicleArray = Object.values(vehicles);

  if (vehicleArray.length === 0) {
    listBox.innerHTML = "No vehicles saved yet.";
    return;
  }

  const filtered = vehicleArray.filter(v => {
    return (
      (v.vin && v.vin.toLowerCase().includes(search)) ||
      (v.plate && v.plate.toLowerCase().includes(search)) ||
      (v.make && v.make.toLowerCase().includes(search)) ||
      (v.model && v.model.toLowerCase().includes(search)) ||
      (v.year && v.year.toLowerCase().includes(search))
    );
  });

  if (filtered.length === 0) {
    listBox.innerHTML = "No matching vehicles found.";
    return;
  }

  listBox.innerHTML = "";

  filtered.forEach(vehicle => {
    const key = vehicle.vin || vehicle.plate;

    const card = document.createElement("div");
    card.className = "vehicle-result-card";

    card.innerHTML = `
      <h3>${vehicle.make || "Unknown"} ${vehicle.model || ""}</h3>
      <p>Year: ${vehicle.year || "-"}</p>
      <p>VIN: ${vehicle.vin || "-"}</p>
      <p>Plate: ${vehicle.plate || "-"}</p>
    `;

    card.onclick = () => openVehicleDetail(key);

    listBox.appendChild(card);
  });
}

document.addEventListener("DOMContentLoaded", renderVehicleList);