---
name: Course Digital Twin Professor Console
description: An evidence-led release dossier for professor-controlled tutor configuration.
colors:
  ink: "#101828"
  cobalt: "#1d4ed8"
  cobalt-soft: "#eef4ff"
  paper: "#ffffff"
  workspace: "#f5f7fb"
  muted: "#667085"
  rule: "#d9e0ea"
  rule-strong: "#98a2b3"
  success: "#087a55"
  success-soft: "#ecfdf3"
  warning: "#a15c08"
  warning-soft: "#fff7e6"
  destructive: "#b42318"
  destructive-soft: "#fff2f0"
typography:
  headline:
    fontFamily: "Geist Variable, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 620
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Geist Variable, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 620
    lineHeight: 1.35
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Geist Variable, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "0"
  label:
    fontFamily: "Geist Variable, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 650
    lineHeight: 1.35
    letterSpacing: "0.1em"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  2xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.md}"
    padding: "8px 14px"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "8px 14px"
  stage-active:
    backgroundColor: "{colors.cobalt-soft}"
    textColor: "{colors.cobalt}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
  status-chip:
    backgroundColor: "{colors.workspace}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "3px 7px"
---

# Design System: Course Digital Twin Professor Console

## Overview

**Creative North Star: "The Course Release Dossier"**

The professor console combines an academic review dossier with the decisiveness
of a code-review merge gate. It is precise, calm, and accountable: every action
is visibly connected to evidence, policy, or release impact. The screen should
feel like one continuous working document, not a collection of dashboard cards.

The interface uses compact editorial hierarchy, ruled divisions, numbered
decision references, and restrained status color. It refuses generic AI-chat
styling, opaque automation, decorative SaaS polish, and invented intelligence.

**Key Characteristics:**

- A persistent five-stage release route with one selected work surface.
- Evidence and workflow trace remain adjacent to the current decision.
- Flat paper surfaces separated by rules, spacing, and tonal bands.
- Cobalt marks interaction; amber, red, and green communicate status only.
- All state is expressed in text as well as color.

## Colors

The palette is cool paper and navy ink, with one operational cobalt and narrowly
reserved semantic colors.

### Primary

- **Decision Cobalt:** Marks the selected stage, links, focus, and the current
  operational action.
- **Dossier Ink:** Carries headings, primary controls, and release-critical text.

### Neutral

- **Review Paper:** The uninterrupted primary working surface.
- **Cool Workspace:** Separates the dossier from the browser canvas and supports
  quiet secondary regions.
- **Audit Rule:** Divides stages, evidence entries, and document sections.
- **Secondary Ink:** Metadata and explanatory copy; never release decisions.

### Tertiary

- **Verified Green:** Confirmed evidence and completed gates only.
- **Review Amber:** Pending decisions and non-destructive blockers only.
- **Blocked Red:** Failed operations, explicit rejection, and blocked release only.

### Named Rules

**The Status Has Meaning Rule.** Green, amber, and red never decorate; each use
must explain a real review state in accompanying text.

**The One Active Signal Rule.** Cobalt identifies the current route or action,
not every interactive surface at once.

## Typography

**Display Font:** Geist Variable with Inter and system fallbacks

**Body Font:** Geist Variable with Inter and system fallbacks

**Label/Mono Font:** Geist Variable for interface labels; system monospace only
for trace identifiers when needed

**Character:** A compact grotesk with the clarity of an assessment form and the
rhythm of technical documentation. Weight and spacing create hierarchy without
hero typography.

### Hierarchy

- **Headline** (620, 24px, 1.2): Page title and the active dossier heading.
- **Title** (620, 15px, 1.35): Decision groups, review artifacts, and route labels.
- **Body** (400, 14px, 1.55): Prompts, policy values, explanations, and evidence;
  prose stays near 70ch when possible.
- **Label** (650, 11px, 0.1em): Short uppercase indices, evidence references, and
  state captions only.

### Named Rules

**The Working Scale Rule.** No product heading exceeds 24px; the console is a
review instrument, not a landing page.

## Layout

Desktop uses a three-region workbench: a narrow release route, a flexible active
workspace, and a compact evidence rail. A release ledger spans the top and keeps
status, blockers, and the recommended next action visible. Dividers align across
regions so the screen reads as a single dossier.

At tablet widths the evidence rail moves below the workspace. On mobile the
five-stage route becomes one horizontally scrollable control above the active
work; release context follows the primary task in document order. Touch targets
remain at least 40px and no critical action relies on hover.

Spacing follows a compact 4/8/12/16/24/32px rhythm. Dense evidence rows use the
smaller steps; major dossier sections use 24-32px separation.

## Elevation & Depth

The system is flat. Depth comes from paper against a cool workspace, strong and
subtle rules, and selected tonal bands. Routine panels and controls have no box
shadow; overlays may use one small structural shadow if introduced later.

### Named Rules

**The Ruled Paper Rule.** Prefer a divider or a slight background change over a
new floating card.

## Shapes

Controls use precise 4-8px corners. Full work regions stay square where they meet
the surrounding dossier grid. Pills are reserved for truly compact status values;
repeated containers must not become rounded floating tiles.

## Components

### Buttons

- **Shape:** Compact, slightly softened rectangle (6px radius).
- **Primary:** Dossier Ink with white text for the decisive action in a region.
- **Hover / Focus:** A short tonal shift and a visible 2px cobalt focus outline.
- **Secondary / Ghost:** White or transparent with an audit rule; never muted to
  the point that the boundary disappears.

### Chips

- **Style:** Small square-cornered labels with an icon or explicit text.
- **State:** Semantic backgrounds are faint; text carries the actual status.

### Cards / Containers

- **Corner Style:** 8px only for self-contained records; structural regions are
  divided by rules rather than wrapped as cards.
- **Background:** Review Paper for active work and Cool Workspace for secondary
  context.
- **Shadow Strategy:** None at rest.
- **Border:** One-pixel Audit Rule; use stronger rules for primary boundaries.
- **Internal Padding:** 16px for records and 24px for major work sections.

### Inputs / Fields

- **Style:** White field, one-pixel Audit Rule, 6px radius, and persistent label.
- **Focus:** Cobalt border and visible focus outline.
- **Error / Disabled:** Explicit text and reduced contrast without removing the
  control boundary.

### Navigation

The five-stage route is the only primary navigation. Each item shows its number,
label, and textual state. The selected item uses cobalt; complete, waiting, and
blocked states retain their semantic labels without competing with selection.

### Evidence Ledger

Evidence entries use a numbered or timestamped row, a short action description,
and compact source or policy references. The ledger stays visually secondary but
adjacent to the active decision.

## Do's and Don'ts

### Do:

- **Do** lead with the current release state and next professor decision.
- **Do** place supporting evidence beside the action it justifies.
- **Do** preserve the exact five stages: Sources, Interview, Policy, Preview, and
  Approval.
- **Do** use whitespace and ruled sections before adding another container.
- **Do** keep professor authority explicit for revisions and approval.

### Don't:

- **Don't** make chat the visual identity of the product.
- **Don't** duplicate route navigation with a second tab bar.
- **Don't** add invented analytics, course data, people, integrations, or release
  actions.
- **Don't** use gradients, glass, purple AI branding, oversized heroes, or soft
  decorative shadows.
- **Don't** hide blockers, provenance, or uncertainty behind color-only state.
