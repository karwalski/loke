# loke — Human-Centred Design Principles

**License:** Apache 2.0
**Document type:** Living document — updated as we learn from users

---

## The Starting Point

loke exists to help people do the right thing without having to think about it.

Not because they're irresponsible. Because the landscape of rules, regulations, costs, and privacy obligations is so fragmented and fast-moving that no individual can reasonably be expected to navigate it alone while also doing their actual job. The person using loke shouldn't need to know whether their data falls under GDPR Article 17 or the Australian Privacy Act Schedule 1. They shouldn't need to mentally calculate whether this prompt will blow their monthly token budget. They shouldn't need to remember which client's data can go to which LLM provider.

loke remembers so they don't have to.

The product's job is to keep people between the lines — gently, clearly, and without getting in the way — so they can focus on the work that matters to them.

---

## What We Mean by "Between the Lines"

Staying between the lines means operating safely within boundaries the user may not even be fully aware of. loke tracks four categories of lines:

**Regulatory lines.** Data protection laws, industry regulations, cross-border transfer rules, AI-specific legislation. These change by jurisdiction, by industry, and over time. loke defaults to the most restrictive applicable standard and loosens only when the user or their organisation explicitly configures otherwise.

**Organisational lines.** Enterprise data policies, acceptable use policies, approved vendor lists, classification schemes, retention requirements. These are set by the user's employer or team and enforced locally on the user's device — not by a cloud service the organisation has to trust.

**Cost lines.** Token budgets, subscription limits, per-model pricing thresholds. loke helps users understand what things cost before they spend, and prevents accidental overspend without blocking legitimate work.

**Ethical lines.** The harder category. Sending someone's medical data to a cloud LLM without anonymisation isn't illegal in every jurisdiction, but it's not the right thing to do. loke defaults to treating data with the care the person it belongs to would want, not the minimum the law requires.

When any of these lines are about to be crossed, loke tells the user clearly, explains why, and offers alternatives. It never silently blocks without explanation. It never silently allows what it knows is risky.

---

## Core Design Principles

### 1. The User Is the Authority

loke advises. The user decides.

Every warning, suggestion, and default can be understood, questioned, and overridden by the user. loke is not a gatekeeper — it's a guide. If a user reads the warning, understands the risk, and chooses to proceed, that's their right. loke logs the decision (for their own records and audit trail) and gets out of the way.

The only exception: enterprise policy hard blocks. If the user's organisation has set a policy that certain data must never leave the device, loke enforces that. But it tells the user exactly what's happening and why, and gives them a path to escalate (contact their admin, request an exception). No silent black boxes.

**In practice:** Every intervention by loke includes three things: what's happening, why it matters, and what the user can do about it.

### 2. We Don't Know What This Product Should Look Like Yet

This is the most important principle in this document.

loke has a clear mission (help people stay between the lines) and a clear technical architecture (local-first privacy, token optimisation, intelligent routing). But we do not presume to know what the right interface is, what features matter most, or how users will actually want to work.

The MVP exists to learn, not to ship a finished product.

Every design decision in the MVP is a hypothesis. We test hypotheses with real users, measure what they actually do (not just what they say), and adapt. Features that users love stay and grow. Features that users ignore or dislike get reworked or removed. Features we never imagined get built because users ask for them.

**What this means practically:**
- No feature is sacred. Everything is revisable.
- Ship the smallest useful version of each feature, then iterate.
- Build measurement and feedback into the feature itself, not as an afterthought.
- The roadmap is a living document, not a contract.
- We'd rather ship something imperfect that teaches us something than delay for polish that might be wasted.

### 3. Feedback Is a First-Class Feature

User feedback is not a nice-to-have bolted on at the end. It is a core product capability, built into every interaction, every screen, and every output.

**Thumbs up / thumbs down on everything.** Every LLM response, every routing decision, every anonymisation result, every warning, every suggestion — the user can give a quick thumbs up or thumbs down. One tap. No friction.

**Thumbs down always invites a comment.** When a user gives a thumbs down, a lightweight comment box appears. Not a modal. Not a form with required fields. Just a text input with a prompt: "What went wrong?" and a send button. If they want to type nothing and just send the thumbs down, that's fine too. The signal alone is valuable.

**Feedback goes directly into the development pipeline.** Thumbs-down-with-comment creates a structured feedback item that feeds into the project's issue tracker. Not a black hole. Not a "we'll review feedback quarterly" process. Every piece of feedback is triaged, and the user can optionally receive a response.

**Feedback is visible and respected.** Users should be able to see that their feedback led to change. A "You asked, we built" section in release notes. A feedback status tracker if they want one. The message is: your input shapes this product.

**Specific feedback surfaces:**

| Surface | What's Rated | Why It Matters |
|---------|-------------|----------------|
| LLM response | Quality of the answer | Trains routing — was the right model selected? |
| Anonymisation preview | Accuracy of PII detection | Were real entities missed? Were non-entities flagged? |
| Routing decision | Was the right model chosen? | Improves the router over time |
| Warning/intervention | Was this helpful or annoying? | Calibrates sensitivity — too many false alarms erode trust |
| Compression result | Did the compressed prompt lose meaning? | Tunes compression aggressiveness |
| Cost estimate | Was the estimate accurate? | Improves budgeting |
| Overall session | How was the experience? | General product health |

### 4. Do the Right Thing by Default

loke's defaults are chosen not by what's easiest to implement, or what's most permissive, or what looks best in a demo — but by what's right for the person whose data is being handled.

- **Default: anonymise.** Unless the user or their policy explicitly says otherwise, PII is replaced before it leaves the device.
- **Default: local first.** If a local model can handle the task adequately, use it.
- **Default: most restrictive regulation.** Until the user tells us their jurisdiction and industry, assume the strictest applicable rules.
- **Default: transparent.** Show the user what's happening. Don't hide the pipeline behind a loading spinner.
- **Default: cautious on cost.** Don't route to an expensive model when a cheap one will do.

### 5. Warnings Must Be Earned

Every warning loke shows costs the user a small amount of trust and attention. If loke warns too often about things that don't matter, users learn to ignore warnings — and then miss the ones that do matter.

**The warning budget is finite.** Treat it like a resource. Every warning must clear a bar:
- Is this something the user can act on?
- Is the consequence of ignoring it meaningful?
- Is this the right moment to show it?

**Graduated severity:**
- **Info** (non-interruptive): shown in pipeline view, logged.
- **Advisory** (subtle): small indicator in the UI, dismissible.
- **Warning** (requires acknowledgement): clear banner.
- **Block** (requires action): cannot proceed without decision.

### 6. Complexity Is Available, Not Imposed

Most users, most of the time, should be able to use loke without understanding its internals.

**Layer 0 (default):** "Your prompt was processed and sent. Here's the response."
**Layer 1 (one click deeper):** "3 PII entities anonymised, prompt compressed by 40%, routed to Qwen-9B locally."
**Layer 2 (dig in):** Full pipeline view — every stage, every decision, every entity detected.
**Layer 3 (expert):** Raw request/response payloads, timing data, model confidence scores, cache state, MCP call traces.

### 7. Speed Is a Feature

Privacy and token optimisation are meaningless if the tool is so slow that users bypass it.

**Targets:**
- Pipeline overhead (anonymise + compress + route): < 1 second for typical prompts
- Intent classification: < 10ms
- First response token streaming: < 2 seconds after pipeline (network-dependent)
- UI interactions (tab switch, menu open, panel toggle): < 100ms

### 8. Privacy Is Not a Feature — It's the Foundation

We don't market privacy as a selling point any more than a bank markets "we don't steal your money." Privacy is the baseline. Everything is built on top of it.

---

## Design Patterns

### The Guardrail Pattern

When loke detects a user is about to cross a line, it doesn't block — it guides. Says what was detected, explains why it matters, offers a safe path forward, and allows override with informed consent. Never lectures or moralises.

### The Scorecard Pattern

Ambient awareness of how the user is tracking against their lines: privacy, cost, compliance, local ratio. Always visible or queryable, never a warning.

### The Explain-It-To-Me Pattern

Any action loke takes should be explainable in plain language on demand. Conversational explanations, not debug logs.

### The Undo Pattern

Where possible, make actions reversible. For destructive actions, require confirmation with a clear statement of what will be lost.

---

## MVP Success Criteria

- Users who install it keep using it after one week (retention > 40%)
- Users give more thumbs up than thumbs down (satisfaction > 70%)
- Users submit feedback comments (engagement > 5% of thumbs-down)
- Token savings are measurable and reported to the user
- Zero PII leakage incidents (pass/fail)
- Users tell other people about it (organic growth)

---

## Iteration Cadence

- **Weekly:** Review all feedback submissions. Group into themes. Identify quick wins.
- **Fortnightly:** Ship a release. Every release includes at least one "you asked, we built" item.
- **Monthly:** Review metrics. Reassess priorities. Adjust the roadmap.
- **Quarterly:** Broader retrospective. Are we solving the right problems?

---

## Living Document

This document will change. It should change. As we learn from users, some principles will be reinforced, some will be refined, and some may be wrong. The only principle that doesn't change is the commitment to listening to users and adapting.

Every change to this document should be accompanied by the reason it changed — what we learned, from whom, and how it shifted our thinking.
