# Grading and rerun plan

Status: proposal, October 24, 2026. This document records follow-up work; it does
not change scoring, start a run, or replace published results.

## What is already implemented

[PR #1](https://github.com/aubwang/weird-ai-bench/pull/1), merged October 7,
added explicit prosody alternatives, syllable-to-note spans (including melisma),
setting-specific stress and phrase boundaries, and consistent pronunciation
within the meter checks. It fixed missing stress positions receiving credit and
introduced scorer v4, judge v5, and changed-input cache invalidation.

The PR explicitly did **not** rescore the published benchmark. The public tree
reviewed at `4479a75d92ca1fc5819510defb9dc21f57b40afd` did not contain a rerun
manifest or completed rerun. Private templates, runs, and
`docs/local/handoff.md` are excluded from Git, so this does not establish whether
a private plan or usable saved outputs exist.

## Changes worth making before a full rerun

### 1. Validate the grader on a small human-checked set

Start with representative contrast pairs: the right syllable count with the
wrong word stress, natural versus strained melisma, an extra syllable in a fast
passage, awkward phrase breaks, and convincing versus strained slant rhymes.
Use synthetic text for public fixtures; keep source-song material local.

Check the accepted deliveries against the score or recording before revealing
model identities. Keep a separate held-out subset to check the final rules.
Record disagreements and estimated pronunciations rather than forcing every
case into a confident pass/fail.

Exact counts alone do not establish singability. As the
[authoring guide](authoring.md#explicit-prosody-settings-and-melisma) explains,
note spans do not encode pitches or durations, rests, pickups, or compression.
A short human sing-through can catch unnatural stresses, breaths, and cramming.
Generated singing may rescue bad lyrics, so use it as a diagnostic, not ground
truth.

### 2. Separate meter from composite adherence

The current [line score](https://github.com/aubwang/weird-ai-bench/blob/4479a75d92ca1fc5819510defb9dc21f57b40afd/weird_ai_bench/orchestrate.py#L107-L119)
combines syllables, stress, rhyme, splits, internal rhyme, and hook checks;
copied lines score zero. Yet
[`meter_by_model`](https://github.com/aubwang/weird-ai-bench/blob/4479a75d92ca1fc5819510defb9dc21f57b40afd/weird_ai_bench/leaderboard.py#L296-L303)
reports that composite adherence under the meter label.

Report these separately:

- Syllable-count accuracy under the declared accepted settings.
- Joint prosody pass rate: one setting and pronunciation satisfy the authored
  count, stress, and phrase checks together.
- Stress and phrase-boundary diagnostics.
- Rhyme quality and originality/copying failures.
- Composite adherence, if retained, clearly labeled as a composite.

Specify denominators, missing-line treatment, and which constraints are actually
annotated. Do not silently average different constraint sets as if they measured
the same thing. Keep copying failures visible so copied text cannot earn an
apparently successful overall result.

The private results-builder was not inspected. This CLI labeling issue is not
proof that the existing published percentages used the wrong calculation.

### 3. Calibrate rhyme and phrasing quality

The [rhyme implementation](https://github.com/aubwang/weird-ai-bench/blob/4479a75d92ca1fc5819510defb9dc21f57b40afd/weird_ai_bench/verify.py#L305-L337)
accepts permissive slants and gives accepted slants full credit. Separate full
rhyme, convincing slant, strained/ambiguous rhyme, and failure. Choose any numeric
weights only after human calibration; do not ban good slant rhyme merely to make
the checker stricter.

Likewise, punctuation at a required syllable boundary is only a proxy for a
natural phrase. Keep the mechanical check, but validate how well it predicts
comfortable delivery.

### 4. Separate creative quality from checker-informed preference

Keep the existing blind identities, family exclusions, and order swaps. Add a
small creative-quality panel that sees the relevant task/reference context but
not automated scores, alongside the existing checker-informed overall judgment.
This reveals whether funny, coherent writing is being confused with compliance.

Include diagnostic contrasts: funny but unsingable, technically compliant but
boring, and well-written but off-premise. Report swapped-order disagreement
separately from genuine indifference, even if the existing ranking model still
encodes it as a tie.

## Smallest sensible rerun sequence

1. **Inventory private inputs.** Check whether templates, raw responses, saved
   run metadata, and the results-builder are available. Do not reconstruct
   missing outputs and label them original.
2. **Freeze the evaluation.** Validate the small human-checked set, pin template
   annotations and grader/judge versions, and resolve the score labels.
3. **Rescore preserved copies first, if outputs survive.**
   [`rescore`](reference.md) rewrites run files. Preserve originals and their
   hashes; work in a separate results directory. Automated rescoring calls no
   model, but fresh pairwise judging may incur API costs. Changed-input caches
   must not stand in for new judgments.
4. **Separate evaluation changes from generation changes.** Rescoring old
   outputs asks whether better evaluation changes conclusions. A new generation
   run under a revised song map asks a different question. Strict-track
   rescoring cannot recreate retries that would have happened under new rules.
5. **Pin a fresh v2 manifest before spending.** Record model/version identifiers,
   prompts, template hashes, guidance, track, retry gates, temperature/reasoning
   settings, sample count, judge panel, and a cost cap. Use enough independent
   samples to inspect ranking stability; repeated lines are not independent
   samples. Keep failed and missing generations in the accounting.
6. **Publish as a versioned comparison.** Preserve v1 and explain which scores
   moved and why. Keep private lyrics, audio, templates, and transcripts local.
   Regenerate the published README section through its existing private builder
   only when the underlying results are ready.

No model selection, spending limit, launch date, or completed validation is
implied by this plan. The immediate next step is the input inventory and a small
grader-calibration set, not an expensive full benchmark.
