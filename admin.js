const submissionsBody = document.getElementById("submissions-body");
const refreshButton = document.getElementById("refresh-submissions");
const exportButton = document.getElementById("export-submissions");

const fetchSubmissions = async () => {
  if (!submissionsBody) return;
  submissionsBody.innerHTML =
    "<tr><td colspan='13' class='empty-row'>Loading…</td></tr>";

  try {
    const response = await fetch("/api/submissions");
    if (!response.ok) {
      submissionsBody.innerHTML =
        "<tr><td colspan='13' class='empty-row'>Failed to load submissions.</td></tr>";
      return;
    }
    const data = await response.json();

    if (!Array.isArray(data) || data.length === 0) {
      submissionsBody.innerHTML =
        "<tr><td colspan='13' class='empty-row'>No submissions yet.</td></tr>";
      return;
    }

    const rows = [];
    data.forEach((submission) => {
      const {
        id,
        submitted_at,
        language,
        dealer = {},
        products = [],
      } = submission;

      products.forEach((product) => {
        const tr = document.createElement("tr");
        const files = [];
        if (product.tradeInProductImagePath) {
          files.push(
            `<a href="/${product.tradeInProductImagePath}" target="_blank" rel="noopener noreferrer">Product</a>`
          );
        }
        if (product.tradeInNameplatePath) {
          files.push(
            `<a href="/${product.tradeInNameplatePath}" target="_blank" rel="noopener noreferrer">Nameplate</a>`
          );
        }
        if (product.invoicePath) {
          files.push(
            `<a href="/${product.invoicePath}" target="_blank" rel="noopener noreferrer">Invoice</a>`
          );
        }

        tr.innerHTML = `
          <td class="id-cell">${id}</td>
          <td class="date-cell">${submitted_at}</td>
          <td>${dealer.dealerNo || ""}</td>
          <td class="company-cell">${dealer.companyName || ""}</td>
          <td>${dealer.postalLocation || ""}</td>
          <td class="email-cell" title="${dealer.email || ""}">${
          dealer.email || ""
        }</td>
          <td>${language || ""}</td>
          <td class="index-cell">${product.productIndex}</td>
          <td>${product.soldModel || ""}</td>
          <td>${product.newSerialNumber || ""}</td>
          <td>${product.tradeInType || ""}</td>
          <td>${product.tradeInSerialNumber || ""}</td>
          <td class="files-cell">${
            files.length > 0 ? files.join(" · ") : "-"
          }</td>
        `;
        rows.push(tr);
      });
    });

    submissionsBody.innerHTML = "";
    rows.forEach((tr) => submissionsBody.appendChild(tr));
  } catch (error) {
    submissionsBody.innerHTML =
      "<tr><td colspan='13' class='empty-row'>Error loading submissions.</td></tr>";
  }
};

refreshButton?.addEventListener("click", () => {
  fetchSubmissions();
});

exportButton?.addEventListener("click", () => {
  window.location.href = "/api/submissions/export";
});

fetchSubmissions();

