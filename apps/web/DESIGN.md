---
name: Course Digital Twin Onboarding
description: A restrained professor review console for source, policy, preview, and approval gates.
colors:
  background: "#ffffff"
  workspace: "#f7f7f4"
  foreground: "#18181b"
  primary: "#27272a"
  primary-foreground: "#fafafa"
  secondary: "#f4f4f5"
  muted: "#f4f4f5"
  muted-foreground: "#71717a"
  border: "#e4e4e7"
  destructive: "#dc2626"
  warning-bg: "#fffbeb"
  warning-text: "#92400e"
  info-bg: "#f0f9ff"
  info-text: "#075985"
typography:
  headline:
    fontFamily: "Geist Variable, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0"
  title:
    fontFamily: "Geist Variable, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "0"
  body:
    fontFamily: "Geist Variable, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0"
  label:
    fontFamily: "Geist Variable, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.35
    letterSpacing: "0"
rounded:
  sm: "6px"
  md: "8px"
  lg: "10px"
  xl: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-outline:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  status-chip:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: "4px 8px"
---

# Design System: Course Digital Twin Onboarding

## 1. Overview

**Creative North Star: "The Review Console"**

This product is a task surface for professors checking whether a Course Digital
Twin is ready for student exposure. The design should feel calm, exact, and
operational: current release state first, review evidence close behind, and the
chat interview treated as one workstream rather than the whole product.

The system rejects generic AI demo styling. It should not use decorative
gradients, glass panels, oversized hero copy, or card-heavy marketing rhythm.
The professor needs a readable console where every release-affecting state is
auditable.

**Key Characteristics:**

- Restrained color with semantic status accents.
- Dense but readable panels for review work.
- Clear active-step hierarchy and release gate visibility.
- Standard shadcn-style controls and lucide icons.

## 2. Colors

The palette is near-neutral and light, with color reserved for semantic review
state.

### Primary

- **Console Ink** (#27272a): Primary actions, active step text, and high-priority
  labels.

### Neutral

- **Workspace Canvas** (#f7f7f4): Page-level background, used to separate the
  working surface from white review panels.
- **Panel White** (#ffffff): Primary content panels and tool surfaces.
- **Divider Gray** (#e4e4e7): Borders, separators, and inactive control outlines.
- **Muted Copy** (#71717a): Secondary metadata only; avoid it for key decisions.

### Semantic

- **Release Warning** (#fffbeb / #92400e): Blocking checklist and pending revision
  notices.
- **Review Info** (#f0f9ff / #075985): Draft-only and source-governance notices.
- **Destructive Red** (#dc2626): Failed requests and destructive states.

### Named Rules

**The Rare Accent Rule.** Color exists to explain state, not decorate the page.
If a color does not indicate review state, selection, or action, remove it.

## 3. Typography

**Display Font:** Geist Variable with Inter and system fallbacks
**Body Font:** Geist Variable with Inter and system fallbacks
**Label/Mono Font:** Same family unless code or source identifiers require mono

**Character:** Compact, utilitarian, and steady. Product text should read like a
review tool, not a launch page.

### Hierarchy

- **Headline** (600, 20px, 1.3): Page title and primary workspace headings only.
- **Title** (600, 14px, 1.35): Panel headers, active-step labels, and checklist
  labels.
- **Body** (400, 14px, 1.5): Messages, policy text, preview explanations, and
  source notes. Long prose should stay near 65-75ch.
- **Label** (500, 12px, 1.35): Metadata, small status, field labels, and compact
  counts. Do not use tracked uppercase as a default section style.

### Named Rules

**The Small Surface Rule.** Product UI uses a fixed rem scale. Avoid fluid type
and hero-scale headings inside the review console.

## 4. Elevation

This system uses tonal layering and borders instead of decorative shadows. Panels
are flat at rest. Depth comes from the page canvas, panel borders, separators,
and active-state backgrounds.

### Named Rules

**The Flat-by-Default Rule.** Do not combine a 1px border with a wide soft shadow
on cards or buttons. Use a border or a small state shadow, not both.

## 5. Components

### Buttons

- **Shape:** Medium radius (8px), matching the existing shadcn button vocabulary.
- **Primary:** Console Ink background with white text for the next decisive
  action.
- **Hover / Focus:** Use existing component variants, visible focus rings, and
  150-200ms state transitions.
- **Secondary / Outline:** White or muted backgrounds with border contrast for
  non-primary actions such as restart, discard, or expand.

### Chips

- **Style:** Small, text-and-icon badges with muted or semantic backgrounds.
- **State:** Status chips must include readable text; color alone cannot carry
  approval, blocker, or draft state.

### Cards / Containers

- **Corner Style:** 10-12px maximum for panels and repeated review items.
- **Background:** White primary panels on the workspace canvas.
- **Shadow Strategy:** Flat by default; no decorative glow.
- **Border:** 1px neutral border for grouping and scan boundaries.
- **Internal Padding:** 16px for standard panels, 12px for dense list items.

### Inputs / Fields

- **Style:** White or background surface, 1px border, medium radius.
- **Focus:** Use ring color from the existing shadcn token set.
- **Error / Disabled:** Preserve text labels and disabled affordances; avoid
  color-only communication.

### Navigation

The onboarding flow should expose a persistent step map with source, interview,
policy, preview, revision, and approval states. The active task should be visually
distinct and linked to the main work area.

### Review Panels

Use panels for actual review artifacts: source inventory, tutor policy, preview
evidence, revision proposal, and approval checklist. Avoid nesting panels inside
larger decorative cards; use full-width bands or side-by-side regions instead.

## 6. Do's and Don'ts

### Do:

- **Do** lead with release readiness and the next blocking decision.
- **Do** keep evidence, source labels, and release blockers close to the relevant
  action.
- **Do** use lucide icons in small controls and status labels.
- **Do** preserve keyboard access and visible focus states for review controls.

### Don't:

- **Don't** make the chat transcript the only dominant element once review
  artifacts exist.
- **Don't** use decorative gradients, glassmorphism, or purple-blue AI branding.
- **Don't** hide release blockers deep in a scroll rail.
- **Don't** use border-left accent stripes, gradient text, or oversized rounded
  cards.
