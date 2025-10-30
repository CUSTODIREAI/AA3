# Dataset Analysis Verdict

## Findings
- Total videos across 3 datasets: 41192
- Real videos suitable (≥10s, ≥720p): 0
- Fake videos: 10475

## Detected Biases
1. Environment: unknown 99%, outdoor 1%, indoor 0% (BIAS: overrepresented: unknown; underrepresented: outdoor, indoor)
1. Shot_type: other 81%, talking_head 18%, interview 1%, selfie 0% (BIAS: overrepresented: other; underrepresented: interview, selfie)
1. Lighting: neutral 99%, low 1%, bright 0% (BIAS: overrepresented: neutral; underrepresented: low, bright)
1. Quality: mq 100%, lq 0%, hq 0% (BIAS: overrepresented: mq; underrepresented: lq, hq)

## Recommended Sampling
- Target: 85 videos (balanced across axes)
- Quotas:
  - outdoor:other:neutral → 1 videos
  - unknown:other:neutral → 82 videos
  - unknown:talking_head:neutral → 2 videos

## Expected Output
- 85 selected videos → ~85 10-second clips
- Feed to W:\workspace_11_custodire_pipeline_v1.6
- Generate 2 fakes per real clip → ~170 fake clips
- Final dataset: 85 real + 170 fake = 255 clips for detector training

## Pipeline Input Recommendation
- Use real_sources.jsonl as manifest of real inputs
- Selection criteria: composite quotas in diversity_balance.json
- Diversity validation: compare axis distributions pre/post via report.json vs selected_counts

## Fake Generation Strategy
- Use multiple generators (e.g., faceswap, GAN-based, neural rendering) with proportions mirroring real composite quotas
- Maintain per-category parity: for each real composite bin, synthesize fakes in same proportion
- Vary identity pairs, compression levels (hq/mq/lq), and lighting to match real distributions

## Identified Gaps
- Missing diversity axes may include pose/extreme motion; consider sourcing more such clips if underrepresented
- Remaining biases after sampling highlighted in axis_overrepresented; seek additional data for categories <10% where feasible

## Verdict: FEASIBLE with sampling strategy applied
Datasets contain sufficient diversity IF properly sampled; without sampling, training may skew towards dominant categories.
