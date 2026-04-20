# UI Platform Specification

**Epic:** P3 — UI Platform
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

The UI platform provides design tokens, theming, component primitives, a client-side router, an application shell, a navigation component, a notification system, and a base settings view. Together these give every loke application a consistent, accessible, themed UI without framework dependencies.

All UI code uses plain CSS and vanilla JavaScript (TypeScript in source). There is no React, Vue, Svelte, or other framework dependency. Components are rendered via DOM APIs and styled via CSS custom properties.

This specification defines:

- Design token system and naming convention (P3.1)
- Dark mode and theming (P3.2)
- CSS reset and base styles (P3.3)
- Component primitives and their states (P3.4)
- Application shell layout (P3.5)
- Client-side router (P3.6)
- Navigation component (P3.7)
- Notification system (P3.8)
- Base settings UI (P3.9)

### 1.1 Design Alignment

This specification follows the loke design principles:

- **Accessible from day one.** Every component uses semantic HTML, supports keyboard navigation, respects `prefers-reduced-motion`, and meets WCAG 2.1 AA contrast ratios.
- **Extensible.** Applications override design tokens to apply branding, register navigation items, add settings sections, and define routes — without forking platform CSS or JS.
- **No framework dependency.** Plain CSS custom properties and vanilla DOM APIs. The platform does not impose a rendering library.
- **Internationalisable.** No hardcoded widths on text containers. Layout accommodates 30-50% text expansion. All user-facing strings pass through the `t()` translation function (see P4 specification).

### 1.2 Requirement Traceability

| Story | Requirement | Section |
|-------|-------------|---------|
| P3.1 | R5.1 | 2. Design Token System |
| P3.2 | R5.2 | 3. Dark Mode and Theming |
| P3.3 | R5.3 | 4. CSS Reset and Base Styles |
| P3.4 | R5.4 | 5. Component Primitives |
| P3.5 | R5.5 | 6. Application Shell |
| P3.6 | R5.6 | 7. Client-Side Router |
| P3.7 | R5.7 | 8. Navigation Component |
| P3.8 | R5.8 | 9. Notification System |
| P3.9 | R5.9 | 10. Settings UI |

---

## 2. Design Token System

**Story:** P3.1 `[R5.1]`

### 2.1 Token Architecture

Tokens are organised in three layers. Each layer references only the layer below it — never raw values.

```
┌──────────────────────────────────────────────┐
│  Component Tokens                            │
│  --button-bg, --card-border, --alert-color   │
│  Reference semantic tokens only              │
├──────────────────────────────────────────────┤
│  Semantic Tokens                             │
│  --color-bg-primary, --space-md, --text-sm   │
│  Reference primitive tokens only             │
├──────────────────────────────────────────────┤
│  Primitive Tokens                            │
│  --gray-600, --space-4, --font-size-14       │
│  Raw values: hex, px, rem, ms                │
└──────────────────────────────────────────────┘
```

**Primitive tokens** hold raw values with no semantic meaning. They are the palette.

**Semantic tokens** assign meaning. `--color-bg-primary` might resolve to `--gray-50` in light mode and `--gray-900` in dark mode. Components never reference primitives directly.

**Component tokens** are optional, scoped overrides for a single component. They reference semantic tokens and exist only when a component needs to deviate from the semantic defaults.

### 2.2 Naming Convention

All tokens are CSS custom properties on `:root`. The naming convention is:

```
--{category}-{property}-{variant}-{state}
```

| Segment | Examples | Required |
|---------|----------|----------|
| `category` | `color`, `space`, `font`, `radius`, `shadow`, `border`, `transition`, `z` | Yes |
| `property` | `bg`, `text`, `border`, `size`, `weight`, `family`, `width` | Yes |
| `variant` | `primary`, `secondary`, `danger`, `muted`, `surface`, `sm`, `md`, `lg`, `xl` | Situational |
| `state` | `hover`, `active`, `disabled`, `focus` | Only for interactive states |

Primitives use a numeric scale instead of semantic names:

```
--gray-50, --gray-100, ..., --gray-900
--blue-50, --blue-100, ..., --blue-900
--space-0, --space-1, ..., --space-12
--font-size-12, --font-size-14, ..., --font-size-32
```

### 2.3 Token Categories

| Category | Prefix | What it controls |
|----------|--------|-----------------|
| Colour | `--color-` | Background, text, border, accent, status colours |
| Spacing | `--space-` | Padding, margin, gap |
| Typography | `--font-` | Family, size, weight, line-height, letter-spacing |
| Border | `--border-` | Width, style |
| Radius | `--radius-` | Border-radius |
| Shadow | `--shadow-` | Box-shadow |
| Transition | `--transition-` | Duration, easing |
| Z-index | `--z-` | Stacking layers |

### 2.4 Example Token File

```css
/* tokens/primitives.css — raw values, no semantic meaning */
:root {
  /* Grey scale */
  --gray-50:  #f9fafb;
  --gray-100: #f3f4f6;
  --gray-200: #e5e7eb;
  --gray-300: #d1d5db;
  --gray-400: #9ca3af;
  --gray-500: #6b7280;
  --gray-600: #4b5563;
  --gray-700: #374151;
  --gray-800: #1f2937;
  --gray-900: #111827;
  --gray-950: #030712;

  /* Blue scale (primary accent) */
  --blue-50:  #eff6ff;
  --blue-100: #dbeafe;
  --blue-200: #bfdbfe;
  --blue-300: #93c5fd;
  --blue-400: #60a5fa;
  --blue-500: #3b82f6;
  --blue-600: #2563eb;
  --blue-700: #1d4ed8;
  --blue-800: #1e40af;
  --blue-900: #1e3a8a;

  /* Status colours */
  --green-500: #22c55e;
  --green-600: #16a34a;
  --yellow-500: #eab308;
  --yellow-600: #ca8a04;
  --red-500: #ef4444;
  --red-600: #dc2626;

  /* Spacing scale (4px base unit) */
  --space-0:  0;
  --space-1:  0.25rem;   /*  4px */
  --space-2:  0.5rem;    /*  8px */
  --space-3:  0.75rem;   /* 12px */
  --space-4:  1rem;      /* 16px */
  --space-5:  1.25rem;   /* 20px */
  --space-6:  1.5rem;    /* 24px */
  --space-8:  2rem;      /* 32px */
  --space-10: 2.5rem;    /* 40px */
  --space-12: 3rem;      /* 48px */
  --space-16: 4rem;      /* 64px */

  /* Font sizes */
  --font-size-12: 0.75rem;
  --font-size-14: 0.875rem;
  --font-size-16: 1rem;
  --font-size-18: 1.125rem;
  --font-size-20: 1.25rem;
  --font-size-24: 1.5rem;
  --font-size-32: 2rem;

  /* Font weights */
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  /* Line heights */
  --line-height-tight: 1.25;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;

  /* Border radii */
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
  --radius-full: 9999px;

  /* Shadows */
  --shadow-sm:  0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md:  0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg:  0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
  --shadow-xl:  0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
  --transition-slow: 350ms ease;

  /* Z-index scale */
  --z-base: 0;
  --z-dropdown: 100;
  --z-sticky: 200;
  --z-overlay: 300;
  --z-modal: 400;
  --z-toast: 500;
  --z-tooltip: 600;
}
```

```css
/* tokens/semantic.css — meaningful names, reference primitives */
:root {
  /* Backgrounds */
  --color-bg-primary:    var(--gray-50);
  --color-bg-secondary:  var(--gray-100);
  --color-bg-surface:    #ffffff;
  --color-bg-muted:      var(--gray-200);
  --color-bg-inverse:    var(--gray-900);

  /* Text */
  --color-text-primary:   var(--gray-900);
  --color-text-secondary: var(--gray-600);
  --color-text-muted:     var(--gray-400);
  --color-text-inverse:   #ffffff;
  --color-text-link:      var(--blue-600);
  --color-text-link-hover: var(--blue-700);

  /* Borders */
  --color-border-default: var(--gray-200);
  --color-border-muted:   var(--gray-100);
  --color-border-strong:  var(--gray-300);

  /* Accent */
  --color-accent:         var(--blue-600);
  --color-accent-hover:   var(--blue-700);
  --color-accent-muted:   var(--blue-100);

  /* Status */
  --color-status-info:      var(--blue-600);
  --color-status-info-bg:   var(--blue-50);
  --color-status-success:   var(--green-600);
  --color-status-success-bg: var(--green-500) / 0.1;
  --color-status-warning:   var(--yellow-600);
  --color-status-warning-bg: var(--yellow-500) / 0.1;
  --color-status-danger:    var(--red-600);
  --color-status-danger-bg: var(--red-500) / 0.1;

  /* Focus */
  --color-focus-ring: var(--blue-500);
  --focus-ring: 0 0 0 2px var(--color-bg-surface), 0 0 0 4px var(--color-focus-ring);

  /* Typography */
  --font-family-sans:  system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-family-mono:  ui-monospace, "Cascadia Code", "Source Code Pro", Menlo, Consolas, monospace;
  --font-size-body:    var(--font-size-14);
  --font-size-sm:      var(--font-size-12);
  --font-size-lg:      var(--font-size-18);
  --font-size-h1:      var(--font-size-32);
  --font-size-h2:      var(--font-size-24);
  --font-size-h3:      var(--font-size-20);
  --font-size-h4:      var(--font-size-18);
  --line-height-body:  var(--line-height-normal);

  /* Spacing aliases */
  --space-xs:  var(--space-1);
  --space-sm:  var(--space-2);
  --space-md:  var(--space-4);
  --space-lg:  var(--space-6);
  --space-xl:  var(--space-8);
  --space-2xl: var(--space-12);

  /* Layout */
  --sidebar-width: 240px;
  --sidebar-width-compact: 56px;
  --header-height: 48px;
  --content-max-width: 1200px;

  /* Transitions */
  --transition-color: color var(--transition-fast), background-color var(--transition-fast), border-color var(--transition-fast);
  --transition-transform: transform var(--transition-fast);
}
```

### 2.5 Override Mechanism

Applications override tokens by loading an additional CSS file after the platform tokens. The cascade ensures application values win:

```html
<link rel="stylesheet" href="/loke/tokens/primitives.css">
<link rel="stylesheet" href="/loke/tokens/semantic.css">
<link rel="stylesheet" href="/app/tokens.css">   <!-- application overrides -->
```

Application token files override only the tokens they need to change:

```css
/* app/tokens.css — application branding overrides */
:root {
  --blue-500: #6366f1;  /* rebrand accent to indigo */
  --blue-600: #4f46e5;
  --blue-700: #4338ca;
  --font-family-sans: "Inter", system-ui, sans-serif;
}
```

Because semantic tokens reference primitives via `var()`, overriding a primitive cascades automatically to every semantic and component token that references it.

### 2.6 Token Validation

At build time, a lint rule verifies:

1. No raw colour, spacing, or font values appear in component CSS — only `var(--token)` references.
2. Component CSS references semantic or component tokens — never primitives directly.
3. All referenced tokens are defined in the token files.

---

## 3. Dark Mode and Theming

**Story:** P3.2 `[R5.2]`

### 3.1 Theme Modes

Three modes are supported:

| Mode | Behaviour |
|------|-----------|
| `system` | Follows the operating system preference via `prefers-color-scheme`. Changes in real time when the OS preference changes. |
| `light` | Manual override. Light palette regardless of OS preference. |
| `dark` | Manual override. Dark palette regardless of OS preference. |

### 3.2 Implementation

The active theme is expressed as a `data-theme` attribute on the `<html>` element:

```html
<html data-theme="light">   <!-- or "dark" or "system" -->
```

When `data-theme="system"`, the theme engine listens to `matchMedia('(prefers-color-scheme: dark)')` and applies the resolved mode as a `data-resolved-theme` attribute:

```html
<html data-theme="system" data-resolved-theme="dark">
```

CSS targets the resolved value:

```css
/* Light mode (default) */
:root {
  --color-bg-primary:   var(--gray-50);
  --color-bg-surface:   #ffffff;
  --color-text-primary: var(--gray-900);
  /* ... all semantic tokens for light */
}

/* Dark mode */
:root[data-resolved-theme="dark"],
:root[data-theme="dark"] {
  --color-bg-primary:   var(--gray-900);
  --color-bg-surface:   var(--gray-800);
  --color-text-primary: var(--gray-50);
  --color-bg-secondary: var(--gray-800);
  --color-bg-muted:     var(--gray-700);
  --color-bg-inverse:   var(--gray-50);

  --color-text-secondary: var(--gray-400);
  --color-text-muted:     var(--gray-500);
  --color-text-inverse:   var(--gray-900);
  --color-text-link:      var(--blue-400);
  --color-text-link-hover: var(--blue-300);

  --color-border-default: var(--gray-700);
  --color-border-muted:   var(--gray-800);
  --color-border-strong:  var(--gray-600);

  --color-accent:       var(--blue-400);
  --color-accent-hover: var(--blue-300);
  --color-accent-muted: var(--blue-900);

  --color-focus-ring: var(--blue-400);

  --shadow-sm:  0 1px 2px 0 rgb(0 0 0 / 0.3);
  --shadow-md:  0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.3);
  --shadow-lg:  0 10px 15px -3px rgb(0 0 0 / 0.4), 0 4px 6px -4px rgb(0 0 0 / 0.3);
}
```

### 3.3 Theme Engine API

```typescript
interface ThemeEngine {
  /** Get the current mode ('system' | 'light' | 'dark'). */
  getMode(): ThemeMode;

  /** Get the resolved effective theme ('light' | 'dark'). */
  getResolvedTheme(): 'light' | 'dark';

  /** Set the theme mode. Persists to settings store. */
  setMode(mode: ThemeMode): void;

  /** Subscribe to resolved theme changes. Returns unsubscribe function. */
  onThemeChange(callback: (resolved: 'light' | 'dark') => void): () => void;
}

type ThemeMode = 'system' | 'light' | 'dark';
```

### 3.4 Persistence

The selected mode is stored in the settings store (F6.7) under the key `loke.ui.theme`. On startup the theme engine reads this value before first render to prevent flash-of-wrong-theme. If no value is stored, `system` is the default.

### 3.5 No Flash of Unstyled Content

A small inline `<script>` in the `<head>` reads the persisted theme preference from `localStorage` (mirrored from the settings store for synchronous access) and sets `data-theme` and `data-resolved-theme` before the first paint:

```html
<script>
  (function() {
    var mode = localStorage.getItem('loke.ui.theme') || 'system';
    document.documentElement.setAttribute('data-theme', mode);
    if (mode === 'system') {
      var dark = matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute('data-resolved-theme', dark ? 'dark' : 'light');
    } else {
      document.documentElement.setAttribute('data-resolved-theme', mode);
    }
  })();
</script>
```

---

## 4. CSS Reset and Base Styles

**Story:** P3.3 `[R5.3]`

### 4.1 Modern CSS Reset

The platform ships a minimal modern reset based on common best practices:

```css
/* reset.css */
*, *::before, *::after {
  box-sizing: border-box;
}

* {
  margin: 0;
  padding: 0;
}

html {
  -webkit-text-size-adjust: 100%;
  -moz-text-size-adjust: 100%;
  text-size-adjust: 100%;
}

body {
  min-height: 100dvh;
  font-family: var(--font-family-sans);
  font-size: var(--font-size-body);
  line-height: var(--line-height-body);
  color: var(--color-text-primary);
  background-color: var(--color-bg-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

img, picture, video, canvas, svg {
  display: block;
  max-width: 100%;
}

input, button, textarea, select {
  font: inherit;
  color: inherit;
}

p, h1, h2, h3, h4, h5, h6 {
  overflow-wrap: break-word;
}

h1, h2, h3, h4, h5, h6 {
  text-wrap: balance;
}

a {
  color: var(--color-text-link);
  text-decoration-skip-ink: auto;
}

a:hover {
  color: var(--color-text-link-hover);
}

table {
  border-collapse: collapse;
}

ul, ol {
  list-style: none;
}
```

### 4.2 Typographic Baseline

```css
/* base/typography.css */
h1 { font-size: var(--font-size-h1); font-weight: var(--font-weight-bold); line-height: var(--line-height-tight); }
h2 { font-size: var(--font-size-h2); font-weight: var(--font-weight-semibold); line-height: var(--line-height-tight); }
h3 { font-size: var(--font-size-h3); font-weight: var(--font-weight-semibold); line-height: var(--line-height-tight); }
h4 { font-size: var(--font-size-h4); font-weight: var(--font-weight-medium); line-height: var(--line-height-tight); }

p + p { margin-top: var(--space-md); }

code, kbd, samp, pre {
  font-family: var(--font-family-mono);
  font-size: 0.875em;
}

code {
  background: var(--color-bg-muted);
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
}

pre {
  overflow-x: auto;
  padding: var(--space-md);
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
}

pre code {
  background: none;
  padding: 0;
}

small { font-size: var(--font-size-sm); }
strong { font-weight: var(--font-weight-semibold); }
```

### 4.3 Focus Styles

```css
/* base/focus.css */
:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}

/* Skip link — visually hidden until focused */
.skip-link {
  position: absolute;
  top: -100%;
  left: var(--space-md);
  padding: var(--space-sm) var(--space-md);
  background: var(--color-bg-surface);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  z-index: var(--z-modal);
  font-size: var(--font-size-body);
}

.skip-link:focus {
  top: var(--space-sm);
}
```

### 4.4 Motion Sensitivity

```css
/* base/motion.css */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 5. Component Primitives

**Story:** P3.4 `[R5.4]`

All components are styled via CSS custom properties. No component uses raw colour, spacing, or font values. All interactive components support keyboard operation and have visible focus indicators via `:focus-visible`.

### 5.1 Buttons

#### 5.1.1 Variants

| Variant | Class | Use |
|---------|-------|-----|
| Primary | `.btn-primary` | Primary actions (submit, save, confirm) |
| Secondary | `.btn-secondary` | Secondary actions (cancel, back) |
| Danger | `.btn-danger` | Destructive actions (delete, remove) |
| Ghost | `.btn-ghost` | Tertiary / low-emphasis actions |

#### 5.1.2 Sizes

| Size | Class | Padding | Font size |
|------|-------|---------|-----------|
| Small | `.btn-sm` | `var(--space-xs) var(--space-sm)` | `var(--font-size-sm)` |
| Medium (default) | — | `var(--space-sm) var(--space-md)` | `var(--font-size-body)` |
| Large | `.btn-lg` | `var(--space-md) var(--space-lg)` | `var(--font-size-lg)` |

#### 5.1.3 State Matrix

| State | Visual change | How triggered |
|-------|--------------|---------------|
| Default | Base variant colours | — |
| Hover | Darker background, cursor pointer | `:hover` |
| Active/Pressed | Further darkened background, slight scale | `:active` |
| Focus | Focus ring | `:focus-visible` |
| Disabled | Reduced opacity (0.5), `cursor: not-allowed`, no hover effect | `[disabled]` or `[aria-disabled="true"]` |
| Loading | Spinner replaces or precedes label, `pointer-events: none` | `.btn-loading` |

#### 5.1.4 Component Tokens

```css
.btn {
  --btn-bg: var(--color-bg-surface);
  --btn-text: var(--color-text-primary);
  --btn-border: var(--color-border-default);
  --btn-radius: var(--radius-md);
}
```

### 5.2 Cards

A card is a content container with background, border, and optional header/footer.

```html
<article class="card">
  <header class="card-header">...</header>
  <div class="card-body">...</div>
  <footer class="card-footer">...</footer>
</article>
```

#### 5.2.1 State Matrix

| State | Visual change |
|-------|--------------|
| Default | Surface background, subtle border, shadow-sm |
| Hover (if interactive) | Elevated shadow-md, optional border accent |
| Focus (if interactive) | Focus ring |

### 5.3 Badges

Inline status indicators. Always paired with text — colour is never the sole indicator (R7.8).

#### 5.3.1 Variants

| Variant | Class | Colour |
|---------|-------|--------|
| Default | `.badge` | Muted background, secondary text |
| Info | `.badge-info` | Status info colours |
| Success | `.badge-success` | Status success colours |
| Warning | `.badge-warning` | Status warning colours |
| Danger | `.badge-danger` | Status danger colours |

Each badge includes a visible text label. Optionally a leading icon reinforces the status.

### 5.4 Form Elements

#### 5.4.1 Inputs (text, email, password, number, search, url, tel)

```html
<div class="form-group">
  <label for="field-name" class="form-label">Label</label>
  <input id="field-name" class="form-input" type="text">
  <p class="form-hint" id="field-name-hint">Optional hint text</p>
  <p class="form-error" id="field-name-error" role="alert">Error message</p>
</div>
```

#### 5.4.2 State Matrix — Form Inputs

| State | Visual change | Attribute/Class |
|-------|--------------|-----------------|
| Default | Border default, surface background | — |
| Focus | Focus ring, accent border | `:focus-visible` |
| Error | Danger border, error message visible | `.form-input-error`, `aria-invalid="true"`, `aria-describedby` pointing to error |
| Disabled | Muted background, reduced opacity, `cursor: not-allowed` | `[disabled]` |
| Read-only | Muted background, no border change | `[readonly]` |
| Placeholder | Muted text | `::placeholder` |

#### 5.4.3 Select

Same states as text input. Uses native `<select>` with custom arrow indicator via `appearance: none` and background SVG.

#### 5.4.4 Textarea

Same states as text input. Allows vertical resize only (`resize: vertical`). Minimum height: 4 lines.

#### 5.4.5 Checkbox and Radio

Custom-styled via `appearance: none` with pseudo-elements. States:

| State | Visual change |
|-------|--------------|
| Unchecked | Border, surface background |
| Checked | Accent background, check/dot icon |
| Focus | Focus ring |
| Disabled | Reduced opacity |
| Indeterminate (checkbox only) | Dash icon |

#### 5.4.6 Toggle Switch

A styled checkbox that renders as a sliding toggle. Includes accessible label and `role="switch"` with `aria-checked`.

| State | Visual change |
|-------|--------------|
| Off | Muted background, knob left |
| On | Accent background, knob right |
| Focus | Focus ring |
| Disabled | Reduced opacity |

### 5.5 Tables

```html
<div class="table-wrapper" role="region" aria-label="Table description" tabindex="0">
  <table class="table">
    <thead>
      <tr><th scope="col">...</th></tr>
    </thead>
    <tbody>
      <tr><td>...</td></tr>
    </tbody>
  </table>
</div>
```

#### 5.5.1 Features

| Feature | Implementation |
|---------|---------------|
| Header styling | Bold weight, muted background, bottom border |
| Zebra striping | `tbody tr:nth-child(even)` gets secondary background |
| Responsive scroll | `.table-wrapper` has `overflow-x: auto` with `-webkit-overflow-scrolling: touch` |
| Row hover | Subtle background change on `:hover` |
| Compact variant | `.table-compact` with reduced padding |

### 5.6 Alerts

```html
<div class="alert alert-warning" role="alert">
  <svg class="alert-icon" aria-hidden="true">...</svg>
  <div class="alert-content">
    <p class="alert-title">Warning</p>
    <p class="alert-message">Description text</p>
  </div>
  <button class="alert-dismiss" aria-label="Dismiss alert">...</button>
</div>
```

#### 5.6.1 Variants

| Variant | Class | Role |
|---------|-------|------|
| Info | `.alert-info` | `status` |
| Success | `.alert-success` | `status` |
| Warning | `.alert-warning` | `alert` |
| Error | `.alert-error` | `alert` |

Each variant uses its corresponding status colour tokens for background, border, and icon.

### 5.7 Loading Indicators

#### 5.7.1 Spinner

An animated SVG circle with `role="status"` and a visually-hidden text label ("Loading..."). Respects `prefers-reduced-motion` by disabling rotation and showing a static indicator.

Sizes: `--spinner-sm` (16px), `--spinner-md` (24px), `--spinner-lg` (40px).

#### 5.7.2 Skeleton

Placeholder shapes (rectangle, circle, text lines) with a shimmer animation. Marked with `aria-busy="true"` and `aria-label` describing what is loading.

#### 5.7.3 Progress Bar

```html
<div class="progress" role="progressbar" aria-valuenow="45" aria-valuemin="0" aria-valuemax="100" aria-label="Upload progress">
  <div class="progress-fill" style="width: 45%"></div>
</div>
```

Indeterminate variant uses a repeating animation when `aria-valuenow` is absent.

### 5.8 Tooltips

Triggered on hover and focus of the owning element. Positioned via JavaScript (no CSS-only positioning to avoid viewport clipping). Accessible via `aria-describedby` linking the trigger to the tooltip content.

| State | Behaviour |
|-------|-----------|
| Hidden | `display: none`, no DOM presence or `visibility: hidden` |
| Visible | Positioned near trigger, fade-in, z-index tooltip layer |
| Dismissed | Escape key hides, mouse-leave hides after delay |

Delay before show: 300ms. Delay before hide: 150ms. Both configurable.

### 5.9 Complete Component State Matrix

| Component | Default | Hover | Active | Focus | Disabled | Error | Loading |
|-----------|---------|-------|--------|-------|----------|-------|---------|
| Button (primary) | Accent bg, white text | Darker bg | Darkest bg, scale | Ring | 50% opacity | — | Spinner |
| Button (secondary) | Surface bg, border | Muted bg | Darker bg | Ring | 50% opacity | — | Spinner |
| Button (danger) | Danger bg, white text | Darker danger | Darkest danger | Ring | 50% opacity | — | Spinner |
| Button (ghost) | Transparent | Muted bg | Darker bg | Ring | 50% opacity | — | Spinner |
| Card | Surface bg, border | Elevated shadow | — | Ring (if interactive) | — | — | Skeleton |
| Badge | Muted bg | — | — | — | — | — | — |
| Input | Surface bg, border | — | — | Ring, accent border | Muted bg, 50% | Danger border | — |
| Select | Surface bg, border | — | — | Ring, accent border | Muted bg, 50% | Danger border | — |
| Textarea | Surface bg, border | — | — | Ring, accent border | Muted bg, 50% | Danger border | — |
| Checkbox | Border circle | — | — | Ring | 50% opacity | Danger border | — |
| Radio | Border circle | — | — | Ring | 50% opacity | Danger border | — |
| Toggle | Muted bg (off), accent (on) | — | — | Ring | 50% opacity | — | — |
| Table row | Transparent / zebra | Subtle bg | — | — | — | — | Skeleton rows |
| Alert | Status bg + border | — | — | — | — | — | — |
| Tooltip | Hidden | Visible | — | Visible | — | — | — |
| Spinner | Rotating | — | — | — | — | — | — |
| Progress | Track bg | — | — | — | — | — | Indeterminate |

---

## 6. Application Shell

**Story:** P3.5 `[R5.5]`

### 6.1 Layout

The application shell uses semantic HTML and CSS Grid to create a responsive layout:

```
┌──────────────────────────────────────────────────────────────────┐
│ <a class="skip-link" href="#main">Skip to content</a>           │
├──────────────────────────────────────────────────────────────────┤
│ <header>                                                         │
│ ┌──────┬─────────────────────────────────────────┬──────────────┐│
│ │ Logo │  [Page title / breadcrumb]              │ [Bell] [User]││
│ └──────┴─────────────────────────────────────────┴──────────────┘│
├────────┬─────────────────────────────────────────────────────────┤
│ <nav>  │ <main id="main">                                       │
│        │                                                         │
│ [Home] │   ┌─────────────────────────────────────────────┐      │
│ [Dash] │   │                                             │      │
│ [Logs] │   │  Route content rendered here                │      │
│ [Set.] │   │                                             │      │
│        │   │                                             │      │
│        │   └─────────────────────────────────────────────┘      │
│        │                                                         │
│        │  <div id="route-announcer" class="sr-only"             │
│        │        aria-live="assertive" aria-atomic="true"></div>  │
├────────┴─────────────────────────────────────────────────────────┤
│ (no footer in default shell — applications may add one)          │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 HTML Structure

```html
<body class="shell">
  <a class="skip-link" href="#main">Skip to content</a>

  <header class="shell-header" role="banner">
    <div class="shell-header-start">
      <button class="sidebar-toggle" aria-label="Toggle navigation"
              aria-expanded="true" aria-controls="sidebar">
        <!-- hamburger icon -->
      </button>
      <span class="shell-logo">loke</span>
    </div>
    <div class="shell-header-center">
      <!-- page title or breadcrumb, populated by router -->
    </div>
    <div class="shell-header-end">
      <!-- notification bell, user menu -->
    </div>
  </header>

  <nav id="sidebar" class="shell-sidebar" role="navigation" aria-label="Main navigation">
    <!-- navigation component renders here -->
  </nav>

  <main id="main" class="shell-main" role="main" tabindex="-1">
    <!-- route content rendered here -->
  </main>

  <div id="route-announcer" class="sr-only" aria-live="assertive" aria-atomic="true"></div>
  <div id="toast-container" class="toast-container" aria-live="polite"></div>
</body>
```

### 6.3 CSS Grid Layout

```css
.shell {
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  grid-template-rows: var(--header-height) 1fr;
  grid-template-areas:
    "header  header"
    "sidebar main";
  min-height: 100dvh;
}

.shell-header  { grid-area: header; }
.shell-sidebar { grid-area: sidebar; }
.shell-main    { grid-area: main; }
```

### 6.4 Responsive Collapse

On viewports narrower than 768px, the sidebar collapses to an overlay:

```css
@media (max-width: 767px) {
  .shell {
    grid-template-columns: 1fr;
    grid-template-areas:
      "header"
      "main";
  }

  .shell-sidebar {
    position: fixed;
    top: var(--header-height);
    left: 0;
    bottom: 0;
    width: var(--sidebar-width);
    transform: translateX(-100%);
    transition: transform var(--transition-normal);
    z-index: var(--z-overlay);
    background: var(--color-bg-surface);
    border-right: 1px solid var(--color-border-default);
  }

  .shell-sidebar[aria-hidden="false"] {
    transform: translateX(0);
  }
}
```

On narrow viewports the sidebar toggle button shows/hides the sidebar. When the sidebar is open as an overlay, clicking outside it or pressing Escape closes it. Focus is trapped within the sidebar while it is open.

### 6.5 Compact Sidebar Mode

On desktop viewports, the sidebar can be collapsed to an icon-only compact mode (56px wide). The toggle button switches between expanded and compact. The compact state is persisted in the settings store under `loke.ui.sidebar.compact`.

```css
.shell.shell-sidebar-compact {
  grid-template-columns: var(--sidebar-width-compact) 1fr;
}
```

---

## 7. Client-Side Router

**Story:** P3.6 `[R5.6]`

### 7.1 Routing Strategy

The router uses hash-based routing (`#/path`). This avoids server configuration for SPA fallback in development and works reliably inside Electron `file://` URLs.

### 7.2 Route Definition

Routes are defined as an array of `RouteDefinition` objects:

```typescript
interface RouteDefinition {
  /** Hash path pattern, e.g. '/dashboard', '/logs/:id', '/settings/*'. */
  path: string;

  /** Document title suffix. Appended to the base title: "loke — {title}". */
  title: string;

  /**
   * Render function. Called when the route matches.
   * Receives extracted params and the container element.
   * Returns a cleanup function called before the next route renders.
   */
  render: (params: RouteParams, container: HTMLElement) => (() => void) | void;

  /**
   * Optional guard. If it returns false, navigation is cancelled.
   * Can return a redirect path string.
   */
  guard?: (params: RouteParams) => boolean | string;
}

interface RouteParams {
  /** Named parameters extracted from the path (e.g. { id: '42' }). */
  params: Record<string, string>;

  /** Query string parameters (after the ?). */
  query: URLSearchParams;

  /** The full matched path string. */
  path: string;
}
```

### 7.3 Parameter Extraction

Path segments prefixed with `:` are named parameters:

| Pattern | URL | Params |
|---------|-----|--------|
| `/logs/:id` | `#/logs/42` | `{ id: '42' }` |
| `/logs/:id/entries/:entryId` | `#/logs/42/entries/7` | `{ id: '42', entryId: '7' }` |

A trailing `*` matches any remaining path (wildcard):

| Pattern | URL | Params |
|---------|-----|--------|
| `/docs/*` | `#/docs/api/v1/routes` | `{ '*': 'api/v1/routes' }` |

### 7.4 Router API

```typescript
interface Router {
  /**
   * Register route definitions. Can be called multiple times
   * (platform registers its routes, then applications register theirs).
   */
  register(routes: RouteDefinition[]): void;

  /** Navigate programmatically. */
  navigate(path: string, options?: { replace?: boolean }): void;

  /** Get the current route params. */
  current(): RouteParams | null;

  /** Subscribe to route changes. Returns unsubscribe function. */
  onNavigate(callback: (params: RouteParams) => void): () => void;

  /** Start listening to hash changes. Call once on startup. */
  start(): void;

  /** Stop listening. Call on shutdown. */
  stop(): void;
}
```

### 7.5 Route Matching Priority

Routes are matched in registration order. The first match wins. Applications should register specific routes before wildcards. The platform registers a catch-all 404 route last.

### 7.6 404 Fallback

If no registered route matches the current hash, the router renders a 404 view with:

- A clear message that the page was not found.
- A link back to the default route (`#/`).
- The document title set to "loke — Page not found".

### 7.7 Document Title Updates

On every route change, the router sets `document.title` to `"loke — {route.title}"`. Applications can override the base prefix by setting `router.titlePrefix`.

### 7.8 Screen Reader Announcements

On every route change, the router writes the new page title to the `#route-announcer` live region:

```typescript
const announcer = document.getElementById('route-announcer');
announcer.textContent = `Navigated to ${route.title}`;
```

This ensures screen readers announce the navigation even though no full page load occurs.

### 7.9 Focus Management

After rendering a new route, the router moves focus to the `<main>` element (which has `tabindex="-1"` for programmatic focus). This ensures keyboard users start at the top of the new content.

---

## 8. Navigation Component

**Story:** P3.7 `[R5.7]`

### 8.1 Data-Driven Items

The navigation component renders from an array of `NavItem` objects:

```typescript
interface NavItem {
  /** Unique identifier. */
  id: string;

  /** Display label (translation key or literal string). */
  label: string;

  /** Hash route path (e.g. '#/dashboard'). */
  href: string;

  /** Icon identifier (SVG sprite or inline SVG reference). */
  icon?: string;

  /** Badge text or count. Omit for no badge. */
  badge?: string | number;

  /** Badge variant for styling. */
  badgeVariant?: 'default' | 'info' | 'success' | 'warning' | 'danger';

  /** Nested children (one level of nesting supported). */
  children?: NavItem[];

  /** Sort order. Lower numbers appear first. */
  order?: number;
}
```

### 8.2 Registration

The platform provides default navigation items (Dashboard, Settings). Applications register additional items:

```typescript
interface NavigationRegistry {
  /** Register navigation items. Merges with existing items by order. */
  register(items: NavItem[]): void;

  /** Remove previously registered items by ID. */
  unregister(ids: string[]): void;

  /** Get all registered items, sorted by order. */
  getItems(): NavItem[];

  /** Subscribe to item changes. Returns unsubscribe function. */
  onChange(callback: (items: NavItem[]) => void): () => void;
}
```

### 8.3 Active State

The navigation component compares each item's `href` to the current router path and applies an `.nav-item-active` class. For items with children, the parent is marked active if any child matches.

### 8.4 Keyboard Navigation

The navigation component implements the WAI-ARIA Treeview pattern:

| Key | Action |
|-----|--------|
| `ArrowDown` | Move focus to next visible item |
| `ArrowUp` | Move focus to previous visible item |
| `ArrowRight` | Expand collapsed group / move to first child |
| `ArrowLeft` | Collapse expanded group / move to parent |
| `Home` | Move focus to first item |
| `End` | Move focus to last visible item |
| `Enter` / `Space` | Activate the focused item (navigate) |

Focus is managed with `tabindex`: the active item has `tabindex="0"`, all others have `tabindex="-1"`. This implements roving tabindex.

### 8.5 Compact and Expanded Modes

| Mode | Sidebar width | Label visibility | Icon visibility | Tooltip |
|------|--------------|-----------------|----------------|---------|
| Expanded | `var(--sidebar-width)` (240px) | Visible | Visible | None |
| Compact | `var(--sidebar-width-compact)` (56px) | Hidden | Visible | Label shown as tooltip on hover/focus |

Transition between modes is animated (width and opacity) unless `prefers-reduced-motion` is active.

### 8.6 Rendering

The navigation renders as a `<ul>` with `role="tree"`:

```html
<ul class="nav-list" role="tree" aria-label="Main navigation">
  <li class="nav-item nav-item-active" role="treeitem" tabindex="0"
      aria-current="page">
    <a href="#/dashboard" class="nav-link">
      <svg class="nav-icon" aria-hidden="true">...</svg>
      <span class="nav-label">Dashboard</span>
    </a>
  </li>
  <li class="nav-item" role="treeitem" tabindex="-1">
    <a href="#/logs" class="nav-link">
      <svg class="nav-icon" aria-hidden="true">...</svg>
      <span class="nav-label">Audit Logs</span>
      <span class="badge badge-info nav-badge">12</span>
    </a>
  </li>
  <!-- ... -->
</ul>
```

---

## 9. Notification System

**Story:** P3.8 `[R5.8]`

### 9.1 Architecture

The notification system has two visual channels:

1. **Notification panel** — a dropdown from a bell icon in the header, showing persistent notifications stored in the database.
2. **Toast notifications** — ephemeral messages that appear at the top-right and auto-dismiss.

Both channels share the same `Notification` type and API.

### 9.2 Notification Data Model

```typescript
interface Notification {
  /** Unique ID (UUID). */
  id: string;

  /** Notification type. */
  type: 'info' | 'success' | 'warning' | 'error';

  /** Short title. */
  title: string;

  /** Optional longer description. */
  message?: string;

  /** ISO 8601 timestamp. */
  createdAt: string;

  /** Whether the user has seen/acknowledged this notification. */
  read: boolean;

  /** Source identifier (e.g. 'loke.backup', 'app.calendar'). */
  source: string;

  /** Optional action URL (hash route). Clicking navigates here. */
  actionUrl?: string;

  /** Optional action label. */
  actionLabel?: string;

  /** Whether to also show as a toast. Default: true for new notifications. */
  showToast?: boolean;

  /** Toast auto-dismiss duration in milliseconds. Default: 5000. Errors: 8000. */
  dismissAfter?: number;
}
```

### 9.3 Database Schema

Notifications are stored in the `loke_notifications` table:

```sql
CREATE TABLE loke_notifications (
  id          TEXT PRIMARY KEY,
  type        TEXT NOT NULL CHECK (type IN ('info', 'success', 'warning', 'error')),
  title       TEXT NOT NULL,
  message     TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  read        INTEGER NOT NULL DEFAULT 0,
  source      TEXT NOT NULL,
  action_url  TEXT,
  action_label TEXT
);

CREATE INDEX idx_notifications_read ON loke_notifications (read, created_at DESC);
CREATE INDEX idx_notifications_source ON loke_notifications (source);
```

### 9.4 Notification API

```typescript
interface NotificationService {
  /**
   * Create a notification. Stores in DB and optionally shows toast.
   * Returns the created notification.
   */
  create(notification: Omit<Notification, 'id' | 'createdAt' | 'read'>): Notification;

  /** Mark a notification as read. */
  markRead(id: string): void;

  /** Mark all notifications as read. */
  markAllRead(): void;

  /** Delete a notification. */
  remove(id: string): void;

  /** Delete all read notifications older than the given date. */
  prune(olderThan: Date): number;

  /** Get notifications, newest first. Supports pagination. */
  list(options?: {
    unreadOnly?: boolean;
    source?: string;
    limit?: number;
    offset?: number;
  }): { notifications: Notification[]; total: number };

  /** Get unread count. */
  unreadCount(): number;

  /** Subscribe to new notifications. Returns unsubscribe function. */
  onNotification(callback: (notification: Notification) => void): () => void;
}
```

### 9.5 Bell Icon and Dropdown Panel

The bell icon in the header shell shows the unread count as a badge:

```html
<button class="notification-bell" aria-label="Notifications"
        aria-haspopup="true" aria-expanded="false"
        aria-controls="notification-panel">
  <svg class="notification-bell-icon" aria-hidden="true">...</svg>
  <span class="badge badge-danger notification-badge" aria-label="3 unread notifications">3</span>
</button>

<div id="notification-panel" class="notification-panel" role="dialog"
     aria-label="Notifications" hidden>
  <header class="notification-panel-header">
    <h2>Notifications</h2>
    <button class="btn-ghost btn-sm" aria-label="Mark all as read">Mark all read</button>
  </header>
  <ul class="notification-list" role="list">
    <!-- notification items rendered here -->
  </ul>
  <footer class="notification-panel-footer">
    <a href="#/notifications">View all</a>
  </footer>
</div>
```

The panel opens on click, closes on Escape or outside click. Focus is trapped within the panel while open.

### 9.6 Toast Notifications

Toasts appear in a fixed container at the top-right corner:

```html
<div id="toast-container" class="toast-container" aria-live="polite" aria-relevant="additions">
  <div class="toast toast-success" role="status">
    <svg class="toast-icon" aria-hidden="true">...</svg>
    <div class="toast-content">
      <p class="toast-title">Backup complete</p>
      <p class="toast-message">Database backed up successfully.</p>
    </div>
    <button class="toast-dismiss" aria-label="Dismiss notification">...</button>
  </div>
</div>
```

| Feature | Behaviour |
|---------|-----------|
| Auto-dismiss | After `dismissAfter` ms (default 5000, errors 8000). Timer pauses on hover. |
| Manual dismiss | Click the dismiss button or press Escape when focused. |
| Stack limit | Maximum 5 visible toasts. Oldest dismissed when limit exceeded. |
| Animation | Slide in from right, fade out. Respects `prefers-reduced-motion`. |
| Screen reader | Container is `aria-live="polite"`. Warning/error toasts use `role="alert"` (assertive). |

### 9.7 REST API

Notifications are also accessible via the platform API for applications that run background processes on the server:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/notifications` | Create a notification |
| `GET` | `/api/v1/notifications` | List notifications (query: `unread`, `source`, `limit`, `offset`) |
| `GET` | `/api/v1/notifications/unread-count` | Get unread count |
| `PATCH` | `/api/v1/notifications/:id/read` | Mark as read |
| `POST` | `/api/v1/notifications/mark-all-read` | Mark all as read |
| `DELETE` | `/api/v1/notifications/:id` | Delete a notification |

---

## 10. Settings UI

**Story:** P3.9 `[R5.9]`

### 10.1 Structure

The settings view renders at `#/settings` with a two-panel layout: a section list on the left and the active section content on the right. On narrow viewports the section list becomes a top-level list and selecting a section navigates to it as a sub-route.

### 10.2 Base Sections

The platform provides the following settings sections:

| Section | Route | Description |
|---------|-------|-------------|
| Appearance | `#/settings/appearance` | Theme toggle (system/light/dark), sidebar mode, font size |
| Timezone | `#/settings/timezone` | User timezone selection, relative time toggle |
| Language | `#/settings/language` | Language selection from available locales |
| Connections | `#/settings/connections` | Integration adapter status (connected/disconnected/error), reconnect buttons |
| Backup | `#/settings/backup` | Manual backup trigger, backup history, restore, retention settings |
| About | `#/settings/about` | Version info, licence, links, update check button |

### 10.3 Extension Mechanism

Applications register additional settings sections:

```typescript
interface SettingsRegistry {
  /** Register a settings section. */
  register(section: SettingsSection): void;

  /** Unregister a section by ID. */
  unregister(id: string): void;

  /** Get all registered sections, sorted by order. */
  getSections(): SettingsSection[];
}

interface SettingsSection {
  /** Unique identifier. */
  id: string;

  /** Display label (translation key or literal). */
  label: string;

  /** Icon identifier. */
  icon?: string;

  /** Sort order. Platform sections use 0-99. Applications should use 100+. */
  order: number;

  /** Sub-route path (appended to #/settings/). */
  path: string;

  /** Render function. Receives the container and returns optional cleanup. */
  render: (container: HTMLElement) => (() => void) | void;
}
```

### 10.4 Appearance Section Detail

The appearance section provides:

| Control | Type | Setting key | Default |
|---------|------|-------------|---------|
| Theme | Three-way toggle (system / light / dark) | `loke.ui.theme` | `system` |
| Sidebar mode | Toggle (expanded / compact) | `loke.ui.sidebar.compact` | `false` |
| Font size | Select (small / default / large) | `loke.ui.fontSize` | `default` |

Changes take effect immediately without requiring a page reload.

### 10.5 About Section Detail

The about section displays:

- **Application name and version** (from package.json or build metadata).
- **Platform version** (loke core version).
- **Runtime** (Electron version if applicable, Node.js version, browser engine).
- **Licence** (Apache 2.0, with link to full text).
- **Update check** button that calls the version check endpoint (A5.3). Displays "Up to date" or "Update available: v{version}" with a link to release notes.
- **Links** to documentation, source repository, and issue tracker.

### 10.6 Settings Persistence

All settings are read from and written to the settings store (F6.7) using the `loke.*` namespace prefix. Changes are applied immediately via the relevant subsystem (theme engine, locale loader, etc.) without requiring restart.

---

## 11. File Organisation

The UI platform CSS and JS files are organised as follows:

```
client/
├── loke/
│   ├── tokens/
│   │   ├── primitives.css        # Primitive token values
│   │   ├── semantic.css          # Semantic token mappings
│   │   └── dark.css              # Dark mode overrides
│   ├── base/
│   │   ├── reset.css             # CSS reset
│   │   ├── typography.css        # Typographic baseline
│   │   ├── focus.css             # Focus styles and skip link
│   │   └── motion.css            # prefers-reduced-motion
│   ├── components/
│   │   ├── buttons.css
│   │   ├── cards.css
│   │   ├── badges.css
│   │   ├── forms.css
│   │   ├── tables.css
│   │   ├── alerts.css
│   │   ├── loading.css
│   │   └── tooltips.css
│   ├── shell/
│   │   ├── shell.css             # Application shell layout
│   │   ├── header.css            # Header styles
│   │   ├── sidebar.css           # Sidebar and navigation styles
│   │   └── responsive.css        # Responsive breakpoints
│   ├── views/
│   │   ├── settings.css          # Settings view layout
│   │   ├── notifications.css     # Notification panel and toasts
│   │   └── not-found.css         # 404 page
│   └── index.css                 # Entry point: imports all above in order
├── js/
│   ├── theme-engine.ts
│   ├── router.ts
│   ├── navigation.ts
│   ├── notifications.ts
│   ├── settings.ts
│   └── index.ts                  # Entry point: initialises all modules
```

The CSS entry point imports files in dependency order: tokens, then reset/base, then components, then shell, then views.

---

## 12. Performance Constraints

| Metric | Target | Source |
|--------|--------|--------|
| Page load (local) | < 500ms for any platform-provided view | R-NFR |
| Total CSS size | < 30KB minified + gzipped | — |
| Total JS size (platform UI) | < 50KB minified + gzipped | — |
| Theme switch | < 16ms (single frame) | — |
| Route transition | < 100ms render time | — |
| Toast animation | 60fps or disabled via `prefers-reduced-motion` | — |

---

## 13. Accessibility Summary

Every component in this specification adheres to WCAG 2.1 AA. The following table summarises the accessibility features per area:

| Area | Technique |
|------|-----------|
| Semantic HTML | All components use `button`, `nav`, `main`, `header`, `article`, `label`, `table`, `th[scope]` |
| Focus visible | `:focus-visible` with 2px offset ring on all interactive elements |
| Skip link | First focusable element, links to `#main` |
| Screen reader announcements | Route changes via `aria-live="assertive"`, toasts via `aria-live="polite"`, errors via `role="alert"` |
| Keyboard | All interactive elements operable via keyboard. Navigation uses roving tabindex. Escape closes overlays. |
| Colour independence | Status always paired with icon + text. WCAG AA contrast ratios. |
| Motion sensitivity | `prefers-reduced-motion` disables all animations |
| Focus trapping | Sidebar overlay, notification panel, and any future modals trap focus |
| ARIA roles | `role="tree"` for navigation, `role="switch"` for toggles, `role="dialog"` for panels, `role="progressbar"` for progress |

---

## 14. Open Questions

1. **Icon system.** Should the platform ship an icon set (e.g. SVG sprite) or require applications to provide their own? A small curated set of ~30 platform icons (navigation, status, actions) is likely sufficient.
2. **CSS layers.** Should we use CSS `@layer` to manage specificity between tokens, base, components, and application overrides? Browser support is sufficient (Chrome 99+, Firefox 97+, Safari 15.4+).
3. **Web Components.** Should any component primitives be implemented as Custom Elements for encapsulation? This would add complexity but provide stronger isolation for application overrides.
