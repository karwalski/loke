# Regulatory Defaults — Specification

**Story:** A3.2 — Regional regulatory defaults
**Status:** Draft
**Last updated:** 2026-04-04

---

## Purpose

loke intercepts, anonymises, and routes LLM traffic on behalf of users. Different jurisdictions impose different requirements on how personal data may be processed, stored, and transferred. This document specifies the seven regulatory presets that ship with loke, the two emerging AI-specific regulations that affect loke's behaviour, and the conflict resolution strategy when multiple regulations apply simultaneously.

Each preset is a **starting point**. Users and enterprise administrators can override any individual setting. The default preset is **EU GDPR**, chosen because it is the most restrictive general-purpose baseline and provides the safest out-of-box experience.

---

## Table of Contents

1. [Preset Summary Matrix](#1-preset-summary-matrix)
2. [EU GDPR](#2-eu-gdpr)
3. [Australian Privacy Act](#3-australian-privacy-act)
4. [US HIPAA](#4-us-hipaa)
5. [US CCPA/CPRA](#5-us-ccpacpra)
6. [UK GDPR](#6-uk-gdpr)
7. [Singapore PDPA](#7-singapore-pdpa)
8. [Minimal Preset](#8-minimal-preset)
9. [EU AI Act](#9-eu-ai-act)
10. [Colorado AI Act](#10-colorado-ai-act)
11. [Cross-Regulation Conflicts and Resolution](#11-cross-regulation-conflicts-and-resolution)
12. [loke Configuration Schema Reference](#12-loke-configuration-schema-reference)

---

## 1. Preset Summary Matrix

| Setting | EU GDPR | AU Privacy Act | US HIPAA | US CCPA/CPRA | UK GDPR | SG PDPA | Minimal |
|---------|---------|----------------|----------|--------------|---------|---------|---------|
| **PII scope** | Broad (any identifier) | Broad (any identifier) | PHI + identifiers | PI + household data | Broad (any identifier) | Broad (any identifier) | Email + phone only |
| **Anonymisation strength** | Full anonymisation or pseudonymisation with safeguards | Reasonable de-identification | Safe Harbor or Expert Determination | Reasonable de-identification | Full anonymisation or pseudonymisation with safeguards | Reasonable anonymisation | Placeholder only |
| **Default retention** | Minimisation (shortest necessary) | Reasonable for purpose | 6 years post-relationship | As long as disclosed | Minimisation (shortest necessary) | Reasonable for purpose | No limit |
| **Cross-border transfers** | Adequacy decision or SCCs required | APP 8 — comparable protections | BAA required, no export ban per se | No explicit restriction | Adequacy or UK IDTA required | Transfer limitation obligation | No restriction |
| **Provider restrictions** | DPA required; no prohibited-jurisdiction providers | None specified beyond APP 8 | BAA mandatory | Service provider contract required | DPA required | Data intermediary obligations | None |
| **Audit log retention** | 5 years recommended | 7 years (tax/corporate) | 6 years minimum | 24 months minimum | 5 years recommended | 5 years recommended | Disabled |
| **Breach notification** | 72 hours to DPA | 30 days to OAIC (eligible breaches) | 60 days to individuals | 45 days to consumers (on request) | 72 hours to ICO | 3 days to PDPC (notifiable) | None |

---

## 2. EU GDPR

### 2.1 Overview

The **General Data Protection Regulation** (Regulation (EU) 2016/679) has applied since 25 May 2018. It governs the processing of personal data of individuals in the European Economic Area (EEA). It applies to any organisation that processes personal data of EEA residents, regardless of where the organisation is established (Article 3 — extraterritorial scope).

GDPR is enforced by national Data Protection Authorities (DPAs). Maximum fines are EUR 20 million or 4% of annual global turnover, whichever is higher.

### 2.2 Key Requirements Relevant to loke

- **Lawful basis for processing** (Art. 6): loke's processing of user data locally relies on legitimate interest or contract performance. Sending data to cloud LLMs requires a lawful basis — loke's anonymisation pipeline is designed to remove the need for one by ensuring no personal data leaves the device.
- **Data minimisation** (Art. 5(1)(c)): Only data adequate, relevant, and limited to what is necessary may be processed. loke's token optimisation pipeline directly serves this principle.
- **Purpose limitation** (Art. 5(1)(b)): Data collected for one purpose must not be repurposed. loke must not use PII mappings or audit data for any purpose beyond the original interaction.
- **Storage limitation** (Art. 5(1)(e)): Personal data must not be kept longer than necessary. PII mapping tables must be purged after the interaction lifecycle completes.
- **Data Protection by Design and Default** (Art. 25): Privacy-protective settings must be the default. This is loke's core philosophy.
- **Right to erasure** (Art. 17): Data subjects can require deletion of their personal data. loke must support purging all stored PII mappings, audit entries referencing a specific data subject, and cached responses containing personal data.
- **Data Protection Impact Assessment** (Art. 35): Required for high-risk processing. Enterprises deploying loke in high-risk contexts (health data, systematic monitoring) must conduct a DPIA.

### 2.3 PII Entity Types

GDPR defines personal data broadly (Art. 4(1)): "any information relating to an identified or identifiable natural person." This includes data that can identify a person directly or indirectly, including by combination with other data.

**Entities loke must detect under EU GDPR preset:**

| Category | Specific types | Detection layer |
|----------|---------------|-----------------|
| **Direct identifiers** | Full name, email address, phone number, national ID (all EU member states), passport number, social security / tax ID | Regex + NLP NER |
| **Location data** | Street address, postcode, GPS coordinates, IP address (confirmed as personal data by CJEU C-582/14) | Regex + NLP NER |
| **Financial** | Bank account (IBAN), credit/debit card number, financial transaction references | Regex |
| **Online identifiers** | IP address (v4 and v6), cookie IDs, device fingerprints, advertising IDs, MAC addresses | Regex |
| **Biometric data** | Facial images, fingerprint hashes, voice prints (Art. 9 special category) | SLM NER |
| **Health data** | Medical conditions, prescriptions, diagnosis codes, health insurance IDs (Art. 9 special category) | SLM NER + Presidio |
| **Genetic data** | DNA sequences, genetic test results (Art. 9 special category) | SLM NER |
| **Racial/ethnic origin** | Ethnicity references, nationality indicators in context (Art. 9 special category) | SLM NER |
| **Political opinions** | Party membership, political statements in context (Art. 9 special category) | SLM NER |
| **Religious/philosophical beliefs** | Religious affiliation, belief statements (Art. 9 special category) | SLM NER |
| **Trade union membership** | Union membership references (Art. 9 special category) | SLM NER |
| **Sexual orientation** | Sexual orientation or sex life references (Art. 9 special category) | SLM NER |
| **Criminal data** | Offences, convictions, criminal proceedings (Art. 10) | SLM NER |
| **Pseudonymous identifiers** | Employee IDs, customer numbers, case reference numbers (identifiable with additional data) | Configurable — off by default, enterprise can enable |

### 2.4 Anonymisation Requirements

GDPR distinguishes between **anonymisation** (irreversible, data is no longer personal data) and **pseudonymisation** (reversible with additional information, data remains personal data — Art. 4(5)).

**loke EU GDPR preset behaviour:**

- **Outbound data to cloud LLMs:** Full anonymisation by default. Placeholder tokens ($c1, $l2) must not be reversible by the LLM provider. The mapping table is stored locally and never transmitted.
- **Local processing:** Pseudonymisation is acceptable because the data never leaves the device and the mapping is under the user's control.
- **Reversibility:** The local mapping table enables response restoration. This is acceptable because the mapping never leaves the device. Under GDPR, pseudonymised data on a single device under user control carries minimal risk.
- **Special category data (Art. 9):** Must be fully anonymised before any cloud transmission. No pseudonymised special category data may be sent externally, even with safeguards. loke must block or fully redact (replace with generic tokens, not consistent placeholders) special category data when the EU GDPR preset is active.
- **Recital 26 threshold:** Anonymisation must render re-identification "reasonably unlikely" considering "all the means reasonably likely to be used." Consistent placeholder tokens across a conversation are acceptable provided the conversation context alone does not enable re-identification.

### 2.5 Data Retention

- **PII mapping tables:** Retained only for the duration of the active conversation or session. Purged within 24 hours of session close unless the user explicitly extends retention for continued work.
- **Audit logs:** Retain for 5 years (aligned with typical DPA enforcement limitation periods). Audit logs must not contain PII — they record metadata only (timestamp, action type, entity count, provider, token count).
- **Semantic cache:** Cached responses containing any PII residue must be purged within 30 days. Cache entries created from fully anonymised prompts may be retained indefinitely.
- **Right to erasure:** loke must support targeted deletion of all data associated with a specific data subject within 30 days of request, including: PII mappings, any cached responses derived from their data, audit log entries that reference their data (replaced with tombstone records to maintain chain integrity).

### 2.6 Cross-Border Transfers

GDPR Chapter V (Arts. 44-49) restricts transfers of personal data outside the EEA.

**loke EU GDPR preset behaviour:**

- **Provider allow-list by jurisdiction:** Only providers in countries with an EU adequacy decision are permitted by default. As of April 2026, adequacy decisions cover: Andorra, Argentina, Canada (PIPEDA), Faroe Islands, Guernsey, Israel, Isle of Man, Japan, Jersey, New Zealand, Republic of Korea, Switzerland, United Kingdom, United States (EU-US Data Privacy Framework participants), and Uruguay.
- **US providers:** Permitted only if the provider is listed on the EU-US Data Privacy Framework (DPF) participant list. OpenAI, Anthropic, and Google are DPF-certified. loke maintains a provider metadata registry that includes DPF status.
- **Non-adequate jurisdictions:** Blocked by default. Enterprise administrators can override with documentation of Standard Contractual Clauses (SCCs) or Binding Corporate Rules (BCRs).
- **Practical implication for loke:** Because loke anonymises data before transmission, and truly anonymised data is outside GDPR scope (Recital 26), the cross-border restriction applies only if anonymisation is incomplete or disabled. The preset enforces maximum anonymisation to make this moot.

### 2.7 Provider Restrictions

- **Data Processing Agreement (DPA):** Any LLM provider receiving data (even anonymised, as a precaution) should have a DPA in place. loke's provider registry tracks DPA status.
- **Sub-processor transparency:** GDPR requires that processors disclose sub-processors. loke's provider metadata should include known sub-processor chains.
- **Local models:** No restrictions. Data processed entirely on-device does not trigger GDPR processor obligations.
- **Companion devices:** Must be on the same network or connected via encrypted tunnel. No GDPR transfer issue if the companion is under the same data controller's physical control.

### 2.8 Audit Requirements

- **Art. 30 — Records of processing activities:** Enterprises must maintain records. loke's audit trail serves this requirement by logging: what data categories were processed, which provider received data, what anonymisation was applied, timestamps.
- **Art. 5(2) — Accountability:** The controller must demonstrate compliance. loke's audit export (PDF/CSV/JSON per story A3.4) enables this.
- **Log retention:** 5 years recommended, aligned with typical limitation periods for DPA enforcement actions.
- **Log contents:** Timestamp, interaction ID, PII entity types detected (not values), anonymisation method applied, provider name and jurisdiction, token counts (input/output), routing decision rationale, user overrides and confirmations.

### 2.9 Breach Notification

- **Art. 33:** Controller must notify the supervisory authority within **72 hours** of becoming aware of a personal data breach, unless the breach is unlikely to result in a risk to rights and freedoms.
- **Art. 34:** Data subjects must be notified without undue delay if the breach is likely to result in a **high risk** to their rights and freedoms.
- **loke relevance:** A breach in loke's context would be: PII transmitted to an LLM provider without anonymisation due to a pipeline failure, PII mapping table exfiltrated, audit logs containing PII leaked.
- **loke safeguards:** The privacy pipeline includes a final validation step (outbound content scan) that blocks transmission if PII is detected after anonymisation. Pipeline failures trigger a local alert and block transmission rather than failing open.

### 2.10 loke Configuration Mapping

```yaml
preset: eu-gdpr

privacy:
  pii_detection:
    layers: [regex, nlp, slm, presidio]  # All four layers active
    entity_types:
      - name
      - email
      - phone
      - national_id
      - passport
      - tax_id
      - address
      - postcode
      - gps_coordinates
      - ip_address
      - iban
      - credit_card
      - cookie_id
      - device_fingerprint
      - mac_address
      - biometric
      - health_data
      - genetic_data
      - racial_ethnic_origin
      - political_opinion
      - religious_belief
      - trade_union
      - sexual_orientation
      - criminal_data
    special_category_handling: block_or_full_redact  # No pseudonymisation for Art. 9 data
  anonymisation:
    strength: full              # Full anonymisation for outbound, pseudonymisation local-only
    reversible: true            # Local mapping retained for response restoration
    placeholder_format: "$t{n}" # e.g., $c1, $l2, $p3
    special_category_mode: irreversible_redact  # Generic tokens, not consistent placeholders

data_retention:
  pii_mappings: 24h             # Purged 24h after session close
  audit_logs: 5y                # 5 years
  semantic_cache: 30d           # PII-containing cache entries
  semantic_cache_clean: unlimited  # Fully anonymised cache entries
  right_to_erasure: enabled

cross_border:
  mode: adequacy_required       # Only adequate jurisdictions or DPF
  adequacy_list: eu_adequacy_2026
  dpf_required_for_us: true
  override_requires: scc_documentation

providers:
  dpa_required: true
  local_models: unrestricted
  companion_devices: encrypted_tunnel_required
  blocked_jurisdictions: []     # Populated by adequacy list inversion

audit:
  enabled: true
  log_pii_values: false         # Never log actual PII
  log_retention: 5y
  export_formats: [pdf, csv, json]
  hash_chain: true              # Tamper detection
  siem_forwarding: optional

breach:
  pipeline_failure_action: block_and_alert  # Never fail open
  outbound_validation: enabled   # Final PII scan before transmission
  notification_window: 72h       # For enterprise alerting integration
```

---

## 3. Australian Privacy Act

### 3.1 Overview

The **Privacy Act 1988** (Cth), together with the **Australian Privacy Principles (APPs)**, governs the handling of personal information by Australian Government agencies and private sector organisations with annual turnover above AUD 3 million (with exceptions for health service providers, certain small businesses handling personal information, and those trading in personal information).

The **Privacy and Other Legislation Amendment (Tranche 1) Act 2024**, which received Royal Assent in November 2024, introduced significant changes effective in stages through 2025-2026:

- A statutory tort for serious invasion of privacy (effective mid-2025)
- A Children's Online Privacy Code (development commenced 2025, expected enforcement 2026)
- Enhanced enforcement powers for the Office of the Australian Information Commissioner (OAIC)
- Criminalisation of doxxing (malicious release of personal data)
- Expanded definition of "personal information" to explicitly include inferred and technical data

The Privacy Act is enforced by the OAIC. Maximum penalties for serious or repeated interferences with privacy are AUD 50 million, three times the benefit obtained, or 30% of adjusted turnover, whichever is greatest (post-2022 amendments).

### 3.2 Key Requirements Relevant to loke

- **APP 3 — Collection:** Personal information must only be collected by lawful and fair means, and only when reasonably necessary for the entity's functions. loke should not collect or retain personal information beyond what is needed for the immediate processing task.
- **APP 6 — Use and disclosure:** Personal information must not be used or disclosed for a secondary purpose unless the individual consents or an exception applies. Sending user data to an LLM provider is a disclosure — anonymisation avoids this.
- **APP 8 — Cross-border disclosure:** Before disclosing personal information to an overseas recipient, the entity must take reasonable steps to ensure the recipient complies with the APPs (or a substantially similar regime). The disclosing entity remains liable for the overseas recipient's actions.
- **APP 11 — Security:** Entities must take reasonable steps to protect personal information from misuse, interference, loss, and unauthorised access or disclosure. loke's encryption and local-first architecture directly serve this.
- **APP 12 — Access:** Individuals have the right to access their personal information. loke's audit trail supports this.
- **APP 13 — Correction:** Individuals can request correction of inaccurate personal information.
- **2024 amendments — Inferred data:** The expanded definition of "personal information" now explicitly covers data inferred or generated about an individual. This is relevant because LLM outputs may contain inferences about users.

### 3.3 PII Entity Types

The Privacy Act defines "personal information" as information or an opinion about an identified individual, or an individual who is reasonably identifiable, whether or not the information is true and whether recorded in a material form or not. Post-2024 amendments, this explicitly includes technical and inferred data.

**Entities loke must detect under AU Privacy Act preset:**

| Category | Specific types | Detection layer |
|----------|---------------|-----------------|
| **Direct identifiers** | Full name, email, phone, date of birth | Regex + NLP NER |
| **Government identifiers** | Tax File Number (TFN), Australian Business Number (ABN), Medicare number, driver's licence number, passport number, Centrelink CRN | Regex |
| **Location data** | Street address, postcode, state, GPS coordinates | Regex + NLP NER |
| **Financial** | Bank account (BSB + account number), credit card, superannuation fund member number | Regex |
| **Online identifiers** | IP address, device identifiers | Regex |
| **Health information** | Health conditions, Medicare claims, prescriptions, mental health records (treated as "sensitive information" under s 6) | SLM NER + Presidio |
| **Biometric data** | Facial images, fingerprints, voice prints (sensitive information) | SLM NER |
| **Racial/ethnic origin** | Ethnicity references (sensitive information) | SLM NER |
| **Political opinions** | Party affiliation (sensitive information) | SLM NER |
| **Religious beliefs** | Religious affiliation (sensitive information) | SLM NER |
| **Sexual orientation** | Sexual orientation references (sensitive information) | SLM NER |
| **Criminal record** | Criminal history (sensitive information) | SLM NER |
| **Trade union membership** | Union membership (sensitive information) | SLM NER |
| **Inferred information** | LLM-generated inferences about individuals (post-2024 amendments) | SLM NER (outbound response scanning) |

### 3.4 Anonymisation Requirements

The Privacy Act does not prescribe specific anonymisation techniques. De-identification (defined in s 6(1) as removing personal identifiers and taking reasonable steps to prevent re-identification) removes data from the Act's scope.

**loke AU Privacy Act preset behaviour:**

- **Outbound data:** De-identification via placeholder replacement. The standard is "reasonable steps in the circumstances" — loke's four-layer pipeline exceeds this.
- **Sensitive information:** Stronger protections apply. The preset applies the same irreversible redaction as EU GDPR for health, biometric, racial, political, religious, sexual orientation, criminal, and trade union data.
- **Re-identification prohibition:** The Privacy Act 2024 amendments reinforce that re-identification of de-identified data is prohibited. loke's mapping tables must be secured accordingly.

### 3.5 Data Retention

- **APP 11.2:** Entities must destroy or de-identify personal information when it is no longer needed for any purpose for which it may be used or disclosed under the APPs.
- **PII mapping tables:** Retained for 48 hours after session close (slightly longer than EU GDPR, reflecting the "reasonable" standard rather than strict minimisation).
- **Audit logs:** 7 years (aligned with Australian corporate and tax record-keeping requirements under the Corporations Act 2001 and Tax Administration Act 1953).
- **No explicit right to erasure:** The Privacy Act does not include a GDPR-style right to erasure. However, APP 13 (correction) and APP 11.2 (destruction when no longer needed) together require deletion of unnecessary data. loke supports deletion requests as best practice.

### 3.6 Cross-Border Transfers

**APP 8** requires that before disclosing personal information to an overseas recipient, the entity must take reasonable steps to ensure the overseas recipient does not breach the APPs. The disclosing entity is **accountable for the overseas recipient's handling** (s 16C).

**loke AU Privacy Act preset behaviour:**

- **No adequacy list:** Australia does not maintain an equivalence or adequacy list. The obligation is on the disclosing entity to satisfy itself about the recipient's practices.
- **Default:** All cloud LLM providers are permitted, but loke logs a compliance notice that the user/enterprise is responsible for assessing the provider's privacy practices.
- **Enterprise override:** Enterprise administrators can restrict providers by jurisdiction or require specific contractual terms.
- **Practical implication:** Because loke anonymises before transmission, APP 8 obligations are largely mitigated — de-identified data is outside the Act's scope.

### 3.7 Provider Restrictions

- No formal equivalent to GDPR's DPA requirement.
- APP 8 accountability means the user/enterprise should assess provider practices.
- loke's provider registry includes a field for "APP 8 assessment completed" — a boolean enterprise administrators can set.
- Government agencies have additional requirements under the Hosting Certification Framework (HCF) — providers handling government data must be certified.

### 3.8 Audit Requirements

- **APP 1 — Open and transparent management:** Entities must take reasonable steps to implement practices, procedures, and systems to ensure compliance. Audit trails demonstrate this.
- **Log retention:** 7 years, aligned with the Corporations Act 2001 general record-keeping requirements.
- **Contents:** Same metadata as EU GDPR preset (no PII values in logs).

### 3.9 Breach Notification

The **Notifiable Data Breaches (NDB) scheme** (Part IIIC, effective February 2018) requires notification of "eligible data breaches."

- **Eligible breach:** Unauthorised access to, or disclosure of, personal information that is likely to result in serious harm to any individual.
- **Timeline:** Must notify the OAIC and affected individuals **as soon as practicable** and in any event within **30 calendar days** of becoming aware of reasonable grounds to believe an eligible breach has occurred.
- **Assessment period:** 30 days to assess whether a suspected breach is an eligible breach.
- **loke relevance:** Same as GDPR — PII leaking past the anonymisation pipeline to an LLM provider would constitute an eligible breach if serious harm is likely.

### 3.10 loke Configuration Mapping

```yaml
preset: au-privacy-act

privacy:
  pii_detection:
    layers: [regex, nlp, slm, presidio]
    entity_types:
      - name
      - email
      - phone
      - date_of_birth
      - tfn                       # Tax File Number
      - abn                       # Australian Business Number
      - medicare_number
      - drivers_licence
      - passport
      - centrelink_crn
      - address
      - postcode
      - gps_coordinates
      - ip_address
      - bank_account_au           # BSB + account number
      - credit_card
      - superannuation_member_id
      - health_data
      - biometric
      - racial_ethnic_origin
      - political_opinion
      - religious_belief
      - sexual_orientation
      - criminal_record
      - trade_union
      - inferred_personal_info    # Post-2024 amendment coverage
    sensitive_info_handling: block_or_full_redact
  anonymisation:
    strength: de_identification   # "Reasonable steps" standard
    reversible: true
    placeholder_format: "$t{n}"
    sensitive_info_mode: irreversible_redact

data_retention:
  pii_mappings: 48h
  audit_logs: 7y
  semantic_cache: 30d
  semantic_cache_clean: unlimited
  right_to_erasure: best_practice   # Not statutory, but supported

cross_border:
  mode: all_permitted_with_notice   # No adequacy list; entity accountability
  app8_assessment_required: true    # Enterprise must confirm assessment
  override_requires: enterprise_approval

providers:
  dpa_required: false               # No formal DPA requirement
  app8_assessment_field: true       # Track per-provider assessment status
  local_models: unrestricted
  companion_devices: encrypted_tunnel_required

audit:
  enabled: true
  log_pii_values: false
  log_retention: 7y
  export_formats: [pdf, csv, json]
  hash_chain: true
  siem_forwarding: optional

breach:
  pipeline_failure_action: block_and_alert
  outbound_validation: enabled
  notification_window: 30d          # NDB scheme timeline
  assessment_period: 30d
```

---

## 4. US HIPAA

### 4.1 Overview

The **Health Insurance Portability and Accountability Act of 1996** (HIPAA), together with the **HIPAA Privacy Rule** (45 CFR Part 160 and Subparts A and E of Part 164) and the **HIPAA Security Rule** (45 CFR Part 160 and Subparts A and C of Part 164), governs the use and disclosure of **Protected Health Information (PHI)** by covered entities and their business associates.

Covered entities are: health plans, health care clearinghouses, and health care providers who transmit health information electronically. Business associates are entities that perform functions involving PHI on behalf of covered entities.

HIPAA is enforced by the US Department of Health and Human Services (HHS) Office for Civil Rights (OCR). Penalties range from USD 100 to USD 50,000 per violation, with annual maximums of USD 1.5 million per violation category. Criminal penalties can reach USD 250,000 and 10 years imprisonment.

**Critical note:** HIPAA applies when loke is used by or on behalf of a covered entity or business associate to process data that includes PHI. If loke processes PHI, the entity operating loke (or the enterprise deploying it) would likely need to be a business associate of the covered entity, requiring a **Business Associate Agreement (BAA)**.

### 4.2 Key Requirements Relevant to loke

- **Minimum Necessary Standard** (45 CFR 164.502(b)): Covered entities must make reasonable efforts to limit PHI to the minimum necessary to accomplish the intended purpose. loke's data minimisation and token optimisation directly serve this.
- **De-identification** (45 CFR 164.514): PHI can be de-identified via Safe Harbor (remove 18 specified identifiers) or Expert Determination (statistical/scientific assessment). De-identified data is no longer PHI and is outside HIPAA scope.
- **Business Associate requirements** (45 CFR 164.502(e)): Any entity that creates, receives, maintains, or transmits PHI on behalf of a covered entity must have a BAA.
- **Security Rule** (45 CFR Part 164 Subpart C): Administrative, physical, and technical safeguards are required for electronic PHI (ePHI). loke's encrypted storage, access controls, and audit trails address these.
- **Right of access** (45 CFR 164.524): Individuals have the right to access their PHI. loke's audit trail and data export features support this.
- **Accounting of disclosures** (45 CFR 164.528): Covered entities must account for disclosures of PHI made in the preceding 6 years.

### 4.3 PII Entity Types

HIPAA's Safe Harbor method (45 CFR 164.514(b)(2)) specifies **18 identifiers** that must be removed for de-identification. loke must detect all 18 plus additional PHI-specific types.

**Entities loke must detect under HIPAA preset:**

| Category | Safe Harbor identifier | Specific types | Detection layer |
|----------|----------------------|---------------|-----------------|
| **Names** | (A) Names | Full name, partial name | NLP NER |
| **Geography** | (B) Geographic subdivisions smaller than state | Street address, city, postcode (3-digit ZIP if population < 20,000), GPS coordinates | Regex + NLP NER |
| **Dates** | (C) All dates directly related to an individual (except year for age < 90) | Date of birth, admission date, discharge date, date of death, appointment dates | Regex + SLM NER |
| **Phone** | (D) Phone numbers | All formats | Regex |
| **Fax** | (E) Fax numbers | All formats | Regex |
| **Email** | (F) Email addresses | All formats | Regex |
| **SSN** | (G) Social Security numbers | SSN format | Regex |
| **MRN** | (H) Medical record numbers | Facility-specific formats | Regex + SLM NER |
| **Health plan ID** | (I) Health plan beneficiary numbers | Insurer-specific formats | Regex + SLM NER |
| **Account numbers** | (J) Account numbers | Bank, billing account numbers | Regex |
| **License numbers** | (K) Certificate/license numbers | DEA, medical licence, driver's licence | Regex + SLM NER |
| **Vehicle IDs** | (L) Vehicle identifiers and serial numbers, including licence plate numbers | VIN, plate numbers | Regex |
| **Device IDs** | (M) Device identifiers and serial numbers | Medical device UDIs, serial numbers | SLM NER |
| **URLs** | (N) Web Universal Resource Locators (URLs) | Patient portal URLs, personal websites | Regex |
| **IP addresses** | (O) Internet Protocol (IP) address numbers | IPv4, IPv6 | Regex |
| **Biometric IDs** | (P) Biometric identifiers, including finger and voice prints | Fingerprint hashes, voice prints | SLM NER |
| **Photographs** | (Q) Full face photographic images and any comparable images | Facial images | SLM NER |
| **Other unique IDs** | (R) Any other unique identifying number, characteristic, or code | Research subject IDs, employee IDs in health context | SLM NER |
| **Clinical data** | Not an identifier but PHI when combined | Diagnosis codes (ICD-10), procedure codes (CPT), medication names, lab results, clinical notes | SLM NER + Presidio |

### 4.4 Anonymisation Requirements

HIPAA provides two explicit de-identification methods:

**Safe Harbor (45 CFR 164.514(b)(2)):**
- Remove all 18 specified identifiers.
- The covered entity must have no actual knowledge that the remaining information could identify an individual.
- This is the method loke implements by default.

**Expert Determination (45 CFR 164.514(b)(1)):**
- A qualified statistical or scientific expert determines that the risk of identifying an individual is "very small."
- Requires documentation of methods and results.
- loke does not implement this method but supports enterprise override for organisations that have obtained an expert determination.

**loke HIPAA preset behaviour:**

- **Safe Harbor enforcement:** All 18 identifier categories are detected and replaced. No exceptions.
- **Clinical data:** Diagnosis codes, medication names, and clinical notes are anonymised (replaced with generic medical category tokens) to prevent indirect identification.
- **Reversibility:** Mapping tables are retained locally under the same encryption and access controls as ePHI. The mapping table itself is treated as PHI.
- **Re-identification:** Only permitted by the covered entity, and only with proper safeguards. loke's local restoration of placeholders is re-identification — this is acceptable because it occurs on the covered entity's device under their control.

### 4.5 Data Retention

- **HIPAA does not specify a general retention period** for medical records (this is governed by state law, typically 6-10 years for adults).
- **45 CFR 164.530(j):** HIPAA requires covered entities to retain documentation of policies, procedures, and certain communications for **6 years from the date of creation or the date last in effect**, whichever is later.
- **PII mapping tables:** Treated as ePHI. Retained for the session duration plus a configurable grace period (default: 72 hours) to allow for follow-up queries.
- **Audit logs:** Retained for **6 years minimum** per HIPAA requirements.
- **Accounting of disclosures:** loke must maintain records of every instance where data was sent to a cloud LLM provider, retained for 6 years.

### 4.6 Cross-Border Transfers

HIPAA does not contain an explicit prohibition on cross-border transfers of PHI. However:

- The **Security Rule** requires that appropriate safeguards are in place wherever PHI is processed.
- A **BAA** must be in place with any entity processing PHI, regardless of jurisdiction.
- In practice, many covered entities' compliance programmes restrict PHI processing to US-based infrastructure.

**loke HIPAA preset behaviour:**

- **Default:** No jurisdiction-based blocking. Provider selection is governed by BAA status.
- **Enterprise override:** Healthcare organisations commonly restrict to US-only providers. loke supports a `us_only` mode under the HIPAA preset.
- **BAA tracking:** The provider registry includes BAA status. Providers without a confirmed BAA are blocked from receiving any data when HIPAA preset is active.

### 4.7 Provider Restrictions

- **BAA mandatory:** Any cloud LLM provider receiving data (even de-identified, as a precautionary measure in healthcare settings) must have a BAA in place. loke blocks transmission to providers without BAA status confirmed in the provider registry.
- **Provider BAA status (as of April 2026):**
  - Anthropic: BAA available for enterprise plans
  - OpenAI: BAA available for enterprise plans
  - Google (Vertex AI): BAA available
  - Microsoft (Azure OpenAI): BAA available
  - Mistral: No BAA offering currently
  - Open-source local models: No BAA needed (no disclosure)
- **Sub-contractor chain:** BAAs must flow down to sub-contractors. loke's provider metadata tracks known sub-processor chains.

### 4.8 Audit Requirements

The HIPAA Security Rule requires:

- **164.312(b) — Audit controls:** Implement hardware, software, and/or procedural mechanisms that record and examine activity in systems that contain or use ePHI.
- **164.308(a)(1)(ii)(D) — Information system activity review:** Implement procedures to regularly review records of information system activity (audit logs, access reports, security incident tracking reports).

**loke HIPAA preset audit:**

- Full audit trail of every interaction involving PHI.
- Record: timestamp, user identity, data categories present, de-identification actions taken, provider receiving data, BAA status confirmation, response data categories.
- Audit logs are append-only with hash chain integrity.
- Audit logs must not contain PHI values.
- Retention: 6 years minimum.
- Export to enterprise SIEM systems supported.

### 4.9 Breach Notification

The **HITECH Act** (2009) and the **Breach Notification Rule** (45 CFR 164.400-414) require:

- **Definition:** Acquisition, access, use, or disclosure of PHI in a manner not permitted by the Privacy Rule which compromises the security or privacy of the PHI.
- **Risk assessment:** Unless the covered entity demonstrates a low probability that PHI has been compromised (four-factor risk assessment).
- **Notification to individuals:** Without unreasonable delay and no later than **60 calendar days** after discovery.
- **Notification to HHS:** If fewer than 500 individuals affected, annually. If 500 or more, within 60 days.
- **Notification to media:** If 500 or more residents of a state/jurisdiction are affected, within 60 days.
- **De-identified data:** Breach of properly de-identified data is not a reportable breach (the data is not PHI).

**loke relevance:** If loke's de-identification pipeline fails and PHI reaches a cloud provider, this constitutes an impermissible disclosure and likely a breach. loke's fail-closed design (block transmission on pipeline error) is critical for HIPAA compliance.

### 4.10 loke Configuration Mapping

```yaml
preset: us-hipaa

privacy:
  pii_detection:
    layers: [regex, nlp, slm, presidio]  # All layers mandatory
    entity_types:
      # Safe Harbor 18 identifiers
      - name
      - address_sub_state          # Geographic subdivisions smaller than state
      - zip_code_restricted        # 3-digit ZIP if population < 20,000 → redact
      - dates_individual           # All dates related to individual (except year if age < 90)
      - phone
      - fax
      - email
      - ssn
      - medical_record_number
      - health_plan_id
      - account_number
      - licence_number
      - vehicle_id
      - device_id_medical
      - url
      - ip_address
      - biometric
      - photo_facial
      - unique_id_other
      # PHI-specific (beyond Safe Harbor identifiers)
      - diagnosis_code             # ICD-10
      - procedure_code             # CPT
      - medication_name
      - lab_result
      - clinical_note_content
    safe_harbor_mode: strict       # All 18 identifiers enforced, no exceptions
  anonymisation:
    strength: safe_harbor           # HIPAA Safe Harbor de-identification
    reversible: true                # Mapping table treated as ePHI
    placeholder_format: "$t{n}"
    clinical_data_mode: generic_category  # Replace with "a medication" not specific placeholder
    mapping_table_classification: ephi    # Must be protected as ePHI

data_retention:
  pii_mappings: 72h                # Grace period for follow-up
  audit_logs: 6y                   # HIPAA 6-year requirement
  disclosure_accounting: 6y        # 164.528 requirement
  semantic_cache: 24h              # Aggressive purging for PHI context
  semantic_cache_clean: 90d        # Even anonymised clinical cache expires
  right_to_access: enabled         # 164.524

cross_border:
  mode: baa_required               # Provider must have BAA regardless of jurisdiction
  us_only: false                   # Enterprise can enable
  override_requires: compliance_officer_approval

providers:
  baa_required: true               # Block providers without confirmed BAA
  baa_status_tracking: enabled
  local_models: unrestricted       # No BAA needed for on-device
  companion_devices: encrypted_tunnel_required
  blocked_without_baa: true        # Hard block, not warning

audit:
  enabled: true                    # Mandatory under Security Rule
  log_pii_values: false
  log_retention: 6y
  disclosure_log: true             # Separate accounting of disclosures
  export_formats: [pdf, csv, json]
  hash_chain: true
  siem_forwarding: recommended
  activity_review: enabled         # 164.308(a)(1)(ii)(D)

breach:
  pipeline_failure_action: block_and_alert
  outbound_validation: enabled
  notification_window: 60d         # HITECH requirement
  risk_assessment_required: true   # Four-factor assessment
  hhs_notification_threshold: 500  # Individual count for immediate vs annual
```

---

## 5. US CCPA/CPRA

### 5.1 Overview

The **California Consumer Privacy Act** (CCPA, Cal. Civ. Code 1798.100-199.100), effective 1 January 2020, and the **California Privacy Rights Act** (CPRA), which amended the CCPA effective 1 January 2023, together form California's comprehensive consumer privacy law. Enforcement transitioned from the California Attorney General to the **California Privacy Protection Agency (CPPA)** in July 2023.

The CCPA/CPRA applies to for-profit businesses that: (a) have gross annual revenue over USD 25 million; or (b) buy, sell, or share the personal information of 100,000 or more consumers or households; or (c) derive 50% or more of annual revenue from selling or sharing consumers' personal information.

Maximum penalties: USD 2,500 per unintentional violation, USD 7,500 per intentional violation. Private right of action for data breaches (USD 100-750 per consumer per incident, or actual damages).

### 5.2 Key Requirements Relevant to loke

- **Right to know** (1798.110): Consumers can request disclosure of what personal information is collected, used, and disclosed. loke's audit trail and data export serve this.
- **Right to delete** (1798.105): Consumers can request deletion of their personal information. loke must support targeted deletion.
- **Right to correct** (1798.106, CPRA addition): Consumers can request correction of inaccurate personal information.
- **Right to opt out of sale/sharing** (1798.120): Consumers can opt out of the sale or sharing of their personal information. If loke transmits personal information to a cloud LLM provider, this could constitute "sharing" under CPRA's broad definition.
- **Data minimisation** (1798.100(c), CPRA addition): Collection and processing must be "reasonably necessary and proportionate" to the purposes for which the data was collected.
- **Sensitive personal information** (1798.121, CPRA addition): Consumers can limit the use and disclosure of sensitive personal information. Businesses must respect the "limit the use of my sensitive personal information" signal.
- **Service provider / contractor obligations** (1798.140(ag), 1798.140(j)): LLM providers receiving data would be service providers or contractors, requiring contractual restrictions on use.

### 5.3 PII Entity Types

CCPA defines "personal information" (1798.140(v)) broadly as information that identifies, relates to, describes, is reasonably capable of being associated with, or could reasonably be linked, directly or indirectly, with a particular consumer or household.

CPRA introduced "sensitive personal information" (1798.140(ae)) as a distinct category with additional protections.

**Entities loke must detect under CCPA/CPRA preset:**

| Category | Specific types | Sensitive PI? | Detection layer |
|----------|---------------|---------------|-----------------|
| **Identifiers** | Name, alias, postal address, email address, IP address, account name | No | Regex + NLP NER |
| **Government IDs** | SSN, driver's licence number, passport number, state ID | Yes (1798.140(ae)(1)) | Regex |
| **Financial** | Financial account number with access credentials (login + password, security code) | Yes (1798.140(ae)(2)) | Regex + SLM NER |
| **Precise geolocation** | GPS coordinates, geolocation data (precise = within 1,850 feet / 564 metres) | Yes (1798.140(ae)(3)) | Regex + SLM NER |
| **Racial/ethnic origin** | Race, ethnicity references | Yes (1798.140(ae)(4)) | SLM NER |
| **Religious/philosophical beliefs** | Religious or philosophical belief references | Yes (1798.140(ae)(4)) | SLM NER |
| **Union membership** | Union membership references | Yes (1798.140(ae)(4)) | SLM NER |
| **Communications content** | Contents of consumer's mail, email, and text messages (unless business is intended recipient) | Yes (1798.140(ae)(5)) | SLM NER |
| **Genetic data** | Genetic data | Yes (1798.140(ae)(6)) | SLM NER |
| **Biometric data** | Biometric information for identification purposes | Yes (1798.140(ae)(7)) | SLM NER |
| **Health data** | Health information | Yes (1798.140(ae)(8)) | SLM NER + Presidio |
| **Sexual orientation** | Sex life or sexual orientation data | Yes (1798.140(ae)(9)) | SLM NER |
| **Household data** | Data linked to a household (unique to CCPA) | No (but PI) | SLM NER |
| **Inferences** | Inferences drawn to create a consumer profile | No (but PI per 1798.140(v)(K)) | SLM NER |
| **Commercial information** | Purchase history, purchasing tendencies | No | Configurable |
| **Internet activity** | Browsing history, search history, interaction with ads/content | No | Configurable |
| **Professional/employment** | Current or past job information | No | SLM NER |
| **Education** | Non-publicly available education information | No | SLM NER |

### 5.4 Anonymisation Requirements

CCPA/CPRA use two relevant concepts:

- **De-identified information** (1798.140(m)): Information that cannot reasonably be used to infer information about, or otherwise be linked to, a particular consumer, provided the business: (1) has implemented technical safeguards prohibiting re-identification; (2) has implemented business processes preventing re-identification; (3) has implemented business processes to prevent inadvertent release; and (4) makes no attempt to re-identify.
- **Aggregate consumer information** (1798.140(b)): Information relating to a group or category of consumers from which individual identities have been removed, not linked or reasonably linkable to any consumer or household.

**loke CCPA/CPRA preset behaviour:**

- **Outbound data:** De-identification via placeholder replacement. loke's local mapping table technically enables re-identification, but since loke is operated by (or on behalf of) the consumer's own employer/organisation — not "the business" selling data — the de-identification requirements are met for the outbound transmission to the LLM provider.
- **Sensitive personal information:** The preset treats all CPRA sensitive PI categories with enhanced protection (irreversible redaction for outbound data).
- **"Do Not Sell or Share" compliance:** If a consumer has exercised their right to opt out, loke must block all transmission of their personal information to cloud LLM providers (or ensure complete de-identification).

### 5.5 Data Retention

- **1798.100(a)(3):** Businesses must disclose retention periods for each category of personal information. There is no maximum retention period specified, but retention must be "no longer than reasonably necessary" for the disclosed purpose.
- **Records of requests:** Businesses must maintain records of consumer requests and how they were complied with for at least **24 months** (11 CCR 7101).
- **PII mapping tables:** 48 hours after session close.
- **Audit logs:** 24 months minimum (consumer request records).
- **Right to delete:** Supported and must be completed within **45 calendar days** of receiving a verifiable consumer request (extendable by 45 days with notice).

### 5.6 Cross-Border Transfers

CCPA/CPRA does not contain cross-border transfer restrictions comparable to GDPR or APP 8. The obligations attach to the business regardless of where processing occurs. However:

- Service provider and contractor contracts must restrict use of personal information.
- If data is transferred to a jurisdiction with weaker protections, the business remains fully liable.

**loke CCPA/CPRA preset behaviour:**

- **No jurisdiction-based blocking.** All providers permitted.
- **Service provider contract tracking:** The provider registry includes a field for CCPA/CPRA-compliant service provider agreement status.

### 5.7 Provider Restrictions

- **Service provider agreements:** LLM providers receiving personal information must be contractually restricted from: retaining, using, or disclosing personal information for any purpose other than performing the services specified in the contract; selling or sharing the personal information; combining personal information received from the business with other sources (except for specific permitted purposes).
- **Contractor agreements:** Similar to service provider but with additional certification requirements.
- **loke enforcement:** Provider registry tracks service provider agreement status. Warning (not block) issued when transmitting to providers without confirmed agreements (less strict than HIPAA BAA requirement).

### 5.8 Audit Requirements

- **CPRA audit regulations:** The CPPA has authority to require annual cybersecurity audits and risk assessments for businesses whose processing presents significant risk to consumer privacy or security. Draft regulations have been in development; final rules expected 2026.
- **Consumer request records:** 24 months retention (11 CCR 7101).
- **loke audit:** Same metadata-only logging as other presets. 24-month minimum retention for consumer-request-related entries; 5 years for general audit trail (anticipating final CPPA regulations).

### 5.9 Breach Notification

CCPA's private right of action (1798.150) applies to breaches of unencrypted or unredacted personal information resulting from the business's failure to implement reasonable security.

Separate from CCPA, California's general breach notification law (Cal. Civ. Code 1798.29, 1798.82) requires:

- **Notification to consumers:** "In the most expedient time possible and without unreasonable delay." No specific day count, but typically interpreted as 30-45 days.
- **Notification to Attorney General:** If more than 500 California residents are affected.

**loke relevance:** A breach in loke's context would be transmission of unencrypted personal information to an LLM provider. loke's encryption and anonymisation pipeline mitigates this.

### 5.10 loke Configuration Mapping

```yaml
preset: us-ccpa-cpra

privacy:
  pii_detection:
    layers: [regex, nlp, slm]        # Presidio optional (not mandatory by regulation)
    entity_types:
      - name
      - alias
      - address
      - email
      - ip_address
      - account_name
      - ssn
      - drivers_licence
      - passport
      - state_id
      - financial_account_with_credentials
      - precise_geolocation          # Within 1,850 feet
      - racial_ethnic_origin
      - religious_belief
      - trade_union
      - communications_content
      - genetic_data
      - biometric
      - health_data
      - sexual_orientation
      - household_data               # Unique to CCPA
      - inferences                   # Consumer profiling
      - commercial_info              # Optional — configurable
      - internet_activity            # Optional — configurable
      - professional_employment
      - education
    sensitive_pi_handling: enhanced_protection
  anonymisation:
    strength: de_identification
    reversible: true
    placeholder_format: "$t{n}"
    sensitive_pi_mode: irreversible_redact
    do_not_sell_share: enforce       # Respect opt-out signals

data_retention:
  pii_mappings: 48h
  audit_logs: 5y                     # Anticipating final CPPA regulations
  consumer_request_records: 24m      # 11 CCR 7101
  semantic_cache: 30d
  semantic_cache_clean: unlimited
  right_to_delete: enabled
  deletion_timeline: 45d             # Verifiable request completion deadline

cross_border:
  mode: unrestricted                 # No jurisdiction-based restrictions
  service_provider_contract_required: true

providers:
  service_provider_agreement: recommended  # Warning, not block
  contractor_certification: optional
  local_models: unrestricted
  companion_devices: encrypted_tunnel_required

audit:
  enabled: true
  log_pii_values: false
  log_retention: 5y
  consumer_request_log: 24m
  export_formats: [pdf, csv, json]
  hash_chain: true
  siem_forwarding: optional

breach:
  pipeline_failure_action: block_and_alert
  outbound_validation: enabled
  notification_window: expedient     # "Most expedient time possible"
  ag_notification_threshold: 500     # California residents
```

---

## 6. UK GDPR

### 6.1 Overview

The **UK General Data Protection Regulation** (UK GDPR) is the retained EU law version of the GDPR, as amended by the **Data Protection Act 2018** (DPA 2018) and the **Data Protection, Privacy and Electronic Communications (Amendments etc) (EU Exit) Regulations 2019**. It has applied since 1 January 2021 (end of the Brexit transition period).

The UK GDPR is substantively similar to EU GDPR but with UK-specific modifications:

- The supervisory authority is the **Information Commissioner's Office (ICO)**, not EU DPAs.
- The UK maintains its own adequacy decisions for international transfers.
- The **UK International Data Transfer Agreement (IDTA)** and **UK Addendum to EU SCCs** replace EU SCCs for UK transfers.
- The **Data Protection and Digital Information Act 2024** (DPDI Act), which received Royal Assent in November 2024, introduced modifications including: a more flexible approach to legitimate interest, reduced requirements for Data Protection Officers, modified rules for international transfers based on a "data protection test," and changes to cookie consent rules.

Enforced by the ICO. Maximum fines: GBP 17.5 million or 4% of annual global turnover, whichever is higher.

### 6.2 Key Requirements Relevant to loke

The core requirements mirror EU GDPR (lawful basis, data minimisation, purpose limitation, storage limitation, data protection by design and default, rights of data subjects). Key UK-specific differences:

- **Legitimate interest:** The DPDI Act 2024 created a limited list of "recognised legitimate interests" that do not require a balancing test (e.g., national security, safeguarding). This does not directly affect loke's privacy processing but may simplify the legal basis analysis for enterprises.
- **International transfers:** The UK's "data protection test" (DPDI Act) replaces the EU adequacy framework with a more flexible assessment. Transfers are permitted if the destination provides data protection that is "not materially lower" than UK standards — a less rigid threshold than EU "essential equivalence."
- **Automated decision-making:** UK GDPR Art. 22 equivalent restricts solely automated decisions with legal or similarly significant effects. The DPDI Act narrows this to decisions made "without meaningful human involvement."
- **Research exemption:** The DPDI Act broadened the research exemption, which may be relevant if loke is used in research contexts.

### 6.3 PII Entity Types

UK GDPR uses the same definition of personal data as EU GDPR (Art. 4(1)). The entity types are identical to the EU GDPR preset with UK-specific additions:

| Category | UK-specific types | Detection layer |
|----------|------------------|-----------------|
| **Government identifiers** | National Insurance Number (NINO), NHS number, UK passport number, UK driving licence number | Regex |
| **Financial** | UK sort code + account number, National Savings & Investments references | Regex |
| All other categories | Same as EU GDPR | Same as EU GDPR |

### 6.4 Anonymisation Requirements

Same framework as EU GDPR: anonymisation (irreversible, outside scope) vs pseudonymisation (reversible, still personal data).

The ICO's anonymisation guidance (updated 2024) emphasises the "motivated intruder" test — whether a motivated person without specialist knowledge but with access to resources such as the internet, public libraries, and public records could re-identify the individual.

**loke UK GDPR preset behaviour:** Identical to EU GDPR preset. Full anonymisation for outbound data, irreversible redaction for special category data.

### 6.5 Data Retention

Same principles as EU GDPR. Configuration identical except for jurisdiction-specific compliance periods.

### 6.6 Cross-Border Transfers

Post-DPDI Act, the UK's transfer framework is:

- **UK adequacy regulations:** The Secretary of State can designate countries as providing adequate protection. Current UK adequacy destinations include all EU/EEA countries plus those covered by EU adequacy decisions that were transitioned into UK law.
- **UK International Data Transfer Agreement (IDTA):** Replaces EU SCCs for UK-originating transfers.
- **UK Addendum to EU SCCs:** A bridge mechanism allowing EU SCCs to cover UK transfers.
- **Data protection test (DPDI Act):** Transfers permitted to destinations where protection is "not materially lower" — assessed by the transferring organisation. This is less prescriptive than the EU approach.

**loke UK GDPR preset behaviour:**

- **Provider allow-list:** Providers in UK-adequate jurisdictions permitted by default.
- **US providers:** Permitted under the UK Extension to the EU-US Data Privacy Framework (UK-US Data Bridge), effective October 2023.
- **Flexible assessment:** Enterprise administrators can approve transfers to non-adequate jurisdictions based on the DPDI "not materially lower" test, with documentation.

### 6.7 Provider Restrictions

- **DPA required:** Same as EU GDPR. Any processor must have a data processing agreement.
- **UK-specific terms:** DPAs should reference UK GDPR and DPA 2018, not EU GDPR.
- **ICO-registered:** Processors handling UK personal data should be registered with the ICO (or exempt).

### 6.8 Audit Requirements

Same as EU GDPR. ICO enforcement limitation period is 6 years for most matters.

- **Log retention:** 5 years recommended (same as EU GDPR).

### 6.9 Breach Notification

- **UK GDPR Art. 33:** Notify the ICO within **72 hours** of becoming aware of a personal data breach, unless the breach is unlikely to result in a risk to rights and freedoms.
- **UK GDPR Art. 34:** Notify data subjects without undue delay if high risk.
- **ICO reporting tool:** The ICO provides an online breach reporting tool. Enterprises using loke should configure the breach alerting to integrate with their ICO notification workflow.

### 6.10 loke Configuration Mapping

```yaml
preset: uk-gdpr

privacy:
  pii_detection:
    layers: [regex, nlp, slm, presidio]
    entity_types:
      # All EU GDPR entities plus UK-specific
      - name
      - email
      - phone
      - nino                        # National Insurance Number
      - nhs_number                  # NHS number
      - uk_passport
      - uk_driving_licence
      - address
      - postcode
      - gps_coordinates
      - ip_address
      - uk_sort_code_account        # Sort code + account number
      - credit_card
      - cookie_id
      - device_fingerprint
      - mac_address
      - biometric
      - health_data
      - genetic_data
      - racial_ethnic_origin
      - political_opinion
      - religious_belief
      - trade_union
      - sexual_orientation
      - criminal_data
    special_category_handling: block_or_full_redact
  anonymisation:
    strength: full
    reversible: true
    placeholder_format: "$t{n}"
    special_category_mode: irreversible_redact

data_retention:
  pii_mappings: 24h
  audit_logs: 5y
  semantic_cache: 30d
  semantic_cache_clean: unlimited
  right_to_erasure: enabled

cross_border:
  mode: adequacy_or_data_protection_test
  uk_adequacy_list: uk_adequacy_2026
  uk_us_data_bridge: true           # UK Extension to EU-US DPF
  flexible_assessment: enterprise_documented  # DPDI "not materially lower" test
  override_requires: documented_assessment

providers:
  dpa_required: true
  uk_gdpr_terms: true               # DPA must reference UK GDPR + DPA 2018
  ico_registration: recommended
  local_models: unrestricted
  companion_devices: encrypted_tunnel_required

audit:
  enabled: true
  log_pii_values: false
  log_retention: 5y
  export_formats: [pdf, csv, json]
  hash_chain: true
  siem_forwarding: optional

breach:
  pipeline_failure_action: block_and_alert
  outbound_validation: enabled
  notification_window: 72h           # ICO notification
```

---

## 7. Singapore PDPA

### 7.1 Overview

The **Personal Data Protection Act 2012** (PDPA, No. 26 of 2012), as amended most recently by the **Personal Data Protection (Amendment) Act 2020**, governs the collection, use, and disclosure of personal data by private-sector organisations in Singapore. It is enforced by the **Personal Data Protection Commission (PDPC)**.

Key amendments in 2020 (effective February 2021):

- Mandatory data breach notification
- Enhanced consent framework (deemed consent by contractual necessity, deemed consent by notification)
- Data portability obligation
- Increased maximum financial penalty from SGD 1 million to **SGD 1 million or 10% of annual turnover** (for organisations with annual turnover above SGD 10 million)
- Legitimate interest and business improvement exceptions

The PDPA works alongside sector-specific legislation, including the Banking Act, Insurance Act, and Healthcare Services Act.

### 7.2 Key Requirements Relevant to loke

- **Consent obligation** (s 13): Organisations must obtain consent for collection, use, or disclosure of personal data, unless an exception applies (e.g., legitimate interest, business improvement, research).
- **Purpose limitation** (s 18): Personal data may only be collected for purposes a reasonable person would consider appropriate and that are notified to the individual.
- **Notification obligation** (s 20): Organisations must inform individuals of the purposes for which personal data is collected, used, or disclosed.
- **Access obligation** (s 21): Individuals can request access to their personal data and information about how it has been used or disclosed in the past year.
- **Correction obligation** (s 22): Individuals can request correction of errors in their personal data.
- **Accuracy obligation** (s 23): Organisations must make reasonable efforts to ensure personal data is accurate and complete.
- **Protection obligation** (s 24): Reasonable security arrangements to protect personal data from unauthorised access, collection, use, disclosure, copying, modification, or disposal.
- **Retention limitation** (s 25): Personal data must not be retained longer than necessary for the purpose, and must be disposed of or anonymised when no longer needed.
- **Transfer limitation** (s 26): Personal data may only be transferred outside Singapore in accordance with regulations (adequate protection or prescribed exceptions).
- **Data portability** (s 26H, 2020 amendment): Individuals can request that their data be transmitted to another organisation in a commonly used machine-readable format.

### 7.3 PII Entity Types

The PDPA defines "personal data" as data about an individual who can be identified from that data, or from that data and other information to which the organisation has or is likely to have access.

**Entities loke must detect under Singapore PDPA preset:**

| Category | Specific types | Detection layer |
|----------|---------------|-----------------|
| **Direct identifiers** | Full name, email, phone number (Singapore format: +65), date of birth | Regex + NLP NER |
| **Government identifiers** | NRIC/FIN number (National Registration Identity Card / Foreign Identification Number), passport number, work permit number | Regex |
| **Location data** | Street address, postal code (6-digit Singapore format), GPS coordinates | Regex + NLP NER |
| **Financial** | Bank account number, credit/debit card number, CPF account number (Central Provident Fund) | Regex |
| **Online identifiers** | IP address, device identifiers | Regex |
| **Health data** | Medical conditions, prescriptions, hospital records | SLM NER + Presidio |
| **Biometric data** | Facial images, fingerprints, voice prints | SLM NER |
| **Employment data** | Employment history, salary information, performance reviews | SLM NER |

The PDPA does not create a formal "sensitive data" category like GDPR Article 9 or CCPA's sensitive PI. However, the PDPC's guidance recognises that certain data (NRIC, health, financial) warrants enhanced protection. The Advisory Guidelines on the NRIC (2018, updated 2024) specifically restrict collection and use of NRIC numbers.

### 7.4 Anonymisation Requirements

The PDPA's Anonymisation Guide (published by PDPC, updated 2022) provides detailed guidance:

- **Anonymised data** is outside the PDPA's scope if it cannot be used to identify an individual.
- The PDPC recommends a risk-based approach: assess the likelihood of re-identification given available data and techniques.
- Recommended techniques: generalisation, suppression, noise addition, data swapping, synthetic data generation.

**loke Singapore PDPA preset behaviour:**

- **Outbound data:** Anonymisation via placeholder replacement. Meets the PDPC's "reasonable steps" standard.
- **NRIC numbers:** Must be fully redacted (not pseudonymised) per the Advisory Guidelines on the NRIC.
- **Health and financial data:** Enhanced protection (irreversible redaction for outbound data).

### 7.5 Data Retention

- **s 25:** Organisations must cease to retain personal data when it is no longer needed for any legal or business purpose.
- **PII mapping tables:** 48 hours after session close.
- **Audit logs:** 5 years (recommended, aligning with the PDPA's general enforcement timeline).
- **PDPC enforcement:** The PDPC can investigate complaints and conduct reviews going back up to 5 years.

### 7.6 Cross-Border Transfers

**s 26** and the **Personal Data Protection Regulations 2014** (as amended) govern cross-border transfers:

- Data may be transferred outside Singapore only if the recipient jurisdiction provides a comparable standard of protection, or if the transferring organisation ensures the recipient is bound by legally enforceable obligations to a comparable standard.
- Acceptable mechanisms: contractual arrangements, binding corporate rules, consent after notification of risks, APEC Cross-Border Privacy Rules (CBPR) certification.
- The PDPC does not maintain an adequacy list but has mutual recognition arrangements with other APEC CBPR-participating economies.

**loke Singapore PDPA preset behaviour:**

- **Default:** Providers in jurisdictions with comparable data protection standards permitted. In practice, most major cloud LLM providers (US providers with CBPR certification, EU/UK providers, Japanese providers) are acceptable.
- **Contractual obligation tracking:** The provider registry tracks whether contractual arrangements ensuring comparable protection are in place.
- **NRIC data:** Never transferred outside Singapore, even with safeguards.

### 7.7 Provider Restrictions

- **Data intermediary obligations:** If the LLM provider processes data on behalf of the organisation (data intermediary under s 4(2)), the organisation must ensure the intermediary protects data to at least the same standard.
- **Contractual requirements:** Contracts with data intermediaries should specify security measures, retention limits, and sub-processing restrictions.
- **No formal "BAA" equivalent:** The obligation is contractual, enforced through the PDPA's protection and retention obligations flowing through to intermediaries.

### 7.8 Audit Requirements

- **s 12 — Policies and practices:** Organisations must develop and implement policies and practices necessary to meet PDPA obligations, and make information about those policies available on request.
- **PDPC inspection:** The PDPC may conduct inspections and require organisations to produce records.
- **Log retention:** 5 years recommended.
- **Access requests:** Organisations must respond within **30 calendar days** (extendable by 30 days with notice).

### 7.9 Breach Notification

The 2020 amendments introduced mandatory breach notification (Part VIA):

- **Notifiable breach:** A data breach that results in or is likely to result in significant harm to affected individuals, or is of a significant scale (500 or more affected individuals).
- **Notification to PDPC:** Within **3 calendar days** of completing assessment that the breach is notifiable (assessment must be completed within 30 days of becoming aware).
- **Notification to individuals:** As soon as practicable if the breach is likely to result in significant harm.
- **Significant harm:** Includes financial loss, damage to reputation or relationships, or other harm that a reasonable person would consider significant.

### 7.10 loke Configuration Mapping

```yaml
preset: sg-pdpa

privacy:
  pii_detection:
    layers: [regex, nlp, slm]        # Presidio optional
    entity_types:
      - name
      - email
      - phone_sg                     # +65 format
      - date_of_birth
      - nric_fin                     # NRIC/FIN — enhanced protection
      - passport
      - work_permit
      - address
      - postal_code_sg               # 6-digit Singapore format
      - gps_coordinates
      - ip_address
      - bank_account
      - credit_card
      - cpf_account                  # Central Provident Fund
      - health_data
      - biometric
      - employment_data
      - salary_info
    nric_handling: full_redact        # Per NRIC Advisory Guidelines
    enhanced_protection: [nric_fin, health_data, financial]
  anonymisation:
    strength: anonymisation           # Risk-based "reasonable steps"
    reversible: true
    placeholder_format: "$t{n}"
    nric_mode: irreversible_redact    # Never pseudonymise NRIC

data_retention:
  pii_mappings: 48h
  audit_logs: 5y
  semantic_cache: 30d
  semantic_cache_clean: unlimited
  right_to_access: enabled
  access_response_deadline: 30d

cross_border:
  mode: comparable_protection_required
  contractual_obligation_tracking: true
  nric_transfer_block: true          # NRIC never leaves Singapore
  cbpr_accepted: true
  override_requires: enterprise_approval

providers:
  data_intermediary_contract: recommended
  local_models: unrestricted
  companion_devices: encrypted_tunnel_required

audit:
  enabled: true
  log_pii_values: false
  log_retention: 5y
  export_formats: [pdf, csv, json]
  hash_chain: true
  siem_forwarding: optional

breach:
  pipeline_failure_action: block_and_alert
  outbound_validation: enabled
  notification_window: 3d            # PDPC notification after assessment
  assessment_period: 30d
  significant_scale_threshold: 500
```

---

## 8. Minimal Preset

### 8.1 Overview

The minimal preset is designed for **development, testing, and demonstration purposes only**. It disables most regulatory protections to reduce processing overhead and simplify debugging. It must never be used with real personal data or in production environments.

When the minimal preset is active, loke displays a persistent warning banner: "Minimal privacy preset active — not suitable for real data."

### 8.2 Configuration

```yaml
preset: minimal

privacy:
  pii_detection:
    layers: [regex]                  # Regex only — fastest, minimal overhead
    entity_types:
      - email
      - phone
    # All other entity types disabled
    special_category_handling: disabled
  anonymisation:
    strength: placeholder_only       # Simple $1, $2 replacement
    reversible: true
    placeholder_format: "$n"
    no_validation: true              # Skip outbound PII scan

data_retention:
  pii_mappings: unlimited            # No automatic purging
  audit_logs: disabled               # No audit logging
  semantic_cache: unlimited
  right_to_erasure: disabled

cross_border:
  mode: unrestricted
  no_checks: true

providers:
  no_restrictions: true
  local_models: unrestricted
  companion_devices: unrestricted

audit:
  enabled: false

breach:
  pipeline_failure_action: warn_and_continue  # Fail open for development
  outbound_validation: disabled

warnings:
  persistent_banner: true
  banner_text: "Minimal privacy preset active — not suitable for real data"
  production_block: true             # Cannot be activated if enterprise policy is loaded
```

### 8.3 Restrictions

- **Enterprise policy override:** If an enterprise policy is loaded (story A3.1), the minimal preset cannot be activated. The policy loader rejects it.
- **No production use:** Application telemetry (if enabled) flags minimal preset usage. Enterprise dashboards can alert on it.
- **Explicit selection required:** The minimal preset is never auto-selected. Users must explicitly choose it and confirm a warning dialog.

---

## 9. EU AI Act

### 9.1 Overview

**Regulation (EU) 2024/1689** — the **Artificial Intelligence Act** — entered into force on 1 August 2024, with provisions applying in phases:

- **February 2025:** Prohibited AI practices and AI literacy obligations
- **August 2025:** Obligations for providers of general-purpose AI (GPAI) models
- **August 2026:** Full application of high-risk AI system requirements (Annex III)
- **August 2027:** High-risk AI systems in products covered by EU harmonised legislation (Annex I)

### 9.2 Relevance to loke

loke is not itself an "AI system" in the Annex III high-risk sense — it is a tool that mediates access to AI systems. However, several provisions are directly relevant:

**GPAI model obligations (Art. 53, effective August 2025):**

Providers of GPAI models must:
- Maintain and make available technical documentation (including training, testing, and evaluation information).
- Provide information and documentation to downstream providers to enable compliance.
- Put in place a policy to comply with EU copyright law.
- Publish a sufficiently detailed summary of the training data content.

**loke impact:** loke routes requests to GPAI models. loke should surface provider compliance information (e.g., whether a provider has published required documentation) in the provider registry. Enterprise administrators should be able to block non-compliant GPAI providers.

**High-risk AI systems (Annex III, effective August 2026):**

loke users may deploy AI systems (via cloud LLMs routed through loke) in high-risk domains including:
- Employment and workers management (recruitment, promotion, task allocation)
- Access to essential services (credit scoring, insurance pricing)
- Law enforcement (individual risk assessments)
- Migration, asylum, and border control
- Administration of justice

**Requirements for high-risk AI:**
- Risk management system (Art. 9)
- Data governance (Art. 10)
- Technical documentation (Art. 11)
- Record-keeping / automatic logging (Art. 12)
- Transparency and human oversight (Art. 13, 14)
- Accuracy, robustness, and cybersecurity (Art. 15)
- Conformity assessment (Art. 43)

**loke impact:** loke's audit trail (Art. 12), transparency features (Art. 13 — showing users exactly what is sent to LLMs), and human oversight features (Art. 14 — user approval before transmission) directly support high-risk compliance. When a user or enterprise indicates they are operating in a high-risk domain, loke should:

- Enforce full audit logging with extended retention (10 years per Art. 18(1))
- Require explicit user confirmation before each cloud LLM dispatch
- Log the specific model and version used for each interaction
- Record the input data, the output, and the user's acceptance/rejection of the output
- Block model auto-selection (user must explicitly choose the model to maintain human oversight)

**Transparency obligations (Art. 50):**

Deployers of AI systems that interact with natural persons must inform them that they are interacting with an AI system (Art. 50(1)). This applies to loke's end users — they must be aware that LLM processing is occurring.

### 9.3 loke Configuration Additions for EU AI Act

```yaml
ai_act:
  enabled: true                      # Activate when operating under EU jurisdiction
  gpai_compliance_tracking: true     # Track provider Regulation compliance
  high_risk:
    enabled: false                   # Enterprise activates for high-risk domains
    domains:                         # Annex III categories
      - employment
      - essential_services
      - law_enforcement
      - migration
      - justice
    audit_retention: 10y             # Art. 18(1)
    explicit_confirmation: true      # Art. 14 human oversight
    model_auto_select: disabled      # Art. 14 human oversight
    input_output_logging: true       # Art. 12 record-keeping
    model_version_logging: true      # Art. 12 record-keeping
  transparency:
    ai_interaction_notice: true      # Art. 50(1)
  blocked_providers:
    gpai_non_compliant: warn         # Warn (or block, enterprise configurable)
```

---

## 10. Colorado AI Act

### 10.1 Overview

The **Colorado Artificial Intelligence Act** (SB 24-205), signed into law in May 2024, takes effect on **1 February 2026** (originally effective 1 June 2026, but delayed during a subsequent amendment session; the current effective date is 1 February 2026).

It is the first comprehensive US state law regulating AI. It focuses specifically on "high-risk artificial intelligence systems" — AI systems that make, or are a substantial factor in making, "consequential decisions" affecting consumers.

### 10.2 Key Definitions

- **Consequential decision:** A decision that has a material legal or similarly significant effect on a consumer's access to, or the cost/terms of: education, employment, financial or lending services, government services, healthcare, housing, insurance, or legal services.
- **High-risk AI system:** An AI system that makes or is a substantial factor in making a consequential decision.
- **Deployer:** A person doing business in Colorado that deploys a high-risk AI system.
- **Developer:** A person doing business in Colorado that develops or intentionally and substantially modifies an AI system.
- **Algorithmic discrimination:** Differential treatment or impact that disfavours individuals based on race, color, ethnicity, sex, religion, age, disability, or other protected characteristic, where the treatment is not justified.

### 10.3 Requirements Relevant to loke

**Deployer obligations (applicable to enterprises using loke):**

- **Risk management policy:** Deployers must implement a risk management policy and programme (s 6-1-1703(1)).
- **Impact assessment:** Before deploying a high-risk AI system, and annually thereafter, deployers must complete an impact assessment (s 6-1-1703(3)).
- **Consumer disclosure:** Deployers must provide consumers with: a statement that a high-risk AI system is being used to make a consequential decision; a plain-language description of the system; contact information for the deployer; and a description of the consumer's right to appeal (s 6-1-1703(4)).
- **Right to appeal:** Consumers must have the opportunity to appeal a consequential decision and, if technically feasible, to request a human alternative (s 6-1-1703(5)).
- **Annual disclosure:** Deployers must publicly disclose a summary of the types of high-risk AI systems they deploy (s 6-1-1703(6)).

**Developer obligations (applicable to LLM providers routed through loke):**

- **Documentation:** Developers must make available to deployers: a general description of the system, known limitations, intended uses, documentation of training data, and evaluation results (s 6-1-1704).
- **Algorithmic discrimination reporting:** Developers must report any known risks of algorithmic discrimination to the Colorado Attorney General within 90 days of discovery (s 6-1-1704(4)).

### 10.4 loke Impact

loke is neither the developer (LLM providers are developers) nor the deployer (enterprises using loke are deployers). However, loke is the infrastructure through which high-risk AI processing flows, and its features directly support compliance:

- **Consumer disclosure:** loke's transparency features (showing what is sent to LLMs, displaying model identity) support the disclosure requirement.
- **Right to appeal / human alternative:** loke's "require-confirmation" mode and ability to route to a local model (human + local alternative) support this.
- **Impact assessment:** loke's audit trail and reporting features (story A3.4) can generate the data needed for annual impact assessments.
- **Algorithmic discrimination:** loke can log input/output pairs with demographic category indicators (post-anonymisation) to support discrimination monitoring, though this requires careful design to avoid creating new privacy risks.

### 10.5 loke Configuration Additions for Colorado AI Act

```yaml
colorado_ai_act:
  enabled: false                     # Enterprise activates for Colorado operations
  high_risk_system:
    consequential_decision_domains:
      - education
      - employment
      - financial_services
      - government_services
      - healthcare
      - housing
      - insurance
      - legal_services
    consumer_disclosure: true        # Display AI system notice
    model_identity_display: true     # Show which model is being used
    right_to_appeal: true            # Enable appeal workflow
    human_alternative: local_model   # Route to local model as human alternative
    impact_assessment_data: true     # Log data needed for annual assessment
  annual_disclosure:
    generate_report: true            # Auto-generate deployment summary
  risk_management:
    policy_reference: ""             # Link to enterprise risk management policy
```

---

## 11. Cross-Regulation Conflicts and Resolution

### 11.1 Resolution Principle: Most Restrictive Wins

When multiple regulatory presets apply (e.g., a UK company processing data of EU residents using a US HIPAA-covered health system), loke resolves conflicts by applying the **most restrictive requirement** from any applicable regulation for each individual setting.

This is consistent with loke's core philosophy: "Conservative defaults that can be relaxed, not permissive defaults that must be tightened."

### 11.2 Conflict Resolution Algorithm

For each configuration parameter, loke applies the following precedence:

1. **Enterprise policy override** (highest priority) — explicit enterprise settings always win.
2. **Most restrictive applicable regulation** — if multiple presets are active, the strictest value applies.
3. **User override** — user preferences apply only if they are more restrictive than the regulatory floor.
4. **Default preset** (lowest priority) — EU GDPR as baseline.

### 11.3 Common Conflicts and Resolutions

| Conflict | EU GDPR says | Other regulation says | Resolution |
|----------|-------------|----------------------|------------|
| **Audit retention** | 5 years | AU: 7 years, HIPAA: 6 years | Apply longest: 7 years (AU) |
| **Breach notification** | 72 hours | SG: 3 days (after assessment), AU: 30 days, HIPAA: 60 days | Apply shortest: 72 hours (EU GDPR / UK GDPR) |
| **Cross-border transfers** | Adequacy decision required | CCPA: no restriction | Apply strictest: adequacy decision required |
| **Provider agreements** | DPA required | HIPAA: BAA required, CCPA: service provider agreement | Apply all: DPA + BAA + service provider agreement |
| **PII entity scope** | Any identifying data | HIPAA: 18 Safe Harbor identifiers + PHI | Apply union: all GDPR entities + all HIPAA entities |
| **Special category data** | Block or full redact | AU: enhanced protection for sensitive info | Apply strictest: block or full redact |
| **Right to erasure** | Statutory right | AU: best practice, CCPA: statutory right to delete | Apply statutory right |
| **Anonymisation strength** | Full anonymisation | CCPA: de-identification | Apply strictest: full anonymisation |
| **Data retention (PII mappings)** | 24 hours | AU: 48 hours, HIPAA: 72 hours | Apply shortest: 24 hours |

### 11.4 Multi-Preset Activation

Enterprises can activate multiple presets simultaneously. loke merges them:

```yaml
# Example: UK company processing EU and US health data
active_presets: [eu-gdpr, uk-gdpr, us-hipaa]

# Resolved configuration (computed, not manually specified):
resolved:
  pii_entity_types: [union of all three presets]
  anonymisation_strength: full              # EU GDPR (strictest)
  pii_mapping_retention: 24h               # EU GDPR (shortest)
  audit_log_retention: 6y                  # HIPAA (longest, since EU/UK is 5y)
  cross_border_mode: adequacy_required     # EU GDPR (strictest)
  provider_requirements: [dpa, baa]        # EU GDPR DPA + HIPAA BAA
  breach_notification: 72h                 # EU/UK GDPR (shortest)
  special_category: block_or_full_redact   # EU GDPR (strictest)
```

### 11.5 Conflicts That Cannot Be Auto-Resolved

Some conflicts require human judgment:

- **Competing retention obligations:** If one regulation requires data retention (e.g., HIPAA's 6-year accounting of disclosures) while another requires deletion (GDPR right to erasure), loke flags the conflict to the enterprise administrator. It does not auto-resolve because the correct answer depends on whether the retention obligation takes legal precedence over the erasure request in the specific context.
- **Jurisdictional ambiguity:** When it is unclear which regulation applies to a specific data subject, loke defaults to the most restrictive applicable preset and flags the ambiguity.
- **Provider blocking vs availability:** If the most restrictive transfer rules block all available providers, loke routes to local-only processing and alerts the user that no cloud provider is available under current regulatory settings.

---

## 12. loke Configuration Schema Reference

This section documents every configuration field introduced by the regulatory presets. These fields are implemented in loke's hierarchical configuration system (story F1.5) and enforced by the policy engine (epic A3).

### 12.1 Top-Level Structure

```yaml
regulatory:
  preset: string                     # One of: eu-gdpr, au-privacy-act, us-hipaa,
                                     #         us-ccpa-cpra, uk-gdpr, sg-pdpa, minimal
  active_presets: string[]           # Multiple presets for cross-regulation scenarios
  privacy: PrivacyConfig
  data_retention: RetentionConfig
  cross_border: CrossBorderConfig
  providers: ProviderConfig
  audit: AuditConfig
  breach: BreachConfig
  ai_act: AIActConfig               # Optional, EU AI Act compliance
  colorado_ai_act: ColoradoAIActConfig  # Optional, Colorado AI Act compliance
  warnings: WarningsConfig           # Minimal preset only
```

### 12.2 PrivacyConfig

```typescript
interface PrivacyConfig {
  pii_detection: {
    layers: ('regex' | 'nlp' | 'slm' | 'presidio')[];
    entity_types: string[];          // From the union of all entity types defined above
    special_category_handling: 'block_or_full_redact' | 'enhanced_protection' | 'disabled';
    safe_harbor_mode?: 'strict';     // HIPAA only
    nric_handling?: 'full_redact';   // Singapore only
    sensitive_pi_handling?: 'enhanced_protection';  // CCPA only
  };
  anonymisation: {
    strength: 'full' | 'safe_harbor' | 'de_identification' | 'anonymisation' | 'placeholder_only';
    reversible: boolean;
    placeholder_format: string;      // e.g., "$t{n}" or "$n"
    special_category_mode?: 'irreversible_redact';
    clinical_data_mode?: 'generic_category';  // HIPAA only
    mapping_table_classification?: 'ephi';     // HIPAA only
    nric_mode?: 'irreversible_redact';         // Singapore only
    sensitive_pi_mode?: 'irreversible_redact'; // CCPA only
    do_not_sell_share?: 'enforce';             // CCPA only
    no_validation?: boolean;                    // Minimal only
  };
}
```

### 12.3 RetentionConfig

```typescript
interface RetentionConfig {
  pii_mappings: string;              // Duration: "24h", "48h", "72h", "unlimited"
  audit_logs: string;                // Duration: "5y", "6y", "7y", "disabled"
  semantic_cache: string;            // Duration: "24h", "30d", "unlimited"
  semantic_cache_clean: string;      // Duration: "90d", "unlimited"
  right_to_erasure: 'enabled' | 'best_practice' | 'disabled';
  right_to_access?: 'enabled';
  right_to_delete?: 'enabled';
  deletion_timeline?: string;        // CCPA: "45d"
  access_response_deadline?: string; // Singapore: "30d"
  disclosure_accounting?: string;    // HIPAA: "6y"
  consumer_request_records?: string; // CCPA: "24m"
}
```

### 12.4 CrossBorderConfig

```typescript
interface CrossBorderConfig {
  mode: 'adequacy_required' | 'adequacy_or_data_protection_test' |
        'all_permitted_with_notice' | 'baa_required' |
        'comparable_protection_required' | 'unrestricted';
  adequacy_list?: string;            // Reference to maintained list
  dpf_required_for_us?: boolean;     // EU GDPR
  uk_us_data_bridge?: boolean;       // UK GDPR
  flexible_assessment?: string;      // UK GDPR DPDI
  app8_assessment_required?: boolean; // Australia
  us_only?: boolean;                 // HIPAA enterprise option
  contractual_obligation_tracking?: boolean;  // Singapore
  nric_transfer_block?: boolean;     // Singapore
  cbpr_accepted?: boolean;           // Singapore
  service_provider_contract_required?: boolean;  // CCPA
  no_checks?: boolean;              // Minimal only
  override_requires: string;         // What documentation is needed for overrides
}
```

### 12.5 ProviderConfig

```typescript
interface ProviderConfig {
  dpa_required?: boolean;            // EU GDPR, UK GDPR
  baa_required?: boolean;            // HIPAA
  baa_status_tracking?: 'enabled';   // HIPAA
  blocked_without_baa?: boolean;     // HIPAA
  service_provider_agreement?: 'recommended' | 'required';  // CCPA
  contractor_certification?: 'optional' | 'required';       // CCPA
  data_intermediary_contract?: 'recommended' | 'required';  // Singapore
  app8_assessment_field?: boolean;    // Australia
  uk_gdpr_terms?: boolean;           // UK GDPR
  ico_registration?: 'recommended' | 'required';            // UK GDPR
  local_models: 'unrestricted';
  companion_devices: 'encrypted_tunnel_required' | 'unrestricted';
  blocked_jurisdictions?: string[];
  no_restrictions?: boolean;         // Minimal only
}
```

### 12.6 AuditConfig

```typescript
interface AuditConfig {
  enabled: boolean;
  log_pii_values: false;             // Always false (except minimal where audit is off)
  log_retention: string;             // Duration
  export_formats: ('pdf' | 'csv' | 'json')[];
  hash_chain: boolean;
  siem_forwarding: 'optional' | 'recommended' | 'required';
  disclosure_log?: boolean;          // HIPAA
  activity_review?: 'enabled';       // HIPAA
  consumer_request_log?: string;     // CCPA — duration
}
```

### 12.7 BreachConfig

```typescript
interface BreachConfig {
  pipeline_failure_action: 'block_and_alert' | 'warn_and_continue';
  outbound_validation: 'enabled' | 'disabled';
  notification_window: string;       // Duration or "expedient"
  assessment_period?: string;        // Duration
  risk_assessment_required?: boolean; // HIPAA
  hhs_notification_threshold?: number; // HIPAA
  ag_notification_threshold?: number;  // CCPA
  significant_scale_threshold?: number; // Singapore
}
```

---

## Appendix A: Entity Type Registry

The following table lists every PII entity type referenced across all presets, which presets require it, and which detection layer handles it.

| Entity type | EU GDPR | AU | HIPAA | CCPA | UK GDPR | SG PDPA | Detection layer |
|-------------|---------|-----|-------|------|---------|---------|-----------------|
| `name` | Yes | Yes | Yes | Yes | Yes | Yes | NLP NER |
| `email` | Yes | Yes | Yes | Yes | Yes | Yes | Regex |
| `phone` | Yes | Yes | Yes | Yes | Yes | Yes | Regex |
| `date_of_birth` | Yes | Yes | Yes | — | Yes | Yes | Regex |
| `address` | Yes | Yes | Yes | Yes | Yes | Yes | Regex + NLP NER |
| `postcode` | Yes | Yes | Yes* | Yes | Yes | Yes | Regex |
| `gps_coordinates` | Yes | Yes | Yes | Yes† | Yes | Yes | Regex |
| `ip_address` | Yes | Yes | Yes | Yes | Yes | Yes | Regex |
| `national_id` | Yes | — | — | — | Yes | — | Regex |
| `ssn` | — | — | Yes | Yes | — | — | Regex |
| `tfn` | — | Yes | — | — | — | — | Regex |
| `abn` | — | Yes | — | — | — | — | Regex |
| `medicare_number` | — | Yes | — | — | — | — | Regex |
| `nric_fin` | — | — | — | — | — | Yes | Regex |
| `nino` | — | — | — | — | Yes | — | Regex |
| `nhs_number` | — | — | — | — | Yes | — | Regex |
| `passport` | Yes | Yes | — | Yes | Yes | Yes | Regex |
| `drivers_licence` | — | Yes | Yes | Yes | Yes | — | Regex |
| `iban` | Yes | — | — | — | Yes | — | Regex |
| `credit_card` | Yes | Yes | — | — | Yes | Yes | Regex |
| `bank_account_au` | — | Yes | — | — | — | — | Regex |
| `uk_sort_code_account` | — | — | — | — | Yes | — | Regex |
| `medical_record_number` | — | — | Yes | — | — | — | Regex + SLM NER |
| `health_plan_id` | — | — | Yes | — | — | — | Regex + SLM NER |
| `health_data` | Yes | Yes | Yes | Yes | Yes | Yes | SLM NER + Presidio |
| `biometric` | Yes | Yes | Yes | Yes | Yes | Yes | SLM NER |
| `genetic_data` | Yes | — | — | Yes | Yes | — | SLM NER |
| `racial_ethnic_origin` | Yes | Yes | — | Yes | Yes | — | SLM NER |
| `political_opinion` | Yes | Yes | — | — | Yes | — | SLM NER |
| `religious_belief` | Yes | Yes | — | Yes | Yes | — | SLM NER |
| `trade_union` | Yes | Yes | — | Yes | Yes | — | SLM NER |
| `sexual_orientation` | Yes | Yes | — | Yes | Yes | — | SLM NER |
| `criminal_data` | Yes | Yes | — | — | Yes | — | SLM NER |
| `diagnosis_code` | — | — | Yes | — | — | — | SLM NER + Presidio |
| `medication_name` | — | — | Yes | — | — | — | SLM NER |
| `household_data` | — | — | — | Yes | — | — | SLM NER |
| `inferences` | — | Yes‡ | — | Yes | — | — | SLM NER |
| `employment_data` | — | — | — | Yes | — | Yes | SLM NER |

\* HIPAA: 3-digit ZIP codes redacted if population < 20,000
† CCPA: "precise geolocation" = within 1,850 feet / 564 metres
‡ Australia: post-2024 amendment "inferred personal information"

---

## Appendix B: Regulatory Update Tracking

Regulations change. loke's preset definitions must be updated when:

- A regulation is amended (e.g., Australian Privacy Act 2024 amendments)
- New adequacy decisions are issued (EU, UK)
- New enforcement guidance is published (ICO, OAIC, PDPC, CPPA, OCR)
- New AI-specific regulations take effect (EU AI Act phases, Colorado AI Act, other US states)

**Update process:**

1. Legal team or compliance officer identifies a regulatory change.
2. Change is documented in an ADR (Architecture Decision Record) under `/docs/adr/`.
3. Preset configuration is updated in the codebase.
4. Release notes document the regulatory change and its effect on the preset.
5. Enterprise administrators are notified via the policy update channel.

**Upcoming regulatory dates to track:**

| Date | Regulation | Change |
|------|-----------|--------|
| Feb 2026 | Colorado AI Act | Full application |
| Aug 2026 | EU AI Act | High-risk AI system requirements (Annex III) |
| Aug 2027 | EU AI Act | High-risk AI in harmonised legislation products (Annex I) |
| TBD 2026 | Australian Children's Online Privacy Code | Expected enforcement |
| TBD 2026 | CPPA final audit regulations | Expected publication |
| Ongoing | US state privacy laws | Connecticut, Virginia, Colorado (privacy), Utah, Iowa, Indiana, Tennessee, Montana, Oregon, Texas, Delaware, New Hampshire, New Jersey, Nebraska, Minnesota, Maryland, Kentucky, Rhode Island, Vermont — all effective by end of 2026 |
