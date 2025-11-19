# AI Recruiter Research Repository

This repository contains research tools, data, and analyses for studying AI-powered recruiting processes. The project focuses on comparing AI-assisted recruitment with traditional manual methods through controlled experiments, analyzing candidate outcomes, and evaluating the effectiveness of AI tools in the hiring pipeline.

## 📋 Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [Key Components](#key-components)
- [Getting Started](#getting-started)
- [Data Organization](#data-organization)
- [Analysis Scripts](#analysis-scripts)

## 🎯 Overview

This research repository investigates:

- **AI vs. Manual Recruitment**: Controlled experiments comparing AI-assisted and manual recruitment pipelines
- **Candidate Outcomes**: Analysis of job finding rates, interview outcomes, and candidate satisfaction
- **Treatment Effects**: Statistical analysis of Average Treatment Effects (ATE) and heterogeneous treatment effects
- **Resume Vetting**: Evaluation of AI-powered resume scoring and skill assessment
- **LinkedIn Profile Analysis**: Tools for scraping and analyzing LinkedIn profiles
- **NPS Analysis**: Candidate experience and Net Promoter Score evaluation

## 📁 Repository Structure

```
AI_recruiter_internal/
│
├── 📊 src/                          # Main analysis scripts (R)
│   ├── ate.R                       # Average Treatment Effect analysis
│   ├── ate_clean.R                 # Cleaned ATE analysis
│   ├── droppingout.R               # Dropout analysis and predictions
│   ├── who_benefits.r              # Heterogeneous treatment effects
│   ├── all_linkedin_analysis.R     # LinkedIn profile analysis
│   ├── embeds_analysis.R           # Embedding analysis
│   ├── skill_vetting.R             # Skill assessment analysis
│   ├── decomposition.R             # Oaxaca decomposition
│   ├── transcripts.R               # Interview transcript analysis
│   ├── linkedin_jobs.R             # LinkedIn job analysis
│   ├── MDE.R                       # Minimum Detectable Effect
│   ├── randomization_exp2.R        # Experiment 2 randomization
│   ├── figures/                    # Generated figures and plots
│   └── linkedin/                   # LinkedIn scraping tools
│       ├── scrapers/               # Production scrapers
│       ├── parsers/                # Profile parsers
│       ├── utils/                  # Utility scripts
│       └── applescripts/           # Safari automation scripts
│
├── 🧪 experiments/                  # Experimental data and scripts
│   ├── resume_vetting/             # Resume scoring experiments
│   │   ├── Ai-Vetted-ranked.csv
│   │   ├── Manual-Resume-ranked.csv
│   │   └── resume_vetting_experiment.py
│   ├── ai_interviews/              # AI interview analysis
│   │   ├── ai_interview_quality.py
│   │   └── ai_transcripts_incoming.csv
│   └── embeddings/                 # Embedding experiments
│
├── 📈 data/                         # Research datasets
│   ├── experiment_2/               # Second experiment data
│   │   ├── math_phd_v1*.csv
│   │   └── math_phd_v2*.csv
│   ├── linkedin/                   # LinkedIn profile data
│   │   ├── *.csv                   # Parsed profiles
│   │   └── *.html                  # Raw HTML profiles
│   ├── treatment_linkedin_urls.csv
│   ├── control_linkedin_urls.csv
│   └── *.csv                       # Various analysis datasets
│
├── 🔬 micro1-controll-experiment-EDA/  # Controlled experiment analysis
│   ├── controlled_experiment_EDA.ipynb
│   ├── job_101(AI)_w_age_gender.csv    # AI pipeline data
│   ├── job_110(Manual)_w_age_gender.csv # Manual pipeline data
│   └── top_candidates_interviewed.csv   # Final interview outcomes
│
├── 📊 auditing_algorithm/          # Algorithm auditing
│   ├── Human vs. AI Interviews Notebook.ipynb
│   ├── Human vs. AI Interviews.xlsx
│   └── [Responses] Human Evals for AI vs. Human interviews.xlsx
│
├── 📈 NPS/                          # Net Promoter Score analysis
│   ├── candidate_nps_with_lee_bounds.py
│   ├── nps_from_Mar4_to_Mar9.ipynb
│   ├── (v1) Candidate Experience NPS.xlsx
│   └── (v1) Time Saving Quantified .xlsx
│
├── 📊 historical_data_AI_predicts_human/  # Historical analysis
│   ├── Human vs AI Interview.ipynb
│   └── Human + AI Outcomes - Input Data.csv
│
├── 📊 score_normalization3/        # Score normalization analysis
│   ├── Human vs. AI Interviews Normalized Output.ipynb
│   └── Source Files (Human Evaluation) Backup/
│
├── 🖼️ figures/                      # Generated visualizations
│   ├── cumulative_rates_*.png
│   ├── job_finding_rates.png
│   ├── oaxaca_decomposition_plot.png
│   └── ...
│
├── 🔧 linkedin_scrapers_backup/    # LinkedIn scraping tools (backup)
│   ├── linkedin_scraper_safari_batch.py
│   ├── linkedin_monitor.py
│   ├── linkedin_profile_parser.py
│   └── README_SCRAPERS.md
│
├── 📦 archive/                      # Deprecated/old code
│   ├── deprecated_parsers/
│   ├── deprecated_scrapers/
│   └── old_scripts/
│
└── 📄 linkedin_html_raw/           # Raw LinkedIn HTML files
```

## 🔑 Key Components

### 1. **Controlled Experiments** (`micro1-controll-experiment-EDA/`)

The core experimental data comparing two recruitment pipelines:
- **AI Pipeline**: Candidates prompted to complete AI-led interviews (6,121 completed out of 25,481)
- **Manual Pipeline**: Candidates sorted by AI ranking, then screened by humans (11,298 ranked)

Key datasets:
- `job_101(AI)_w_age_gender.csv`: Treatment group (AI pipeline)
- `job_110(Manual)_w_age_gender.csv`: Control group (Manual pipeline)
- `top_candidates_interviewed.csv`: Final interview outcomes

### 2. **Statistical Analysis** (`src/`)

R scripts for comprehensive statistical analysis:

| Script | Purpose |
|--------|---------|
| `ate.R` / `ate_clean.R` | Average Treatment Effect estimation |
| `who_benefits.r` | Heterogeneous treatment effects analysis |
| `droppingout.R` | Dropout prediction and analysis |
| `decomposition.R` | Oaxaca decomposition for outcome differences |
| `embeds_analysis.R` | Embedding-based analysis |
| `skill_vetting.R` | Skill assessment and vetting analysis |
| `all_linkedin_analysis.R` | Comprehensive LinkedIn profile analysis |

### 3. **Resume Vetting Experiments** (`experiments/resume_vetting/`)

Comparison of AI vs. manual resume scoring:
- `Ai-Vetted-ranked.csv`: AI-scored resumes with skill assessments
- `Manual-Resume-ranked.csv`: Human-scored resumes
- `resume_vetting_experiment.py`: Experiment runner

### 4. **LinkedIn Tools** (`src/linkedin/`)

Production-ready LinkedIn scraping and parsing tools:
- **Scrapers**: Safari-based batch scrapers with anti-detection
- **Parsers**: Extract structured data from LinkedIn profiles
- **Utilities**: Monitoring, status checking, and data processing

See `src/linkedin/README_SCRAPERS.md` for detailed documentation.

### 5. **NPS Analysis** (`NPS/`)

Candidate experience evaluation:
- Net Promoter Score calculation with statistical bounds
- Time saving quantification
- Candidate satisfaction analysis

### 6. **Algorithm Auditing** (`auditing_algorithm/`)

Evaluation of AI vs. human interview assessments:
- Comparison of AI and human evaluations
- Normalization and scoring analysis

## 🚀 Getting Started

### Prerequisites

- **R** (with packages: `dplyr`, `ggplot2`, `grf`, `stargazer`, `broom`, `gbm`, etc.)
- **Python 3** (for scraping and some analysis scripts)
- **Safari** (for LinkedIn scraping - see below)

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd AI_recruiter_internal
   ```

2. **Install R packages:**
   ```r
   # Run in R console
   install.packages(c("dplyr", "ggplot2", "stringr", "tidyr", "lubridate",
                      "knitr", "grf", "caret", "stargazer", "broom",
                      "kableExtra", "gridExtra", "gbm", "jsonlite", "purrr",
                      "oaxaca", "sampleSelection", "survival", "riskRegression"))
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r src/linkedin/requirements.txt
   ```

4. **Setup Safari for LinkedIn scraping** (optional):
   ```bash
   sudo safaridriver --enable
   ```
   Enable: Safari → Develop → Allow Remote Automation

### Running Analyses

**Example: Average Treatment Effect Analysis**
```r
# In R
source("src/ate.R")
```

**Example: Dropout Analysis**
```r
# In R
source("src/droppingout.R")
```

**Example: LinkedIn Scraping**
```bash
cd src/linkedin/scrapers
python linkedin_scraper_safari_batch.py
```

## 📊 Data Organization

### Experimental Data

- **Treatment/Control Groups**: Separated by recruitment pipeline (AI vs. Manual)
- **LinkedIn Profiles**: Matched to candidates via `job_application_id`
- **Interview Outcomes**: Final interview results and pass/fail status
- **Resume Scores**: Both AI-generated and human-assessed scores

### Data Flow

```
Raw Application Data
    ↓
Pipeline Assignment (AI vs. Manual)
    ↓
Resume Scoring (AI or Human)
    ↓
Interview Selection
    ↓
Final Outcomes
    ↓
LinkedIn Profile Matching
    ↓
Analysis & Visualization
```

## 📈 Analysis Scripts

### Main Analysis Workflows

1. **Treatment Effect Analysis** (`src/ate.R`)
   - Compares outcomes between AI and manual pipelines
   - Estimates average treatment effects
   - Controls for covariates

2. **Heterogeneous Effects** (`src/who_benefits.r`)
   - Identifies which candidate groups benefit most from AI
   - Subgroup analysis by demographics, skills, etc.

3. **Dropout Analysis** (`src/droppingout.R`)
   - Predicts dropout probability
   - Analyzes factors affecting completion rates
   - Uses GBM for prediction

4. **LinkedIn Analysis** (`src/all_linkedin_analysis.R`)
   - Job finding rates over time
   - Survival analysis
   - Profile characteristics analysis

5. **Skill Vetting** (`src/skill_vetting.R`)
   - Skill assessment accuracy
   - Relationship with outcomes
   - Geographic patterns

## 📝 Notes

- **Path Configuration**: Many R scripts use hardcoded paths. Update `root_dir` variables to match your system.
- **Data Privacy**: All data is for research purposes. Ensure compliance with data protection regulations.
- **LinkedIn Scraping**: Use responsibly and in accordance with LinkedIn's terms of service.

## 🔗 Related Documentation

- `src/linkedin/README_SCRAPERS.md` - Detailed LinkedIn scraper documentation
- `linkedin_scrapers_backup/README.md` - Backup scraper documentation
- Individual script headers contain usage instructions

## 📧 Contact

For questions about this research repository, please contact the repository maintainer.

---

**Last Updated**: Repository reorganized and restructured for better organization and clarity.

