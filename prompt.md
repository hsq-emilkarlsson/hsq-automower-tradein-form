You are a senior front-end engineer. Build a production-quality static prototype for a Husqvarna form called “Automower Trade-in Bonus”, using ONLY vanilla HTML/CSS/JS (no frameworks). Output MUST be a complete multi-file project that runs on static hosting (GitHub Pages) and also via Docker on localhost:8080.

========================================================
PROJECT OUTPUT (REQUIRED FILES)
========================================================
Create exactly these files in the repository root:
1) index.html
2) styles.css
3) script.js
4) Dockerfile
5) docker-compose.yml (optional, only if needed)
6) N8N-DPI-Warranty-Form-Submit.json (importable n8n workflow)

Do not include build steps. Do not require Node, bundlers, or external runtime dependencies.

========================================================
FORM: "Automower Trade-in Bonus"
========================================================
A) Dealer data (ALL REQUIRED)
- Dealer no (text)
- Company name (text)
- Postal code & location (text)
- E-mail (email)

B) Product info (REPEATABLE SECTION)
Each product row contains:
1) Sold model (dropdown, required)
   - Automower 430V NERA
   - Automower 435X AWD NERA

2) Serial number of the new Automower (required, EXACTLY 9 digits)
   - Validate: /^[0-9]{9}$/ with a clear message if invalid.

3) Trade-in type (dropdown, required)
   - Ambrogio, Bosch, EGO, Gardena, Honda, Husqvarna, Kress, Mammotion, Robomow, Segway, Stihl/Viking, Worx, Others

4) Trade-in identification (ONE of these is required)
   - Trade-in serial number (text) OR
   - Upload nameplate image (file)
   Validation rule: at least one must be provided.
   UX: if user fills serial -> nameplate upload becomes optional; if user uploads nameplate -> serial becomes optional.

5) Upload image of trade-in product (file, REQUIRED)

6) Upload invoice/leasing contract (file, REQUIRED)

C) Add product behavior (STRICT)
- A user can add another product row ONLY when ALL required fields in the current (last) row are completed and valid.
- Show a clear inline message if the user tries to add a row too early.
- Allow removing any additional row (but keep at least one row).

D) Validation + Error UI (STRICT)
- Required inputs: red border when invalid.
- Field-level error messages directly under the field (human readable).
- Validate:
  - Email format client-side
  - Required fields
  - New Automower serial: exactly 9 digits
  - File size limit: implement client-side max file size check (choose 10 MB per file) with a clear error.
- Prevent submission until valid.
- After successful submission: reset the entire form back to initial state (one empty product row) and show a success message.

========================================================
SUBMISSION / INTEGRATION
========================================================
- Submit via POST to a backend webhook using a placeholder URL constant:
  WEBHOOK_URL = "https://example.com/webhook-not-configured"
- Use multipart/form-data (FormData).
- Payload format:
  - Add a "data" field containing JSON string with all non-file fields, including an array of product rows.
  - Attach files with stable keys (e.g. products[0].tradeInImage, products[0].invoice, products[0].nameplateImage if provided).
- Handle “endpoint not configured” clearly:
  If WEBHOOK_URL includes "webhook-not-configured" (or is empty), do NOT attempt fetch.
  Instead show a prominent warning banner telling the user the endpoint is not configured.
- If fetch is attempted: show loading state on submit button, handle network errors gracefully, and show result messages.

========================================================
STYLING (HUSQVARNA LOOK & FEEL)
========================================================
- Light UI, clean spacing, accessible contrast.
- Primary color: Husqvarna blue #273A60 used for header, primary button, focus states.
- Provide a top header with:
  - Husqvarna logo:
    - Attempt to load from a local SVG fallback (create an inline SVG in index.html if you can’t import Storybook).
    - Keep it simple and crisp.
  - Title: "Automower Trade-in Bonus"
- Use a responsive layout:
  - Max width container (e.g. 960px)
  - Product rows as cards with subtle shadow/border
  - Clear section headers (Dealer data / Product info)
- Buttons:
  - Primary: Submit
  - Secondary: Add product
  - Destructive/subtle: Remove product row

Accessibility:
- Use proper <label for=...>, aria-live region for form-level status messages, keyboard focus styles.

========================================================
DOCKER (STATIC SERVER)
========================================================
- Provide a Dockerfile that serves the static files on port 8080.
- Prefer a tiny web server image (e.g. nginx:alpine) configured to listen on 8080.
- The default container run must expose the app at:
  http://localhost:8080

(Optional) docker-compose.yml if it meaningfully simplifies running.

========================================================
N8N WORKFLOW (IMPORTABLE JSON)
========================================================
Create a file named exactly:
N8N-DPI-Warranty-Form-Submit.json

Workflow requirements:
1) Webhook node: receives multipart/form-data
2) Parse node(s): extract "data" JSON and files
3) HTTP Request node: POST to a Power Automate HTTP endpoint (placeholder):
   "https://example.com/power-automate-endpoint"
- Ensure the workflow is importable as-is in n8n.
- Include minimal sane defaults (method POST, JSON body containing parsed data, and include file metadata or binary if appropriate).
- Name nodes clearly.

========================================================
QUALITY BAR
========================================================
- Code must be readable and commented.
- No external dependencies required to run (CDNs ok only for optional fonts/icons; do not rely on them).
- Everything must work on GitHub Pages: relative paths, no server-only features.

========================================================
DELIVER THE OUTPUT
========================================================
Return the full contents of every required file (index.html, styles.css, script.js, Dockerfile, optional docker-compose.yml, and N8N-DPI-Warranty-Form-Submit.json). 
Do NOT omit any file content.