# Task: Analyze Existing Datasets for Deepfake Detector Training Pipeline

## Goal
Analyze three existing deepfake/video datasets to design a first-stage pipeline for creating a balanced real→fake dataset suitable for training a state-of-the-art deepfake detector.

## Dataset Locations
1. `X:\dataset_3`
2. `X:\dataset2`
3. `X:\DEEPFAKE_DATASETS`

**Note**: Some datasets include JSON metadata files that should be leveraged for analysis.

## Processing Pipeline
- **Pipeline Location**: `W:\workspace_11_custodire_pipeline_v1.6`
- **Purpose**: This pipeline processes selected real videos to create clips
- **Critical Constraint**: We CANNOT run all videos through the pipeline
  - Some datasets have disproportional data that would create bias
  - Running everything would give skewed/biased results
  - **Strategy Required**: Select a DIVERSE subset from the datasets

## Diversity Sampling Strategy (CRITICAL)
⚠️ **The agents MUST design a sampling strategy that:**
- Identifies diversity axes in the existing datasets (demographics, quality, lighting, sources, etc.)
- Detects disproportional categories (e.g., if 80% of videos are one type)
- Recommends balanced sampling to avoid bias
- Specifies HOW MANY videos to select from WHICH categories
- Ensures the selected subset represents the full diversity without overrepresenting any single type

**Example**: If dataset_3 has 1000 videos but 800 are indoor selfies and 200 are outdoor interviews:
- ❌ BAD: Process all 1000 → 80% indoor bias
- ✅ GOOD: Process 100 indoor + 100 outdoor → balanced representation

## Analysis Requirements

### 1. Dataset Discovery & Inventory
- Scan all three dataset directories recursively
- Identify video files (mp4, avi, mov, mkv, etc.)
- Find and parse any JSON metadata files
- Extract:
  - Total file counts per dataset
  - Video formats and codecs
  - Resolution distribution
  - Duration statistics
  - Any existing labels (real/fake, manipulation type, etc.)
  - Folder structure and naming conventions

### 2. Real Video Assessment
Identify and catalog REAL videos suitable for:
- Extracting 10-second clips
- Serving as source material for fake generation
- Coverage across:
  - Demographics (age, gender, ethnicity if detectable)
  - Lighting conditions (indoor/outdoor, varied lighting)
  - Video quality (resolution, bitrate)
  - Head poses and movements
  - Background complexity
  - Camera types/sources

### 3. Existing Fake Video Assessment
If fake videos exist in these datasets:
- Catalog manipulation methods used (if labeled)
- Note quality levels
- Identify generators used (FaceSwap, DeepFaceLab, GANs, etc.)
- Assess temporal consistency
- Note any artifacts or tells

### 4. Pipeline Design Recommendations
Based on analysis, propose:

**Stage 1: Real Clip Extraction**
- Selection criteria for source videos
- Clip extraction strategy (10-sec segments)
- Diversity sampling approach
- Quality filters
- Deduplication strategy

**Stage 2: Fake Generation Plan**
- Which real clips to use as sources
- Which fake generators to employ
- Parameter variations for each generator
- How to ensure diversity in fakes

**Stage 3: Dataset Construction**
- Train/val/test split strategy
- Balancing real vs fake
- Diversity requirements per split
- Metadata/manifest format
- Append-only promotion via ingest.promote

## Deliverables

### 1. Analysis Script (`workspace/analyze_datasets.py`)
Python script that:
- Scans all three dataset directories
- Parses JSON metadata where available
- Generates comprehensive statistics
- Outputs analysis report to `staging/dataset_analysis/`

### 2. Analysis Report (`staging/dataset_analysis/report.json`)
JSON report containing:
```json
{
  "datasets": {
    "dataset_3": {
      "total_videos": N,
      "real_videos": N,
      "fake_videos": N,
      "formats": {...},
      "resolutions": {...},
      "durations": {...},
      "metadata_files": [...],
      "recommendations": {...}
    },
    "dataset2": {...},
    "DEEPFAKE_DATASETS": {...}
  },
  "pipeline_recommendations": {
    "stage1_real_selection": {...},
    "stage2_fake_generation": {...},
    "stage3_dataset_assembly": {...}
  },
  "diversity_gaps": [...],
  "quality_concerns": [...]
}
```

### 3. Recommended Real Video Manifest (`staging/dataset_analysis/real_sources.jsonl`)
JSONL file listing SAMPLED real videos for processing through pipeline at `W:\workspace_11_custodire_pipeline_v1.6`:
```jsonl
{"path": "X:/dataset_3/...", "duration": 120, "resolution": "1920x1080", "category": "outdoor_interview", "reason": "high quality, diverse lighting, underrepresented category", "extract_clips": 12}
```

### 4. Diversity Balance Report (`staging/dataset_analysis/diversity_balance.json`)
Analysis showing:
- Original dataset distributions (what we have)
- Identified biases (overrepresented categories)
- Recommended sampling quotas (how many from each category)
- Target balanced distribution
- Rationale for sampling decisions

## Constraints
- Read-only access to source datasets (X:\ locations)
- All analysis outputs in `staging/dataset_analysis/`
- Script in `workspace/` (can be edited/refined)
- Use tools: fs.write, fs.append (for outputs)
- No container needed unless you want to use ffmpeg for detailed video analysis
- Total analysis runtime: aim for <30 minutes

## Success Criteria
✅ All three datasets scanned and inventoried
✅ Real videos identified and assessed for suitability
✅ Existing fakes (if any) cataloged with methods
✅ Diversity gaps identified
✅ Clear pipeline recommendations for:
   - Which videos to use as real sources
   - How many 10-sec clips to extract per video
   - Which fake generators to use
   - How to balance the final detector training dataset
✅ Analysis outputs ready for review in staging/

## Expected Agent Verdict
Agents should discuss and reach consensus on:

1. **Dataset Composition**:
   - What categories/types exist in each dataset?
   - Which categories are overrepresented (bias risk)?
   - Which categories are underrepresented (need more)?

2. **Sampling Strategy**:
   - HOW MANY total videos to select for pipeline processing?
   - WHICH categories to sample from and in what proportions?
   - Specific quotas per category to achieve balance
   - Example: "Select 500 total: 100 indoor_neutral_lighting, 100 outdoor_bright, 100 indoor_low_light, 100 outdoor_interviews, 100 mixed_settings"

3. **Pipeline Input Recommendation**:
   - Concrete list of videos to feed into `W:\workspace_11_custodire_pipeline_v1.6`
   - Expected output: X clips suitable for fake generation
   - Diversity validation: Does this sample avoid bias?

4. **Fake Generation Strategy**:
   - Which generators to use on the selected clips
   - How to ensure fake diversity matches real diversity

5. **Gaps & Risks**:
   - What diversity axes are missing entirely?
   - What biases remain even after sampling?
   - What additional data collection is needed?

## Notes
- This is an analysis task, not execution yet - we're planning the pipeline
- Agents should be thorough but practical
- Focus on what will actually help train a robust deepfake detector
- Consider the insights from our earlier Codex conversation about dataset diversity
