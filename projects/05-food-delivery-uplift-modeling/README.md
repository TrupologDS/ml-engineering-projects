# Food Delivery Promo Uplift Modeling

This project identifies customers most likely to respond incrementally to a food delivery promo code using uplift modeling rather than standard response prediction.

## Overview
- Business context: target a limited promo-code budget at users whose conversion probability increases because of the offer.
- ML problem type: uplift modeling / causal treatment effect ranking.
- Final deliverable: tuned T-learner model and inference wrapper for scoring users.

## ML Task
- Target variable: promo conversion indicator.
- Input features: purchase recency, historical spend, customer segment, channel, category affinity flags, and treatment assignment.
- Evaluation metrics: Uplift AUC, Qini AUC, Uplift@30.
- Assumptions: randomized treatment/control assignment is valid and the public notebook is re-run with the private CSV.

## Data
The raw `uplift_fp_data.csv` file is not included. The notebook expects it to be placed in the project root or the path updated.

## Solution Architecture
```mermaid
flowchart LR
    A[Private uplift dataset] --> B[EDA and balance checks]
    B --> C[Train/test split]
    C --> D[S-, T-, X-learner comparison]
    D --> E[Optuna tuning]
    E --> F[T-learner inference wrapper]
    F --> G[Top-30 percent targeting export]
```

## Repository Structure
```text
.
|-- data/
|-- models/
|-- notebooks/
`-- requirements.txt
```

## Tech Stack
Python, pandas, NumPy, scikit-learn, scikit-uplift, causalml, Optuna, statsmodels, matplotlib, seaborn.

## How to Run
```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
# place uplift_fp_data.csv in the project root
jupyter lab notebooks/food_delivery_uplift_modeling.ipynb
```

## Pipeline Details
- The notebook checks randomization balance and segment-level uplift.
- S-, T-, and X-learner RandomForest approaches are compared.
- Optuna optimizes the T-learner for Uplift@30.
- `UpliftModelInference` wraps separate treatment and control models for scoring.

## Model Evaluation
Actual notebook-reported metrics:
| Model | Uplift AUC | Qini AUC | Uplift@30 |
| --- | ---: | ---: | ---: |
| T-learner RF baseline | 0.0260 | 0.0588 | 0.0452 |
| S-learner RF | 0.0256 | 0.0573 | 0.0442 |
| X-learner RF | 0.0278 | 0.0617 | 0.0429 |
| Tuned T-learner RF | 0.0277 | 0.0623 | 0.0516 |

The notebook also reported an estimated 198 additional conversions for top-30 percent targeting on the test set.

## Engineering Highlights
- Uplift-specific metrics instead of plain conversion accuracy.
- Treatment/control model comparison.
- Hyperparameter tuning against the business-relevant top-percentile metric.
- Inference wrapper with feature validation.
- Raw data and model artifacts excluded from GitHub.

## Limitations and Next Steps
- Add calibration diagnostics for uplift scores.
- Add confidence intervals for segment uplift.
- Package the inference wrapper as a reusable module.
- Add batch scoring and monitoring for campaign outcomes.
