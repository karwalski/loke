RG1.2. Tests the production APRA CPS 230 preset (`core.policy.presets.apracps230`) through `core.policy.presets.registry`, `core.policy.loader` and `core.governance.rulesengine`. Paragraph numbers are those of the 2026 instrument (F2026L00475), in force from 1 July 2026.

Asserts that it loads by name as one regulation carrying all 36 declared rules. Every rule must be classed (exactly 4 evaluable and 6 unimplemented), cite a `CPS 230 para`, and every documentation-only rule must be `log`. Each paragraph in `requiredparas()` must be cited. That is every entity requirement except para 27 (an entity providing a material service) and APRA's own powers.

Named requirements: paras 48 and 49, a model provider as a candidate material service provider; paras 14 and 52, an evaluable provider deny; the 72-hour (para 32), 24-hour (para 41) and 20-business-day (para 60) notifications; continuity and critical operations as the entity's; degrade-to-local named unimplemented and unvalidated; the missing register; the absence of request-path enforcement; both commencement dates and the instrument cited.

Each evaluable rule is checked against its field: the `*` provider denied with `requiresdpa`, local allowed to restricted, the budget blocking with a non-zero limit, `crossborderallowed` false, and the rules engine's derived `apra-cps-230-no-cross-border` deny.

Evaluation: every rule evaluated by its own id yields exactly one violation with its own id and action. The offshoring rule blocks at high, and an unrelated context yields none. Stale wording ("fails OPEN", local degradation as "the real" continuity control, "Nothing calls the metrics collector") and compliance claims must be absent.

Mutant (2026-10-01): removing `cps230-materiality-determined-by-entity` failed 3 assertions (rule count, para 49 cited, the paras 48 and 49 rule).
