function getCustomers() {
  return JSON.parse(localStorage.getItem("customers") || "{}");
}

function saveCustomers(customers) {
  localStorage.setItem("customers", JSON.stringify(customers));
}

function saveCustomer() {
  const customer = {
    name: document.getElementById("custName").value.trim(),
    phone: document.getElementById("custPhone").value.trim(),
    email: document.getElementById("custEmail").value.trim(),
    license: document.getElementById("custLicense").value.trim(),
    address: document.getElementById("custAddress").value.trim(),
    notes: document.getElementById("custNotes").value.trim(),
    createdAt: new Date().toISOString()
  };

  if (!customer.name || !customer.license) {
    alert("Name and Driving License Number are required.");
    return;
  }

  const customers = getCustomers();
  customers[customer.license] = customer;
  saveCustomers(customers);

  document.getElementById("custStatus").innerText =
    "Customer saved: " + customer.name;
}

function findCustomer() {
  const license = document.getElementById("searchLicense").value.trim();

  if (!license) {
    alert("Enter driving license number.");
    return;
  }

  const customers = getCustomers();
  const customer = customers[license];

  if (!customer) {
    document.getElementById("searchResult").innerText =
      "No customer found for this license number.";
    document.getElementById("linkedVehicles").innerText =
      "No vehicles loaded.";
    return;
  }

  document.getElementById("searchResult").innerText =
    JSON.stringify(customer, null, 2);

  showLinkedVehicles(license);
}

function showLinkedVehicles(license) {
  const vehicles = JSON.parse(localStorage.getItem("vehicles") || "{}");

  const linked = Object.values(vehicles).filter(vehicle =>
    vehicle.ownerLicense === license
  );

  if (linked.length === 0) {
    document.getElementById("linkedVehicles").innerText =
      "No vehicles linked to this customer.";
    return;
  }

  document.getElementById("linkedVehicles").innerText =
    JSON.stringify(linked, null, 2);
}