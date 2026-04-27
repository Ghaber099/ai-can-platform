async function loadPartial(containerId, filePath) {
  try {
    const res = await fetch(filePath);
    const html = await res.text();
    document.getElementById(containerId).innerHTML = html;
  } catch (err) {
    console.error("Partial load error:", err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadPartial("customerContainer", "partials/customer.html");
});