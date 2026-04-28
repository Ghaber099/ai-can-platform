const API_BASE = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", loadDashboard);

async function loadDashboard() {
  await loadRecentCustomers();
  await loadRecentVehicles();
}

async function loadRecentCustomers() {
  try {
    const res = await fetch(`${API_BASE}/customers/search?q=`);
    const data = await res.json();
    const customers = data.customers || [];

    document.getElementById("dashCustomers").innerText = customers.length;

    const table = document.getElementById("recentCustomersTable");
    table.innerHTML = "";

    if (!customers.length) {
      table.innerHTML = `<tr><td colspan="5">No customers yet.</td></tr>`;
      return;
    }

    customers.slice(0, 5).forEach(c => {
      table.innerHTML += `
        <tr>
          <td>${c.name || "-"}</td>
          <td>${c.phone || "-"}</td>
          <td>${c.email || "-"}</td>
          <td>${c.license || "-"}</td>
          <td><button class="primary-btn" onclick="openCustomer('${c.license}')">Open</button></td>
        </tr>
      `;
    });
  } catch {
    document.getElementById("recentCustomersTable").innerHTML =
      `<tr><td colspan="5">Backend not connected.</td></tr>`;
  }
}

async function loadRecentVehicles() {
  try {
    const res = await fetch(`${API_BASE}/vehicles/search?q=`);
    const data = await res.json();
    const vehicles = data.vehicles || [];

    document.getElementById("dashVehicles").innerText = vehicles.length;
    document.getElementById("dashRepairs").innerText = "--";
    document.getElementById("dashAlerts").innerText = "0";

    const table = document.getElementById("recentVehiclesTable");
    table.innerHTML = "";

    if (!vehicles.length) {
      table.innerHTML = `<tr><td colspan="6">No vehicles yet.</td></tr>`;
      return;
    }

    vehicles.slice(0, 5).forEach(v => {
      table.innerHTML += `
        <tr>
          <td>${v.make || "-"}</td>
          <td>${v.model || "-"}</td>
          <td>${v.year || "-"}</td>
          <td>${v.vin || "-"}</td>
          <td>${v.plate || "-"}</td>
          <td><button class="primary-btn" onclick="openVehicle('${v.id}')">Open</button></td>
        </tr>
      `;
    });
  } catch {
    document.getElementById("recentVehiclesTable").innerHTML =
      `<tr><td colspan="6">Backend not connected.</td></tr>`;
  }
}

function openCustomer(license) {
  location.href = `customer_detail.html?license=${encodeURIComponent(license)}`;
}

function openVehicle(id) {
  location.href = `vehicle_detail.html?vehicle=${encodeURIComponent(id)}`;
}