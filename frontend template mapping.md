# Frontend Template Mapping (Current Project)

This document maps the existing Flask templates to frontend frame sections and component responsibilities.
It is structure-only and intended for design handoff.

## 1) Base Frame (Shared Across Pages)

Source: `templates/base.html`

### Frame Blocks
- Header/Nav block
  - Brand/logo slot
  - Top-level links: Upload, Patients, Search, AI Assistant
- Flash message block
  - Dismissible alerts from backend flash messages
- Main content block
  - Child templates render inside `{% block content %}`
- Footer block
  - Disclaimer and product meta

### Shared Frontend Components
- `TopNav`
- `FlashAlertStack`
- `MainContentSlot`
- `Footer`

## 2) Upload Landing Page Mapping

Source: `templates/index.html`
Route: `/`

### Page Sections
1. Hero section
   - Product title + subtitle
2. Upload card
   - File input
   - File type help text
   - Submit button
   - Processing alert state
3. Pipeline overview card
   - 4-step process blocks
4. Quick links section
   - Patients, Search, Assistant shortcuts

### Form Behavior
- Form target: `POST /upload`
- `enctype="multipart/form-data"`
- Required field: `file`
- Accepted extensions: `.pdf,.png,.jpg,.jpeg,.tiff`
- On submit:
  - disable submit button
  - show processing alert block

### Component Breakdown
- `UploadHero`
- `UploadFormCard`
- `ProcessingAlert`
- `PipelineSteps`
- `QuickLinksGrid`

## 3) Patients List Page Mapping

Source: `templates/patients.html`
Route: `/patients`

### Page Sections
1. Header row
   - Page title
   - CTA: Upload New
2. Conditional body
   - If data exists: table section
   - If no data: empty state section

### Table Frame
- Columns:
  - ID
  - Patient Name
  - DOB
  - Symptoms (truncated)
  - Urgency badge
  - Upload date
  - Actions
- Row action:
  - View -> `/patients/<id>`

### Component Breakdown
- `PageHeaderWithCta`
- `PatientsTable`
- `UrgencyBadge`
- `PatientsEmptyState`

## 4) Patient Detail Page Mapping

Source: `templates/patient_detail.html`
Route: `/patients/<id>`

### Page Frame
- Top back action
- Two-column content layout:
  - Left primary column (record details)
  - Right side panel (AI summary + actions + source info)

### Left Column Sections
1. Patient summary card
   - name
   - urgency badge
   - DOB/upload date
2. Clinical fields section
   - symptoms
   - existing conditions
   - medications
   - allergies
   - referral reason
3. Confidence score section (conditional)
   - field-level progress bars
4. Full extracted text card (conditional)

### Right Column Sections
1. AI summary card
   - Button to request summary
   - Dynamic summary content area
2. Quick actions card
   - Ask assistant
   - Find similar cases
3. Source document card
   - original filename
   - blob identifier

### Dynamic Behavior
- Summary endpoint call: `GET /patients/<id>/summary`
- UI states:
  - idle button
  - loading spinner state
  - success summary content
  - error alert state

### Component Breakdown
- `DetailHeader`
- `PatientInfoCard`
- `ClinicalFieldsSection`
- `ConfidenceScoresPanel`
- `FullTextPanel`
- `AiSummaryCard`
- `QuickActionsCard`
- `SourceDocumentCard`

## 5) Search Page Mapping

Source: `templates/search.html`
Route: `/search`

### Page Sections
1. Search form card
   - query input
   - urgency filter select
   - submit action
2. Results status strip
   - count + active filters text
3. Results section (cards)
   - patient summary card per result
4. Empty/no-results states
5. Search tips card

### Query Parameters
- `q`
- `urgency`

### Result Card Frame
- name
- urgency badge
- DOB
- symptoms
- referral reason
- upload date
- view record action

### Component Breakdown
- `SearchForm`
- `SearchMetaBar`
- `SearchResultsGrid`
- `SearchResultCard`
- `SearchEmptyState`
- `SearchTips`

## 6) Assistant Page Mapping

Source: `templates/assistant.html`
Route: `/assistant`

### Page Sections
1. Page title + disclaimer
2. Chat container card
   - chat history area
   - input composer area
3. Example query card

### Chat Frame
- Message types:
  - assistant message
  - user message
  - typing indicator
- Input form:
  - text field
  - send button

### API Behavior
- Endpoint: `POST /api/assistant`
- Request payload:
  - `question`
  - `history` (last 10 messages)
- Response payload:
  - `answer` or `error`

### Interaction Rules
- Submit on form action
- Disable send while request in flight
- Show typing indicator during request
- Append assistant response on success
- Show fallback error message on failure
- Pre-fill query via URL parameter `?q=...` when present

### Component Breakdown
- `AssistantDisclaimer`
- `ChatHistoryPanel`
- `ChatComposer`
- `TypingIndicator`
- `ExampleQueryList`

## 7) Shared Behavior Mapping

Source: `static/js/app.js`

- Auto-dismiss flash alerts after 5 seconds.
- Uses Bootstrap alert instance handling.

Component mapping:
- `FlashAlertAutoDismiss`

## 8) Frontend Data Dependencies (By Template)

- `index.html`
  - no initial dataset required
- `patients.html`
  - requires `patients` list
- `patient_detail.html`
  - requires `patient` object with extracted fields
- `search.html`
  - requires `results`, `query`, `urgency`
- `assistant.html`
  - no initial dataset required

## 9) Handoff Notes for Design Team

- Keep section boundaries and component intent intact.
- Visual treatment is fully open (layout styling, typography, color, icon style).
- Preserve semantic grouping and data flow:
  - upload -> process -> status
  - list -> detail -> AI summary
  - search -> result cards -> detail
  - assistant chat -> request/response timeline
