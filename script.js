const form = document.getElementById("tradein-form");
const message = document.getElementById("form-message");
const addProductButton = document.getElementById("add-product");
const additionalProducts = document.getElementById("additional-products");
const productTemplate = document.getElementById("product-row-template");

const baseRequiredSelectors = [
  "input[name='dealerNo']",
  "input[name='companyName']",
  "input[name='postalLocation']",
  "input[name='email']",
  "select[name='soldModel']",
  "input[name='newSerialNumber']",
  "select[name='tradeInType']",
  "input[name='tradeInProductImage']",
  "input[name='invoiceFile']",
  "input[name='privacyAccepted']",
];

const tradeInSerial = form.querySelector("input[name='tradeInSerialNumber']");
const tradeInImage = form.querySelector("input[name='tradeInNameplateImage']");

const clearMessage = () => {
  message.textContent = "";
};

const setMessage = (text) => {
  message.textContent = text;
};

const markValidity = (field, isValid) => {
  if (!field) return;
  field.classList.toggle("error", !isValid);
};

const isFilled = (field) => {
  if (!field) return false;
  if (field.type === "checkbox") return field.checked;
  if (field.type === "file") return field.files && field.files.length > 0;
  return field.value.trim() !== "";
};

const validateTradeInSerialOrImage = () => {
  const serialFilled = isFilled(tradeInSerial);
  const imageFilled = isFilled(tradeInImage);
  const valid = serialFilled || imageFilled;
  markValidity(tradeInSerial, valid);
  markValidity(tradeInImage, valid);
  return valid;
};

const validateBaseFields = () => {
  let valid = true;
  baseRequiredSelectors.forEach((selector) => {
    const field = form.querySelector(selector);
    const filled = isFilled(field);
    markValidity(field, filled);
    if (!filled) valid = false;
  });

  if (!validateTradeInSerialOrImage()) {
    valid = false;
  }

  return valid;
};

const getCurrentAdditionalRows = () =>
  Array.from(additionalProducts.querySelectorAll(".product-row"));

const validateTradeInSerialOrImageForRow = (row) => {
  const serialField = row.querySelector(
    "input[name='additionalTradeInSerialNumber']"
  );
  const nameplateField = row.querySelector(
    "input[name='additionalTradeInNameplateImage']"
  );
  const serialFilled = isFilled(serialField);
  const imageFilled = isFilled(nameplateField);
  const valid = serialFilled || imageFilled;
  markValidity(serialField, valid);
  markValidity(nameplateField, valid);
  return valid;
};

const validateAdditionalRow = (row) => {
  const requiredFields = row.querySelectorAll("[required]");
  let valid = true;
  requiredFields.forEach((field) => {
    const filled = isFilled(field);
    markValidity(field, filled);
    if (!filled) valid = false;
  });

  if (!validateTradeInSerialOrImageForRow(row)) {
    valid = false;
  }

  return valid;
};

const updateAddButtonState = () => {
  const rows = getCurrentAdditionalRows();
  if (rows.length === 0) {
    addProductButton.disabled = false;
    return;
  }
  const lastRow = rows[rows.length - 1];
  addProductButton.disabled = !validateAdditionalRow(lastRow);
};

const addAdditionalProduct = () => {
  const clone = productTemplate.content.cloneNode(true);
  additionalProducts.appendChild(clone);
  updateAddButtonState();
};

additionalProducts.addEventListener("input", updateAddButtonState);

additionalProducts.addEventListener("click", (event) => {
  const removeButton = event.target.closest(".remove-product");
  if (!removeButton) return;
  const row = removeButton.closest(".product-row");
  if (row) row.remove();
  updateAddButtonState();
});

addProductButton.addEventListener("click", () => {
  const rows = getCurrentAdditionalRows();
  if (rows.length > 0) {
    const lastRow = rows[rows.length - 1];
    if (!validateAdditionalRow(lastRow)) {
      setMessage(
        "Please complete all fields in the current additional product row."
      );
      return;
    }
  }
  clearMessage();
  addAdditionalProduct();
});

form.addEventListener("input", () => {
  clearMessage();
  validateTradeInSerialOrImage();
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  clearMessage();

  const baseValid = validateBaseFields();
  const rowsValid = getCurrentAdditionalRows().every((row) =>
    validateAdditionalRow(row)
  );

  if (!baseValid || !rowsValid) {
    setMessage(
      "Please complete all required fields before requesting a refund."
    );
    return;
  }

  setMessage("Form is valid. Prototype ready for submission.");
  alert("Thank you! Your request has been received.");
});

updateAddButtonState();
