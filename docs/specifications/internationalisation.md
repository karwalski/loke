# Internationalisation Specification

**Epic:** P4 — Internationalisation
**Stories:** P4.1, P4.2, P4.3
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

loke ships with an internationalisation (i18n) framework so that every user-facing string passes through a translation layer from day one. The framework provides a translation function, a locale file structure, a locale loader, and formatting utilities built on the `Intl` APIs.

This specification defines:

- The `t()` translation function: signature, namespacing, interpolation, pluralisation, and fallback behaviour
- The locale file directory structure and naming conventions
- Layout accommodation guidelines for text expansion
- Locale-aware formatting for dates, times, numbers, and relative time

### 1.1 Design Alignment

This specification follows the loke design principles:

- **Internationalisable from day one.** Every user-facing string passes through a translation layer. The platform ships with an i18n framework and locale file structure. Applications provide their own translations.
- **Extensible.** Applications add their own locale files alongside platform translations, using namespace separation to avoid collisions.
- **Do the right thing by default.** When a translation is missing, the framework falls back gracefully — first to the base locale, then to the key itself. The user always sees something meaningful.
- **Privacy is the foundation.** Translation keys and interpolation parameters must never contain unsanitised user data that could leak through logging or error messages.

### 1.2 Requirements Traceability

| Requirement | Story |
|-------------|-------|
| R6.1 — Translation function | P4.1 |
| R6.2 — Locale file structure | P4.2 |
| R6.3 — Locale loader | P4.1 |
| R6.4 — Layout accommodation | P4.3 |
| R6.5 — Date, time, and number formatting | P4.3 |
| R9.5 — Relative time display | P4.3 |

---

## 2. Translation Function

The `t()` function is the single entry point for all translated strings. It is a pure function — given the same key, parameters, and loaded locale data, it always returns the same result. No I/O, no side effects.

### 2.1 Function Signature

```typescript
/**
 * Look up a namespaced translation key, interpolate parameters,
 * apply pluralisation rules, and return the resolved string.
 *
 * @param key - Dot-separated, namespaced translation key (e.g. "loke.settings.language")
 * @param params - Optional interpolation parameters and/or count for pluralisation
 * @returns The resolved, interpolated string. Falls back to base locale, then to the key itself.
 */
function t(key: string, params?: TranslationParams): string;

interface TranslationParams {
  /** Named interpolation values. Inserted at {{name}} placeholders. */
  [name: string]: string | number;

  /** Pluralisation count. When present, selects the _zero / _one / _other suffix. */
  count?: number;
}
```

### 2.2 Key Namespacing

Translation keys use dot-separated namespaces to avoid collisions between platform and application strings.

| Prefix | Owner | Example |
|--------|-------|---------|
| `loke.*` | Platform | `loke.settings.language`, `loke.errors.network_timeout` |
| `<app>.*` | Application | `myapp.dashboard.title`, `myapp.meeting.status_active` |

Rules:

- Platform keys are always prefixed `loke.`.
- Applications choose their own prefix, documented in their plugin registration.
- Keys must match `^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+$` — lowercase, dot-separated, underscores within segments.
- Nesting depth is unlimited but three to four levels is recommended for readability.

### 2.3 Interpolation

Parameters are inserted into translation strings using `{{name}}` placeholders:

```json
{
  "loke.welcome.greeting": "Welcome, {{name}}. You have {{count}} notifications."
}
```

```typescript
t("loke.welcome.greeting", { name: "Alice", count: 5 });
// => "Welcome, Alice. You have 5 notifications."
```

Rules:

- Placeholder names must match `[a-zA-Z][a-zA-Z0-9_]*`.
- Unmatched placeholders are left as-is (e.g. `"{{name}}"` if `name` is not provided). This makes missing parameters visible during development.
- Parameter values are converted to strings via `String(value)`. No HTML is interpreted.
- Numeric parameters used in display text should be formatted via `Intl.NumberFormat` before being passed to `t()`, unless the translation string handles formatting itself.

### 2.4 Pluralisation

Pluralisation uses suffix-based key variants. When `params.count` is provided, the function selects the appropriate variant:

| Suffix | Selected when |
|--------|---------------|
| `_zero` | `count === 0` |
| `_one` | `count === 1` |
| `_other` | All other values (including negative numbers and decimals) |

```json
{
  "loke.notifications.unread_zero": "No unread notifications",
  "loke.notifications.unread_one": "1 unread notification",
  "loke.notifications.unread_other": "{{count}} unread notifications"
}
```

```typescript
t("loke.notifications.unread", { count: 0 });
// => "No unread notifications"

t("loke.notifications.unread", { count: 1 });
// => "1 unread notification"

t("loke.notifications.unread", { count: 7 });
// => "7 unread notifications"
```

Resolution order when `count` is present:

1. Look up `key_zero` / `key_one` / `key_other` based on the count value.
2. If the specific suffix variant is missing, fall back to `key_other`.
3. If `key_other` is also missing, fall back to the base key (without suffix).
4. If no variant is found in the current locale, repeat steps 1-3 in the base locale.
5. If still not found, return the key.

#### 2.4.1 Future: CLDR Plural Rules

The `_zero` / `_one` / `_other` model covers English and most European languages. Languages with more complex plural categories (Arabic has six forms, Polish has four) will require CLDR plural rules. The suffix-based approach is forward-compatible: additional suffixes (`_two`, `_few`, `_many`) can be added when CLDR support is implemented. The `_other` suffix always serves as the final fallback.

### 2.5 Fallback Chain

When a key is not found in the current locale, the function follows this chain:

```
current locale (e.g. "de") -> base locale ("en") -> return key as-is
```

1. **Current locale.** Look up the key in the user's selected locale.
2. **Base locale.** If not found, look up the key in `en` (English). English is always loaded and serves as the base locale.
3. **Key as-is.** If the key does not exist in any locale, return the key string itself (e.g. `"loke.settings.language"`). This ensures the UI never shows `undefined` or an empty string, and makes missing translations immediately visible during development and testing.

When a fallback to the base locale occurs, the framework logs a warning at `debug` level with the missing key and the requested locale. This supports translation completeness auditing without polluting production logs.

---

## 3. Locale Loader

### 3.1 Loading Behaviour

Locale files are loaded at two points:

1. **Startup.** The base locale (`en`) and the user's configured locale are loaded during the startup sequence (after config, logger, and database; before routes and server). Loading is synchronous to the startup sequence — the server does not start until the configured locale is loaded.
2. **On language change.** When the user changes their language preference in settings, the new locale is loaded on demand. The UI updates immediately after loading.

### 3.2 Lazy Loading

Locales not loaded at startup are loaded lazily when requested:

```typescript
/**
 * Load a locale file on demand. Returns a promise that resolves
 * when the locale data is available for use by t().
 */
function loadLocale(locale: string): Promise<void>;

/** Returns the currently active locale code (e.g. "en", "de", "ja"). */
function getCurrentLocale(): string;

/** Returns the list of locale codes for which locale files exist. */
function getAvailableLocales(): string[];
```

The locale loader discovers available locales by scanning the `locales/` directory at startup. The list of available locales is cached and does not require re-scanning unless explicitly refreshed.

### 3.3 Error Handling

| Failure | Behaviour |
|---------|-----------|
| Base locale (`en`) file missing or malformed | Fatal error. loke refuses to start. |
| User's configured locale file missing | Warning logged. Falls back to base locale. |
| Lazily loaded locale file missing | `loadLocale()` rejects. Current locale remains unchanged. Warning logged. |
| Malformed JSON in locale file | Locale file rejected. Previous locale data for that language remains (or base locale if first load). Error logged with file path and parse error. |

---

## 4. Locale File Structure

### 4.1 Directory Layout

```
locales/
├── en.json          # Base locale (English) — always present
├── de.json          # German
├── fr.json          # French
├── ja.json          # Japanese
├── zh-Hans.json     # Simplified Chinese
├── pt-BR.json       # Brazilian Portuguese
└── ...
```

Rules:

- One file per locale, named with the IETF BCP 47 language tag (e.g. `en`, `de`, `fr`, `ja`, `zh-Hans`, `pt-BR`).
- Files are JSON. No comments (JSON does not support them). Use key names to provide context.
- The `en.json` file is the base locale and must contain every key used by the platform. It serves as the canonical reference for translators.
- Application locale files follow the same structure in the application's own `locales/` directory. The loader merges platform and application locale data at startup, with namespace prefixes preventing collisions.

### 4.2 File Format

Locale files use a flat key-value structure with dot-separated keys. Nesting is not used — flat keys are simpler to search, merge, and validate.

```json
{
  "loke.app.name": "loke",
  "loke.app.tagline": "Local-first privacy proxy for LLM traffic",

  "loke.nav.dashboard": "Dashboard",
  "loke.nav.settings": "Settings",
  "loke.nav.privacy": "Privacy",
  "loke.nav.audit": "Audit Log",

  "loke.settings.language": "Language",
  "loke.settings.language_description": "Choose your preferred display language.",
  "loke.settings.theme": "Appearance",
  "loke.settings.theme_system": "System",
  "loke.settings.theme_light": "Light",
  "loke.settings.theme_dark": "Dark",
  "loke.settings.timezone": "Timezone",
  "loke.settings.save": "Save",
  "loke.settings.saved": "Settings saved.",

  "loke.notifications.unread_zero": "No unread notifications",
  "loke.notifications.unread_one": "1 unread notification",
  "loke.notifications.unread_other": "{{count}} unread notifications",

  "loke.errors.network_timeout": "The request timed out. Please try again.",
  "loke.errors.not_found": "The requested resource was not found.",
  "loke.errors.generic": "Something went wrong. Please try again later.",

  "loke.privacy.pii_detected": "{{count}} sensitive items detected and anonymised.",
  "loke.privacy.pipeline_blocked": "This request was blocked by the privacy pipeline.",

  "loke.time.just_now": "just now",
  "loke.time.minutes_ago_one": "1 minute ago",
  "loke.time.minutes_ago_other": "{{count}} minutes ago"
}
```

An application adds its own keys with its own prefix:

```json
{
  "myapp.dashboard.title": "My Dashboard",
  "myapp.dashboard.welcome": "Welcome back, {{name}}.",
  "myapp.meeting.status_active": "In progress",
  "myapp.meeting.status_ended": "Ended",
  "myapp.meeting.participants_one": "1 participant",
  "myapp.meeting.participants_other": "{{count}} participants"
}
```

### 4.3 Translation Guidelines for Contributors

1. **Translate meaning, not words.** Adapt phrasing to be natural in the target language.
2. **Preserve all `{{placeholders}}`.** Every placeholder in the English string must appear in the translation. The placeholder name must not be translated.
3. **Provide all plural variants.** If the English key has `_zero`, `_one`, and `_other` variants, the translation must provide at least `_one` and `_other`. The `_zero` variant is optional if the language does not distinguish zero grammatically.
4. **Do not hardcode punctuation assumptions.** Some languages use different quotation marks, list separators, or sentence-ending punctuation.
5. **Keep strings reasonably concise.** Translations expand (see section 5), but excessively long translations will still cause layout issues.
6. **British English for the base locale.** The base locale uses British English spelling (anonymise, optimise, colour, licence).

### 4.4 Locale File Validation

A validation utility checks locale files for correctness:

```bash
loke locale validate [locale]
```

Checks performed:

| Check | Severity | Description |
|-------|----------|-------------|
| Valid JSON | Error | File must parse as valid JSON. |
| All base locale keys present | Warning | Every key in `en.json` should have a corresponding key in the target locale. |
| No orphaned keys | Warning | Keys present in the target locale but not in `en.json` are likely stale. |
| Placeholders match | Error | Every `{{name}}` in the English string must appear in the translation. |
| Plural variants complete | Warning | If English has `_one` and `_other`, the translation should too. |
| Key format valid | Error | Keys must match the namespace pattern. |
| No HTML in values | Warning | Translation strings should not contain HTML markup. |

---

## 5. Layout Accommodation

### 5.1 Text Expansion Guidelines

Translated text is frequently longer than the English source. German, Finnish, and Japanese (when romanised) commonly expand by 30-50%. Some languages contract (Chinese, Korean).

| Source length (English characters) | Expected expansion |
|------------------------------------|--------------------|
| 1-10 | Up to 200-300% |
| 11-20 | Up to 180-200% |
| 21-70 | Up to 140-180% |
| 71+ | Up to 130-150% |

Short strings (button labels, menu items) expand the most proportionally.

### 5.2 Layout Rules

All platform-provided UI components must follow these rules:

1. **No hardcoded widths on text containers.** Use `min-width` if a minimum is needed, but never `width` or `max-width` that would truncate translated text. Flexbox and grid layouts are preferred.
2. **Buttons and labels must grow with content.** Use `padding` for spacing, not fixed widths. Buttons use `min-width` for visual consistency but expand for longer text.
3. **Truncation is a last resort.** If a container genuinely cannot grow (e.g. a table cell), use CSS `text-overflow: ellipsis` with a `title` attribute showing the full text. Never silently truncate.
4. **No text in images.** Text baked into images, icons, or SVGs cannot be translated. Use text overlays or adjacent labels.
5. **Test with pseudo-localisation.** During development, a pseudo-locale (e.g. `en-XL`) can be generated that pads every string by 40% with accented characters. This exposes layout breakage before real translations arrive.

### 5.3 Directionality

RTL (right-to-left) layout support is not required in v1, but the layout must not hardcode LTR assumptions:

- Use CSS logical properties (`margin-inline-start`, `padding-inline-end`) instead of physical properties (`margin-left`, `padding-right`) where practical.
- Use `dir="auto"` on user-generated content containers.
- Avoid absolute positioning that assumes text flows left to right.
- Icons that imply direction (arrows, chevrons) should be aware that they may need to flip in RTL contexts. Use CSS `transform: scaleX(-1)` controlled by a `[dir="rtl"]` selector rather than baking direction into the icon.

---

## 6. Locale-Aware Formatting

All date, time, number, and relative time formatting uses the `Intl` APIs. No hardcoded formats anywhere in the platform.

### 6.1 Date and Time Formatting

```typescript
/**
 * Format a date for display in the user's locale.
 *
 * @param date - The Date object or ISO 8601 string to format
 * @param style - Predefined format style
 * @returns Locale-formatted date string
 */
function formatDate(
  date: Date | string,
  style: "short" | "medium" | "long" | "full"
): string;

/**
 * Format a time for display in the user's locale.
 */
function formatTime(
  date: Date | string,
  style: "short" | "medium" | "long"
): string;

/**
 * Format a date and time together.
 */
function formatDateTime(
  date: Date | string,
  dateStyle: "short" | "medium" | "long" | "full",
  timeStyle: "short" | "medium" | "long"
): string;
```

Implementation uses `Intl.DateTimeFormat`:

```typescript
// Internal implementation pattern
const formatter = new Intl.DateTimeFormat(getCurrentLocale(), {
  dateStyle: style,
  timeZone: getUserTimezone(),  // Always explicit — never rely on system default
});
return formatter.format(date instanceof Date ? date : new Date(date));
```

Example outputs for the same timestamp (`2026-04-05T14:30:00Z`):

| Locale | `formatDate(d, "long")` | `formatTime(d, "short")` |
|--------|-------------------------|--------------------------|
| `en` | 5 April 2026 | 14:30 |
| `en-US` | April 5, 2026 | 2:30 PM |
| `de` | 5. April 2026 | 14:30 |
| `ja` | 2026年4月5日 | 14:30 |

### 6.2 Number Formatting

```typescript
/**
 * Format a number for display in the user's locale.
 */
function formatNumber(
  value: number,
  options?: {
    style?: "decimal" | "currency" | "percent";
    currency?: string;         // ISO 4217 code, required when style is "currency"
    minimumFractionDigits?: number;
    maximumFractionDigits?: number;
  }
): string;
```

Implementation uses `Intl.NumberFormat`:

```typescript
const formatter = new Intl.NumberFormat(getCurrentLocale(), options);
return formatter.format(value);
```

Example outputs:

| Locale | `formatNumber(1234567.89)` | `formatNumber(0.15, { style: "percent" })` |
|--------|----------------------------|--------------------------------------------|
| `en` | 1,234,567.89 | 15% |
| `de` | 1.234.567,89 | 15 % |
| `fr` | 1 234 567,89 | 15 % |
| `ja` | 1,234,567.89 | 15% |

### 6.3 Relative Time Formatting

Relative time formatting is used throughout the UI for timestamps ("2 minutes ago", "in 3 hours", "yesterday").

```typescript
/**
 * Format a timestamp as a human-readable relative time string.
 *
 * @param date - The Date object or ISO 8601 string to format relative to now
 * @returns Locale-formatted relative time string (e.g. "2 minutes ago", "in 3 hours")
 */
function formatRelativeTime(date: Date | string): string;
```

Implementation uses `Intl.RelativeTimeFormat` with automatic unit selection:

```typescript
function formatRelativeTime(date: Date | string): string {
  const target = date instanceof Date ? date : new Date(date);
  const now = Date.now();
  const diffMs = target.getTime() - now;
  const diffSeconds = Math.round(diffMs / 1000);

  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["year", 60 * 60 * 24 * 365],
    ["month", 60 * 60 * 24 * 30],
    ["week", 60 * 60 * 24 * 7],
    ["day", 60 * 60 * 24],
    ["hour", 60 * 60],
    ["minute", 60],
    ["second", 1],
  ];

  const formatter = new Intl.RelativeTimeFormat(getCurrentLocale(), {
    numeric: "auto",  // "yesterday" instead of "1 day ago"
  });

  for (const [unit, secondsInUnit] of units) {
    if (Math.abs(diffSeconds) >= secondsInUnit || unit === "second") {
      const value = Math.round(diffSeconds / secondsInUnit);
      return formatter.format(value, unit);
    }
  }

  return formatter.format(0, "second");  // "now" / "just now"
}
```

Example outputs for `en`:

| Time difference | Output |
|-----------------|--------|
| 0 seconds | "now" |
| -30 seconds | "30 seconds ago" |
| -120 seconds | "2 minutes ago" |
| -86400 seconds (1 day) | "yesterday" |
| +3600 seconds | "in 1 hour" |
| +604800 seconds | "next week" |

### 6.4 Timezone Handling

All timestamps are stored in UTC (as defined in F6.1). Display formatting always converts to the user's configured timezone:

- The user's timezone preference is stored in the settings store under `loke.timezone`.
- If not configured, the platform detects the system timezone via `Intl.DateTimeFormat().resolvedOptions().timeZone`.
- All `Intl.DateTimeFormat` calls pass the timezone explicitly. The platform never relies on the implicit system timezone.
- The wrapper application is responsible for any multi-timezone comparison UI (R9.2, R9.3). loke provides the formatting primitives.

---

## 7. Integration with Other Platform Systems

### 7.1 Startup Sequence

Locale loading occurs in the startup sequence at the position defined in F1.6:

```
config -> logger -> database -> migrations -> settings -> locale -> routes -> server
```

The `settings` step loads the user's language preference. The `locale` step loads the base locale and the user's selected locale. If locale loading fails for the user's language, the startup continues with the base locale and logs a warning.

### 7.2 Settings UI

The settings view (P3.9) includes a language selector populated by `getAvailableLocales()`. Changing the language:

1. Calls `loadLocale(newLocale)`.
2. Persists the preference via the settings store (`loke.locale`).
3. Re-renders the current view with the new locale.

### 7.3 Plugin System

Applications register their locale files during plugin registration (P2.1). The plugin provides the path to its `locales/` directory. The loader merges application locale data with platform locale data, namespaced by prefix.

### 7.4 Error Messages

Error messages shown to users (P6.1, P6.2) pass through `t()`. Error codes map to translation keys:

```typescript
// Server error handler produces a translatable error
return {
  error: {
    code: "NETWORK_TIMEOUT",
    message: t("loke.errors.network_timeout"),
    requestId: correlationId,
  },
};
```

### 7.5 Notifications

Notification messages (P3.8) are stored with their translation key and parameters, not with the pre-rendered string. This allows notifications to be re-rendered when the locale changes:

```typescript
// Stored in database
{ key: "loke.privacy.pii_detected", params: { count: 3 } }

// Rendered on display
t("loke.privacy.pii_detected", { count: 3 });
// => "3 sensitive items detected and anonymised."
```

---

## 8. Testing

### 8.1 Unit Testing

The `t()` function is pure and testable without I/O:

```typescript
// Load test locale data directly
loadLocaleData("en", { "test.greeting": "Hello, {{name}}" });

expect(t("test.greeting", { name: "Alice" })).toBe("Hello, Alice");
expect(t("test.missing_key")).toBe("test.missing_key");
```

### 8.2 Translation Completeness

The `loke locale validate` command (section 4.4) can be run in CI to catch missing translations before merge.

### 8.3 Pseudo-Localisation

A development-only pseudo-locale (`en-XL`) is generated from the base locale by:

1. Wrapping each string in brackets: `[...string...]`
2. Replacing ASCII characters with accented equivalents: `a` -> `à`, `e` -> `ê`, etc.
3. Padding strings by 40% with extra characters.

This makes it easy to visually identify untranslated strings (they lack brackets) and to spot layout issues caused by text expansion.

---

## 9. Security Considerations

- **No HTML in translations.** Translation strings must not contain HTML. The rendering layer is responsible for markup. This prevents XSS via translation injection.
- **No user input in keys.** The `key` parameter to `t()` must always be a compile-time string literal or a constant. Never construct keys from user input.
- **Parameter sanitisation.** Interpolation parameters are converted to strings and inserted as text content. The rendering layer must treat the output of `t()` as text, not as HTML.
- **Log redaction.** When logging missing translation keys at debug level, the parameters are not logged (they may contain user data). Only the key and locale are logged.
