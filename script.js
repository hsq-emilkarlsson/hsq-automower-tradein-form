const form = document.getElementById("tradein-form");
const message = document.getElementById("form-message");
const addProductButton = document.getElementById("add-product");
const additionalProducts = document.getElementById("additional-products");
const productTemplate = document.getElementById("product-row-template");
const languageSelect = document.getElementById("language-select");
const successPanel = document.getElementById("success-panel");
const successRestartButton = document.getElementById("success-restart");

const MAX_FILE_SIZE_MB = 25;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

// Backend API endpoint for submissions when running via FastAPI container.
const API_SUBMIT_URL = "/api/submissions";

const translations = {
  en: {
    title: "Automower Trade-in Bonus",
    subtitle: "Prototype form for validating all fields and selections.",
    languageLabel: "Language",
    dealerDataTitle: "Dealer data",
    dealerNo: "Dealer no",
    companyName: "Company name",
    postalLocation: "Postal code & location",
    email: "E-mail",
    productInfoTitle: "Information about the products",
    soldModel: "Select sold model",
    selectModel: "Select model",
    newSerialNumber: "Serial number of the new Automower",
    tradeInType: "Trade-in type",
    selectBrand: "Select brand",
    infotextLabel: "Infotext:",
    tradeInSerialInfo:
      "Serial number of the trade-in product: Please enter the serial number of the trade-in product. If it is not legible, please upload a photo of the nameplate.",
    tradeInSerialNumber: "Serial number of the trade-in product",
    nameplateImage: "Upload image of the nameplate (if serial not legible)",
    tradeInProductImage: "Upload image of the trade-in product",
    invoiceUpload: "Upload invoice",
    maxFileSize: "Max file size: 25 MB",
    additionalProductsTitle: "Additional products",
    addAnotherProduct: "Add another product",
    additionalProductsHint:
      "You can add more products once all fields in the current product row are filled.",
    requestRefund: "Request a refund",
    newAutomowerSerial: "New Automower serial number",
    serialNineDigits: "9 digits",
    nameplateImageShort: "Nameplate image (if serial not legible)",
    remove: "Remove",
    addRowIncomplete:
      "Please complete all fields in the current additional product row.",
    invalidEmail: "Please enter a valid e-mail address.",
    fileTooLarge: "One or more files exceed the 25 MB limit.",
    requiredField: "This field is required.",
    serialOrImageRequired: "Enter a serial number or upload the nameplate.",
    serialNineDigitsError: "Serial number must be exactly 9 digits.",
    requiredFields:
      "Please complete all required fields before requesting a refund.",
    formValid: "Form is valid. Prototype ready for submission.",
    confirmReceived: "Thank you! Your request has been received.",
    submitNotConfigured:
      "Submission endpoint is not configured yet.",
    submitFailed: "Submission failed. Please try again.",
  },
  "de-AT": {
    title: "Automower Eintauschbonus",
    subtitle: "Prototyp-Formular zur Validierung aller Felder und Auswahlen.",
    languageLabel: "Sprache",
    dealerDataTitle: "Händlerdaten",
    dealerNo: "Händlernummer",
    companyName: "Firmenname",
    postalLocation: "PLZ & Ort",
    email: "E-Mail-Adresse",
    productInfoTitle: "Produktinformationen",
    soldModel: "Verkauftes Modell",
    selectModel: "Modell auswählen",
    newSerialNumber: "Seriennummer des neuen Automower",
    tradeInType: "Eintauschtyp",
    selectBrand: "Marke auswählen",
    infotextLabel: "Hinweis:",
    tradeInSerialInfo:
      "Seriennummer des Eintauschprodukts: Bitte geben Sie die Seriennummer des Eintauschprodukts ein. Wenn sie nicht lesbar ist, laden Sie bitte ein Foto des Typenschilds hoch.",
    tradeInSerialNumber: "Seriennummer des Eintauschprodukts",
    nameplateImage:
      "Bild des Typenschilds hochladen (falls Seriennummer unlesbar)",
    tradeInProductImage: "Bild des Eintauschprodukts hochladen",
    invoiceUpload: "Rechnung hochladen",
    maxFileSize: "Maximale Dateigroesse: 25 MB",
    additionalProductsTitle: "Weitere Produkte",
    addAnotherProduct: "Weiteres Produkt hinzufügen",
    additionalProductsHint:
      "Sie können weitere Produkte hinzufügen, sobald alle Felder in der aktuellen Produktzeile ausgefüllt sind.",
    requestRefund: "Rückerstattung beantragen",
    newAutomowerSerial: "Seriennummer des neuen Automower",
    serialNineDigits: "9 Ziffern",
    nameplateImageShort: "Typenschild-Bild (falls Seriennummer unlesbar)",
    remove: "Entfernen",
    addRowIncomplete:
      "Bitte füllen Sie alle Felder in der aktuellen Produktzeile aus.",
    invalidEmail: "Bitte geben Sie eine gültige E-Mail-Adresse ein.",
    fileTooLarge: "Eine oder mehrere Dateien überschreiten die 25-MB-Grenze.",
    requiredField: "Dieses Feld ist erforderlich.",
    serialOrImageRequired:
      "Seriennummer eingeben oder Typenschild hochladen.",
    serialNineDigitsError: "Seriennummer muss genau 9 Ziffern haben.",
    requiredFields:
      "Bitte füllen Sie alle Pflichtfelder aus, bevor Sie die Rückerstattung beantragen.",
    formValid: "Formular ist gültig. Prototyp bereit zum Absenden.",
    confirmReceived: "Danke! Ihre Anfrage ist eingegangen.",
    submitNotConfigured:
      "Sende-Endpunkt ist noch nicht konfiguriert.",
    submitFailed: "Senden fehlgeschlagen. Bitte erneut versuchen.",
  },
};

let currentLanguage = languageSelect?.value || "en";
let messageKey = "";

const t = (key) => translations[currentLanguage]?.[key] || translations.en[key] || key;

const applyTranslations = (root = document) => {
  root.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.getAttribute("data-i18n");
    const value = t(key);
    if (value) element.textContent = value;
  });
  document.documentElement.lang = currentLanguage;
  if (messageKey) {
    message.textContent = t(messageKey);
  }
};

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
];

const tradeInSerial = form.querySelector("input[name='tradeInSerialNumber']");
const tradeInImage = form.querySelector("input[name='tradeInNameplateImage']");

const clearMessage = () => {
  message.textContent = "";
  messageKey = "";
};

const setMessage = (text) => {
  message.textContent = text;
  messageKey = "";
};

const setMessageKey = (key) => {
  messageKey = key;
  message.textContent = t(key);
};

const markValidity = (field, isValid) => {
  if (!field) return;
  field.classList.toggle("error", !isValid);
};

const isEmailValid = (value) => /.+@.+\..+/.test(value);
const isNineDigits = (value) => /^\d{9}$/.test(value);

const getErrorElement = (field) => {
  const label = field.closest("label");
  if (!label) return null;
  const selector = `.field-error[data-error-for="${field.name}"]`;
  let error = label.querySelector(selector);
  if (!error) {
    error = document.createElement("span");
    error.className = "field-error";
    error.setAttribute("data-error-for", field.name);
    label.appendChild(error);
  }
  return error;
};

const setFieldError = (field, key) => {
  const error = getErrorElement(field);
  if (!error) return;
  error.textContent = t(key);
  markValidity(field, false);
};

const clearFieldError = (field) => {
  const error = getErrorElement(field);
  if (!error) return;
  error.textContent = "";
};

const isFilled = (field) => {
  if (!field) return false;
  if (field.type === "checkbox") return field.checked;
  if (field.type === "file") return field.files && field.files.length > 0;
  return field.value.trim() !== "";
};

const buildPayloadAndFiles = () => {
  const payload = {
    language: currentLanguage,
    submittedAt: new Date().toISOString(),
    dealer: {
      dealerNo: form.querySelector("input[name='dealerNo']").value.trim(),
      companyName: form.querySelector("input[name='companyName']").value.trim(),
      postalLocation: form
        .querySelector("input[name='postalLocation']")
        .value.trim(),
      email: form.querySelector("input[name='email']").value.trim(),
    },
    product: {
      soldModel: form.querySelector("select[name='soldModel']").value,
      newSerialNumber: form
        .querySelector("input[name='newSerialNumber']")
        .value.trim(),
      tradeInType: form.querySelector("select[name='tradeInType']").value,
      tradeInSerialNumber: form
        .querySelector("input[name='tradeInSerialNumber']")
        .value.trim(),
      tradeInNameplateKey: "tradeInNameplateImage",
      tradeInProductImageKey: "tradeInProductImage",
      invoiceKey: "invoiceFile",
    },
    additionalProducts: [],
  };

  const formData = new FormData();
  const baseNameplate = form.querySelector(
    "input[name='tradeInNameplateImage']"
  );
  const baseProductImage = form.querySelector(
    "input[name='tradeInProductImage']"
  );
  const baseInvoice = form.querySelector("input[name='invoiceFile']");

  if (baseNameplate && baseNameplate.files[0]) {
    formData.append("tradeInNameplateImage", baseNameplate.files[0]);
  }
  if (baseProductImage && baseProductImage.files[0]) {
    formData.append("tradeInProductImage", baseProductImage.files[0]);
  }
  if (baseInvoice && baseInvoice.files[0]) {
    formData.append("invoiceFile", baseInvoice.files[0]);
  }

  getCurrentAdditionalRows().forEach((row, index) => {
    const suffix = `_${index + 1}`;
    const additional = {
      index: index + 1,
      soldModel: row.querySelector("select[name='additionalSoldModel']").value,
      newSerialNumber: row
        .querySelector("input[name='additionalNewSerialNumber']")
        .value.trim(),
      tradeInType: row
        .querySelector("select[name='additionalTradeInType']")
        .value,
      tradeInSerialNumber: row
        .querySelector("input[name='additionalTradeInSerialNumber']")
        .value.trim(),
      tradeInNameplateKey: `additionalTradeInNameplateImage${suffix}`,
      tradeInProductImageKey: `additionalTradeInProductImage${suffix}`,
      invoiceKey: `additionalInvoiceFile${suffix}`,
    };

    const nameplate = row.querySelector(
      "input[name='additionalTradeInNameplateImage']"
    );
    const productImage = row.querySelector(
      "input[name='additionalTradeInProductImage']"
    );
    const invoice = row.querySelector("input[name='additionalInvoiceFile']");

    if (nameplate && nameplate.files[0]) {
      formData.append(additional.tradeInNameplateKey, nameplate.files[0]);
    }
    if (productImage && productImage.files[0]) {
      formData.append(additional.tradeInProductImageKey, productImage.files[0]);
    }
    if (invoice && invoice.files[0]) {
      formData.append(additional.invoiceKey, invoice.files[0]);
    }

    payload.additionalProducts.push(additional);
  });

  formData.append("payload", JSON.stringify(payload));
  return formData;
};

const validateTradeInSerialOrImage = () => {
  const serialFilled = isFilled(tradeInSerial);
  const imageFilled = isFilled(tradeInImage);
  const valid = serialFilled || imageFilled;
  if (!valid) {
    setFieldError(tradeInSerial, "serialOrImageRequired");
    setFieldError(tradeInImage, "serialOrImageRequired");
  } else {
    clearFieldError(tradeInSerial);
    clearFieldError(tradeInImage);
    markValidity(tradeInSerial, true);
    markValidity(tradeInImage, true);
  }
  return valid;
};

const validateFileSizes = (root) => {
  let valid = true;
  const fileInputs = root.querySelectorAll("input[type='file']");
  fileInputs.forEach((input) => {
    if (!input.files || input.files.length === 0) {
      // No file selected: only clear size-specific error
      const error = getErrorElement(input);
      if (error && error.textContent === t("fileTooLarge")) {
        error.textContent = "";
      }
      return;
    }
    let withinLimit = true;
    Array.from(input.files).forEach((file) => {
      if (file.size > MAX_FILE_SIZE_BYTES) {
        withinLimit = false;
      }
    });
    if (!withinLimit) {
      setFieldError(input, "fileTooLarge");
    } else {
      clearFieldError(input);
      markValidity(input, true);
    }
    if (!withinLimit) valid = false;
  });
  return valid;
};

const validateBaseFields = () => {
  let valid = true;
  let emailValid = true;
  let filesValid = true;
  baseRequiredSelectors.forEach((selector) => {
    const field = form.querySelector(selector);
    const filled = isFilled(field);
    if (!filled) {
      setFieldError(field, "requiredField");
      valid = false;
    } else {
      clearFieldError(field);
      markValidity(field, true);
    }
  });

  const emailField = form.querySelector("input[name='email']");
  if (emailField && isFilled(emailField)) {
    emailValid = isEmailValid(emailField.value.trim());
    if (!emailValid) {
      setFieldError(emailField, "invalidEmail");
      valid = false;
    } else {
      clearFieldError(emailField);
      markValidity(emailField, true);
    }
  }

  const newSerialField = form.querySelector("input[name='newSerialNumber']");
  if (newSerialField && isFilled(newSerialField)) {
    const serialValid = isNineDigits(newSerialField.value.trim());
    if (!serialValid) {
      setFieldError(newSerialField, "serialNineDigitsError");
      valid = false;
    } else {
      clearFieldError(newSerialField);
      markValidity(newSerialField, true);
    }
  }

  if (!validateTradeInSerialOrImage()) {
    valid = false;
  }

  filesValid = validateFileSizes(form);
  if (!filesValid) valid = false;

  return { valid, emailValid, filesValid };
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
  if (!valid) {
    setFieldError(serialField, "serialOrImageRequired");
    setFieldError(nameplateField, "serialOrImageRequired");
  } else {
    clearFieldError(serialField);
    clearFieldError(nameplateField);
    markValidity(serialField, true);
    markValidity(nameplateField, true);
  }
  return valid;
};

const validateAdditionalRow = (row) => {
  const requiredFields = row.querySelectorAll("[required]");
  let valid = true;
  requiredFields.forEach((field) => {
    const filled = isFilled(field);
    if (!filled) {
      setFieldError(field, "requiredField");
      valid = false;
    } else {
      clearFieldError(field);
      markValidity(field, true);
    }
  });

  if (!validateTradeInSerialOrImageForRow(row)) {
    valid = false;
  }

  const newSerialField = row.querySelector(
    "input[name='additionalNewSerialNumber']"
  );
  if (newSerialField && isFilled(newSerialField)) {
    const serialValid = isNineDigits(newSerialField.value.trim());
    if (!serialValid) {
      setFieldError(newSerialField, "serialNineDigitsError");
      valid = false;
    } else {
      clearFieldError(newSerialField);
      markValidity(newSerialField, true);
    }
  }

  if (!validateFileSizes(row)) {
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
  const newRow = additionalProducts.lastElementChild;
  if (newRow) applyTranslations(newRow);
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
      setMessageKey("addRowIncomplete");
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

form.addEventListener("change", (event) => {
  if (event.target && event.target.type === "file") {
    validateFileSizes(form);
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessage();

  const baseResult = validateBaseFields();
  const rowsValid = getCurrentAdditionalRows().every((row) =>
    validateAdditionalRow(row)
  );

  if (!baseResult.valid || !rowsValid) {
    if (!baseResult.filesValid) {
      setMessageKey("fileTooLarge");
    } else if (!baseResult.emailValid) {
      setMessageKey("invalidEmail");
    } else {
      setMessageKey("requiredFields");
    }
    return;
  }

  setMessageKey("formValid");
  try {
    const formData = buildPayloadAndFiles();
    const response = await fetch(API_SUBMIT_URL, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      setMessageKey("submitFailed");
      return;
    }

    const result = await response.json().catch(() => null);
    if (!result || !result.success) {
      setMessageKey("submitFailed");
      return;
    }

    // Show a friendly thank-you panel and hide the form.
    form.hidden = true;
    if (successPanel) {
      successPanel.hidden = false;
    }
  } catch (error) {
    setMessageKey("submitFailed");
  }
});

successRestartButton?.addEventListener("click", () => {
  // Reload the whole page to start with a fresh, empty form.
  window.location.reload();
});

languageSelect?.addEventListener("change", (event) => {
  currentLanguage = event.target.value;
  applyTranslations();
});

applyTranslations();
updateAddButtonState();
