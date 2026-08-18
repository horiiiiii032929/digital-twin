---
name: Course Digital Twin Product Workspace
description: A conversation-first grounded AI workspace with inspectable setup and evidence.
colors:
  ink: "#202123"
  accent: "#5b5bd6"
  accent-soft: "#eeeeff"
  canvas: "#ffffff"
  shell: "#f7f7f8"
  subtle: "#f0f0f2"
  muted: "#6b6b73"
  border: "#e2e2e6"
  success: "#147a57"
  success-soft: "#eaf8f2"
  warning: "#a85d00"
  warning-soft: "#fff6e5"
  destructive: "#c2413b"
  destructive-soft: "#fff0ef"
typography:
  headline:
    fontFamily: "Geist Variable, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 620
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Geist Variable, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Geist Variable, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "0"
  label:
    fontFamily: "Geist Variable, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 550
    lineHeight: 1.35
    letterSpacing: "0"
rounded:
  sm: "8px"
  md: "12px"
  lg: "16px"
  full: "999px"
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
    textColor: "{colors.canvas}"
    rounded: "{rounded.sm}"
    padding: "8px 14px"
  button-secondary:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "8px 14px"
  nav-active:
    backgroundColor: "{colors.subtle}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "8px 10px"
  status-chip:
    backgroundColor: "{colors.subtle}"
    textColor: "{colors.ink}"
    rounded: "{rounded.full}"
    padding: "3px 8px"
---

# Design System: Course Digital Twin Product Workspace

## Overview

**Creative North Star: "Conversation with accountable context"**

Both roles share one recognizable LLM-product structure: a quiet navigation
rail, a dominant conversation canvas, a minimal course header, and one floating
composer. Course setup, release blockers, and citation lineage open as
contextual inspectors only when the user asks for them. The product-specific
difference is not more dashboard chrome; it is that every answer and release
decision can reveal its evidence and boundary.

This direction replaces both the release-dossier presentation and the setup
wizard presentation. It removes horizontal stage bars, permanently open
inspectors, metric grids, repeated explanatory prose, and task controls that
compete with the conversation.

**Key Characteristics:**

- A shared 216px quiet rail for product identity, the current course, and only
  truthful role-specific navigation.
- Conversation remains visible across professor setup stages; structured tools
  open in a contextual inspector rather than replacing the workspace.
- Release state and blockers are concise, discoverable, and never decorative.
- Context is closed by default for students and opens from an inline citation;
  professor setup opens from the active stage or Setup action.
- Familiar LLM-product density, rounding, hover states, and composer behavior.

## Colors

The palette is neutral and screen-native. Near-black carries primary actions;
iris marks selection and focus; semantic colors are reserved for real states.

### Primary

- **Workspace Ink** (#202123): Primary text and decisive actions.
- **Context Iris** (#5b5bd6): Selected navigation, focus, and current AI context.

### Neutral

- **Conversation Canvas** (#ffffff): Main task and chat surface.
- **Soft Shell** (#f7f7f8): Application navigation and page background.
- **Quiet Fill** (#f0f0f2): Hover, selected-neutral, and grouped metadata.
- **Soft Border** (#e2e2e6): Inputs and structural separation.
- **Secondary Text** (#6b6b73): Explanations and metadata.

### Tertiary

- **Ready Green** (#147a57): Completed release conditions.
- **Review Amber** (#a85d00): Pending decisions and blockers.
- **Blocked Red** (#c2413b): Failed actions and explicit rejection.

### Named Rules

**The Quiet Shell Rule.** Navigation supports the work and never becomes the
largest visual object on screen.

**The One Active Signal Rule.** Iris identifies the current place or focused AI
context; it is not scattered across every interactive element.

## Typography

**Display Font:** Geist Variable with system fallbacks

**Body Font:** Geist Variable with system fallbacks

**Character:** A neutral, highly legible UI grotesk associated with contemporary
AI workspaces. Hierarchy comes from weight and spacing, not uppercase labels or
editorial display treatments.

### Hierarchy

- **Headline** (620, 20px, 1.25): Current workspace title.
- **Title** (600, 15px, 1.4): Tool sections and substantial records.
- **Body** (400, 14px, 1.55): Conversation, descriptions, and review content.
- **Label** (550, 12px, 1.35): Navigation state, metadata, and concise captions.

### Named Rules

**The Human Label Rule.** Use sentence case. Uppercase is limited to unavoidable
identifiers from stored evidence, never used as the main hierarchy device.

## Layout

Desktop uses a familiar LLM workspace: a 216px navigation rail, a flexible
conversation canvas, and a 384-408px contextual inspector only while context is
open. The rail owns product identity and concise role navigation. The header
belongs to the conversation canvas and contains the current course, the truthful
release state, and one context action.

Professor setup stages are concise rail rows followed by one explicit blocker
summary. Selecting a stage opens its inspector while preserving the interview
conversation. Student navigation contains only the assigned course, New chat,
and the one browser-local conversation; it never implies server-side history.
Selecting an inline citation opens the source inspector and preserves transcript
position.

Below 1024px the rail becomes a menu sheet and contextual tools become an
accessible bottom sheet. The conversation remains the page beneath the sheet.
The primary task precedes supporting evidence in document order at every size.

Spacing follows a 4/8/12/16/24/32px rhythm. Routine controls are compact; major
task transitions use 24-32px separation.

## Elevation & Depth

The shell is mostly tonal and flat. A restrained ambient shadow is allowed for
the chat composer, popovers, and a context panel that overlays narrow layouts.
Ordinary content groups use background contrast and spacing rather than stacks
of bordered cards.

### Named Rules

**The Floating Composer Rule.** The composer is the clearest elevated object in
conversation mode; routine records must not compete with it.

**The Conversation Stays Home Rule.** Opening setup, blockers, activity, or a
citation may narrow or cover the canvas temporarily, but it never navigates the
user into a separate dashboard page.

## Shapes

Navigation and controls use 8px corners; substantive floating surfaces use
12-16px. Status chips may be fully rounded because they communicate short,
atomic values. Avoid both square report frames and excessive bubble-shaped cards.

## Components

### Buttons

- **Shape:** Compact 8px rectangle.
- **Primary:** Near-black with white text for the decisive action.
- **Hover / Focus:** Subtle tonal shift and a visible iris focus outline.
- **Secondary / Ghost:** Quiet fill or white with a soft border.

### Chips

- **Style:** Short sentence-case state labels with restrained fills.
- **State:** Meaning remains explicit in text; color is supplementary.

### Cards / Containers

- **Corner Style:** 12px for self-contained records and 16px for floating tools.
- **Background:** White task canvas or quiet neutral fill.
- **Shadow Strategy:** None at rest except composer and overlays.
- **Border:** Soft border only when grouping cannot be expressed by spacing.
- **Internal Padding:** 12-20px depending on density.

### Inputs / Fields

- **Style:** White or quiet-fill field, soft border, 8-12px radius.
- **Focus:** Iris border and focus outline.
- **Error / Disabled:** Explicit supporting text and stable control boundaries.

### Navigation

The rail uses compact open rows, not a tab bar. Professor rows show the five real
setup stages and their text/icon state; student rows show only the real assigned
course and browser-local conversation. The active item uses a quiet iris fill.
On mobile the rail becomes a modal menu sheet rather than a horizontal stepper.

### Context Inspector

The inspector is 384-408px on desktop, white with one left rule and no resting
shadow. It has a compact sticky header with title and Close action. On mobile it
is a bottom sheet with a visible drag affordance, a maximum height that preserves
orientation, keyboard focus containment, Escape close, and focus return.

### Conversation Composer

The composer is a rounded, elevated input region at the bottom of the interview
workspace. Suggested answers appear as compact prompt chips above it. Interview
history uses restrained assistant identity and natural content width rather than
speech-bubble theater.

## Do's and Don'ts

### Do:

- **Do** make the interface recognizable as an LLM workspace within seconds.
- **Do** keep conversation as the stable center and reveal structured context
  only when it is relevant.
- **Do** preserve the five real stages and professor-controlled approval.
- **Do** use progressive disclosure for trace and secondary metadata.
- **Do** state prototype limitations in secondary product chrome or documentation.

### Don't:

- **Don't** reproduce another product's logo, exact branding, or proprietary UI.
- **Don't** return to a horizontal setup wizard or permanently open three-column
  dashboard.
- **Don't** lead with evaluation terminology, metric grids, or a dossier metaphor.
- **Don't** make every section a bordered dashboard card.
- **Don't** invent courses, users, integrations, analytics, or model capabilities.
- **Don't** hide source permissions, blockers, citations, or uncertainty.
