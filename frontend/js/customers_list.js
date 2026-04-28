async function renderCustomers() {
  const search = document.getElementById("customerSearchBox").value.trim();

  try {
    const res = await fetch(
      `http://127.0.0.1:8000/customers/search?q=${encodeURIComponent(search)}`
    );

    const data = await res.json();
    const table = document.getElementById("customerTable");

    table.innerHTML = "";

    if (!data.customers || data.customers.length === 0) {
      table.innerHTML = `
        <tr>
          <td colspan="6">No customers found.</td>
        </tr>
      `;
      return;
    }

    data.customers.forEach(c => {
      const row = document.createElement("tr");

      row.innerHTML = `
        <td>${c.name || "-"}</td>
        <td>${c.phone || "-"}</td>
        <td>${c.email || "-"}</td>
        <td>${c.license || "-"}</td>
        <td>${c.address || "-"}</td>
        <td>
          <button class="primary-btn" onclick="openCustomer('${c.license}')">
            Open
          </button>
        </td>
      `;

      table.appendChild(row);
    });

  } catch (err) {
    console.error(err);
  }
}

function openCustomer(license) {
  window.open(
    `customer_detail.html?license=${encodeURIComponent(license)}`,
    "_blank",
    "width=1200,height=850"
  );
}

document.addEventListener("DOMContentLoaded", renderCustomers);