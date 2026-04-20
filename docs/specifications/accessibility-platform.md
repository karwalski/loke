# Accessibility Platform Specification

**Epic:** X3 — Accessibility Platform
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

loke is committed to accessibility as a platform responsibility, not an application afterthought. This specification defines the accessibility infrastructure that all loke-provided UI must implement and that applications can leverage to meet the same standard.

The target conformance level is **WCAG 2.1 AA**. This specification defines:

- Semantic HTML element usage rules and ARIA supplemental patterns
- Keyboard navigation framework and behaviour matrix
- Focus management utilities (trapping, restoration, programmatic movement)
- Screen reader live region infrastructure
- Colour independence and motion sensitivity requirements
- Automated accessibility testing with axe-core

### 1.1 Design Alignment

This specification follows the loke design principles:

- **Accessible from day one.** Accessibility is a platform responsibility. The platform provides semantic structure, focus management, keyboard navigation, screen reader support, and automated testing infrastructure.
- **The user is the authority.** Users who rely on assistive technology are first-class users. Every feature must be operable without a mouse, without colour perception, and without visual access to the screen.
- **Do the right thing by default.** Platform components are accessible out of the box. Applications that compose platform primitives inherit accessibility without additional effort.
- **Feedback is first-class.** Status changes, notifications, and pipeline events are announced to assistive technology with appropriate urgency levels.

---

## 2. Semantic HTML and ARIA Support

### 2.1 Semantic Element Decision Tree

When building any UI component, follow this decision tree to select the correct element:

```
Is it a page-level landmark?
├─ Primary content area          → <main>
├─ Site/app header               → <header>
├─ Site/app footer               → <footer>
├─ Primary navigation            → <nav aria-label="Primary">
├─ Secondary/local navigation    → <nav aria-label="Secondary">
└─ Complementary sidebar         → <aside>

Is it a content section?
├─ Self-contained, redistributable content → <article>
├─ Thematic grouping with a heading        → <section aria-labelledby="...">
└─ Generic grouping (no semantic meaning)  → <div> (last resort)

Is it interactive?
├─ Triggers an action            → <button>
├─ Navigates to a URL            → <a href="...">
├─ Accepts user input            → <input>, <textarea>, <select>
├─ Groups related inputs         → <fieldset> + <legend>
├─ Binary toggle                 → <input type="checkbox"> or <button aria-pressed>
└─ Mutually exclusive choice     → <input type="radio"> within <fieldset>

Is it a data structure?
├─ Tabular data                  → <table> + <thead>/<tbody>/<th scope>
├─ Ordered sequence              → <ol>
├─ Unordered collection          → <ul>
└─ Term/definition pairs         → <dl> + <dt>/<dd>

Is it a heading?
└─ Yes → <h1> through <h6>, maintaining a logical hierarchy (no skipped levels)
```

**Hard rules:**

1. Never use `<div>` with `onclick` as a button substitute. Use `<button>`.
2. Never use `<span>` or `<div>` as an interactive element without also adding `role`, `tabindex`, and keyboard event handlers — and even then, prefer the native element.
3. Every `<img>` has an `alt` attribute. Decorative images use `alt=""`.
4. Every form control has a visible `<label>` element associated via `for`/`id`, or uses `aria-label` when a visible label is inappropriate (e.g. icon-only search input).
5. Headings follow a logical hierarchy starting from `<h1>`. No skipped heading levels within a landmark.

### 2.2 ARIA Pattern Reference

ARIA is supplemental to semantic HTML — never a replacement. Use ARIA only when native HTML semantics are insufficient.

| Pattern | ARIA Roles/Properties | When to Use | Example |
|---------|----------------------|-------------|---------|
| **Dialog (modal)** | `role="dialog"`, `aria-modal="true"`, `aria-labelledby` | Overlay that blocks interaction with the page behind it | Confirmation dialog, settings modal |
| **Alert dialog** | `role="alertdialog"`, `aria-modal="true"`, `aria-labelledby`, `aria-describedby` | Urgent dialog requiring immediate user response | Destructive action confirmation |
| **Tabbed interface** | `role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-selected`, `aria-controls` | Content sections switchable via tab bar | Settings sections, pipeline detail views |
| **Menu** | `role="menu"`, `role="menuitem"`, `aria-haspopup`, `aria-expanded` | Dropdown action menus (not navigation) | Context menus, action dropdowns |
| **Tree view** | `role="tree"`, `role="treeitem"`, `aria-expanded`, `aria-level` | Hierarchical collapsible list | File browsers, nested config views |
| **Toolbar** | `role="toolbar"`, `aria-label`, `aria-orientation` | Group of related action buttons | Editor toolbars, bulk action bars |
| **Status** | `role="status"` | Non-urgent status information | Connection indicator, sync status |
| **Log** | `role="log"` | Appended sequential information | Pipeline stage progression |
| **Progressbar** | `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-label` | Operation progress indicator | File upload, pipeline progress |
| **Tooltip** | `role="tooltip"`, triggered by `aria-describedby` | Supplementary information on hover/focus | Icon button descriptions |
| **Live region** | `aria-live="polite"` or `aria-live="assertive"`, `aria-atomic` | Dynamic content updates for screen readers | Notifications, status changes |
| **Combobox** | `role="combobox"`, `aria-expanded`, `aria-autocomplete`, `aria-activedescendant` | Text input with dropdown suggestions | Model selector, search with suggestions |
| **Switch** | `role="switch"`, `aria-checked` | Binary on/off toggle (distinct from checkbox) | Feature toggles, dark mode switch |

### 2.3 Form Labelling Rules

Every form control must have an accessible name. The platform enforces these rules:

| Control | Labelling Method | Example |
|---------|-----------------|---------|
| Text input | `<label for="...">` | `<label for="api-key">API Key</label><input id="api-key">` |
| Textarea | `<label for="...">` | `<label for="prompt">Prompt</label><textarea id="prompt">` |
| Select | `<label for="...">` | `<label for="model">Model</label><select id="model">` |
| Checkbox | `<label>` wrapping the input, or `for`/`id` | `<label><input type="checkbox"> Enable caching</label>` |
| Radio group | `<fieldset>` + `<legend>` + individual `<label>` per radio | `<fieldset><legend>Routing strategy</legend>...` |
| Icon-only button | `aria-label` | `<button aria-label="Close dialog">×</button>` |
| Search input | `aria-label` (when visible label is redundant with context) | `<input type="search" aria-label="Search conversations">` |
| Group of related fields | `<fieldset>` + `<legend>` | `<fieldset><legend>Provider credentials</legend>...` |

**Validation errors** must be associated with their control via `aria-describedby` pointing to the error message element, and the control must have `aria-invalid="true"` when in an error state.

```html
<label for="port">Port</label>
<input id="port" aria-describedby="port-error" aria-invalid="true" value="abc">
<p id="port-error" role="alert">Port must be a number between 1 and 65535.</p>
```

---

## 3. Keyboard Navigation

### 3.1 Principles

1. Every interactive element is reachable and operable via keyboard alone.
2. Tab order follows the visual reading order (left-to-right, top-to-bottom in LTR layouts).
3. No mouse-only interactions exist anywhere in the platform.
4. Keyboard shortcuts do not conflict with assistive technology shortcuts.
5. Custom keyboard shortcuts are documented and discoverable (via a help overlay triggered by `?` when no input is focused).

### 3.2 Keyboard Behaviour Matrix

| Context | Key | Action |
|---------|-----|--------|
| **Global** | `Tab` | Move focus to next focusable element |
| | `Shift+Tab` | Move focus to previous focusable element |
| | `Escape` | Close the topmost overlay (modal, dropdown, tooltip) |
| | `?` (when no input focused) | Open keyboard shortcut help overlay |
| **Buttons** | `Enter` or `Space` | Activate the button |
| **Links** | `Enter` | Follow the link |
| **Checkbox** | `Space` | Toggle checked state |
| **Radio group** | `Arrow Up/Down` | Move selection between radio options |
| | `Space` | Select the focused option |
| **Select (dropdown)** | `Arrow Up/Down` | Move between options |
| | `Enter` | Select the focused option |
| | `Escape` | Close the dropdown without changing selection |
| **Tab bar** | `Arrow Left/Right` | Move between tabs |
| | `Enter` or `Space` | Activate the focused tab |
| | `Home` | Move to first tab |
| | `End` | Move to last tab |
| **Menu** | `Arrow Up/Down` | Move between menu items |
| | `Enter` | Activate the focused menu item |
| | `Escape` | Close the menu, return focus to trigger |
| | `Home` | Move to first menu item |
| | `End` | Move to last menu item |
| **Tree view** | `Arrow Up/Down` | Move between visible nodes |
| | `Arrow Right` | Expand collapsed node, or move to first child |
| | `Arrow Left` | Collapse expanded node, or move to parent |
| | `Enter` | Activate the focused node |
| | `Home` | Move to first node |
| | `End` | Move to last visible node |
| **Toolbar** | `Arrow Left/Right` | Move between toolbar buttons |
| | `Enter` or `Space` | Activate the focused button |
| | `Home` | Move to first button |
| | `End` | Move to last button |
| **Combobox** | `Arrow Down` | Open suggestion list / move to next suggestion |
| | `Arrow Up` | Move to previous suggestion |
| | `Enter` | Select the highlighted suggestion |
| | `Escape` | Close suggestions, retain typed text |
| **Modal/dialog** | `Tab` | Cycle through focusable elements within the modal (trapped) |
| | `Escape` | Close the modal, restore focus to trigger |
| **Pipeline panel** | `Tab` / `Shift+Tab` | Move between stages |
| | `Enter` or `Space` | Expand/collapse stage detail |
| | `Escape` | Collapse current stage detail, or close panel |
| | `Home` / `End` | Jump to first/last stage |

### 3.3 Composite Widget Navigation Pattern

Composite widgets (tab bars, menus, toolbars, radio groups, tree views) use the **roving tabindex** pattern:

1. The composite widget itself has a single tab stop. Only one item within the widget has `tabindex="0"`; all others have `tabindex="-1"`.
2. Arrow keys move focus between items within the widget and update `tabindex` values accordingly.
3. `Tab` exits the widget entirely and moves to the next focusable element outside it.
4. Focus wraps: pressing `Arrow Down` on the last item moves to the first item (and vice versa), unless the component is a tree view where wrapping is not applied.

```typescript
// Roving tabindex implementation pattern
function handleArrowKey(
  items: HTMLElement[],
  currentIndex: number,
  direction: 'next' | 'previous',
  wrap: boolean = true
): number {
  const nextIndex = direction === 'next'
    ? (currentIndex + 1) % items.length
    : (currentIndex - 1 + items.length) % items.length;

  if (!wrap && (
    (direction === 'next' && currentIndex === items.length - 1) ||
    (direction === 'previous' && currentIndex === 0)
  )) {
    return currentIndex;
  }

  items[currentIndex].setAttribute('tabindex', '-1');
  items[nextIndex].setAttribute('tabindex', '0');
  items[nextIndex].focus();
  return nextIndex;
}
```

### 3.4 Skip-to-Content Link

The first focusable element in the DOM is a skip-to-content link. It is visually hidden until it receives focus, at which point it becomes visible.

```html
<a href="#main-content" class="skip-link">Skip to main content</a>
<!-- ... header, nav, etc. ... -->
<main id="main-content" tabindex="-1">
  <!-- page content -->
</main>
```

```css
.skip-link {
  position: absolute;
  top: -100%;
  left: 0;
  z-index: var(--z-skip-link, 10000);
  padding: var(--space-2) var(--space-4);
  background: var(--colour-surface);
  color: var(--colour-text);
  text-decoration: underline;
}

.skip-link:focus {
  top: 0;
}
```

When activated, the link moves focus to `<main>`, which has `tabindex="-1"` to allow programmatic focus without being part of the natural tab order.

---

## 4. Focus Management

### 4.1 Focus Trapping

When a modal dialog or other overlay is open, focus must be trapped within the overlay. The user cannot tab out of the overlay into the page behind it.

**Implementation requirements:**

1. On overlay open: move focus to the first focusable element within the overlay (or the element specified by `autofocus`).
2. `Tab` on the last focusable element wraps to the first focusable element.
3. `Shift+Tab` on the first focusable element wraps to the last focusable element.
4. `Escape` closes the overlay.
5. Background content has `aria-hidden="true"` and `inert` attribute while the overlay is open.

```typescript
interface FocusTrapOptions {
  /** The container element to trap focus within. */
  container: HTMLElement;

  /** Element to focus on activation. Defaults to first focusable. */
  initialFocus?: HTMLElement | 'first' | 'container';

  /** Whether Escape closes the trap. Default: true. */
  escapeDeactivates?: boolean;

  /** Callback invoked when the trap is deactivated. */
  onDeactivate?: () => void;
}

interface FocusTrap {
  /** Activate the focus trap. */
  activate(): void;

  /** Deactivate the focus trap and restore focus. */
  deactivate(): void;

  /** Whether the trap is currently active. */
  isActive(): boolean;
}

function createFocusTrap(options: FocusTrapOptions): FocusTrap;
```

### 4.2 Focus Restoration

When an overlay (modal, dropdown, tooltip, popover) closes, focus must return to the element that triggered the overlay. This is non-negotiable — losing focus to `<body>` is a WCAG failure.

**Implementation requirements:**

1. Before opening an overlay, record `document.activeElement` as the trigger element.
2. On overlay close, call `triggerElement.focus()`.
3. If the trigger element has been removed from the DOM (e.g. the triggering list item was deleted), focus the nearest logical ancestor or sibling.

### 4.3 Programmatic Focus on Route Changes

When the client-side router navigates to a new view:

1. Update the document title to reflect the new route.
2. Move focus to the `<main>` element (or a designated heading within the new view) via `element.focus()`.
3. Announce the route change to screen readers via the live region (see section 5).

This ensures that keyboard and screen reader users know a navigation event occurred, rather than being left at a stale position in the DOM.

### 4.4 Focus Indicators

All focusable elements must have a visible focus indicator when focused via keyboard (`:focus-visible`). The platform provides a default focus ring style:

```css
:focus-visible {
  outline: 2px solid var(--colour-focus-ring);
  outline-offset: 2px;
}
```

The focus ring colour must meet WCAG 2.1 AA contrast requirements against all backgrounds it appears over. The platform's default `--colour-focus-ring` is tested against both light and dark theme surfaces.

Focus indicators are **never** removed via `outline: none` without providing an equivalent visual indicator (e.g. a box shadow or border change).

---

## 5. Screen Reader Live Regions

### 5.1 Live Region Architecture

The platform provides a persistent live region container in the application shell. This container is always present in the DOM but visually hidden. All dynamic announcements are injected into this container.

```html
<!-- Visually hidden, always present in the DOM -->
<div id="loke-live-region-polite" aria-live="polite" aria-atomic="true" class="sr-only"></div>
<div id="loke-live-region-assertive" aria-live="assertive" aria-atomic="true" class="sr-only"></div>
```

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

### 5.2 Announcement API

```typescript
type AnnouncementPriority = 'polite' | 'assertive';

/**
 * Announce a message to screen readers via the appropriate live region.
 *
 * - 'polite': announced at the next graceful opportunity (after the user
 *   finishes their current interaction). Use for status updates, route
 *   changes, and non-urgent notifications.
 * - 'assertive': announced immediately, interrupting the current speech.
 *   Use for errors, destructive confirmations, and urgent alerts.
 */
function announce(message: string, priority?: AnnouncementPriority): void;
```

**Implementation detail:** To ensure screen readers detect the change, the function clears the live region's `textContent`, waits one animation frame, then sets the new message. This forces the screen reader to recognise the change even if the new message is identical to the previous one.

### 5.3 When to Announce

| Event | Priority | Example Announcement |
|-------|----------|---------------------|
| Route change | `polite` | "Navigated to Settings" |
| Toast notification (info/success) | `polite` | "Notification: Policy saved successfully" |
| Toast notification (warning/error) | `assertive` | "Error: Failed to connect to Ollama" |
| Pipeline stage complete | `polite` | "Privacy Scan complete: 7 entities found" |
| Pipeline error | `assertive` | "Pipeline error at routing stage: no available providers" |
| Form validation error | `assertive` | "Error: Port must be a number between 1 and 65535" |
| Modal opened | `polite` | Handled by focus movement to dialog; no separate announcement needed |
| Content loaded asynchronously | `polite` | "Search results loaded: 12 conversations found" |
| Streaming LLM update (throttled) | `polite` | "LLM call in progress: 200 tokens received, 1.5 seconds elapsed" (every 5 seconds) |
| Pipeline complete | `polite` | "Pipeline complete. 6 entities anonymised, 42% token savings, 1.8 seconds" |

### 5.4 Throttling

During continuous operations (streaming LLM responses, pipeline execution), announcements are throttled to prevent overwhelming the screen reader:

- **Streaming updates:** maximum one announcement every 5 seconds.
- **Pipeline stage transitions:** announced individually as they complete (typically sub-second intervals between stages, which is acceptable).
- **Rapid-fire notifications:** if more than 3 notifications arrive within 2 seconds, batch them into a single announcement: "3 new notifications."

---

## 6. Colour Independence and Motion Sensitivity

### 6.1 No Colour-Only Indicators

Colour must never be the sole means of conveying information. Every colour-coded element must have at least one additional non-colour indicator:

| Information | Colour | Additional Indicator |
|-------------|--------|---------------------|
| Pipeline stage: complete | Green | Checkmark icon + "complete" text |
| Pipeline stage: error | Red | Cross icon + "error" text |
| Pipeline stage: skipped | Grey | Dash icon + "skipped" text |
| Pipeline stage: active | Blue | Pulsing animation + "in progress" text |
| Alert: info | Blue | Info icon (ℹ) + "Info:" prefix |
| Alert: success | Green | Checkmark icon (✓) + "Success:" prefix |
| Alert: warning | Amber | Warning icon (⚠) + "Warning:" prefix |
| Alert: error | Red | Error icon (✗) + "Error:" prefix |
| Form field: error state | Red border | Error icon + error message text below the field |
| Badge: status variant | Colour variant | Text label within the badge |
| Confidence: high | Green | "> 0.9" text value |
| Confidence: medium | Amber | "0.7–0.9" text value |
| Confidence: low | Red | "< 0.7" text value |

### 6.2 Contrast Requirements

All colour pairings in the platform must meet WCAG 2.1 AA contrast ratios:

| Element | Minimum Contrast Ratio |
|---------|----------------------|
| Normal text (< 18pt / < 14pt bold) | 4.5:1 |
| Large text (≥ 18pt / ≥ 14pt bold) | 3:1 |
| UI components and graphical objects | 3:1 |
| Focus indicators | 3:1 against adjacent colours |

The platform's design token system (P3.1) defines all colours as CSS custom properties. Contrast compliance is verified for both light and dark themes. The token file includes comments documenting the contrast ratio for each foreground/background pairing.

### 6.3 High Contrast Mode

The platform respects the operating system's high contrast preference via the `prefers-contrast: more` media query. When active:

- Borders on all interactive elements are increased to 2px solid.
- Background/foreground contrast is maximised using system colours (`Canvas`, `CanvasText`, `LinkText`, `ButtonFace`, `ButtonText`).
- Subtle visual distinctions (light grey separators, shadows) are replaced with solid borders.

### 6.4 Motion Sensitivity

The platform respects the `prefers-reduced-motion` media query:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

**Rules:**

1. No essential information is conveyed by animation alone. If an animation communicates state (e.g. a pulsing indicator for "active"), the same information is available via text or icon.
2. Animations that involve large movement (slide-ins, parallax, expanding panels) are reduced or eliminated when the preference is set.
3. Auto-playing animations (loading spinners, streaming indicators) use a static alternative when the preference is set (e.g. "Loading..." text instead of a spinner).
4. The pipeline visibility panel's stage progression animation is replaced with instant state transitions when reduced motion is preferred.

---

## 7. Automated Accessibility Testing

### 7.1 axe-core Integration

The platform integrates axe-core into the test suite via Vitest. Every platform-provided component must pass axe-core analysis with zero violations at the "wcag2a" and "wcag2aa" rule sets.

### 7.2 Test Helper

The platform exports a helper function that applications can use to run the same checks on their own components:

```typescript
import { checkAccessibility } from '@loke/shared/test-utils';

describe('MyComponent', () => {
  it('has no accessibility violations', async () => {
    // Render the component into the DOM
    const container = document.createElement('div');
    document.body.appendChild(container);
    container.innerHTML = renderMyComponent();

    // Run axe-core analysis
    await checkAccessibility(container);

    // Cleanup
    document.body.removeChild(container);
  });
});
```

**`checkAccessibility` implementation:**

```typescript
import { run as axeRun, configure as axeConfigure } from 'axe-core';

interface AccessibilityCheckOptions {
  /** axe-core rule sets to run. Default: ['wcag2a', 'wcag2aa']. */
  runOnly?: string[];

  /** Rules to disable for this specific check. Use sparingly. */
  disableRules?: string[];

  /** Element to check. Default: the provided container. */
  context?: HTMLElement;
}

async function checkAccessibility(
  container: HTMLElement,
  options: AccessibilityCheckOptions = {}
): Promise<void> {
  const { runOnly = ['wcag2a', 'wcag2aa'], disableRules = [] } = options;

  const rules: Record<string, { enabled: boolean }> = {};
  for (const rule of disableRules) {
    rules[rule] = { enabled: false };
  }

  const results = await axeRun(container, {
    runOnly: { type: 'tag', values: runOnly },
    rules,
  });

  if (results.violations.length > 0) {
    const messages = results.violations.map((violation) => {
      const nodes = violation.nodes
        .map((node) => `    - ${node.html}`)
        .join('\n');
      return `  ${violation.id} (${violation.impact}): ${violation.description}\n${nodes}`;
    });

    throw new Error(
      `Found ${results.violations.length} accessibility violation(s):\n${messages.join('\n\n')}`
    );
  }
}

export { checkAccessibility, type AccessibilityCheckOptions };
```

### 7.3 Quality Gate Integration

Accessibility tests are part of the quality gate script (X4.2). The gate runs the following sequence, and accessibility checks occur as part of the unit and integration test phases:

```
lint → format check → dependency audit → unit tests (includes a11y) → integration tests (includes a11y) → build
```

If any axe-core check produces a violation, the quality gate fails. There is no "acceptable violation count" — the target is zero.

### 7.4 What axe-core Checks

The following axe-core rule categories are enforced:

| Category | Examples | Impact |
|----------|----------|--------|
| **Colour contrast** | Text contrast ratio, link contrast | Ensures text is readable |
| **Keyboard** | Focusable elements, tabindex values, keyboard traps | Ensures keyboard operability |
| **Names and labels** | Form labels, button names, image alt text | Ensures screen reader usability |
| **Structure** | Heading order, landmark regions, list structure | Ensures navigability |
| **ARIA** | Valid roles, required attributes, allowed values | Ensures correct AT communication |
| **Language** | `lang` attribute on `<html>` | Ensures correct pronunciation |

### 7.5 Manual Testing Supplementary Checklist

Automated testing catches approximately 30-50% of accessibility issues. The following manual checks supplement axe-core and should be performed for any new component or view:

1. **Keyboard-only walkthrough.** Navigate the entire feature using only the keyboard. Every action must be possible.
2. **Screen reader walkthrough.** Use VoiceOver (macOS) to navigate the feature. Content must be announced in a logical order with appropriate context.
3. **Zoom to 200%.** The layout must remain usable when the browser is zoomed to 200%.
4. **Reduced motion.** Enable "Reduce motion" in OS settings. No animation should convey information that is lost when reduced.
5. **High contrast.** Enable high contrast mode. All interactive elements must remain distinguishable.

---

## 8. Component Accessibility Contracts

Platform-provided components (P3.4) must each satisfy the following minimum contracts:

| Component | Semantic Element | ARIA | Keyboard | Focus |
|-----------|-----------------|------|----------|-------|
| Button | `<button>` | `aria-disabled` when non-interactive, `aria-pressed` for toggles | `Enter`/`Space` activates | Visible `:focus-visible` ring |
| Card | `<article>` or `<section>` | `aria-labelledby` pointing to card heading | Not independently focusable unless interactive | N/A |
| Badge | `<span>` | `aria-label` if text is abbreviated or icon-only | Not focusable | N/A |
| Text input | `<input>` | `aria-invalid`, `aria-describedby` for errors, `aria-required` | Standard input behaviour | Visible focus ring, error state border |
| Select | `<select>` or custom with `role="listbox"` | `aria-expanded`, `aria-activedescendant` | Arrow keys, Enter, Escape | Focus ring on trigger |
| Checkbox | `<input type="checkbox">` | Native semantics sufficient | `Space` toggles | Visible focus ring |
| Radio group | `<fieldset>` + `<input type="radio">` | Native semantics, `<legend>` for group label | Arrow keys move selection | Visible focus ring on active radio |
| Table | `<table>` + `<th scope>` | `aria-sort` on sortable columns | Tab to table, arrow keys within if interactive | Row focus if table is interactive |
| Alert | `<div role="alert">` | `aria-live="assertive"` implicit | Not focusable | N/A |
| Toast | Custom | `role="status"` or `role="alert"` depending on severity | Escape dismisses, not independently focusable | N/A |
| Tooltip | Custom | `role="tooltip"`, `aria-describedby` on trigger | Visible on focus of trigger element | N/A |
| Modal | `<dialog>` or `role="dialog"` | `aria-modal="true"`, `aria-labelledby` | Focus trapped, Escape closes | Auto-focus first element, restore on close |
| Navigation | `<nav>` | `aria-label`, `aria-current="page"` on active item | Arrow keys between items | Roving tabindex |
| Loading spinner | `<div>` | `role="status"`, `aria-label="Loading"` | Not focusable | N/A |
| Progress bar | `<progress>` or `role="progressbar"` | `aria-valuenow`, `aria-valuemin`, `aria-valuemax` | Not focusable | N/A |

---

## 9. Performance Considerations

| Requirement | Target |
|-------------|--------|
| Focus trap activation | < 5ms |
| Live region announcement injection | < 1ms |
| axe-core test execution per component | < 500ms |
| Skip-link rendering on focus | < 16ms (one frame) |
| Focus restoration after overlay close | < 1 frame (synchronous) |

Accessibility infrastructure must not degrade the performance of the application. Focus trapping uses event delegation on the container rather than mutation observers. Live region updates are batched within a single animation frame when multiple announcements arrive simultaneously.
