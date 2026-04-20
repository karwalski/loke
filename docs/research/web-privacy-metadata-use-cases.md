# Web Privacy Metadata: Use Cases Document

## Per-Element AI Privacy Declarations in HTML

### Companion to the Web Privacy Metadata Specification

**Date:** 4 April 2026

---

## 1. Introduction

This document presents real-world use cases for the `data-ai-sensitivity` and `data-ai-consume` HTML attributes proposed in the Web Privacy Metadata Specification. Each use case describes a scenario, provides example HTML markup, explains expected AI user agent behavior, and identifies the benefits of adoption.

These use cases are drawn from industries and applications where AI browser extensions, assistive agents, and screen-reading tools are already in active use -- and where the absence of per-element privacy declarations creates measurable risk.

---

## 2. Use Case: Healthcare Portal with Patient Data

### 2.1 Scenario

A hospital patient portal allows patients to view their medical records, upcoming appointments, lab results, and billing information. The portal also contains general health education articles, hospital news, and navigation elements. An AI browser extension offers to "summarise this page" for the user.

Without privacy metadata, the extension reads the entire DOM -- including diagnosis codes, medication lists, and insurance policy numbers -- and transmits all of it to a cloud LLM for summarisation.

### 2.2 Regulatory Context

- HIPAA (United States) -- Protected Health Information (PHI) must not be disclosed to unauthorised parties.
- GDPR Article 9 (EU) -- Health data is a "special category" requiring explicit consent for processing.
- EU AI Act (August 2026) -- AI systems processing health data are classified as high-risk.

### 2.3 Example Markup

```html
<html lang="en">
<head>
  <meta name="ai-sensitivity" content="confidential">
  <meta name="ai-consume" content="local-only">
  <title>MyHealth Portal</title>
</head>
<body>
  <header data-ai-sensitivity="public" data-ai-consume="unrestricted">
    <h1>Regional Medical Center</h1>
    <nav>
      <a href="/appointments">Appointments</a>
      <a href="/records">Records</a>
      <a href="/billing">Billing</a>
    </nav>
  </header>

  <main>
    <section class="patient-demographics" data-ai-sensitivity="restricted">
      <h2>Patient Information</h2>
      <p>Name: <span class="phi">Maria Garcia</span></p>
      <p>DOB: <span class="phi">1978-09-22</span></p>
      <p>MRN: <span class="phi">MRN-00284719</span></p>
      <p>Insurance ID: <span class="phi">BCBS-AX9812456</span></p>
    </section>

    <section class="diagnoses" data-ai-sensitivity="restricted">
      <h2>Active Diagnoses</h2>
      <ul>
        <li>E11.9 - Type 2 Diabetes Mellitus without complications</li>
        <li>I10 - Essential (primary) hypertension</li>
      </ul>
    </section>

    <section class="medications" data-ai-sensitivity="restricted"
             data-ai-consume="local-only">
      <h2>Current Medications</h2>
      <ul>
        <li>Metformin 500mg - twice daily</li>
        <li>Lisinopril 10mg - once daily</li>
      </ul>
    </section>

    <section class="lab-results" data-ai-sensitivity="confidential"
             data-ai-consume="local-only">
      <h2>Recent Lab Results</h2>
      <table>
        <tr><th>Test</th><th>Result</th><th>Reference</th></tr>
        <tr><td>HbA1c</td><td>7.2%</td><td>4.0-5.6%</td></tr>
        <tr><td>Creatinine</td><td>0.9 mg/dL</td><td>0.7-1.3 mg/dL</td></tr>
      </table>
    </section>

    <aside data-ai-sensitivity="public" data-ai-consume="unrestricted">
      <h2>Health Tips</h2>
      <article>
        <h3>Understanding Your HbA1c Results</h3>
        <p>HbA1c measures your average blood sugar over the past 2-3 months.
           A result below 5.7% is considered normal...</p>
      </article>
    </aside>
  </main>
</body>
</html>
```

### 2.4 Expected AI User Agent Behavior

| Page Region | Effective Sensitivity | Effective Consume | AI Agent Action |
|---|---|---|---|
| Header/navigation | `public` | `unrestricted` | Process and transmit normally |
| Patient demographics | `restricted` | `local-only` | Skip entirely -- no processing |
| Diagnoses | `restricted` | `local-only` | Skip entirely -- no processing |
| Medications | `restricted` | `local-only` | Skip entirely -- no processing |
| Lab results | `confidential` | `local-only` | Process locally only, if user has enabled local AI |
| Health tips sidebar | `public` | `unrestricted` | Process and transmit normally |

If the user requests "summarise this page," the AI agent would produce a summary based only on the header, navigation, and health tips sidebar. It would note: "Some sections of this page are marked as restricted and were not included in this summary."

### 2.5 Benefits

- **Compliance:** Prevents inadvertent HIPAA violations by AI browser extensions.
- **Patient trust:** Patients can use AI tools on the portal without risking PHI exposure.
- **Hospital liability:** Demonstrates reasonable technical measures to protect PHI.

---

## 3. Use Case: Banking Application with Account Details

### 3.1 Scenario

An online banking application displays account balances, transaction history, and fund transfer forms. A user has an AI assistant extension that helps them manage finances. The extension should be able to help with general banking questions using the promotional and educational content on the page, but must not exfiltrate account numbers, routing numbers, or exact balances to external servers.

### 3.2 Regulatory Context

- PCI-DSS -- Payment card data must be protected from unauthorised access.
- GLBA (Gramm-Leach-Bliley Act) -- Financial institutions must protect consumer financial data.
- PSD2 (EU) -- Strong customer authentication and data protection for payment services.

### 3.3 Example Markup

```html
<div class="banking-dashboard">
  <section class="account-overview" data-ai-sensitivity="confidential"
           data-ai-consume="local-only">
    <h2>Your Accounts</h2>

    <div class="account-card">
      <h3>Checking Account</h3>
      <p class="account-number" data-ai-sensitivity="restricted">
        Account: ****4521
      </p>
      <p class="balance" data-ai-sensitivity="restricted">
        Balance: $8,432.17
      </p>
      <p class="last-transaction">
        Last activity: 3 April 2026
      </p>
    </div>

    <div class="account-card">
      <h3>Savings Account</h3>
      <p class="account-number" data-ai-sensitivity="restricted">
        Account: ****7893
      </p>
      <p class="balance" data-ai-sensitivity="restricted">
        Balance: $52,100.00
      </p>
    </div>
  </section>

  <section class="transfer-form" data-ai-sensitivity="restricted"
           data-ai-consume="local-only">
    <h2>Transfer Funds</h2>
    <form>
      <label>From Account
        <select name="from_account">
          <option>Checking (****4521)</option>
          <option>Savings (****7893)</option>
        </select>
      </label>
      <label>To Account Number
        <input type="text" name="to_account"
               data-ai-sensitivity="restricted">
      </label>
      <label>Routing Number
        <input type="text" name="routing"
               data-ai-sensitivity="restricted">
      </label>
      <label>Amount
        <input type="number" name="amount">
      </label>
      <button type="submit">Transfer</button>
    </form>
  </section>

  <section class="transaction-history" data-ai-sensitivity="confidential"
           data-ai-consume="anonymised-ok">
    <h2>Recent Transactions</h2>
    <table>
      <thead>
        <tr><th>Date</th><th>Description</th><th>Amount</th></tr>
      </thead>
      <tbody>
        <tr><td>2026-04-03</td><td>Whole Foods Market</td><td>-$87.32</td></tr>
        <tr><td>2026-04-02</td><td>Direct Deposit - Employer</td><td>+$3,200.00</td></tr>
        <tr><td>2026-04-01</td><td>Electric Utility Co</td><td>-$142.50</td></tr>
      </tbody>
    </table>
  </section>

  <section class="financial-tips" data-ai-sensitivity="public"
           data-ai-consume="unrestricted">
    <h2>Smart Money Tips</h2>
    <p>Set up automatic transfers to your savings account to build
       your emergency fund. Financial advisors recommend saving 3-6
       months of living expenses...</p>
  </section>
</div>
```

### 3.4 Expected AI User Agent Behavior

- **Account numbers, balances, transfer form:** Skipped entirely (`restricted`). No data leaves the device.
- **Transaction history:** May be processed with anonymisation. The AI agent could analyse spending patterns after replacing "Whole Foods Market" and specific amounts with placeholders, if the user requests it.
- **Financial tips:** Processed normally. The AI agent can use this content to answer general financial questions.

### 3.5 Benefits

- **PCI-DSS alignment:** Account numbers and routing numbers are never exposed to external AI services.
- **Useful AI:** Users can still get help from AI tools for general financial questions and anonymised spending analysis.
- **Fraud prevention:** Transfer form data cannot be intercepted by compromised extensions.

---

## 4. Use Case: HR System with Employee Records

### 4.1 Scenario

A human resources information system (HRIS) displays employee directories, performance reviews, compensation details, and organisational charts. HR managers use AI tools to draft performance review summaries, analyse team structures, and generate reports. The AI tool should be able to help with structural analysis but must not exfiltrate compensation data or personal identifiers.

### 4.2 Example Markup

```html
<div class="hr-dashboard" data-ai-sensitivity="confidential"
     data-ai-consume="anonymised-ok">

  <section class="org-chart" data-ai-sensitivity="internal"
           data-ai-consume="anonymised-ok">
    <h2>Engineering Department</h2>
    <div class="org-node">
      <span class="name">Sarah Chen</span>
      <span class="title">VP of Engineering</span>
      <span class="direct-reports">Reports: 5</span>
    </div>
    <div class="org-node">
      <span class="name">James Wilson</span>
      <span class="title">Senior Engineering Manager</span>
      <span class="direct-reports">Reports: 12</span>
    </div>
  </section>

  <section class="compensation" data-ai-sensitivity="restricted">
    <h2>Compensation Details</h2>
    <table>
      <tr>
        <td>Sarah Chen</td>
        <td data-ai-sensitivity="restricted">$285,000 base</td>
        <td data-ai-sensitivity="restricted">$75,000 bonus</td>
        <td data-ai-sensitivity="restricted">5,000 RSUs</td>
      </tr>
      <tr>
        <td>James Wilson</td>
        <td data-ai-sensitivity="restricted">$225,000 base</td>
        <td data-ai-sensitivity="restricted">$50,000 bonus</td>
        <td data-ai-sensitivity="restricted">3,000 RSUs</td>
      </tr>
    </table>
  </section>

  <section class="performance-reviews" data-ai-sensitivity="confidential"
           data-ai-consume="anonymised-ok">
    <h2>Performance Reviews - Q1 2026</h2>
    <div class="review">
      <h3>Sarah Chen - VP of Engineering</h3>
      <p class="rating">Overall: Exceeds Expectations</p>
      <p class="feedback">Demonstrated exceptional leadership in
         the platform migration. Successfully hired 8 engineers
         and reduced time-to-deploy by 40%...</p>
    </div>
  </section>

  <section class="personal-info" data-ai-sensitivity="restricted">
    <h2>Personal Information</h2>
    <p>SSN: ***-**-4523</p>
    <p>Home Address: 1234 Oak Street, San Francisco, CA 94102</p>
    <p>Emergency Contact: Michael Chen, 415-555-0198</p>
  </section>
</div>
```

### 4.3 Expected AI User Agent Behavior

An HR manager asks the AI: "Summarise the engineering team structure and performance highlights."

The AI agent:

1. Reads the org chart (`internal`, `anonymised-ok`) -- processes with names replaced by role-based placeholders: "The VP of Engineering has 5 direct reports. A Senior Engineering Manager has 12 direct reports."
2. Skips compensation (`restricted`) entirely.
3. Reads performance reviews (`confidential`, `anonymised-ok`) -- processes with anonymisation: "Employee A received Exceeds Expectations. Key achievements include platform migration leadership and 40% improvement in deployment time."
4. Skips personal information (`restricted`) entirely.

### 4.4 Benefits

- **Pay equity protection:** Compensation data cannot be leaked through AI tools.
- **Useful analysis:** HR managers can still use AI to analyse team structures and performance trends.
- **Employee trust:** Workers can be assured their personal details are not processed by AI.

---

## 5. Use Case: Legal Document Review Platform

### 5.1 Scenario

A law firm uses a document management system to review contracts, litigation documents, and client communications. Junior associates use AI tools to help identify key clauses, summarise documents, and find precedents. The platform must prevent client-identifying information and privileged communications from being transmitted externally while still allowing AI assistance with legal analysis.

### 5.2 Example Markup

```html
<div class="document-viewer" data-ai-sensitivity="confidential"
     data-ai-consume="local-only">

  <header class="document-meta">
    <h1>Contract Review: Technology Licensing Agreement</h1>
    <p class="client-info" data-ai-sensitivity="restricted">
      Client: Acme Corporation (Matter #2026-LIC-0847)
    </p>
    <p class="attorney" data-ai-sensitivity="confidential">
      Assigned: Partner J. Martinez, Associate K. Patel
    </p>
    <p class="document-type" data-ai-sensitivity="internal">
      Type: Technology License, Software-as-a-Service
    </p>
  </header>

  <section class="contract-body">
    <article class="clause" data-ai-sensitivity="confidential"
             data-ai-consume="anonymised-ok">
      <h2>Section 3: License Grant</h2>
      <p>Licensor grants to Licensee a non-exclusive, non-transferable,
         worldwide license to use the Software for the purpose of
         internal business operations...</p>
    </article>

    <article class="clause" data-ai-sensitivity="confidential"
             data-ai-consume="anonymised-ok">
      <h2>Section 7: Limitation of Liability</h2>
      <p>In no event shall either party's aggregate liability exceed
         <span data-ai-sensitivity="restricted">$5,000,000</span>
         (the "Liability Cap")...</p>
    </article>

    <article class="clause privileged" data-ai-sensitivity="restricted">
      <h2>Attorney Notes (Privileged)</h2>
      <p>Client expressed concern about the indemnification scope.
         Recommend narrowing Section 9.2 to exclude third-party
         IP claims. Client's prior litigation (Case No. 2024-CV-1234)
         is relevant -- opposing counsel may raise this...</p>
    </article>
  </section>

  <aside class="legal-research" data-ai-sensitivity="public"
         data-ai-consume="unrestricted">
    <h2>Reference: Standard SaaS License Provisions</h2>
    <p>Common limitation of liability provisions in SaaS agreements
       typically cap liability at 12 months of fees paid...</p>
  </aside>
</div>
```

### 5.3 Expected AI User Agent Behavior

A junior associate asks: "What are the key risk areas in this contract?"

The AI agent:

1. Reads contract clauses (`confidential`, `anonymised-ok`) with anonymisation -- replaces party names with "Party A" and "Party B."
2. Skips the specific liability cap amount (`restricted`).
3. Skips attorney-privileged notes (`restricted`) entirely -- this is attorney-client privilege.
4. Uses the public legal research section for contextual reference.
5. Produces analysis like: "The license grant is non-exclusive and worldwide. The limitation of liability clause references a cap amount [REDACTED]. Standard SaaS agreements typically cap at 12 months of fees."

### 5.4 Benefits

- **Privilege protection:** Attorney-client privileged notes are never exposed to external AI.
- **Deal term confidentiality:** Specific financial terms are protected.
- **Useful assistance:** Associates can still get AI help with legal analysis of non-privileged contract terms.

---

## 6. Use Case: Government Services with Citizen PII

### 6.1 Scenario

A government tax filing portal allows citizens to submit their annual tax returns. The forms collect Social Security Numbers, income figures, bank account details for direct deposit, and dependent information. A UC Davis study documented that the AI browser extension Merlin was exfiltrating SSNs from IRS forms -- this use case directly addresses that documented threat.

### 6.2 Example Markup

```html
<html data-ai-sensitivity="restricted" data-ai-consume="local-only">
<head>
  <meta name="ai-sensitivity" content="restricted">
  <meta name="ai-consume" content="local-only">
  <title>Annual Tax Return Filing</title>
</head>
<body>
  <header data-ai-sensitivity="public" data-ai-consume="unrestricted">
    <h1>National Revenue Service - Tax Filing Portal</h1>
    <nav>
      <a href="/help">Filing Help</a>
      <a href="/deadlines">Deadlines</a>
      <a href="/forms">Forms</a>
    </nav>
  </header>

  <main>
    <form id="tax-return">
      <fieldset data-ai-sensitivity="restricted">
        <legend>Taxpayer Information</legend>
        <label>Social Security Number
          <input type="text" name="ssn" autocomplete="off"
                 data-ai-sensitivity="restricted">
        </label>
        <label>Full Legal Name
          <input type="text" name="legal_name"
                 data-ai-sensitivity="restricted">
        </label>
        <label>Date of Birth
          <input type="date" name="dob"
                 data-ai-sensitivity="restricted">
        </label>
      </fieldset>

      <fieldset data-ai-sensitivity="restricted">
        <legend>Income Information</legend>
        <label>W-2 Wages and Salaries
          <input type="number" name="w2_wages"
                 data-ai-sensitivity="restricted">
        </label>
        <label>1099 Income
          <input type="number" name="1099_income"
                 data-ai-sensitivity="restricted">
        </label>
        <label>Employer Name
          <input type="text" name="employer"
                 data-ai-sensitivity="restricted">
        </label>
        <label>Employer EIN
          <input type="text" name="employer_ein"
                 data-ai-sensitivity="restricted">
        </label>
      </fieldset>

      <fieldset data-ai-sensitivity="restricted">
        <legend>Direct Deposit</legend>
        <label>Bank Routing Number
          <input type="text" name="routing"
                 data-ai-sensitivity="restricted">
        </label>
        <label>Bank Account Number
          <input type="text" name="account"
                 data-ai-sensitivity="restricted">
        </label>
      </fieldset>

      <fieldset data-ai-sensitivity="restricted">
        <legend>Dependents</legend>
        <div class="dependent">
          <label>Dependent Name
            <input type="text" name="dep_name"
                   data-ai-sensitivity="restricted">
          </label>
          <label>Dependent SSN
            <input type="text" name="dep_ssn"
                   data-ai-sensitivity="restricted">
          </label>
        </div>
      </fieldset>
    </form>

    <aside data-ai-sensitivity="public" data-ai-consume="unrestricted">
      <h2>Filing Tips</h2>
      <p>Make sure to have your W-2 forms ready before you begin.
         The filing deadline is April 15, 2026.</p>
      <p>Common deductions include mortgage interest, charitable
         contributions, and state/local taxes...</p>
    </aside>
  </main>
</body>
</html>
```

### 6.3 Expected AI User Agent Behavior

The entire form is marked `restricted`. A compliant AI browser extension:

1. Does not read any form field values.
2. Does not read any form field labels in the context of their values.
3. Does not transmit any content from the form to external services.
4. Does not include any form content in its context window.
5. Can still read and process the public header and filing tips sidebar.
6. If the user asks "help me fill out this form," the agent responds based only on the public filing tips, without accessing any entered data.

### 6.4 Benefits

- **Prevents documented attacks:** Directly addresses the Merlin SSN exfiltration vector documented by UC Davis.
- **Citizen trust:** Citizens can use AI tools on government sites without fear.
- **Government compliance:** Demonstrates technical measures for protecting citizen PII under FISMA and the Privacy Act.

---

## 7. Use Case: E-Commerce with Payment Details

### 7.1 Scenario

An e-commerce platform displays product catalogues, shopping carts, and checkout forms. Product information is public, but the checkout flow contains payment card details, billing addresses, and order history that must be protected. An AI shopping assistant should be able to help compare products and find deals but must not access payment information.

### 7.2 Example Markup

```html
<div class="ecommerce-site">
  <section class="product-catalogue" data-ai-sensitivity="public"
           data-ai-consume="unrestricted">
    <div class="product-card">
      <h2>Wireless Noise-Cancelling Headphones</h2>
      <p class="price">$249.99</p>
      <p class="description">Premium wireless headphones with adaptive
         noise cancellation, 30-hour battery life...</p>
      <div class="reviews">
        <p>4.5 stars (2,341 reviews)</p>
        <blockquote>"Best headphones I've ever owned..."</blockquote>
      </div>
    </div>
  </section>

  <section class="shopping-cart" data-ai-sensitivity="internal"
           data-ai-consume="anonymised-ok">
    <h2>Your Cart (3 items)</h2>
    <div class="cart-item">
      <span>Wireless Headphones</span>
      <span>Qty: 1</span>
      <span>$249.99</span>
    </div>
    <div class="cart-item">
      <span>USB-C Cable</span>
      <span>Qty: 2</span>
      <span>$25.98</span>
    </div>
    <p class="cart-total">Total: $275.97</p>
  </section>

  <section class="checkout" data-ai-sensitivity="restricted"
           data-ai-consume="local-only">
    <h2>Payment Information</h2>
    <form>
      <label>Card Number
        <input type="text" name="card_number"
               data-ai-sensitivity="restricted"
               autocomplete="cc-number">
      </label>
      <label>Expiration Date
        <input type="text" name="card_expiry"
               data-ai-sensitivity="restricted"
               autocomplete="cc-exp">
      </label>
      <label>CVV
        <input type="text" name="card_cvv"
               data-ai-sensitivity="restricted"
               autocomplete="cc-csc">
      </label>
      <label>Billing Address
        <input type="text" name="billing_address"
               data-ai-sensitivity="confidential">
      </label>
    </form>
  </section>

  <section class="order-history" data-ai-sensitivity="confidential"
           data-ai-consume="anonymised-ok">
    <h2>Past Orders</h2>
    <div class="order">
      <p>Order #2026-0312 - March 12, 2026</p>
      <p>Laptop Stand - $89.99</p>
      <p>Shipped to: <span data-ai-sensitivity="restricted">
         123 Main St, Apt 4B, New York, NY 10001</span></p>
    </div>
  </section>
</div>
```

### 7.3 Expected AI User Agent Behavior

A user asks: "Is this a good deal on these headphones?"

The AI agent:

1. Reads the product catalogue (`public`, `unrestricted`) -- compares prices, reads reviews.
2. Reads the cart (`internal`, `anonymised-ok`) -- can reference cart contents if helpful: "You have 3 items totalling $275.97."
3. Skips payment information (`restricted`) entirely.
4. Reads order history (`confidential`, `anonymised-ok`) with anonymisation -- can note purchase patterns without exposing shipping addresses.

### 7.4 Benefits

- **PCI-DSS compliance:** Payment card data is never exposed to AI services.
- **Useful shopping assistance:** AI can still help with product comparison, deal finding, and purchase history analysis.
- **Consumer confidence:** Shoppers can use AI assistants without risking financial data exposure.

---

## 8. Use Case: Social Media with User-Generated Content

### 8.1 Scenario

A social media platform displays public posts, private messages, account settings, and advertising content. The platform wants AI tools to be able to interact with public posts (which users have chosen to publish) but must protect private messages, draft posts, and account security settings.

### 8.2 Example Markup

```html
<div class="social-media-app">
  <section class="public-feed" data-ai-sensitivity="public"
           data-ai-consume="unrestricted">
    <article class="post">
      <header>
        <span class="author">@techwriter</span>
        <time>2 hours ago</time>
      </header>
      <p>Just published my article on web privacy standards.
         Check it out! #WebPrivacy #AIethics</p>
      <div class="engagement">
        <span>42 likes</span>
        <span>7 replies</span>
      </div>
    </article>
  </section>

  <section class="private-messages" data-ai-sensitivity="confidential"
           data-ai-consume="local-only">
    <h2>Direct Messages</h2>
    <div class="conversation">
      <div class="message incoming">
        <span class="sender">@colleague</span>
        <p>Hey, did you see the draft proposal? I think we should
           revise section 3 before the meeting tomorrow.</p>
      </div>
      <div class="message outgoing">
        <p>Agreed. I'll update it tonight. Can you review the
           budget numbers?</p>
      </div>
    </div>
  </section>

  <section class="account-settings" data-ai-sensitivity="restricted"
           data-ai-consume="local-only">
    <h2>Security Settings</h2>
    <div class="two-factor">
      <p>Two-Factor Authentication: Enabled</p>
      <p>Recovery Codes:
        <code data-ai-sensitivity="restricted">A3X9-K2M4-P7R1-W5N8</code>
      </p>
    </div>
    <div class="connected-apps">
      <p>API Key: <code data-ai-sensitivity="restricted">
         sk_live_REDACTED_EXAMPLE_KEY</code></p>
    </div>
  </section>

  <section class="draft-posts" data-ai-sensitivity="internal"
           data-ai-consume="local-only">
    <h2>Your Drafts</h2>
    <article class="draft">
      <p>Working on thoughts about the acquisition.
         Not ready to publish yet...</p>
    </article>
  </section>
</div>
```

### 8.3 Expected AI User Agent Behavior

- **Public feed:** Full AI access -- summarisation, reply suggestions, content analysis.
- **Private messages:** Local-only processing. An on-device AI can help draft a reply, but message content never leaves the device.
- **Account settings:** Completely opaque to AI. Recovery codes and API keys are never processed.
- **Draft posts:** Local-only. AI can help refine drafts on-device but does not transmit unpublished content.

### 8.4 Benefits

- **Content creator control:** Public posts are intentionally public; private content stays private.
- **Security:** Recovery codes and API keys are protected from AI exfiltration.
- **Creative privacy:** Draft posts are not exposed until the user chooses to publish.

---

## 9. Use Case: Enterprise Internal Tools with Classified Information

### 9.1 Scenario

A defence contractor's internal project management tool displays project timelines, resource allocation, and technical specifications. Some projects are classified at different levels. AI tools can help with project management tasks but must respect classification boundaries.

### 9.2 Example Markup

```html
<div class="project-dashboard" data-ai-sensitivity="internal"
     data-ai-consume="local-only">

  <section class="project-overview">
    <h2>Active Projects</h2>

    <div class="project" data-ai-sensitivity="internal">
      <h3>Project Aurora - IT Infrastructure Upgrade</h3>
      <p>Status: On track | Budget: Within allocation</p>
      <p>Timeline: Q1-Q3 2026</p>
      <div class="team">
        <span>Lead: Engineering Team A</span>
        <span>Members: 12</span>
      </div>
    </div>

    <div class="project" data-ai-sensitivity="confidential">
      <h3>Project Meridian - Next-Gen Platform</h3>
      <p>Status: Phase 2 | Budget: [See classified annex]</p>
      <div class="technical-specs" data-ai-sensitivity="restricted">
        <h4>Technical Specifications (CLASSIFIED)</h4>
        <p>Operating frequency: [REDACTED]</p>
        <p>Range: [REDACTED]</p>
        <p>Detection threshold: [REDACTED]</p>
      </div>
      <div class="schedule" data-ai-sensitivity="confidential">
        <h4>Schedule</h4>
        <p>Milestone 1: Complete - Jan 2026</p>
        <p>Milestone 2: In progress - Target May 2026</p>
      </div>
    </div>
  </section>

  <section class="resource-allocation" data-ai-sensitivity="internal"
           data-ai-consume="anonymised-ok">
    <h2>Resource Allocation</h2>
    <table>
      <tr><th>Team</th><th>Headcount</th><th>Utilisation</th></tr>
      <tr><td>Engineering A</td><td>12</td><td>85%</td></tr>
      <tr><td>Engineering B</td><td>8</td><td>92%</td></tr>
      <tr><td>QA</td><td>6</td><td>78%</td></tr>
    </table>
  </section>
</div>
```

### 9.3 Expected AI User Agent Behavior

A project manager asks: "Which teams are over-allocated?"

The AI agent:

1. Reads resource allocation (`internal`, `anonymised-ok`) -- can analyse utilisation: "Engineering B is at 92% utilisation and may need additional resources."
2. Reads Project Aurora details (`internal`) -- can reference timeline and status.
3. Reads Project Meridian schedule (`confidential`) locally only.
4. Skips classified technical specifications (`restricted`) entirely.

### 9.4 Benefits

- **Classification enforcement:** Classified specifications are protected at the DOM level.
- **Useful project management:** Managers can use AI for scheduling and resource analysis on non-classified data.
- **Audit trail:** All AI access patterns are deterministic based on declared sensitivity levels.

---

## 10. Use Case: Educational Platform with Student Data

### 10.1 Scenario

A learning management system (LMS) displays course materials, student grades, assignment submissions, and student profile information. Instructors use AI tools to help grade assignments, generate feedback, and analyse class performance. Students use AI tools to help understand course materials. Student PII and grades must be protected under FERPA.

### 10.2 Example Markup

```html
<div class="lms-dashboard">
  <section class="course-materials" data-ai-sensitivity="public"
           data-ai-consume="unrestricted">
    <h2>CS 301: Data Structures - Course Materials</h2>
    <article class="lecture">
      <h3>Week 10: Binary Search Trees</h3>
      <p>A binary search tree (BST) is a binary tree where each node's
         key is greater than all keys in its left subtree and less than
         all keys in its right subtree...</p>
      <pre><code>
class BSTNode:
    def __init__(self, key):
        self.key = key
        self.left = None
        self.right = None
      </code></pre>
    </article>
  </section>

  <section class="gradebook" data-ai-sensitivity="confidential"
           data-ai-consume="local-only">
    <h2>Gradebook</h2>
    <table>
      <thead>
        <tr>
          <th data-ai-sensitivity="restricted">Student</th>
          <th>Assignment 1</th>
          <th>Assignment 2</th>
          <th>Midterm</th>
        </tr>
      </thead>
      <tbody>
        <tr data-ai-sensitivity="restricted">
          <td>Emily Rodriguez (ID: STU-20240892)</td>
          <td>95</td>
          <td>88</td>
          <td>91</td>
        </tr>
        <tr data-ai-sensitivity="restricted">
          <td>David Kim (ID: STU-20240915)</td>
          <td>82</td>
          <td>79</td>
          <td>85</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section class="submission" data-ai-sensitivity="confidential"
           data-ai-consume="local-only">
    <h2>Assignment Submission Review</h2>
    <div class="student-submission">
      <p class="student-info" data-ai-sensitivity="restricted">
        Student: Emily Rodriguez (STU-20240892)
      </p>
      <div class="code-submission" data-ai-sensitivity="confidential">
        <pre><code>
def insert(self, key):
    if self.root is None:
        self.root = BSTNode(key)
    else:
        self._insert_recursive(self.root, key)
        </code></pre>
      </div>
    </div>
  </section>

  <section class="class-statistics" data-ai-sensitivity="internal"
           data-ai-consume="anonymised-ok">
    <h2>Class Performance Summary</h2>
    <p>Class average: 86.3%</p>
    <p>Median: 88%</p>
    <p>Standard deviation: 7.2</p>
    <p>Students above 90%: 12 of 45 (27%)</p>
  </section>
</div>
```

### 10.3 Expected AI User Agent Behavior

An instructor asks: "How is the class doing overall on BST assignments?"

The AI agent:

1. Reads course materials (`public`) -- understands the topic context.
2. Skips individual student grades (`restricted`) -- cannot access per-student data.
3. Reads class statistics (`internal`, `anonymised-ok`) -- "The class average is 86.3% with a median of 88%. 27% of students scored above 90%."
4. For assignment review, processes code submissions locally only (`confidential`, `local-only`) -- can provide code feedback on-device but does not transmit student work externally.

### 10.4 Benefits

- **FERPA compliance:** Individual student records are protected from external AI transmission.
- **Educational value:** AI can still assist with teaching using public course materials and anonymised class statistics.
- **Academic integrity:** Student submissions are processed locally, preventing external exposure.

---

## 11. Use Case: CRM System with Customer Information

### 11.1 Scenario

A customer relationship management (CRM) system displays customer contact information, deal pipelines, communication history, and account health metrics. Sales representatives use AI tools to draft emails, forecast revenue, and prioritise leads. Customer PII must be protected while allowing AI to assist with sales workflow.

### 11.2 Example Markup

```html
<div class="crm-dashboard">
  <section class="pipeline-overview" data-ai-sensitivity="internal"
           data-ai-consume="anonymised-ok">
    <h2>Q2 2026 Pipeline</h2>
    <div class="pipeline-stage">
      <h3>Qualification (12 deals)</h3>
      <p>Total value: $2.4M</p>
      <p>Average deal size: $200K</p>
      <p>Win probability: 15%</p>
    </div>
    <div class="pipeline-stage">
      <h3>Negotiation (5 deals)</h3>
      <p>Total value: $1.8M</p>
      <p>Average deal size: $360K</p>
      <p>Win probability: 65%</p>
    </div>
  </section>

  <section class="customer-detail" data-ai-sensitivity="confidential"
           data-ai-consume="anonymised-ok">
    <h2>Customer Record</h2>

    <div class="contact-info" data-ai-sensitivity="restricted">
      <h3>Contact Information</h3>
      <p>Name: Lisa Thompson</p>
      <p>Email: l.thompson@megacorp.com</p>
      <p>Phone: +1 (415) 555-0142</p>
      <p>Company: MegaCorp Industries</p>
    </div>

    <div class="deal-details" data-ai-sensitivity="confidential">
      <h3>Deal: Enterprise Platform License</h3>
      <p>Stage: Negotiation</p>
      <p>Value: $450,000 ARR</p>
      <p>Close date: May 2026</p>
      <p>Decision maker: CTO</p>
      <p>Competitors: Vendor A, Vendor B</p>
    </div>

    <div class="communication-history" data-ai-sensitivity="confidential"
         data-ai-consume="local-only">
      <h3>Recent Communications</h3>
      <div class="email">
        <p class="subject">Re: Pricing Discussion</p>
        <p class="body">Hi Lisa, following up on our call yesterday.
           We can offer a 15% discount on the 3-year commitment...</p>
      </div>
      <div class="note">
        <p class="author">Sales Rep: Mark Johnson</p>
        <p class="content">Lisa mentioned they're under pressure
           from their board to reduce SaaS spend by 20%.
           Key concern is integration with their SAP instance.</p>
      </div>
    </div>
  </section>

  <section class="account-health" data-ai-sensitivity="internal"
           data-ai-consume="anonymised-ok">
    <h2>Account Health Metrics</h2>
    <p>NPS Score: 72</p>
    <p>Product usage: 89% of licensed seats active</p>
    <p>Support tickets (last 90 days): 3 (all resolved)</p>
    <p>Renewal risk: Low</p>
  </section>

  <section class="sales-playbook" data-ai-sensitivity="public"
           data-ai-consume="unrestricted">
    <h2>Sales Playbook: Enterprise Deals</h2>
    <p>For deals over $200K ARR, engage the solutions engineering
       team by Stage 3. Key differentiators to emphasise:
       integration ecosystem, uptime SLA, dedicated CSM...</p>
  </section>
</div>
```

### 11.3 Expected AI User Agent Behavior

A sales rep asks: "Help me prepare for my next call with this customer."

The AI agent:

1. Reads the sales playbook (`public`) -- provides standard guidance for enterprise deals.
2. Reads pipeline overview (`internal`, `anonymised-ok`) -- understands deal context without specific customer names.
3. Reads deal details (`confidential`, `anonymised-ok`) -- can reference deal stage, competitors, and decision maker with anonymisation: "The deal is in negotiation stage with a CTO decision maker. Competitors include two vendors."
4. Reads communications locally (`confidential`, `local-only`) -- on-device processing can prepare call notes: "Key concern is SaaS cost reduction and SAP integration."
5. Skips contact PII (`restricted`) -- does not process name, email, or phone.
6. Reads account health (`internal`, `anonymised-ok`) -- "Account health is strong with high NPS and product adoption."

### 11.4 Benefits

- **Customer data protection:** Contact PII is never transmitted to external AI services.
- **Sales effectiveness:** AI can still help with deal strategy, call preparation, and pipeline analysis.
- **Competitive intelligence protection:** Sensitive deal details stay local or are anonymised.

---

## 12. Summary: Attribute Usage Patterns by Industry

| Industry | Typical Page Default | Restricted Elements | Public Elements | Primary Consume Mode |
|---|---|---|---|---|
| Healthcare | `confidential` | Patient demographics, diagnoses, medications | Health education, navigation | `local-only` |
| Banking | `confidential` | Account numbers, card details, routing numbers | Product promotions, financial tips | `local-only` |
| Human Resources | `confidential` | Compensation, SSNs, home addresses | Job postings, company policies | `anonymised-ok` |
| Legal | `confidential` | Privileged communications, deal terms | Legal research, public filings | `local-only` |
| Government | `restricted` | SSNs, tax data, citizen PII | Filing instructions, public info | `local-only` |
| E-Commerce | `public` | Payment card details, billing addresses | Product catalogues, reviews | `unrestricted` |
| Social Media | `public` | DMs, security settings, API keys | Public posts, profiles | `unrestricted` |
| Defence/Classified | `internal` | Classified specs, security clearances | Unclassified project info | `local-only` |
| Education | `public` | Student grades, PII, submissions | Course materials, syllabi | `local-only` |
| CRM | `internal` | Customer contact info, deal pricing | Sales playbooks, public metrics | `anonymised-ok` |

---

## 13. Implementation Recommendations for Content Authors

### 13.1 Start with Page-Level Defaults

Set the most common sensitivity level as the page default using a `<meta>` tag, then override specific sections:

```html
<head>
  <meta name="ai-sensitivity" content="confidential">
  <meta name="ai-consume" content="local-only">
</head>
<body>
  <!-- Most content inherits confidential/local-only -->
  <header data-ai-sensitivity="public" data-ai-consume="unrestricted">
    <!-- Navigation is explicitly public -->
  </header>
  <main>
    <!-- Inherits confidential/local-only -->
    <aside data-ai-sensitivity="public" data-ai-consume="unrestricted">
      <!-- Help content is public -->
    </aside>
  </main>
</body>
```

### 13.2 Mark Sensitive Form Fields Individually

Even within a `restricted` form, mark individual inputs for defence in depth:

```html
<form data-ai-sensitivity="restricted">
  <input name="ssn" data-ai-sensitivity="restricted">
  <input name="name" data-ai-sensitivity="restricted">
</form>
```

### 13.3 Use `anonymised-ok` for Analytical Use Cases

When data is valuable for AI analysis but contains PII, use `anonymised-ok` to enable AI assistance while requiring PII removal:

```html
<section data-ai-sensitivity="confidential"
         data-ai-consume="anonymised-ok">
  <!-- AI can process this with anonymisation -->
</section>
```

### 13.4 Test with the loke Reference Implementation

The loke project provides a reference implementation that content authors can use to verify their attribute declarations produce the expected AI agent behavior. See the Web Privacy Metadata Specification, Appendix A for details.

---

## 14. Conclusion

These use cases demonstrate that per-element AI privacy metadata addresses real, documented risks across every major industry vertical. The `data-ai-sensitivity` and `data-ai-consume` attributes provide a simple, standards-compatible mechanism for content authors to declare their privacy intent at the granularity that matters -- individual DOM elements containing sensitive data.

The absence of such a mechanism has already resulted in documented privacy violations (UC Davis/Merlin study). The regulatory landscape (GDPR, HIPAA, EU AI Act, FERPA, PCI-DSS) increasingly demands that organisations demonstrate technical measures for protecting sensitive data from AI systems. These attributes provide exactly that: a declarative, auditable, machine-readable signal that content authors control and AI user agents can respect.

---

*End of document.*
