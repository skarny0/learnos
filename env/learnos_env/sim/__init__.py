"""Simulated learner.

Two layers, strictly separated:
  dynamics.py  - numeric hidden-state updates. Pure Python/numpy, seeded. The ONLY
                 thing that touches LearnerState. Reproduces known effects (see
                 docs/environment-spec.md §6) and is checked by validate.py.
  renderer.py  - turns a sampled outcome + coarse state bins into student text
                 (a reply, a quiz answer wording). Template-first; an LLM may
                 paraphrase, but never decides correctness or updates state.
  validate.py  - behavioural checks against real data / published effect sizes.
"""
