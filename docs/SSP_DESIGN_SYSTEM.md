# SSP Document Design System
**BLACKSITE GRC Platform — TheKramerica**
**Version:** 1.0 | **Date:** 2026-03-01 | **Owner:** Dan Kessler

---

## 1. Design Principles

| Principle | Rationale |
|-----------|-----------|
| **Grayscale-first** | Prepared for color laser and black-and-white print. All color pairs with a distinct grayscale value. No meaning conveyed by hue alone. |
| **Variable-driven** | Org name, system name, version, classification, dates, and owner are single-source tokens. Editing any takes seconds. |
| **Content density** | GRC documents are long. Tables and lists must compress without sacrificing scan-ability. |
| **Regulatory legibility** | Reviewers scan for control IDs and status. These must dominate visually at a glance. |
| **Board-ready** | Cover page and section headings use proportional serif typography. Tables and code use monospace. |

---

## 2. Style Guide Tokens

### 2.1 Document Variables (Jinja2 / Template)

```
{{ org_name }}        → "TheKramerica"
{{ system_name }}     → "Advanced Asset Management Framework"
{{ system_abbr }}     → "AAMF"
{{ doc_version }}     → "1.0"
{{ doc_date }}        → "2026-03-01"
{{ doc_owner }}       → "Dan Kessler"
{{ classification }}  → "Controlled Unclassified Information (CUI)"
{{ generated_at }}    → "2026-03-01 00:33 UTC"
{{ prepared_for }}    → "AAMF Security Assessment Team <sca@thekramerica.com>"
{{ framework }}       → "NIST SP 800-53 Rev 5"
{{ ato_status }}      → "Authorized to Operate (ATO)"
{{ ato_expiry }}      → "2028-01-15"
{{ brand_tagline }}   → "Governance, Risk & Compliance"
```

### 2.2 Typography

| Token | Value | Usage |
|-------|-------|-------|
| `--font-serif`  | `"Georgia", "Times New Roman", serif` | Cover title, H1, H2 |
| `--font-sans`   | `"Segoe UI", "Helvetica Neue", Arial, sans-serif` | Body, captions, labels |
| `--font-mono`   | `"Courier New", "Lucida Console", monospace` | Control IDs, code, hashes |
| `--size-base`   | `11pt` | Body text |
| `--size-small`  | `9pt` | Table cells, captions, footer |
| `--size-h1`     | `22pt` | Document title on cover |
| `--size-h2`     | `16pt` | Section titles (numbered) |
| `--size-h3`     | `12pt` | Sub-section titles |
| `--size-h4`     | `11pt` | Label/caption tier |
| `--lh-body`     | `1.6` | Paragraph line height |
| `--lh-table`    | `1.4` | Table cell line height |

### 2.3 Color Palette (with grayscale equivalents)

| Token | Hex | Grayscale equiv | Use |
|-------|-----|-----------------|-----|
| `--clr-ink`       | `#111111` | black | Primary text |
| `--clr-muted`     | `#555555` | 34% gray | Secondary text, labels |
| `--clr-ghost`     | `#888888` | 53% gray | Captions, placeholder |
| `--clr-rule`      | `#CCCCCC` | 80% gray | Table borders, dividers |
| `--clr-bg-alt`    | `#F5F5F5` | 96% gray | Table header, callout bg |
| `--clr-bg-stripe` | `#FAFAFA` | 98% gray | Alternating table row |
| `--clr-accent`    | `#1A3A6B` | 23% gray | Headings, cover bar, links |
| `--clr-accent-lt` | `#EEF3FB` | 94% gray | Heading bg, light callouts |
| `--clr-critical`  | `#B71C1C` | 27% gray | CRITICAL_GAP badge |
| `--clr-high`      | `#E65100` | 40% gray | HIGH_GAP badge |
| `--clr-medium`    | `#F57F17` | 57% gray | MEDIUM_GAP badge |
| `--clr-adequate`  | `#1B5E20` | 23% gray | ADEQUATE badge, pass |
| `--clr-na`        | `#616161` | 38% gray | N/A, deferred |

**Grayscale rule:** Critical = darkest (black border), High = dark gray, Medium = mid gray, Adequate = light gray.

### 2.4 Spacing Scale

```
--sp-xs   4px
--sp-sm   8px
--sp-md   16px
--sp-lg   24px
--sp-xl   40px
--sp-2xl  60px
```

---

## 3. Page Layout Spec

### 3.1 Print Dimensions

| Property | Value |
|----------|-------|
| Page size | US Letter (8.5 × 11 in) |
| Top margin | 1 in (72pt) — reserved for running header |
| Bottom margin | 0.9 in (64pt) — reserved for footer |
| Left margin | 1.25 in (90pt) |
| Right margin | 1 in (72pt) |
| Content width | 6.25 in (450pt) |

### 3.2 Running Header (print only)

```
┌─────────────────────────────────────────────────────────────────┐
│  [CLASSIFICATION]              [ORG NAME] · [SYSTEM ABBR] SSP   │
│  ─────────────────────────────────────────────────────────────  │
```

- **Left:** Classification marking in `--clr-critical` (CUI) or `--clr-adequate` (Unclassified).
- **Right:** `{{ org_name }} · {{ system_abbr }} SSP`
- Separator: 0.5pt rule, `--clr-rule`
- Font: `--font-sans`, 8pt, `--clr-muted`
- Suppressed on cover page and ToC.

### 3.3 Running Footer (print only)

```
│  ─────────────────────────────────────────────────────────────  │
│  {{ classification }}    │    {{ doc_date }} v{{ version }}    │    Page N of M  │
└─────────────────────────────────────────────────────────────────┘
```

- Three zones separated by `|` pipes.
- Font: `--font-sans`, 8pt, `--clr-muted`
- Page number: right-aligned.

### 3.4 CSS Print Rules

```css
@page {
  size: letter;
  margin: 1in 1in 0.9in 1.25in;
  @top-left   { content: var(--classification, "UNCLASSIFIED"); font: 8pt sans-serif; color: #888; }
  @top-right  { content: var(--org-name, "TheKramerica") " · SSP";  font: 8pt sans-serif; color: #888; }
  @bottom-left   { content: var(--classification); font: 8pt sans-serif; color: #888; }
  @bottom-center { content: var(--doc-date) " v" var(--doc-version); font: 8pt sans-serif; }
  @bottom-right  { content: "Page " counter(page) " of " counter(pages); font: 8pt sans-serif; }
}

/* Cover page: suppress running head/foot on page 1 */
@page :first { margin: 0.75in 1in; @top-left { content: ""; } @top-right { content: ""; } }

/* Widow/orphan control */
p, li        { widows: 3; orphans: 3; }
h2, h3       { page-break-after: avoid; }
tr           { page-break-inside: avoid; }
.section-break { page-break-before: always; }
```

---

## 4. Cover Page Spec

### 4.1 Layout

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│   [Left accent bar: 4px solid --clr-accent, full height]       │
│                                                                │
│   ORG NAME · BRAND TAGLINE        (0.75em, ALL CAPS, muted)   │
│   ─────────────────────────────                               │
│                                                                │
│   [System Name]                   (22pt serif, bold, ink)      │
│   System Security Plan (SSP)      (14pt serif, muted)          │
│                                                                │
│   ─────────────────────────────                               │
│                                                                │
│   Organization      TheKramerica                              │
│   Version           1.0                                        │
│   Document Date     2026-03-01 00:33 UTC                       │
│   Prepared For      AAMF Security Assessment Team              │
│   System            Advanced Asset Management Framework (AAMF) │
│   Owner             Dan Kessler                                │
│   Framework         NIST SP 800-53 Rev 5                       │
│   Reference         NIST SP 800-18                             │
│                                                                │
│   ─────────────────────────────                               │
│                                                                │
│   [CLASSIFICATION BANNER]                                      │
│   Controlled Unclassified Information (CUI)                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 4.2 Cover Metadata Table

Two-column key/value table, no outer border, internal row separators only.

```css
.cover-meta td:first-child {
  width: 160px;
  font-size: 0.8em;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--clr-muted);
  padding: 6px 16px 6px 0;
  vertical-align: top;
}
.cover-meta td:last-child {
  font-size: 0.92em;
  color: var(--clr-ink);
  padding: 6px 0;
  font-weight: 500;
}
.cover-meta tr + tr td { border-top: 1px solid var(--clr-bg-alt); }
```

### 4.3 Classification Banner

```css
.classification-banner {
  margin-top: 36px;
  padding: 10px 20px;
  background: var(--clr-accent-lt);
  border: 1px solid var(--clr-accent);
  border-radius: 3px;
  font-size: 0.82em;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  text-align: center;
  color: var(--clr-accent);
}
/* CUI variant */
.classification-banner.cui { border-color: #B71C1C; color: #B71C1C; background: #FFF5F5; }
```

---

## 5. Section & Heading Hierarchy

| Level | Element | CSS | Behavior |
|-------|---------|-----|----------|
| H2 | `<div class="ssp-section-title">` | 13pt serif bold, accent left-bar 3px, background accent-lt, padding 10px 16px, margin-top 32px | Always on new page for numbered sections 1–10 |
| H3 | `<h3 class="ssp-h3">` | 11pt sans-serif bold, uppercase, letter-spacing 0.1em, muted color, border-bottom 1px rule | Stays with following paragraph (page-break-after: avoid) |
| H4 | `<span class="ssp-label">` | 8pt sans-serif, ALL CAPS, letter-spacing 0.15em, ghost color | Inline label before data field |
| Body | `<div class="prose">` | 11pt, line-height 1.6, justified | Standard paragraph block |
| Note | `<div class="callout">` | See §6 below | Blue-accent left bar |
| Code | `<code>`, `<pre>` | mono, 9.5pt, bg #F5F5F5, border 1px rule | Never breaks inside code span |

---

## 6. Callout / Annotation Component

```css
/* Standard note (informational) */
.callout {
  border-left: 3px solid var(--clr-accent);
  background: var(--clr-accent-lt);
  padding: 12px 16px;
  margin: 16px 0;
  font-size: 0.88em;
  line-height: 1.55;
  border-radius: 0 4px 4px 0;
}

/* Warning (incomplete / placeholder) */
.callout-warn {
  border-left-color: var(--clr-medium);
  background: #FFF8E1;
}

/* Pass / adequate */
.callout-pass {
  border-left-color: var(--clr-adequate);
  background: #F1F8F2;
}

/* Fail / critical gap */
.callout-fail {
  border-left-color: var(--clr-critical);
  background: #FFF5F5;
}
```

---

## 7. Table Component Spec

### 7.1 Standard Data Table

```css
table.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85em;
  line-height: var(--lh-table);
  page-break-inside: auto;
}
table.data-table thead tr {
  background: var(--clr-bg-alt);
  border-top: 2px solid var(--clr-accent);
  border-bottom: 1.5px solid var(--clr-rule);
}
table.data-table th {
  padding: 8px 12px;
  text-align: left;
  font-size: 0.82em;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--clr-muted);
  font-weight: 700;
  white-space: nowrap;
}
table.data-table td {
  padding: 7px 12px;
  border-bottom: 1px solid var(--clr-rule);
  vertical-align: top;
  color: var(--clr-ink);
}
/* Alternating rows */
table.data-table tbody tr:nth-child(even) td {
  background: var(--clr-bg-stripe);
}
/* Hover (screen only) */
@media screen {
  table.data-table tbody tr:hover td { background: var(--clr-accent-lt); }
}
/* Keep rows together on print */
@media print {
  table.data-table tr { page-break-inside: avoid; }
  /* Repeat header on each page */
  table.data-table thead { display: table-header-group; }
}
```

### 7.2 Control Implementation Table

Additional rules on top of `.data-table`:

```css
/* Control ID column: monospace, no-wrap, fixed width */
.ctrl-table td.ctrl-id {
  font-family: var(--font-mono);
  font-size: 0.88em;
  white-space: nowrap;
  width: 96px;
  font-weight: 600;
}
/* Status grade badges */
.ctrl-table .grade-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 0.78em;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.grade-COMPLETE        { background: #E8F5E9; color: #1B5E20; border: 1px solid #A5D6A7; }
.grade-PARTIAL         { background: #E3F2FD; color: #0D47A1; border: 1px solid #90CAF9; }
.grade-INSUFFICIENT    { background: #FFF3E0; color: #E65100; border: 1px solid #FFCC80; }
.grade-NOT_FOUND       { background: #FCE4EC; color: #B71C1C; border: 1px solid #EF9A9A; }
.grade-NA              { background: #F5F5F5; color: #616161; border: 1px solid #BDBDBD; }

/* Narrative column: limits height on screen, full height on print */
@media screen {
  .ctrl-table td.narrative { max-width: 420px; overflow: hidden; display: -webkit-box;
    -webkit-line-clamp: 3; -webkit-box-orient: vertical; }
}
```

### 7.3 Long-Table Wrap Rules

- `word-break: break-word` on narrative and description columns.
- `overflow-wrap: anywhere` on URL and hash columns.
- `white-space: normal` on all cells (no cell should ever overflow the page).
- Tables wider than 600pt use `@media print { font-size: 8.5pt; }` to compress.

---

## 8. Revision History Table Format

Appears on page 2 of every SSP, after the cover page.

```html
<section class="section-break" id="revision-history">
  <h2 class="ssp-section-title">Revision History</h2>
  <table class="data-table rev-history-table">
    <thead>
      <tr>
        <th style="width:60px">Version</th>
        <th style="width:96px">Date</th>
        <th style="width:140px">Author</th>
        <th style="width:120px">Change Type</th>
        <th>Summary of Changes</th>
        <th style="width:120px">Reviewed By</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="font-family:monospace">1.0</td>
        <td>2026-03-01</td>
        <td>Dan Kessler</td>
        <td><span class="change-badge initial">Initial Release</span></td>
        <td>First production version. Full NIST 800-53r5 baseline for AAMF.</td>
        <td>SCA Team</td>
      </tr>
      {# Additional rows appended on each revision #}
    </tbody>
  </table>
  <p class="prose" style="font-size:0.82em;color:var(--clr-muted);margin-top:8px">
    Changes are tracked per NIST SP 800-18 §4.3. All revisions require ISSO review
    before distribution. Major revisions (X.0) require AO notification.
  </p>
</section>
```

**Change type badges:**

```css
.change-badge {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 2px;
  font-size: 0.78em;
  font-weight: 600;
  text-transform: uppercase;
}
.change-badge.initial  { background: #E3F2FD; color: #0D47A1; border: 1px solid #90CAF9; }
.change-badge.minor    { background: #E8F5E9; color: #1B5E20; border: 1px solid #A5D6A7; }
.change-badge.major    { background: #FFF3E0; color: #E65100; border: 1px solid #FFCC80; }
.change-badge.security { background: #FCE4EC; color: #B71C1C; border: 1px solid #EF9A9A; }
.change-badge.admin    { background: #F5F5F5; color: #616161; border: 1px solid #BDBDBD; }
```

---

## 9. Appendix System Spec

### 9.1 Controls Only Mode

Appendix section at end of SSP contains:
1. **Heading:** `Appendices` (H2 section heading)
2. **Sub-heading:** `Appendix Registry` (H3, with explanatory note: "reference listing only; files not embedded")
3. **Appendix Registry Table** — columns:

| Column | Width | Notes |
|--------|-------|-------|
| Label | 90px | "Appendix A" — bold |
| Document ID | 100px | `DOC-xxxxxx` — monospace |
| Title | auto | Full document title |
| Type | 80px | Uppercase: SSP, SAR, FIPS199, etc. |
| Version | 60px | |
| Date | 80px | ISO `YYYY-MM-DD` |
| Owner | 110px | |
| Storage Reference | 140px | Filename or path — monospace, word-break |

Registry table uses `.data-table` with repeat-header on print.

No embedded files. Each row may include a page reference note in the Storage Reference column if the document is physically present in an accompanying binder.

### 9.2 Full Report Mode

1. **Appendix Registry Table** — same as Controls Only, at the top of the Appendices section.
2. After the registry, each appendix that has an embeddable file gets its own page-break section:

```
╔══════════════════════════════════════════════════════════╗
║  Appendix A · DOC-AB12CD                                 ║
║  Information Type Table (NIST SP 800-60)                 ║
║  FIPS199 · Version 1.0 · 2026-03-01 · Owner: Dan Kessler║
╠══════════════════════════════════════════════════════════╣
║  [Embedded PDF viewer: full width, 900px height]         ║
║  [or: Image rendered inline at 100% width]               ║
║  [or: Preformatted text block for .txt files]            ║
╚══════════════════════════════════════════════════════════╝
```

Files not embeddable (DOCX, XLSX) get a **placeholder block** with:
- Document metadata
- Storage reference
- Note: "Binary format — locate at storage reference above"

### 9.3 Appendix Label Scheme

```
A, B, C, … Z, AA, AB, … AZ, BA, …
```

Label assigned sequentially: ATO documents first (sorted by doc_type, title), then evidence artifacts (sorted by type, title).

### 9.4 Appendix Registry — Print Behavior

```css
.appendix-registry thead { display: table-header-group; }  /* repeat on each page */
.appendix-registry tr    { page-break-inside: avoid; }
.appendix-section        { page-break-before: always; }
.appendix-section:first-child { page-break-before: always; } /* even first */
```

---

## 10. Sample Rendering — Excerpt

The following shows the excerpt content rendered with this design system.

---

### COVER PAGE

```
┌────────────────────────────────────────────────────────────────────────┐
│ ╠ TheKramerica · Governance, Risk & Compliance             [accent bar] │
│   ────────────────────────────────────────────────                     │
│                                                                         │
│   Advanced Asset Management Framework                [22pt serif bold]  │
│   System Security Plan (SSP)                         [14pt serif muted] │
│                                                                         │
│   ────────────────────────────────────────────────                     │
│   Organization       TheKramerica                                       │
│   Version            1.0                                                │
│   Document Date      2026-03-01 00:33 UTC                               │
│   Prepared For       AAMF Security Assessment Team                      │
│                      <sca@thekramerica.com>                             │
│   System             Advanced Asset Management Framework (AAMF)         │
│   Owner              Dan Kessler                                        │
│   Framework          NIST SP 800-53 Rev 5                               │
│   Reference          NIST SP 800-18                                     │
│   ────────────────────────────────────────────────                     │
│   ╔══════════════════════════════════════════════╗                      │
│   ║  CONTROLLED UNCLASSIFIED INFORMATION (CUI)  ║                      │
│   ╚══════════════════════════════════════════════╝                      │
└────────────────────────────────────────────────────────────────────────┘
```

*Page break*

---

### REVISION HISTORY

| Version | Date | Author | Change Type | Summary | Reviewed By |
|---------|------|--------|-------------|---------|-------------|
| 1.0 | 2026-03-01 | Dan Kessler | **Initial Release** | First production version. Full NIST 800-53r5 baseline for AAMF. | SCA Team |

---

### TABLE OF CONTENTS

- 1. System Identification
- 2. Security Categorization (FIPS 199)
- 3. System Overview
- 4. Operational Environment
- 5. System Boundary
- 6. Roles & Responsibilities
- 7. Information Types
- 8. Control Implementation
- 9. Plan of Action & Milestones (POA&M)
- 10. Interconnections
- Appendices

---

### 1. System Identification

*[Rendered as a two-column definition table, `.data-table`]*

| Field | Value |
|-------|-------|
| **System Name** | Advanced Asset Management Framework |
| **Abbreviation** | `AAMF` |
| **System Type** | Major Application |
| **Operational Environment** | On-Premises |
| **System Owner** | Dan Kessler |
| **Owner Email** | d.kessler@thekramerica.com |
| **Authorization Status** | Authorized to Operate (ATO) |
| **Authorization Date** | 2025-01-15 |
| **Authorization Expiry** | 2028-01-15 |
| **Assessment Filename** | `System_Security_Plan_AAMF.pdf` |
| **Assessment Date** | 2025-01-10 09:00 UTC |

---

### 2. Security Categorization (FIPS 199)

*[Callout block — `.callout`]*

> Security categorization performed per FIPS 199 and NIST SP 800-60.

*[Impact level table — `.data-table`, with grade-adequate/grade-NOT_FOUND shading]*

| Security Objective | Impact Level | Description |
|--------------------|-------------|-------------|
| **Confidentiality** | `HIGH` | Preserving authorized restrictions on information access and disclosure. |
| **Integrity** | `HIGH` | Guarding against improper information modification or destruction. |
| **Availability** | `HIGH` | Ensuring timely and reliable access to information. |
| **Overall Impact** | `HIGH` | Maximum impact level across all security objectives (FIPS 199 §3). |

*[SC formula block — `.callout .callout-fail` (HIGH = critical posture)]*

> **SC AAMF = {(Confidentiality, HIGH), (Integrity, HIGH), (Availability, HIGH)}**

---

### 8. Control Implementation (excerpt)

*[Section intro callout — `.callout`]*

> Control assessment performed against NIST SP 800-53 Rev 5. Grades: **COMPLETE** · **PARTIAL** · **INSUFFICIENT** · **NOT FOUND** · **N/A**

*[Controls table — `.data-table ctrl-table`]*

| Control ID | Title | Status | Grade | Implementation Narrative |
|------------|-------|--------|-------|--------------------------|
| `AC-1` | Policy and Procedures | implemented | **COMPLETE** | The AAMF enforces access control through role-based access controls (RBAC) aligned to asset ownership hierarchies. Asset Stewards may only view and modify assets within their assigned organizational units. Privileged access (bulk import, system config) is restricted to Asset Administrators… |
| `AC-10` | Concurrent Session Control | implemented | **COMPLETE** | The AAMF enforces access control through role-based access controls (RBAC) aligned to asset ownership hierarchies. Asset Stewards may only view and modify assets within their assigned organizational units… |
| `SR-9` | Tamper Resistance and Detection | implemented | **COMPLETE** | Supply chain risk management is implemented for all AAMF hardware and software components. Approved vendor lists are maintained and reviewed annually. Software bills of materials (SBOMs) are maintained for all AAMF application components… |
| `SR-9.1` | SDLC Multiple Stages | implemented | **COMPLETE** | Supply chain risk management is implemented across all AAMF development lifecycle phases. Software components are verified against known-good baselines at each stage… |

---

### APPENDICES — Controls Only Mode

#### Appendix Registry
*(Reference listing only — files not embedded in this output)*

| Label | Document ID | Title | Type | Version | Date | Owner | Storage Reference |
|-------|------------|-------|------|---------|------|-------|------------------|
| Appendix A | `DOC-AB12CD` | Information Type Inventory (NIST SP 800-60) | FIPS199 | 1.0 | 2026-01-15 | Dan Kessler | `AAMF_InfoTypes_v1.pdf` |
| Appendix B | `DOC-EF34GH` | Interconnection Security Agreements | ISA | 1.0 | 2026-01-20 | Dan Kessler | `AAMF_ISA_v1.pdf` |

---

### APPENDICES — Full Report Mode

#### Appendix Registry
*(Embedded copies follow this registry)*

*[Same registry table as above]*

---

*[Page break — Appendix A]*

**Appendix A · DOC-AB12CD**
Information Type Inventory (NIST SP 800-60)
FIPS199 · Version 1.0 · 2026-01-15 · Owner: Dan Kessler

```
[PDF embedded as base64 <object> tag, 100% width, 900px height]
```

---

### DOCUMENT FOOTER

```
[Classification: CUI]   |   [2026-03-01 v1.0]   |   Page 1 of N
Generated by BLACKSITE GRC Platform · TheKramerica · 2026-03-01 00:33 UTC
NIST SP 800-53 Rev 5 · FIPS 199 · NIST SP 800-18
```

---

## 11. Implementation Notes

### Template Variables Block (top of ssp_export.html)
```jinja2
{% set org_name      = brand %}
{% set system_name   = linked_system.name if linked_system else candidate.name %}
{% set system_abbr   = linked_system.abbreviation if linked_system else '' %}
{% set doc_version   = assessment.version | default('1.0') %}
{% set doc_date      = generated_at %}
{% set doc_owner     = linked_system.owner if linked_system else '' %}
{% set classification = linked_system.classification | default('Controlled Unclassified Information (CUI)') %}
{% set ato_status    = linked_system.auth_status if linked_system else '' %}
{% set ato_expiry    = linked_system.auth_expiry if linked_system else '' %}
{% set framework     = 'NIST SP 800-53 Rev 5' %}
```

### CSS Variable Injection
```html
<style>
  :root {
    --classification: "{{ classification }}";
    --org-name: "{{ org_name }}";
    --system-abbr: "{{ system_abbr }}";
    --doc-date: "{{ doc_date[:10] }}";
    --doc-version: "{{ doc_version }}";
  }
</style>
```

---

*Design System v1.0 · BLACKSITE GRC · TheKramerica · 2026-03-01*
