# Simplification backlog

Raised by Sam, 2026-08-29, during Project 1 Module A.

## The concern

The pipeline has become deep. Module A alone reproduces the open-data skeleton of
a product Metsa has refined over decades: area-based regression and k-NN
imputation from ALS, a Sentinel-2 spectral composite, spatially-blocked
cross-validation, a circularity probe, and a benchmark against MS-NFI 2023. That
is a lot of theory and method for a portfolio piece whose author is coming to
forest inventory new and will be learning it *backwards* from the code in order
to explain it at interview.

It very likely sits above what a lower-seniority hire would be expected to
produce or fully defend on day one. The counter-point: the roles being targeted
(analytics / pipeline, category 2.5-3) compete against people with several years
of GIS experience, so some depth is the point. The risk is not the depth itself
but **being unable to explain it plainly**.

## Decision

Finish Project 1 as currently planned. Do **not** slim anything down mid-build.

After the project is complete and the layered write-ups exist (one-line summary,
then per-module plain-language explanations, then the per-function / per-statistic
detail), revisit this: produce a **slimmed-down, simplified version** that a
newcomer can hold in their head and narrate end to end - fewer methods, the same
shape, the headline result intact. Likely form: one attribute (total volume), one
method (the sqrt-OLS area-based model), ALS + one spectral index, a single
train/test split, one validation figure. The full version stays as the "here is
how far it can go" artefact.

## When and the decision path (agreed 2026-08-29)

Project 1 complete -> then, in order:

1. **Focus on genuinely learning Project 1 well** - the layered write-ups, then
   Sam working through them until he can narrate every module cold.
2. **If that lands inside the timeframe:** move on to Project 2 (which may itself
   be built deliberately leaner and better-explained from the start).
3. **If it does not:** carve the parts Sam does understand - one attribute (total
   volume), sqrt-OLS ABA, ALS + one spectral index, one train/test split, one
   figure - into their own standalone project and present that instead. The full
   Project 1 stays as the "how far it can go" artefact but is not the thing led
   with.

Not before Project 1 is done. No slimming mid-build.
