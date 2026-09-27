RG1.3. Tests the production AU Privacy Act preset (`core.policy.presets.auprivacy`) through `core.policy.presets.registry`, `core.policy.loader` and `core.governance.rulesengine`.

Asserts that it loads by name as one regulation carrying every declared rule, under the AU jurisdiction. It also asserts one `apa-t1-` rule for each change the Privacy and Other Legislation Amendment Act 2024 made, and exactly nine of them, each naming the Act. The automated-decision rule must say it is not in force until 10 December 2026, the tort must state its 10 June 2025 start, and the Children's Online Privacy Code must be marked NOT IMPLEMENTED. At least four `apa-t2-proposed-` rules must exist, each beginning "PROPOSED, NOT LAW" and each `log`-only. The old false wording (a "Tranche 1 Act 2024", and the two rules that stated proposals as 2024 law) must be gone, and no rule may claim compliance.

Evaluation: `loader.evaluatepreset` on an enacted rule id yields exactly one violation with that rule's action and severity. A proposal yields `log`, APP 9 yields `block`, and a context naming no rule yields none. Cross-border disclosure is off, and the rules engine derives the `au-privacy-no-cross-border` deny rule from that.

A violation is read only when the result is non-empty, so a missing rule fails an assertion rather than crashing the test.
