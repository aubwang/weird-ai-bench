# Working benchmark protocol

This is the working profile for new craft-guided experiments. It is an experimental setup, not a change to the published leaderboard or a claim that text judging establishes singing quality. Keep older templates and results available as baselines.

## Writer setup

- Use a reviewed template with explicit line counts, rhyme groups, source reference, and score-derived rhythm where available. Describe omissions or rearrangements; an excerpt is not a full performance.
- Use `--track freeform --guidance full --rhythm beats --retries 0`. There is one writing attempt per turn. Keep declared template gates and tolerances unchanged across comparisons.
- Put source-device descriptions in `craft_notes`. Notes describe rhetorical or musical structure, not new jokes or proposed answers. Any one cue may change, but enough other features should keep the lyrics recognizable as a transformation of the source.
- Match writer models, singer roles, scenario, effort, token limit, temperature and sampling policy across arms. When studying one model, give that same model each singer role rather than inadvertently sweeping mixed-model lineups.
- Keep calibration examples and human-written answers out of writer prompts. Inspect and save the actual prompts before generation.

A free, synthetic prompt preview:

```sh
uv run weird-ai-bench run \
  --spec examples/rhythm.yaml --scenario none \
  --model provider/model --names assigned --persona 'Singer 1' \
  --track freeform --guidance full --rhythm beats --retries 0 \
  --effort medium --max-tokens 32000 --dry-run
```

The example has one singer. For a two-singer template, supply two `--model` and two `--persona` arguments. The provider/model placeholder is suitable for this offline preview only.

## Judge setup

The rubric belongs inside the judge prompt. Feedback explains the judgment; it is not a second numerical score. Keep humor, recognizable transformation, coherence, and the applicable melody-fit/interplay criteria explicit. A funny rewrite may receive weak craft credit if it loses the source's identity; retaining source phrases without changing their point should also earn weak craft credit.

Compare complete songs blindly with judges from different model families than the writers. Show each pair in both orders. A judge whose two votes disagree contributes a tie. Report each judge separately; any consensus rule must be declared before collecting judgments. Keep invalid or missing responses unresolved rather than silently counting them as valid ties. Save failed generation attempts and apply the declared forfeit policy.

For a treatment comparison, use one common judging endpoint for both arms and document it. The standard mixed-comparison path preserves each song's original criteria, which is a different question. Do not silently replace saved template snapshots to force content groups together. Historical baselines can be reused for an exploratory comparison, but model/provider changes and arbitrary pairing of independent samples remain limitations.

## Report separate outcomes

- **Judged preference:** pair outcomes, order sensitivity, inter-judge disagreement and concrete explanations. These are opinions under a declared rubric.
- **Mechanical adherence:** counts and denominators for syllables, stress, rhyme, structure and copying flags. These checks retain their configured gate roles; calling them diagnostics does not switch gates off. They do not prove singability.
- **Human recognition, when available:** the exact question and yes/no/unsure responses. Keep unsure separate. A chorus recognition rating is not an overall full-song preference or permission to copy.
- **Cost and failures:** all attempted jobs, saved partial outputs, successful-call costs and any missing usage information.

Do not blend judged preference with mechanical adherence into an arbitrary 50/50 result. The judge already sees the diagnostics. The legacy per-song rubric mode can emit a `singability_blended` side field; this working profile uses pairwise preferences and does not rank on that field. Preserve existing originality checks and report increased source overlap as a trade-off, not automatically as successful recognition.

## Reproducibility

Freeze the templates, scenario, criteria text, source-code revision or hashes, dependency lockfile, model IDs, full settings, initial prompts, pair schedule, and analysis rules before paid calls. A content hash identifies that packet; saved snapshots preserve what a run used. Refuse a mismatched packet and create a new version when the setup changes. This reproduces inputs and offline analysis, not stochastic provider responses.

Keep private song assets, exact private run manifests and human feedback in the gitignored local folders described in `AGENTS.md`. Public examples must remain synthetic. Do not publish the exploratory results as a stable ranking or pool different songs and treatment groups without an explicit analysis design.
