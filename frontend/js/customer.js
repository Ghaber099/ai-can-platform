function getCustomers() {
  return JSON.parse(localStorage.getItem("customers") || "{}");
}

function saveCustomers(customers) {
  localStorage.setItem("customers", JSON.stringify(customers));
}

async function saveCustomer() {
  const data = {
    name: document.getElementById("custName").value.trim(),
    phone: document.getElementById("custPhone").value.trim(),
    email: document.getElementById("custEmail").value.trim(),
    license: document.getElementById("custLicense").value.trim(),
    address: document.getElementById("custAddress").value.trim(),
    notes: document.getElementById("custNotes").value.trim()
  };

  if (!data.name || !data.license) {
    alert("Name and Driving License Number are required.");
    return;
  }

  try {
    const res = await fetch("http://127.0.0.1:8000/customer/save", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(data)
    });

    const result = await res.json();

    if (!res.ok || result.error) {
      throw new Error(result.error || "Save failed");
    }

    document.getElementById("custStatus").innerText =
      "Customer saved successfully: " + data.name;

  } catch (error) {
    document.getElementById("custStatus").innerText =
      "Error: " + error.message;
  }
}

async function findCustomer() {
  const query = document.getElementById("searchLicense").value.trim();

  if (!query) {
    alert("Enter name, phone, or driving license.");
    return;
  }

  try {
    const res = await fetch(
      `http://127.0.0.1:8000/customers/search?q=${encodeURIComponent(query)}`
    );

    const data = await res.json();

    if (!res.ok || !data.customers || data.customers.length === 0) {
      document.getElementById("searchResult").innerText =
        "No customer found.";
      return;
    }

    document.getElementById("searchResult").innerText =
      JSON.stringify(data.customers, null, 2);

  } catch (error) {
    document.getElementById("searchResult").innerText =
      "Error: " + error.message;
  }
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