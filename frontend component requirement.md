# Frontend Component Requirement

## 1) Purpose

This document defines only the frontend frame and behavior requirements:
- screen structure
- component hierarchy
- interaction flow
- data contracts between frontend and backend

This document intentionally does not prescribe colors, theme, or visual style.

## 2) Frontend Scope

The frontend has two surfaces:
- Public surface: document upload and submission tracking
- Admin surface: login, dashboard, patient records, search, assistant

## 3) Route and Screen Map

### Public
- `/`
  - Upload landing page
- `/upload/status/:submissionId`
  - Submission status page for one upload

### Admin
- `/admin/login`
  - Admin authentication page
- `/admin/dashboard`
  - Operational overview and event timeline
- `/patients`
  - Patient list page
- `/patients/:id`
  - Patient detail page
- `/search`
  - Search page
- `/assistant`
  - Triage assistant page

## 4) High-Level Layout Frame

Every page should follow a consistent shell:
- Header area
- Main content area
- Optional sidebar (admin pages)
- Footer area

### 4.1 Public Shell
- Header:
  - Logo slot
  - Product name slot
  - Help/support link slot
- Main:
  - Intro block
  - Upload block
  - Processing status block
- Footer:
  - Legal/support links

### 4.2 Admin Shell
- Header:
  - Logo slot
  - Global search slot
  - Notification slot
  - Profile/account slot
- Body:
  - Left nav rail
  - Main work area
- Footer (optional):
  - Build/version/info

## 5) DOM/Div Frame (Structure Only)

### 5.1 Upload Page

```html
<div class="app-shell public-shell">
  <header class="top-nav">
    <div class="brand-block"></div>
    <div class="utility-block"></div>
  </header>

  <main class="page upload-page">
    <section class="intro-section"></section>
    <section class="upload-section">
      <div class="upload-card">
        <div class="file-picker-row"></div>
        <div class="file-list-row"></div>
        <div class="consent-row"></div>
        <div class="action-row"></div>
      </div>
      <div class="status-card"></div>
    </section>
  </main>

  <footer class="app-footer"></footer>
</div>
```

### 5.2 Admin Dashboard

```html
<div class="app-shell admin-shell">
  <header class="top-nav"></header>

  <div class="body-layout">
    <aside class="sidebar-nav"></aside>

    <main class="main-content dashboard-page">
      <section class="kpi-row"></section>
      <section class="processing-queue"></section>
      <section class="webhook-timeline"></section>
      <section class="error-panel"></section>
    </main>
  </div>
</div>
```

### 5.3 Patients List

```html
<main class="main-content patients-page">
  <section class="page-header"></section>
  <section class="filter-toolbar"></section>
  <section class="table-container">
    <div class="patients-table"></div>
  </section>
</main>
```

### 5.4 Patient Detail

```html
<main class="main-content patient-detail-page">
  <section class="detail-header"></section>
  <section class="detail-grid">
    <div class="patient-info-card"></div>
    <div class="summary-card"></div>
  </section>
  <section class="raw-content-panel"></section>
</main>
```

## 6) Required Components and Responsibility

### Global Components
- `AppShell`
  - Owns page frame and route layout
- `TopNav`
  - Global navigation and utility actions
- `SidebarNav`
  - Admin section navigation
- `Footer`
  - Static legal/support links

### Upload Flow Components
- `UploadForm`
  - Holds file input, consent, and submit action
- `FileDropzone`
  - Accept/validate selected files
- `FileList`
  - Shows selected files and remove action
- `ConsentCheckbox`
  - Gate before submit
- `SubmissionStatus`
  - Displays current processing stage and errors

### Admin Components
- `KpiPanel`
  - Shows key counters (processing, failed, high urgency)
- `WebhookTimeline`
  - Event stream by submission
- `PatientsTable`
  - Sort/filter/paginate patient rows
- `PatientSummary`
  - Structured view of extracted fields
- `AssistantChat`
  - Prompt input + answer history

### Shared Components
- `AlertBanner`
- `Toast`
- `LoadingState`
- `EmptyState`
- `ErrorState`
- `Pagination`
- `Modal`

## 7) Frontend State Model

### 7.1 Upload State
- `idle`
- `file_selected`
- `validating`
- `submitting`
- `submitted`
- `processing`
- `completed`
- `failed`

### 7.2 Admin Data State
- `loading`
- `ready`
- `empty`
- `error`

### 7.3 Session State
- `anonymous`
- `authenticating`
- `authenticated`
- `session_expired`

## 8) API Contracts Required by Frontend

### 8.1 Upload
- `POST /upload`
  - Request: multipart form (`file`)
  - Response: `{ submissionId, status, message }`

### 8.2 Submission Status
- `GET /upload/status/:submissionId`
  - Response: `{ submissionId, status, step, recordId?, errors? }`

### 8.3 Admin Login
- `POST /admin/login`
  - Request: `{ username, password }`
  - Response: `{ success, token/session }`

### 8.4 Patients List
- `GET /patients?query=&urgency=&page=`
  - Response: `{ items: [], total, page, pageSize }`

### 8.5 Patient Detail
- `GET /patients/:id`
  - Response: structured patient record payload

### 8.6 Search
- `GET /search?q=&urgency=`
  - Response: `{ results: [] }`

### 8.7 Assistant
- `POST /api/assistant`
  - Request: `{ question, history }`
  - Response: `{ answer }`

## 9) Webhook-to-Frontend Flow (Behavior Only)

1. User submits file.
2. Frontend receives `submissionId` quickly.
3. Backend processing continues asynchronously.
4. Webhook updates backend submission status.
5. Frontend fetches status periodically using `submissionId`.
6. Frontend transitions status UI based on backend state.
7. On completion:
  - Public: show completion message
  - Admin: allow navigation to patient detail

## 10) Access Control Requirements

- Public routes must not expose patient record data.
- Admin routes must require authenticated session.
- If session expires, redirect to `/admin/login`.
- Admin-only components should not render for anonymous users.

## 11) Icon and Logo Slots (No Style Spec)

The frontend must reserve placement slots for:
- Brand logo in header
- Functional icons for: upload, success, warning, error, search, filter, user, notification

Design team decides icon set, look, and branding style. Frontend requirement is placement and behavior only.

## 12) Responsive Frame Requirements

- Public upload page:
  - Single-column frame on small screens
  - Multi-block layout on larger screens
- Admin pages:
  - Sidebar may collapse into drawer on small screens
  - Main content remains readable without horizontal scroll

## 13) Error and Edge-Case Behavior

- Invalid file type/size: block submit and show inline message
- Upload failure: retain selected file and allow retry
- Processing timeout: show delayed state and retry option
- API 401/403 on admin routes: redirect to login
- API 5xx: show recoverable error and retry action

## 14) Deliverables for Design Team

This frontend frame document is sufficient for UI design handoff if design team provides:
- visual style/theme
- typography and spacing system
- color system
- icon pack
- logo assets

Engineering will map designs onto the component/frame structure above.
