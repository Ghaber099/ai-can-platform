const API_BASE = "http://127.0.0.1:8000";

function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

async function loadCustomerDetail() {
  const license = getQueryParam("license");

  if (!license) {
    document.getElementById("customerInfoBox").innerText = "No license provided.";
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/customer/${encodeURIComponent(license)}`);
    const customer = await res.json();

    if (!res.ok || customer.error) {
      document.getElementById("customerTitle").innerText = "Customer Not Found";
      document.getElementById("customerInfoBox").innerText = "No customer found.";
      return;
    }

    document.getElementById("customerTitle").innerText = customer.name || "Customer History";
    document.getElementById("customerSubtitle").innerText =
      `License: ${customer.license || "-"} | Email: ${customer.email || "-"}`;

    document.getElementById("customerPhone").innerText = customer.phone || "--";
    document.getElementById("customerLicense").innerText = customer.license || "--";

    document.getElementById("customerInfoBox").innerHTML = `
        <div class="info-item"><span>Name</span><strong>${customer.name || "-"}</strong></div>
        <div class="info-item"><span>Phone</span><strong>${customer.phone || "-"}</strong></div>
        <div class="info-item"><span>Email</span><strong>${customer.email || "-"}</strong></div>
        <div class="info-item"><span>License</span><strong>${customer.license || "-"}</strong></div>
        <div class="info-item wide"><span>Address</span><strong>${customer.address || "-"}</strong></div>
        <div class="info-item wide"><span>Notes</span><strong>${customer.notes || "-"}</strong></div>
    `;

    await loadLinkedVehicles(customer.license);
    await loadCustomerTimeline(customer.license);

  } catch (error) {
    document.getElementById("customerInfoBox").innerText =
      "Error: " + error.message;
  }
}

async function loadLinkedVehicles(license) {
  const res = await fetch(`${API_BASE}/vehicles/customer/${encodeURIComponent(license)}`);
  const data = await res.json();

  const vehicles = data.vehicles || [];
  const table = document.getElementById("customerVehiclesTable");

  document.getElementById("linkedVehicleCount").innerText = vehicles.length;
  document.getElementById("totalVisits").innerText = "--";

  table.innerHTML = "";

  if (vehicles.length === 0) {
    table.innerHTML = `
      <tr>
        <td colspan="6">No vehicles linked to this customer yet.</td>
      </tr>
    `;
    return;
  }

  vehicles.forEach(vehicle => {
    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${vehicle.make || "-"}</td>
      <td>${vehicle.model || "-"}</td>
      <td>${vehicle.year || "-"}</td>
      <td>${vehicle.vin || "-"}</td>
      <td>${vehicle.plate || "-"}</td>
      <td>
        <button class="primary-btn" onclick="openVehicleDetail(${vehicle.id})">
          Open
        </button>
      </td>
    `;

    table.appendChild(row);
  });
}

function openVehicleDetail(vehicleId) {
  window.open(
    `vehicle_detail.html?vehicle=${encodeURIComponent(vehicleId)}`,
    "_blank",
    "width=1200,height=850"
  );
}

function addVehicleForCustomer() {
  const license = getQueryParam("license");

  window.open(
    `vehicle.html?customer=${encodeURIComponent(license)}`,
    "_blank",
    "width=1200,height=850"
  );
}

async function loadCustomerTimeline(license) {
  const res = await fetch(
    `http://127.0.0.1:8000/customer/${encodeURIComponent(license)}/timeline`
  );

  const data = await res.json();
  const table = document.getElementById("customerHistoryTable");

  table.innerHTML = "";

  const events = [];

  (data.vehicle_links || []).forEach(item => {
    events.push({
      date: item.date,
      vehicle: `${item.make || "-"} ${item.model || "-"} (${item.year || "-"})`,
      type: `Vehicle linked as ${item.relationship || "owner"}`,
      notes: `VIN: ${item.vin || "-"} | Plate: ${item.plate || "-"}`
    });
  });

  (data.repairs || []).forEach(item => {
    events.push({
      date: item.date,
      vehicle: `${item.make || "-"} ${item.model || "-"}`,
      type: `Repair: ${item.title || "-"}`,
      notes: `Mileage: ${item.mileage || "-"} | ${item.work_done || "-"}`
    });
  });

  if (events.length === 0) {
    table.innerHTML = `
      <tr>
        <td colspan="4">No customer history yet.</td>
      </tr>
    `;
    return;
  }

  events.sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")));

  events.forEach(event => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${event.date || "-"}</td>
      <td>${event.vehicle || "-"}</td>
      <td>${event.type || "-"}</td>
      <td>${event.notes || "-"}</td>
    `;
    table.appendChild(row);
  });
}




document.addEventListener("DOMContentLoaded", loadCustomerDetail);