# Human Evaluation Rubric (SFT vs SFT+DPO)

Use this rubric while scoring `blind_eval_sheet.csv`.

## Axes (1-5)

1. `naturalness_score_1_5`
- 1: robotic, unnatural flow
- 3: acceptable but uneven
- 5: natural and fluent

2. `factuality_score_1_5`
- 1: many factual errors
- 3: mixed quality
- 5: mostly correct

3. `helpfulness_score_1_5`
- 1: does not solve user intent
- 3: partially useful
- 5: directly useful and complete

4. `fluency_score_1_5`
- 1: grammar/cohesion issues
- 3: understandable with minor issues
- 5: clean and coherent Turkish

5. `hallucination_flag_0_1`
- 0: no clear hallucination
- 1: contains hallucinated claims

## Acceptance Gate

Promote `SFT+DPO` only if:

- Mean naturalness score improves vs baseline and SFT
- Mean helpfulness score improves vs baseline and SFT
- Hallucination flag rate does not increase
- Long-form prompts show fewer truncation/repetition artifacts
