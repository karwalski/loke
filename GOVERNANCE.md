# Governance

This document describes how the loke project is governed, how decisions are made, and how contributors can take on greater responsibility.

## Principles

- **Transparency.** Decisions are made in the open. Discussion happens in GitHub issues, pull requests, and RFCs — not in private channels.
- **Merit-based.** Influence comes from contribution quality and consistency, not from title or tenure.
- **Consensus-seeking.** We prefer to reach agreement through discussion. When consensus cannot be reached, maintainers make the final call.
- **Privacy is non-negotiable.** Any decision that weakens loke's privacy guarantees requires an RFC and unanimous maintainer approval.

## Roles

### Contributors

Anyone who submits a pull request, opens an issue, improves documentation, or participates in discussions. All contributors must follow the [Code of Conduct](CODE_OF_CONDUCT.md) and sign off their commits under the [DCO](https://developercertificate.org/).

### Committers

Contributors who have demonstrated sustained, high-quality contributions may be invited to become committers. Committers can:

- Merge pull requests (with at least one approving review from another committer or maintainer)
- Triage and label issues
- Review pull requests

Committer status is granted by maintainer consensus and can be revoked for inactivity (12+ months of no contribution) or conduct violations.

### Maintainers

Maintainers are responsible for the project's direction, release management, and final decision-making. Maintainers can:

- Everything committers can do
- Approve and merge RFCs
- Cut releases
- Manage repository settings and CI/CD
- Grant and revoke committer status
- Make final calls when consensus cannot be reached

### Security Team

A subset of maintainers responsible for handling vulnerability reports (see [SECURITY.md](SECURITY.md)). Security team members have access to private vulnerability reports and coordinate fixes and disclosures.

## Decision-Making

### Day-to-Day Decisions

Most decisions happen through the normal pull request process:

1. Open a PR with your changes
2. Get at least one approving review
3. All CI checks pass
4. Merge

Disagreements on PRs are resolved through discussion. If no consensus is reached, a maintainer makes the call.

### Significant Decisions (RFC Process)

Changes that affect loke's architecture, public API, privacy guarantees, security model, or governance require a formal RFC (Request for Comments).

**What requires an RFC:**

- New core components or removal of existing ones
- Changes to the privacy pipeline's guarantees or behaviour
- New dependency on a GPL-licensed component
- Changes to the policy format or merge semantics
- Breaking changes to the CLI interface or configuration format
- Changes to this governance document

**RFC process:**

1. **Draft.** Author opens a GitHub issue with the `rfc` label using the RFC template. The issue must include: problem statement, proposed solution, alternatives considered, migration path (if breaking), and privacy/security impact assessment.

2. **Discussion.** The RFC is open for community discussion for a minimum of 14 days. All feedback is considered. The author revises the proposal based on feedback.

3. **Decision.** After the discussion period, maintainers vote:
   - **Accept** — the RFC is approved and can be implemented
   - **Revise** — the RFC needs changes before it can be accepted
   - **Reject** — the RFC is declined with a written explanation

4. **Implementation.** Accepted RFCs are tracked as GitHub issues. The author or any contributor can implement the RFC. Implementation follows the normal PR process.

**Privacy-affecting RFCs** require unanimous maintainer approval. All other RFCs require a simple majority.

### Emergency Decisions

Security vulnerabilities and critical bugs may require immediate action without the full RFC process. In these cases, a maintainer can act unilaterally, but must document the decision and rationale in a post-incident write-up within 48 hours.

## Releases

- Releases follow [semantic versioning](https://semver.org/)
- Any maintainer can cut a release
- The pre-release security audit checklist (see `docs/security-audit-checklist.md`) must be completed before every release
- Release notes must include a "You asked, we built" section crediting community feedback that influenced the release

## Amendments

Changes to this governance document require an RFC and unanimous maintainer approval.
