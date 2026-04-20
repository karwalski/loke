# Per-Element AI Privacy Metadata for HTML

## Web Privacy Metadata Specification

### Draft Community Group Report, 4 April 2026

---

**Latest published version:**
: This document

**Editors:**
: Matthew Watt (loke project)

**Participate:**
: [GitHub repository](https://github.com/loke/web-privacy-metadata)
: [File an issue](https://github.com/loke/web-privacy-metadata/issues)

---

## Abstract

This specification defines two HTML attributes -- `data-ai-sensitivity` and `data-ai-consume` -- that enable web content authors to declare per-element privacy sensitivity levels and permitted AI processing modes. These attributes provide machine-readable signals that AI user agents, browser extensions, and assistive tools can use to determine how to handle specific portions of a web page.

While existing standards such as the IETF AIPREF headers, the TDM Reservation Protocol, and robots.txt AI directives operate at the page or site level, no mechanism currently exists for authors to express fine-grained, element-level privacy declarations within an HTML document. This specification fills that gap.

## Status of This Document

This document is a Draft Community Group Report. It has no official standing and does not represent consensus of any standards body. It is published for discussion and review purposes.

This specification is intended for submission as either a W3C Community Group Report or an IETF Internet-Draft. Feedback is solicited from the W3C community, browser vendors, web developers, and the broader privacy and AI standards communities.

Comments regarding this document are welcome. Please file issues on the [GitHub repository](https://github.com/loke/web-privacy-metadata/issues).

## Table of Contents

1. [Introduction and Motivation](#1-introduction-and-motivation)
2. [Terminology](#2-terminology)
3. [Problem Statement](#3-problem-statement)
4. [Proposed Solution](#4-proposed-solution)
5. [Attribute Definitions](#5-attribute-definitions)
6. [Inheritance Model](#6-inheritance-model)
7. [HTTP Header and Meta Tag Equivalents](#7-http-header-and-meta-tag-equivalents)
8. [Processing Model](#8-processing-model)
9. [Integration with Existing Standards](#9-integration-with-existing-standards)
10. [Security Considerations](#10-security-considerations)
11. [Privacy Considerations](#11-privacy-considerations)
12. [IANA Considerations](#12-iana-considerations)
13. [Examples](#13-examples)
14. [References](#14-references)

---

## 1. Introduction and Motivation

The rapid proliferation of AI-powered browser extensions, assistive agents, and screen-reading tools has created an urgent need for web content authors to express privacy intent at a granular level within HTML documents.

Current privacy mechanisms for web content operate at coarse granularities:

- **robots.txt** and **Robots-Tag headers** control crawler access to entire pages or resources.
- **IETF AIPREF headers** (RFC in development) express page-level preferences for AI training and inference.
- **TDM Reservation Protocol** (W3C) declares text and data mining rights at the resource level.
- **C2PA content credentials** attest provenance and editing history of media assets.

None of these mechanisms allow a content author to declare that a specific `<div>` containing a Social Security Number should be treated differently from the marketing text on the same page. Yet this is precisely the distinction that matters when an AI browser extension reads page content to "help" the user.

### 1.1 Motivating Incidents

A UC Davis study published in August 2025 documented serious privacy violations by AI browser extensions. The extension Merlin was observed exfiltrating Social Security Numbers from IRS tax filing forms to remote servers. The extension had access to the full DOM and made no distinction between public-facing content and sensitive form data. Had those form fields carried machine-readable privacy declarations, a well-behaved AI agent could have excluded them from processing, and a browser could have enforced that exclusion.

At TPAC 2025, Google stated that it is time for "additional machine-readable means for web publisher choice and control for emerging AI." This specification is a direct response to that call.

### 1.2 Design Goals

1. **Simplicity.** The mechanism must be trivially adoptable by web developers using standard HTML `data-*` attributes.
2. **Granularity.** Declarations must be expressible at any level of the DOM, from the `<html>` element to an individual `<input>`.
3. **Composability.** Element-level declarations must compose with page-level defaults (HTTP headers, `<meta>` tags) and site-level policies (robots.txt, AIPREF headers).
4. **Progressive adoption.** Pages without these attributes continue to function exactly as before. The absence of attributes carries no implication.
5. **Enforceability.** The attributes must be defined precisely enough that user agents can implement deterministic processing rules.

---

## 2. Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC2119] [RFC8174] when, and only when, they appear in all capitals, as shown here.

**AI User Agent**
: Any software that reads, processes, or transmits web page content for the purpose of AI inference, training, summarisation, or assistive functionality. This includes browser extensions, embedded AI features, screen readers with AI capabilities, and standalone AI tools that consume web content.

**Content Author**
: The person or system that produces the HTML markup of a web page.

**Sensitivity Level**
: A classification of how sensitive a piece of content is, as declared by the content author.

**Consumption Mode**
: A declaration of how an AI user agent is permitted to process a piece of content.

**Effective Sensitivity**
: The sensitivity level that applies to a given element after inheritance resolution.

**Effective Consumption Mode**
: The consumption mode that applies to a given element after inheritance resolution.

---

## 3. Problem Statement

### 3.1 The Granularity Gap

Existing web privacy standards operate at the wrong granularity for the AI agent era. Consider a healthcare portal:

- The page header and navigation are public marketing content.
- The sidebar contains general health information articles.
- The main content area displays the patient's name, date of birth, diagnoses, and medications.
- A form allows updating insurance information including policy numbers.

A robots.txt directive or an AIPREF header can only say "this entire page is off-limits" or "this entire page is available." Neither can express the reality that the page contains a mixture of public and highly sensitive content.

### 3.2 The Enforcement Gap

Even when pages are marked as off-limits to crawlers, AI browser extensions operate within the user's authenticated session and read the rendered DOM directly. They bypass robots.txt entirely because they are not crawlers -- they are user agents acting on behalf of the user. No existing mechanism allows the content author to communicate privacy expectations to these in-browser AI tools.

### 3.3 The Semantic Gap

CSS classes like `sensitive` or `private` are presentational hints with no standardised semantics. ARIA attributes describe accessibility roles, not privacy intent. The HTML specification includes no vocabulary for expressing "this content should not be read by AI tools" or "this content may be processed but must not leave the device."

---

## 4. Proposed Solution

This specification introduces two HTML attributes using the `data-*` extension mechanism defined in the HTML Living Standard (section 3.2.6.6):

1. **`data-ai-sensitivity`** -- Declares the sensitivity classification of the element's content.
2. **`data-ai-consume`** -- Declares the permitted AI processing mode for the element's content.

These attributes are designed to:

- Be immediately deployable on any HTML page without browser updates.
- Be detectable by AI user agents via standard DOM APIs (`element.dataset.aiSensitivity`).
- Compose with page-level and site-level signals through a well-defined precedence model.
- Be enforceable by browsers that choose to implement native support.

### 4.1 Rationale for `data-*` Attributes

The `data-*` attribute namespace is the HTML-sanctioned mechanism for embedding custom data in HTML elements. Using `data-ai-sensitivity` rather than a bare `ai-sensitivity` attribute ensures:

- Immediate compatibility with all existing HTML parsers.
- No conflict with current or future HTML attributes.
- Accessibility via the `HTMLElement.dataset` API in JavaScript.
- Validity under HTML validation tools.

Should this specification achieve standardisation, the attributes could be promoted to first-class HTML attributes (e.g., `aisensitivity`) in a future HTML revision, with `data-ai-sensitivity` retained as a synonym for backward compatibility.

---

## 5. Attribute Definitions

### 5.1 The `data-ai-sensitivity` Attribute

**Purpose:** Declares the sensitivity classification of the content within the element.

**Syntax:**

```
data-ai-sensitivity = "public" | "internal" | "confidential" | "restricted"
```

**Values:**

| Value | Definition | Examples |
|---|---|---|
| `public` | Content that is intended for unrestricted public access. No special handling required by AI user agents. | Marketing copy, public documentation, published articles, product descriptions, open-source code. |
| `internal` | Content that is not secret but is intended for a limited audience. AI user agents SHOULD NOT transmit this content to external services without explicit user consent. | Internal company announcements, team wiki pages, non-sensitive operational data, internal tool interfaces. |
| `confidential` | Content that contains sensitive information. AI user agents MUST NOT transmit this content to external services. Local-only processing is permitted if the user has explicitly enabled it. | Employee records, financial reports, customer lists, unpublished research, legal documents under review. |
| `restricted` | Content that contains highly sensitive information subject to regulatory or legal protection. AI user agents MUST NOT process this content in any way. The content MUST be treated as opaque and unreadable. | Patient health records (HIPAA), Social Security Numbers, credit card numbers (PCI-DSS), classified government information, biometric data. |

**ABNF Grammar:**

```abnf
ai-sensitivity-value = "public" / "internal" / "confidential" / "restricted"
```

**When this attribute is absent,** the element inherits its effective sensitivity from its parent element (see Section 6). If no ancestor declares a sensitivity level and no page-level default exists, the effective sensitivity is undefined, and AI user agents SHOULD apply their own default policy.

### 5.2 The `data-ai-consume` Attribute

**Purpose:** Declares the permitted processing mode for the content within the element when consumed by AI user agents.

**Syntax:**

```
data-ai-consume = "local-only" | "anonymised-ok" | "unrestricted"
```

**Values:**

| Value | Definition | Processing Requirements |
|---|---|---|
| `local-only` | Content may be processed only on the user's local device. No content, derivative, or summary may be transmitted to any external service. | AI user agents MUST process this content entirely on-device. If no local processing capability exists, the content MUST be skipped. |
| `anonymised-ok` | Content may be transmitted to external services only after personally identifiable information and sensitive data elements have been removed or replaced with non-reversible placeholders. | AI user agents MUST apply PII detection and anonymisation before any external transmission. The anonymisation process MUST be documented and auditable. |
| `unrestricted` | Content may be processed and transmitted without special restrictions beyond the AI user agent's general privacy policy. | Standard processing applies. No additional constraints imposed by this attribute. |

**ABNF Grammar:**

```abnf
ai-consume-value = "local-only" / "anonymised-ok" / "unrestricted"
```

**When this attribute is absent,** the element inherits its effective consumption mode from its parent element (see Section 6). If no ancestor declares a consumption mode and no page-level default exists, the effective consumption mode is undefined, and AI user agents SHOULD apply their own default policy.

### 5.3 Attribute Interaction

The two attributes are orthogonal and may be combined freely. The `data-ai-sensitivity` attribute classifies the content; the `data-ai-consume` attribute constrains how it may be processed.

When both attributes are present, the more restrictive interpretation applies. For example:

- `data-ai-sensitivity="restricted"` combined with `data-ai-consume="unrestricted"` -- The `restricted` sensitivity level takes precedence. AI user agents MUST NOT process this content regardless of the consumption mode.
- `data-ai-sensitivity="public"` combined with `data-ai-consume="local-only"` -- The content is not sensitive, but the author has requested local-only processing. AI user agents MUST respect the `local-only` constraint.

**Conflict Resolution Rule:** When `data-ai-sensitivity` and `data-ai-consume` imply different restriction levels, the AI user agent MUST apply the more restrictive of the two.

The following table defines the effective processing constraint for each combination:

| Sensitivity \ Consume | `local-only` | `anonymised-ok` | `unrestricted` |
|---|---|---|---|
| `public` | Local-only processing | Anonymised external OK | Unrestricted |
| `internal` | Local-only processing | Anonymised external OK | External with user consent |
| `confidential` | Local-only processing | Anonymised external with user consent | Local-only processing |
| `restricted` | No processing | No processing | No processing |

---

## 6. Inheritance Model

### 6.1 General Rule

If an element does not specify `data-ai-sensitivity` or `data-ai-consume`, it inherits the effective value from its nearest ancestor that does specify the attribute. This inheritance follows the DOM tree, not the visual layout.

```html
<div data-ai-sensitivity="confidential">
  <!-- All children inherit confidential sensitivity -->
  <p>This paragraph is confidential.</p>
  <p data-ai-sensitivity="public">This paragraph is explicitly public.</p>
  <div>
    <!-- Still confidential, inherited from grandparent -->
    <span>This span is confidential.</span>
  </div>
</div>
```

### 6.2 Inheritance Precedence

The effective value for an element is determined by the following precedence order (highest to lowest):

1. The element's own `data-ai-sensitivity` or `data-ai-consume` attribute.
2. The nearest ancestor's attribute value (walking up the DOM tree).
3. The `<meta>` tag value (see Section 7.2).
4. The HTTP header value (see Section 7.1).
5. Undefined (no declaration exists).

### 6.3 Escalation Rule

A child element MAY escalate to a more restrictive level than its parent. A child element SHOULD NOT de-escalate to a less restrictive level than its parent, but this is not prohibited. Content authors who de-escalate accept responsibility for ensuring the de-escalated content genuinely warrants less protection.

**Restriction ordering** (least to most restrictive):

For `data-ai-sensitivity`:
```
public < internal < confidential < restricted
```

For `data-ai-consume`:
```
unrestricted < anonymised-ok < local-only
```

### 6.4 Shadow DOM

For elements within a Shadow DOM, inheritance crosses shadow boundaries. The shadow host's effective values apply to the shadow root's children unless those children specify their own values.

### 6.5 Iframes

Attributes on an `<iframe>` element apply to the iframe container only, not to the content within the iframe. The framed document establishes its own attribute hierarchy starting from its own `<html>` element, HTTP headers, and `<meta>` tags.

---

## 7. HTTP Header and Meta Tag Equivalents

### 7.1 HTTP Headers

Two HTTP response headers are defined for page-level defaults:

**`X-AI-Sensitivity`**

```http
X-AI-Sensitivity: confidential
```

Sets the default sensitivity level for the entire document. Equivalent to placing `data-ai-sensitivity` on the `<html>` element.

**`X-AI-Consume`**

```http
X-AI-Consume: local-only
```

Sets the default consumption mode for the entire document. Equivalent to placing `data-ai-consume` on the `<html>` element.

**Header Syntax (ABNF):**

```abnf
X-AI-Sensitivity = ai-sensitivity-value
X-AI-Consume     = ai-consume-value
```

These headers use the provisional `X-` prefix. Should this specification be adopted by the IETF, the headers would be registered without the `X-` prefix as `AI-Sensitivity` and `AI-Consume`.

### 7.2 Meta Tags

For content authors who cannot control HTTP headers, equivalent `<meta>` tags are defined:

```html
<meta name="ai-sensitivity" content="confidential">
<meta name="ai-consume" content="local-only">
```

**Precedence:** If both an HTTP header and a `<meta>` tag are present, the HTTP header takes precedence. If both a `<meta>` tag and an attribute on the `<html>` element are present, the attribute on the `<html>` element takes precedence.

### 7.3 Relationship to robots.txt and Robots-Tag

These attributes do not replace or override robots.txt or Robots-Tag headers. Those mechanisms control crawler access; these attributes control in-session AI agent behavior. Both may apply simultaneously:

- `robots.txt` may disallow crawling of a page entirely.
- If a user navigates to the page anyway, the `data-ai-*` attributes guide in-session AI tools.

---

## 8. Processing Model

This section defines how conforming AI user agents MUST process these attributes.

### 8.1 Discovery

When an AI user agent accesses a web page, it MUST:

1. Check for `X-AI-Sensitivity` and `X-AI-Consume` HTTP response headers.
2. Check for `<meta name="ai-sensitivity">` and `<meta name="ai-consume">` tags in the document `<head>`.
3. Before processing any DOM element, resolve the element's effective sensitivity and consumption mode using the inheritance rules in Section 6.

### 8.2 Processing Rules by Sensitivity Level

**`public`:**
- The AI user agent MAY process, store, and transmit the content.
- No special handling is required.

**`internal`:**
- The AI user agent SHOULD NOT transmit the content to external services without explicit, informed user consent.
- The AI user agent MAY process the content locally.
- If transmitted externally, the AI user agent SHOULD log the transmission for auditability.

**`confidential`:**
- The AI user agent MUST NOT transmit the content to external services in its original form.
- The AI user agent MAY process the content locally if the user has explicitly enabled local AI processing.
- If the `data-ai-consume` value is `anonymised-ok`, the AI user agent MAY transmit an anonymised derivative after obtaining explicit user consent.

**`restricted`:**
- The AI user agent MUST NOT process, store, cache, or transmit the content.
- The AI user agent MUST treat the content as opaque.
- The AI user agent MUST NOT include any part of the content in prompts, summaries, context windows, or any other AI processing pipeline.
- Violation of this rule constitutes a security incident.

### 8.3 Processing Rules by Consumption Mode

**`unrestricted`:**
- Standard processing. The AI user agent's general privacy policy applies.

**`anonymised-ok`:**
- Before transmitting content externally, the AI user agent MUST:
  1. Detect personally identifiable information (PII) using at minimum regex-based pattern matching for structured PII (emails, phone numbers, government IDs, financial account numbers).
  2. Replace detected PII with non-reversible placeholders.
  3. Ensure the anonymised content cannot be re-identified.
  4. Log the anonymisation operation for audit purposes.

**`local-only`:**
- The AI user agent MUST NOT transmit the content, or any derivative of the content, to any external service.
- Processing MUST occur entirely on the user's device.
- If the AI user agent has no local processing capability, it MUST skip the content entirely.

### 8.4 User Override

A user MAY choose to override these declarations for their own data. For example, a user may explicitly instruct an AI agent to "send this to Claude anyway" for content marked `confidential`. In such cases:

- The AI user agent SHOULD warn the user that the content author has declared the content as sensitive.
- The AI user agent SHOULD log the override for audit purposes.
- The AI user agent MUST NOT silently override declarations without user knowledge.

Content authors SHOULD NOT rely on these attributes as a security mechanism. They are declarations of intent, not access controls. Enforcement depends on the AI user agent's compliance.

### 8.5 Handling of Unknown Values

If an AI user agent encounters a value for `data-ai-sensitivity` or `data-ai-consume` that it does not recognise, it MUST treat the element as if the attribute were set to the most restrictive known value (`restricted` for sensitivity, `local-only` for consumption mode). This ensures forward compatibility: new, more restrictive values introduced in future versions will be handled safely by older agents.

---

## 9. Integration with Existing Standards

### 9.1 IETF AIPREF Working Group

The IETF AIPREF Working Group, established in January 2025, is developing HTTP-level signaling for AI preferences. The working group's focus is on:

- HTTP headers for expressing training and inference preferences.
- Site-level declarations for AI crawler behavior.
- Machine-readable policies at the origin level.

**Integration point:** The `X-AI-Sensitivity` and `X-AI-Consume` headers defined in this specification (Section 7.1) are designed to complement AIPREF headers. While AIPREF expresses site-wide or page-wide preferences for AI systems operating at the network level, this specification's headers express content sensitivity that applies to in-session AI user agents.

**Coordination:** This specification's authors intend to coordinate with the AIPREF Working Group to ensure header namespace compatibility and to explore whether the element-level attributes could be referenced from AIPREF's framework.

### 9.2 TDM Reservation Protocol

The W3C TDM Reservation Protocol (TDM-RP) allows rights holders to declare whether their content may be used for text and data mining purposes. TDM-RP operates via:

- `tdm-reservation` property in `/.well-known/tdmrep.json`
- `TDM-Reservation` HTTP header.

**Integration point:** TDM-RP addresses the legal right to mine content; this specification addresses the operational handling of content by AI tools. They are complementary:

- A page may declare `TDM-Reservation: 1` (no mining permitted) AND `data-ai-sensitivity="public"` (content is not sensitive for in-session use).
- A page may declare no TDM reservation (mining permitted) AND `data-ai-sensitivity="restricted"` on specific elements (certain content must not be exposed to AI tools even during legitimate user sessions).

### 9.3 robots.txt AI Directives

Several AI companies have introduced custom robots.txt directives:

- `User-agent: GPTBot` (OpenAI)
- `User-agent: Google-Extended` (Google)
- `User-agent: ClaudeBot` (Anthropic)
- `User-agent: CCBot` (Common Crawl)

**Integration point:** robots.txt controls which pages AI crawlers may access. This specification controls how in-session AI tools handle content on pages the user has navigated to. There is no conflict: robots.txt may block GPTBot from crawling a page, while `data-ai-sensitivity` attributes guide a browser extension that reads the same page during a user session.

### 9.4 C2PA Content Credentials

The Coalition for Content Provenance and Authenticity (C2PA) specification provides a mechanism for attaching provenance metadata to media assets, including who created the content, how it was edited, and whether AI was involved in its creation.

**Integration point:** C2PA credentials establish trust in content origin; this specification declares how content should be handled by AI systems. They compose naturally:

- An image with C2PA credentials declaring it was created by a human photographer could carry `data-ai-sensitivity="confidential"` on its containing element, indicating it should not be processed by AI tools.
- A document with C2PA credentials could include `data-ai-consume="anonymised-ok"` to indicate that AI tools may process it only after anonymisation.

AI user agents that are C2PA-aware SHOULD consider both the C2PA credentials and the `data-ai-*` attributes when making processing decisions.

### 9.5 Content Security Policy (CSP)

While CSP is primarily a security mechanism, future work could define CSP directives that enforce `data-ai-*` attribute compliance at the browser level, preventing non-compliant extensions from accessing elements marked as `restricted`.

---

## 10. Security Considerations

### 10.1 Attributes Are Declarations, Not Enforcement

The `data-ai-*` attributes are advisory. They declare the content author's intent but do not enforce it. A malicious or non-compliant AI user agent can ignore these attributes entirely. Content authors MUST NOT rely on these attributes as a substitute for proper access controls, encryption, or server-side security measures.

### 10.2 Attribute Spoofing

A malicious script running on the page could modify `data-ai-*` attributes to either:

- **Downgrade protection** (change `restricted` to `public`) -- to enable data exfiltration by a colluding AI agent.
- **Upgrade protection** (change `public` to `restricted`) -- to prevent legitimate AI tools from functioning, as a form of denial of service.

Mitigation: Browsers that implement native support for these attributes SHOULD capture the attribute values at parse time and detect subsequent modifications. Changes to `data-ai-*` attributes after initial parse SHOULD trigger a security event.

### 10.3 Extension Trust Model

Browser extensions operate with elevated privileges. An extension that ignores `data-ai-*` attributes is indistinguishable from one that respects them, from the page's perspective. The value of this specification depends on:

- Browser vendors incorporating attribute awareness into extension review policies.
- Extension stores (Chrome Web Store, Firefox Add-ons) requiring compliance.
- User agents exposing compliance status to users.

### 10.4 Side Channels

Even when an AI user agent respects `local-only` processing, side channels may exist:

- The AI agent may transmit telemetry about the existence of sensitive content (e.g., "user viewed a page with 5 restricted elements").
- Timing analysis of AI agent behavior may reveal information about content sensitivity.
- AI user agents MUST NOT transmit metadata about the presence, count, or distribution of `data-ai-*` attributes to external services.

---

## 11. Privacy Considerations

### 11.1 Sensitivity Declarations as Metadata

The `data-ai-*` attributes themselves constitute metadata that may reveal information. A page that marks certain form fields as `restricted` implicitly reveals that those fields contain sensitive data. AI user agents MUST NOT treat the attribute values themselves as a data source for inference.

### 11.2 User Consent and Control

This specification does not alter the user's relationship with their own data. A user who copies content from a `restricted` element and pastes it into an AI chat is exercising their own agency. The attributes guide automated AI tools, not manual user actions.

### 11.3 Regulatory Alignment

The sensitivity levels defined in this specification align with common data classification frameworks:

| This Specification | ISO 27001 | GDPR Concept | NIST SP 800-60 |
|---|---|---|---|
| `public` | Public | N/A | Low |
| `internal` | Internal | Legitimate interest data | Moderate |
| `confidential` | Confidential | Personal data | High |
| `restricted` | Restricted | Special category data | Critical |

This alignment is intentional, enabling organisations to map their existing data classification policies directly to HTML element attributes.

### 11.4 Minimisation Principle

Content authors SHOULD apply the least restrictive classification that accurately reflects the content's sensitivity. Over-classification (marking everything as `restricted`) reduces the utility of the specification and degrades user experience with AI tools.

---

## 12. IANA Considerations

### 12.1 HTTP Header Field Registration

If this specification is published as an IETF RFC, the following HTTP header fields would be registered in the "Hypertext Transfer Protocol (HTTP) Field Name Registry":

**Header Field Name:** AI-Sensitivity
: Status: Provisional
: Specification: This document, Section 7.1

**Header Field Name:** AI-Consume
: Status: Provisional
: Specification: This document, Section 7.1

During the provisional period, the `X-AI-Sensitivity` and `X-AI-Consume` names are used.

### 12.2 Meta Tag Name Registration

The following `<meta>` name values would be registered in the WHATWG Wiki MetaExtensions registry:

- `ai-sensitivity` (Section 7.2)
- `ai-consume` (Section 7.2)

---

## 13. Examples

### 13.1 Healthcare Portal

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta name="ai-sensitivity" content="confidential">
  <meta name="ai-consume" content="local-only">
  <title>Patient Portal - MedCare Health</title>
</head>
<body>
  <header data-ai-sensitivity="public" data-ai-consume="unrestricted">
    <nav><!-- Public navigation --></nav>
  </header>

  <main>
    <section class="patient-info" data-ai-sensitivity="restricted">
      <h2>Patient Information</h2>
      <dl>
        <dt>Name</dt>
        <dd>Jane Doe</dd>
        <dt>Date of Birth</dt>
        <dd>1985-03-15</dd>
        <dt>SSN</dt>
        <dd>***-**-6789</dd>
        <dt>Diagnosis</dt>
        <dd>Type 2 Diabetes Mellitus</dd>
      </dl>
    </section>

    <section class="health-articles" data-ai-sensitivity="public"
             data-ai-consume="unrestricted">
      <h2>Health Resources</h2>
      <article>
        <h3>Managing Diabetes: A Patient Guide</h3>
        <p>General health information accessible to AI tools...</p>
      </article>
    </section>
  </main>
</body>
</html>
```

**Expected behavior:** An AI browser extension reading this page would process the navigation and health articles normally but would skip the patient information section entirely due to the `restricted` classification.

### 13.2 Banking Application

```html
<div class="account-dashboard">
  <div class="account-summary" data-ai-sensitivity="confidential"
       data-ai-consume="local-only">
    <h2>Account Summary</h2>
    <div class="balance" data-ai-sensitivity="restricted">
      <span>Checking: $12,456.78</span>
      <span>Savings: $45,230.00</span>
    </div>
    <div class="recent-transactions">
      <table>
        <tr>
          <td>2026-04-01</td>
          <td>Grocery Store</td>
          <td>-$67.43</td>
        </tr>
      </table>
    </div>
  </div>

  <div class="transfer-form" data-ai-sensitivity="restricted"
       data-ai-consume="local-only">
    <h2>Transfer Funds</h2>
    <label>Account Number
      <input type="text" name="account_number">
    </label>
    <label>Routing Number
      <input type="text" name="routing_number">
    </label>
    <label>Amount
      <input type="number" name="amount">
    </label>
  </div>

  <div class="promotions" data-ai-sensitivity="public"
       data-ai-consume="unrestricted">
    <p>Earn 4.5% APY with our new savings account!</p>
  </div>
</div>
```

### 13.3 Enterprise HR System

```html
<div class="employee-record" data-ai-sensitivity="confidential"
     data-ai-consume="anonymised-ok">
  <h2>Employee Profile</h2>

  <div class="basic-info">
    <span class="name">John Smith</span>
    <span class="department">Engineering</span>
    <span class="title">Senior Developer</span>
  </div>

  <div class="compensation" data-ai-sensitivity="restricted">
    <span class="salary">$185,000</span>
    <span class="bonus">$25,000</span>
    <span class="equity">1,500 RSUs</span>
  </div>

  <div class="performance" data-ai-sensitivity="confidential">
    <h3>Performance Reviews</h3>
    <p>Q1 2026: Exceeds expectations in technical leadership...</p>
  </div>
</div>
```

**Expected behavior:** An AI tool assisting an HR manager could process the basic info and performance review with anonymisation (replacing the name with a placeholder), but must skip the compensation section entirely.

### 13.4 Government Service with Citizen PII

```html
<html data-ai-sensitivity="restricted" data-ai-consume="local-only">
<head>
  <title>Tax Filing - Revenue Service</title>
</head>
<body>
  <header data-ai-sensitivity="public" data-ai-consume="unrestricted">
    <h1>National Revenue Service</h1>
    <nav><!-- Public navigation --></nav>
  </header>

  <main>
    <form id="tax-return" data-ai-sensitivity="restricted">
      <fieldset>
        <legend>Personal Information</legend>
        <label>Social Security Number
          <input type="text" name="ssn"
                 data-ai-sensitivity="restricted">
        </label>
        <label>Full Legal Name
          <input type="text" name="full_name"
                 data-ai-sensitivity="restricted">
        </label>
      </fieldset>

      <fieldset>
        <legend>Income</legend>
        <label>W-2 Wages
          <input type="number" name="wages"
                 data-ai-sensitivity="restricted">
        </label>
      </fieldset>
    </form>

    <aside data-ai-sensitivity="public" data-ai-consume="unrestricted">
      <h2>Filing Help</h2>
      <p>Need help? View our tax filing guide...</p>
    </aside>
  </main>
</body>
</html>
```

### 13.5 Mixed Content Page with Multiple Sensitivity Levels

```html
<article data-ai-sensitivity="public" data-ai-consume="unrestricted">
  <h1>Company Quarterly Report</h1>
  <p>Acme Corp reported strong Q1 results...</p>

  <section class="public-metrics">
    <h2>Published Metrics</h2>
    <p>Revenue: $2.3B (up 15% YoY)</p>
  </section>

  <section class="internal-analysis" data-ai-sensitivity="internal"
           data-ai-consume="anonymised-ok">
    <h2>Internal Analysis</h2>
    <p>Market share in APAC grew to 23%...</p>

    <div class="executive-notes" data-ai-sensitivity="confidential"
         data-ai-consume="local-only">
      <h3>Board Notes</h3>
      <p>Acquisition target: XYZ Corp. Preliminary valuation...</p>
    </div>
  </section>
</article>
```

---

## 14. References

### 14.1 Normative References

**[RFC2119]**
: Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, DOI 10.17487/RFC2119, March 1997, <https://www.rfc-editor.org/info/rfc2119>.

**[RFC8174]**
: Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, DOI 10.17487/RFC8174, May 2017, <https://www.rfc-editor.org/info/rfc8174>.

**[HTML]**
: WHATWG, "HTML Living Standard", <https://html.spec.whatwg.org/multipage/>.

**[HTML-DATA]**
: WHATWG, "HTML Living Standard, Section 3.2.6.6: Embedding custom non-visible data with the data-* attributes", <https://html.spec.whatwg.org/multipage/dom.html#embedding-custom-non-visible-data-with-the-data-*-attributes>.

### 14.2 Informative References

**[AIPREF]**
: IETF AIPREF Working Group, "AI Preferences Signaling", Internet-Draft (work in progress), 2025, <https://datatracker.ietf.org/wg/aipref/about/>.

**[TDM-RP]**
: W3C, "TDM Reservation Protocol", Community Group Report, <https://www.w3.org/community/reports/tdmrep/CG-FINAL-tdmrep-20240510/>.

**[C2PA]**
: Coalition for Content Provenance and Authenticity, "C2PA Specification", <https://c2pa.org/specifications/>.

**[ROBOTS-TXT]**
: Koster, M., Illyes, G., Zeller, H., and L. Sassman, "Robots Exclusion Protocol", RFC 9309, DOI 10.17487/RFC9309, September 2022, <https://www.rfc-editor.org/info/rfc9309>.

**[CSP]**
: W3C, "Content Security Policy Level 3", <https://www.w3.org/TR/CSP3/>.

**[ISO27001]**
: ISO/IEC 27001:2022, "Information security, cybersecurity and privacy protection -- Information security management systems -- Requirements".

**[GDPR]**
: European Parliament and Council, "General Data Protection Regulation (GDPR)", Regulation (EU) 2016/679, April 2016.

**[NIST-SP800-60]**
: National Institute of Standards and Technology, "Guide for Mapping Types of Information and Information Systems to Security Categories", NIST SP 800-60 Vol. 1 Rev. 1, August 2008.

**[UC-DAVIS-2025]**
: UC Davis Department of Computer Science, "Privacy Violations in AI Browser Extensions: An Empirical Study", August 2025.

**[EU-AI-ACT]**
: European Parliament and Council, "Regulation laying down harmonised rules on artificial intelligence (Artificial Intelligence Act)", Regulation (EU) 2024/1689, June 2024.

---

## Appendix A: Reference Implementation

The loke project (<https://github.com/loke/loke>) includes a reference implementation of this specification in its browser mode. The implementation:

1. **DOM Scanner:** On page load and DOM mutation, scans for `data-ai-*` attributes and builds an in-memory sensitivity map.
2. **Inheritance Resolver:** Walks the DOM tree to compute effective sensitivity and consumption mode for any element.
3. **Processing Gate:** Before any AI processing pipeline reads DOM content, the gate checks the element's effective values and enforces the processing rules defined in Section 8.
4. **Override UI:** When a user explicitly requests processing of sensitive content, a confirmation dialog displays the content author's declared sensitivity level.
5. **Audit Logger:** All attribute encounters, processing decisions, and user overrides are logged to a local audit trail.

### A.1 JavaScript API

```javascript
// Resolve effective sensitivity for an element
function getEffectiveSensitivity(element) {
  let current = element;
  while (current && current !== document.documentElement) {
    if (current.dataset && current.dataset.aiSensitivity) {
      return current.dataset.aiSensitivity;
    }
    current = current.parentElement;
  }

  // Check meta tag
  const meta = document.querySelector('meta[name="ai-sensitivity"]');
  if (meta) return meta.content;

  // No declaration found
  return undefined;
}

// Resolve effective consumption mode for an element
function getEffectiveConsume(element) {
  let current = element;
  while (current && current !== document.documentElement) {
    if (current.dataset && current.dataset.aiConsume) {
      return current.dataset.aiConsume;
    }
    current = current.parentElement;
  }

  // Check meta tag
  const meta = document.querySelector('meta[name="ai-consume"]');
  if (meta) return meta.content;

  // No declaration found
  return undefined;
}

// Determine if content may be processed
function mayProcess(element) {
  const sensitivity = getEffectiveSensitivity(element);
  const consume = getEffectiveConsume(element);

  if (sensitivity === 'restricted') return { allowed: false, reason: 'restricted' };
  if (consume === 'local-only') return { allowed: true, mode: 'local-only' };
  if (consume === 'anonymised-ok') return { allowed: true, mode: 'anonymised' };
  if (sensitivity === 'confidential') return { allowed: true, mode: 'local-only' };
  if (sensitivity === 'internal') return { allowed: true, mode: 'consent-required' };

  return { allowed: true, mode: 'unrestricted' };
}
```

---

## Appendix B: Migration Path

### B.1 Immediate Deployment (No Browser Changes Required)

Content authors can add `data-ai-*` attributes today. AI user agents (browser extensions, assistive tools) can detect them via standard DOM APIs. No browser update is needed.

### B.2 Browser-Native Support (Future)

Browser vendors may choose to:

1. Expose a `navigator.aiPrivacy` API for querying effective sensitivity.
2. Block non-compliant extensions from accessing `restricted` elements.
3. Display visual indicators for sensitive content (similar to the padlock icon for HTTPS).
4. Integrate with Content Security Policy for enforcement.

### B.3 Standardisation Path

1. **Phase 1 (Current):** Publish as `data-*` attributes with community adoption.
2. **Phase 2:** Submit to W3C Web Platform Incubator Community Group (WICG) for incubation.
3. **Phase 3:** If sufficient adoption, propose as first-class HTML attributes to WHATWG.
4. **Phase 4:** Register HTTP headers with IANA; coordinate with IETF AIPREF.

---

## Acknowledgements

This specification was developed as part of the loke project's research into local-first AI privacy. The authors acknowledge the work of the IETF AIPREF Working Group, the W3C TDM Reservation Protocol Community Group, and the C2PA coalition, whose foundational work in AI and privacy standards informed this proposal.

---

*End of document.*
