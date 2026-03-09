# Voluntary Product Accessibility Template® (VPAT®)
## BLACKSITE — GRC Security Assessment Platform

**Version:** VPAT 2.5 ACR (Accessibility Conformance Report)
**Date:** 2026-03-09
**Product:** BLACKSITE GRC Platform (Web Application)
**Version Assessed:** Current (build date 2026-03-09)
**Prepared By:** BLACKSITE Development Team
**Contact:** admin@borisov.network

---

## Applicable Standards/Guidelines

This report covers conformance with the following accessibility standards:

- **WCAG 2.1** — Web Content Accessibility Guidelines, Levels A and AA
- **Section 508** — 36 CFR Part 1194 (2018 refresh, aligns with WCAG 2.1 AA)
- **EN 301 549** — European Standard for ICT Accessibility (v3.2.1)

---

## Terms Used in This Report

| Term | Meaning |
|------|---------|
| **Supports** | The functionality of the product meets the criterion without known defects |
| **Partially Supports** | Some functionality meets the criterion; known deficiencies exist |
| **Does Not Support** | The functionality does not meet the criterion |
| **Not Applicable** | The criterion is not relevant to this product |
| **Not Evaluated** | The criterion has not been evaluated |

---

## WCAG 2.1 Report

### Table 1: Success Criteria, Level A

| Criterion | Conformance Level | Remarks |
|-----------|------------------|---------|
| **1.1.1 Non-text Content** | Supports | All images include descriptive `alt` attributes. Icon-only buttons include `aria-label`. Color-only status indicators include `aria-label`. |
| **1.2.1 Audio-only and Video-only (Prerecorded)** | Not Applicable | Product contains no audio or video content. |
| **1.2.2 Captions (Prerecorded)** | Not Applicable | No multimedia content present. |
| **1.2.3 Audio Description or Media Alternative (Prerecorded)** | Not Applicable | No multimedia content present. |
| **1.3.1 Info and Relationships** | Supports | Semantic HTML used throughout. Tables include `scope` attributes on headers. Form inputs are associated with labels via `for`/`id` or `aria-label`. ARIA roles (`role="dialog"`, `role="tab"`, `role="tabpanel"`) applied to custom components. |
| **1.3.2 Meaningful Sequence** | Supports | Content is presented in a logical reading order in source markup. |
| **1.3.3 Sensory Characteristics** | Supports | Instructions do not rely solely on shape, size, color, or location. |
| **1.4.1 Use of Color** | Supports | Status indicators include both color and text labels or `aria-label` attributes. Color is not the sole means of conveying information. |
| **1.4.2 Audio Control** | Not Applicable | No auto-playing audio present. |
| **2.1.1 Keyboard** | Partially Supports | Primary navigation and most interactive controls are keyboard-accessible. Some complex AJAX interactions (file uploads, drag-and-drop) may have keyboard limitations. Full keyboard regression testing is in progress. |
| **2.1.2 No Keyboard Trap** | Supports | Modal dialogs implement focus traps with Escape key dismissal and focus restoration to trigger element. |
| **2.1.4 Character Key Shortcuts** | Not Applicable | No single-character key shortcuts are implemented. |
| **2.2.1 Timing Adjustable** | Partially Supports | Session idle timeout enforced via Authelia (configurable). Application-layer timeout warning is implemented. Users can extend sessions. |
| **2.2.2 Pause, Stop, Hide** | Supports | No auto-moving, auto-updating, or auto-scrolling content present. |
| **2.3.1 Three Flashes or Below Threshold** | Supports | No flashing content present. |
| **2.4.1 Bypass Blocks** | Supports | Skip navigation link ("Skip to main content") is the first focusable element on every page. |
| **2.4.2 Page Titled** | Supports | All pages include a descriptive `<title>` element that includes the application name and page context. |
| **2.4.3 Focus Order** | Supports | Focus order follows a logical sequence. Modal dialogs move focus to the first focusable element on open and restore focus on close. |
| **2.4.4 Link Purpose (In Context)** | Supports | All links include descriptive text or `aria-label`. External links include context about destination. Symbol-only links include `aria-label`. |
| **2.5.1 Pointer Gestures** | Not Applicable | No multi-point or path-based gestures required. |
| **2.5.2 Pointer Cancellation** | Supports | Click events are on `mouseup`/standard click; no down-event-only actions. |
| **2.5.3 Label in Name** | Supports | Visible labels match or are contained within accessible names. |
| **2.5.4 Motion Actuation** | Not Applicable | No motion-activated functionality present. |
| **3.1.1 Language of Page** | Supports | `lang="en"` declared on the `<html>` element. |
| **3.2.1 On Focus** | Supports | No context changes occur on focus alone. |
| **3.2.2 On Input** | Partially Supports | Auto-submitting `<select>` elements are labeled to inform users of auto-apply behavior (`aria-label="… (auto-applies on change)"`). Users are informed of the behavior via label before interacting. |
| **3.3.1 Error Identification** | Partially Supports | Most form errors are displayed inline. Some API error states surface as toast messages only; association with specific fields is not always present. |
| **3.3.2 Labels or Instructions** | Supports | All form inputs have associated labels. Required fields include `aria-required="true"`. Decorative asterisks are marked `aria-hidden="true"`. |
| **4.1.1 Parsing** | Supports | HTML is validated. No duplicate IDs on interactive elements. ARIA attributes are used per specification. |
| **4.1.2 Name, Role, Value** | Supports | All interactive elements have accessible names, roles, and states. Custom components (tabs, modals, accordions) use appropriate ARIA roles and properties. |

---

### Table 2: Success Criteria, Level AA

| Criterion | Conformance Level | Remarks |
|-----------|------------------|---------|
| **1.2.4 Captions (Live)** | Not Applicable | No live multimedia content. |
| **1.2.5 Audio Description (Prerecorded)** | Not Applicable | No multimedia content. |
| **1.3.4 Orientation** | Supports | Interface is functional in both portrait and landscape orientations. |
| **1.3.5 Identify Input Purpose** | Partially Supports | Standard profile fields (name, email) do not yet include `autocomplete` attributes. Administrative and compliance forms are system-specific and not applicable to `autocomplete` purpose tokens. |
| **1.4.3 Contrast (Minimum)** | Not Evaluated | Color palette has been designed for high contrast (dark theme default). Formal contrast ratio measurement against all text/background combinations has not been completed. Evaluation in progress. |
| **1.4.4 Resize Text** | Supports | Interface uses relative units (em, rem). Text resizes up to 200% without loss of content or functionality. |
| **1.4.5 Images of Text** | Supports | No images of text are used. All text is rendered as HTML. |
| **1.4.10 Reflow** | Partially Supports | Most pages reflow at 320px CSS width without horizontal scrolling. Complex data tables (control assessments, audit logs) require horizontal scroll at narrow widths. |
| **1.4.11 Non-text Contrast** | Not Evaluated | UI components (buttons, form controls, focus indicators) have been designed with contrast in mind. Formal measurement pending. |
| **1.4.12 Text Spacing** | Supports | No loss of content or functionality when text spacing properties are overridden per criterion. |
| **1.4.13 Content on Hover or Focus** | Supports | Tooltips (`title` attributes) are dismissible and persistent. No content on hover that obscures other content. |
| **2.4.5 Multiple Ways** | Supports | Navigation sidebar, page titles, and URL structure provide multiple means of locating pages. |
| **2.4.6 Headings and Labels** | Supports | Descriptive headings used throughout. Form labels are descriptive and associated with controls. |
| **2.4.7 Focus Visible** | Partially Supports | Browser default focus indicators are present. Custom focus styles are implemented in some areas. Comprehensive styled focus rings across all interactive elements are in progress. |
| **3.1.2 Language of Parts** | Not Applicable | All content is in English. No foreign-language passages. |
| **3.2.3 Consistent Navigation** | Supports | Navigation sidebar and header are consistent across all pages. |
| **3.2.4 Consistent Identification** | Supports | Components that have the same function are identified consistently throughout the interface. |
| **3.3.3 Error Suggestion** | Partially Supports | Most validation errors include suggested corrections. Some API-level errors surface generic messages without specific remediation guidance. |
| **3.3.4 Error Prevention (Legal, Financial, Binding)** | Supports | Destructive actions (deletion, status changes) require confirmation. ATO decisions and authorization actions include explicit confirmation dialogs. |
| **4.1.3 Status Messages** | Supports | Dynamic content regions include `aria-live="polite"` to announce status updates to screen reader users. Toast notifications are announced. |

---

## Section 508 Report

### Chapter 3: Functional Performance Criteria

| Criteria | Conformance | Remarks |
|----------|-------------|---------|
| 302.1 Without Vision | Partially Supports | Screen reader support implemented via ARIA. Full screen reader regression testing (NVDA, JAWS, VoiceOver) in progress. |
| 302.2 With Limited Vision | Supports | Interface scales to 200% text size. High-contrast dark theme is default. |
| 302.3 Without Perception of Color | Supports | Information is not conveyed by color alone. |
| 302.4 Without Hearing | Not Applicable | No audio content. |
| 302.5 Without Speech | Not Applicable | No speech input required. |
| 302.6 With Limited Manipulation | Partially Supports | All controls are keyboard-accessible. Touch target sizes are generally adequate. Full testing in progress. |
| 302.7 With Limited Reach and Strength | Supports | No time limits that cannot be extended. No actions requiring sustained physical effort. |
| 302.8 With Limited Language | Not Applicable | Product is designed for GRC professionals; simplified language version not applicable. |
| 302.9 With Limited Cognitive | Not Applicable | Product is a specialized professional tool. |

---

### Chapter 4: Hardware

**Not Applicable** — BLACKSITE is a web application. No hardware component.

---

### Chapter 5: Software

| Criteria | Conformance | Remarks |
|----------|-------------|---------|
| 502 Interoperability with Assistive Technology | Partially Supports | Web-based; relies on browser accessibility APIs. ARIA implementation follows WAI-ARIA 1.2 specification. |
| 503 Applications | Supports | Application-level accessibility features implemented per WCAG 2.1 AA. |

---

### Chapter 6: Support Documentation and Services

| Criteria | Conformance | Remarks |
|----------|-------------|---------|
| 601.1 Scope | Supports | This VPAT constitutes the accessibility conformance documentation. |
| 602 Support Documentation | Partially Supports | User documentation is in development. Accessibility-specific guidance will be included. |
| 603 Support Services | Supports | Support is available via the platform administrator. Accessibility issues can be reported via the Accessibility Statement page. |

---

## Known Limitations and Remediation Roadmap

| Issue | Status | Target |
|-------|--------|--------|
| Color contrast ratios not formally measured | In Progress | Q2 2026 |
| Keyboard regression testing (NVDA, JAWS, VoiceOver) | Planned | Q2 2026 |
| `autocomplete` attributes on profile fields | Planned | Q2 2026 |
| Focus ring styling consistency | In Progress | Q2 2026 |
| Complex data tables on narrow viewports | Known limitation | Q3 2026 |

---

## Legal Disclaimer

*This VPAT was prepared based on evaluation by the BLACKSITE development team. It represents a good-faith assessment of the product's conformance as of the date indicated. Conformance claims reflect testing performed on the current build using Chrome and Firefox desktop browsers. Screen reader testing with NVDA/JAWS/VoiceOver is ongoing. This document will be updated as issues are identified and remediated.*

*VPAT® is a registered trademark of the Information Technology Industry Council (ITI).*
