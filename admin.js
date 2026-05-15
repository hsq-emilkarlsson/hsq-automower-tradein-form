const submissionsBody = document.getElementById("submissions-body");
const refreshButton = document.getElementById("refresh-submissions");
const exportButton = document.getElementById("export-submissions");
const filterPeriod = document.getElementById("filter-period");
const filterMarket = document.getElementById("filter-market");

const esc = (val) => {
  const node = document.createElement("span");
  node.textContent = val == null ? "" : String(val);
  return node.innerHTML;
};

const escAttr = (val) => esc(val).replace(/"/g, "&quot;");

let allSubmissions = [];

const applyFilters = () => {
  const months = filterPeriod?.value;
  const market = filterMarket?.value;

  const cutoff =
    months === "all"
      ? null
      : new Date(Date.now() - parseInt(months, 10) * 30 * 24 * 60 * 60 * 1000);

  const filtered = allSubmissions.filter((s) => {
    if (cutoff && new Date(s.submitted_at) < cutoff) return false;
    if (market && s.language !== market) return false;
    return true;
  });

  if (filtered.length === 0) {
    submissionsBody.innerHTML =
      "<tr><td colspan='13' class='empty-row'>No submissions match the selected filters.</td></tr>";
    return;
  }

  const rows = [];
  filtered.forEach((submission) => {
    const { id, submitted_at, language, dealer = {}, products = [] } = submission;

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
        <td class="files-cell">${files.length > 0 ? files.join(" · ") : "-"}</td>
      `;
      rows.push(tr);
    });
  });

  submissionsBody.innerHTML = "";
  rows.forEach((tr) => submissionsBody.appendChild(tr));
};

const populateMarketFilter = () => {
  const markets = [...new Set(allSubmissions.map((s) => s.language).filter(Boolean))].sort();
  const current = filterMarket?.value;
  if (!filterMarket) return;

  filterMarket.innerHTML = '<option value="">All countries</option>';
  markets.forEach((lang) => {
    const opt = document.createElement("option");
    opt.value = lang;
    opt.textContent = lang.toUpperCase();
    filterMarket.appendChild(opt);
  });

  if (current && markets.includes(current)) filterMarket.value = current;
};

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

    allSubmissions = data;
    populateMarketFilter();
    applyFilters();
  } catch {
    submissionsBody.innerHTML =
      "<tr><td colspan='13' class='empty-row'>Error loading submissions.</td></tr>";
  }
};

refreshButton?.addEventListener("click", () => fetchSubmissions());
exportButton?.addEventListener("click", () => {
  window.location.href = "/api/submissions/export";
});
filterPeriod?.addEventListener("change", applyFilters);
filterMarket?.addEventListener("change", applyFilters);

fetchSubmissions();
