const form = document.getElementById("tradein-form");
const message = document.getElementById("form-message");
const addProductButton = document.getElementById("add-product");
const additionalProducts = document.getElementById("additional-products");
const productTemplate = document.getElementById("product-row-template");
const languageSelect = document.getElementById("language-select");

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
    invoiceUpload: "Upload invoice or leasing contract",
    additionalProductsTitle: "Additional products",
    addAnotherProduct: "Add another product",
    additionalProductsHint:
      "You can add more products once all fields in the current product row are filled.",
    privacyText:
      "I accept the privacy policy. Your data will only be used for the purpose of the trade-in bonus.",
    requestRefund: "Request a refund",
    newAutomowerSerial: "New Automower serial number",
    nameplateImageShort: "Nameplate image (if serial not legible)",
    remove: "Remove",
    addRowIncomplete:
      "Please complete all fields in the current additional product row.",
    requiredFields:
      "Please complete all required fields before requesting a refund.",
    formValid: "Form is valid. Prototype ready for submission.",
    confirmReceived: "Thank you! Your request has been received.",
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
    invoiceUpload: "Rechnung oder Leasingvertrag hochladen",
    additionalProductsTitle: "Weitere Produkte",
    addAnotherProduct: "Weiteres Produkt hinzufügen",
    additionalProductsHint:
      "Sie können weitere Produkte hinzufügen, sobald alle Felder in der aktuellen Produktzeile ausgefüllt sind.",
    privacyText:
      "Ich akzeptiere die Datenschutzerklärung. Ihre Daten werden nur zum Zweck des Eintauschbonus verwendet.",
    requestRefund: "Rückerstattung beantragen",
    newAutomowerSerial: "Seriennummer des neuen Automower",
    nameplateImageShort: "Typenschild-Bild (falls Seriennummer unlesbar)",
    remove: "Entfernen",
    addRowIncomplete:
      "Bitte füllen Sie alle Felder in der aktuellen Produktzeile aus.",
    requiredFields:
      "Bitte füllen Sie alle Pflichtfelder aus, bevor Sie die Rückerstattung beantragen.",
    formValid: "Formular ist gültig. Prototyp bereit zum Absenden.",
    confirmReceived: "Danke! Ihre Anfrage ist eingegangen.",
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
  "input[name='privacyAccepted']",
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

form.addEventListener("submit", (event) => {
  event.preventDefault();
  clearMessage();

  const baseValid = validateBaseFields();
  const rowsValid = getCurrentAdditionalRows().every((row) =>
    validateAdditionalRow(row)
  );

  if (!baseValid || !rowsValid) {
    setMessageKey("requiredFields");
    return;
  }

  setMessageKey("formValid");
  alert(t("confirmReceived"));
});

languageSelect?.addEventListener("change", (event) => {
  currentLanguage = event.target.value;
  applyTranslations();
});

applyTranslations();
updateAddButtonState();
