# Task: Autonomous Dataset Analysis and Sampling Verdict

## Goal
FULLY AUTONOMOUSLY analyze three datasets, execute the analysis, and provide a concrete verdict on dataset composition and sampling strategy for deepfake detector training.

## Critical Requirement: FULL AUTONOMY
⚠️ **This task must be completed WITHOUT human intervention**
- Create analysis tools
- EXECUTE the analysis
- Review results
- Provide verdict with REAL DATA (not placeholders)

## Dataset Locations
1. `X:\dataset_3`
2. `X:\dataset2`
3. `X:\DEEPFAKE_DATASETS`

## Processing Pipeline Context
- **Pipeline**: `W:\workspace_11_custodire_pipeline_v1.6`
- **Constraint**: Cannot process ALL videos (causes bias from disproportional data)
- **Required**: Select balanced, diverse subset

## Required Actions (All Must Execute Autonomously)

### Phase 1: Create Analysis Tool
Write Python script to:
- Scan all 3 dataset directories recursively
- Identify video files and JSON metadata
- Extract: counts, formats, resolutions, durations, labels (real/fake)
- Categorize by: environment (indoor/outdoor), shot_type (selfie/interview/etc), lighting, quality
- Detect biases (categories >60% = overrepresented)
- Compute balanced sampling quotas

### Phase 2: EXECUTE Analysis (Must Happen in Plan)
**CRITICAL**: Your plan must include an action that RUNS the analysis script!

Use `exec.container_cmd` or direct execution to:
```bash
python workspace/analyze_datasets.py
```

This will generate REAL statistics in `staging/dataset_analysis/`

### Phase 3: Review Results and Give Verdict
After execution, review the ACTUAL results and provide:

**Dataset Composition Verdict:**
- What categories exist in each dataset?
- Which are overrepresented (>60%)?
- Which are underrepresented (<10%)?
- Total real videos available

**Concrete Sampling Strategy:**
- SPECIFIC number of videos to select (e.g., "Select 437 videos")
- EXACT quotas per category (e.g., "indoor:selfie → 45, outdoor:interview → 67")
- Rationale for each quota based on REAL distributions found

**Pipeline Input Recommendation:**
- List of specific video paths OR selection criteria
- Expected clip output (e.g., "~3,200 10-second clips")
- Diversity validation metrics

**Fake Generation Strategy:**
- Which generators to use with what proportions
- How to ensure fake diversity matches real diversity

**Identified Gaps:**
- Missing diversity axes
- Remaining biases after sampling
- Additional data needs

## Deliverables (Created AND Populated)

1. **`workspace/analyze_datasets.py`** - Analysis script
2. **`staging/dataset_analysis/report.json`** - REAL statistics (not placeholders!)
3. **`staging/dataset_analysis/real_sources.jsonl`** - Concrete video selections
4. **`staging/dataset_analysis/diversity_balance.json`** - Real distributions + quotas
5. **`staging/dataset_analysis/verdict.md`** - Human-readable verdict summary

## Example Verdict Format

```markdown
# Dataset Analysis Verdict

## Findings
- Total videos across 3 datasets: 4,237
- Real videos suitable (≥10s, ≥720p): 2,891
- Fake videos: 1,346

## Detected Biases
1. **Environment**: Indoor 72%, Outdoor 28% (BIAS: indoor overrepresented)
2. **Shot Type**: Selfie 68%, Interview 22%, Other 10% (BIAS: selfie dominant)
3. **Lighting**: Neutral 81%, Low 12%, Bright 7% (BIAS: neutral dominant)

## Recommended Sampling
- **Target**: 520 videos (balanced across axes)
- **Quotas**:
  - indoor:selfie:neutral → 45 videos (cap overrepresented)
  - outdoor:interview:bright → 80 videos (boost underrepresented)
  - indoor:interview:low → 65 videos (boost underrepresented)
  - [... specific quotas for each category]

## Expected Output
- 520 selected videos → ~4,200 10-second clips
- Feed to W:\workspace_11_custodire_pipeline_v1.6
- Generate 2 fakes per real clip → 8,400 fake clips
- Final dataset: 4,200 real + 8,400 fake = 12,600 clips for detector training

## Verdict: FEASIBLE with sampling strategy applied
Datasets contain sufficient diversity IF properly sampled. Without sampling,
training would be biased toward indoor selfies with neutral lighting.
```

## Success Criteria

✅ Analysis script created in `workspace/`
✅ Analysis EXECUTED (script ran, not just written)
✅ Real statistics generated (not placeholders)
✅ Concrete sampling quotas with REAL numbers
✅ Verdict based on ACTUAL dataset composition
✅ All outputs promoted to dataset/ with manifest entries

## Constraints

- Read-only access to source datasets (X:\ locations)
- Writable: `workspace/`, `staging/`
- Protected: `dataset/` (append-only via ingest.promote)
- No privileged Docker
- Use tools: fs.write, fs.append, exec.container_cmd (to RUN the script), ingest.promote
- If ffprobe unavailable, analyze based on filenames/paths/JSONs only

## Notes for Agents

**Proposer**: Your plan MUST include:
1. Action to write the analysis script
2. Action to EXECUTE the script (exec.container_cmd or similar)
3. Action to write verdict based on results
4. Action to promote all outputs

**Critic**: Verify the plan includes EXECUTION, not just script creation.
The plan should produce REAL data, not placeholders.

**Both**: This is the test of true autonomy. Complete the full loop without human help.
