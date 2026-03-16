const submissionsBody = document.getElementById("submissions-body");
const refreshButton = document.getElementById("refresh-submissions");
const exportButton = document.getElementById("export-submissions");

const esc = (val) => {
  const node = document.createElement("span");
  node.textContent = val == null ? "" : String(val);
  return node.innerHTML;
};

const escAttr = (val) => esc(val).replace(/"/g, "&quot;");

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
            `<a href="/api/files/${escAttr(product.tradeInProductImagePath)}" target="_blank" rel="noopener noreferrer">Product</a>`
          );
        }
        if (product.tradeInNameplatePath) {
          files.push(
            `<a href="/api/files/${escAttr(product.tradeInNameplatePath)}" target="_blank" rel="noopener noreferrer">Nameplate</a>`
          );
        }
        if (product.invoicePath) {
          files.push(
            `<a href="/api/files/${escAttr(product.invoicePath)}" target="_blank" rel="noopener noreferrer">Invoice</a>`
          );
        }

        tr.innerHTML = `
          <td class="id-cell">${esc(id)}</td>
          <td class="date-cell">${esc(submitted_at)}</td>
          <td>${esc(dealer.dealerNo)}</td>
          <td class="company-cell">${esc(dealer.companyName)}</td>
          <td>${esc(dealer.postalLocation)}</td>
          <td class="email-cell" title="${escAttr(dealer.email)}">${esc(dealer.email)}</td>
          <td>${esc(language)}</td>
          <td class="index-cell">${esc(product.productIndex)}</td>
          <td>${esc(product.soldModel)}</td>
          <td>${esc(product.newSerialNumber)}</td>
          <td>${esc(product.tradeInType)}</td>
          <td>${esc(product.tradeInSerialNumber)}</td>
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

