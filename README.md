# ML Engineering Projects

A collection of ML engineering projects focused on production-oriented data pipelines, reproducible model training, experiment tracking, serving, monitoring, and recommendation systems.

| # | Project | Domain | ML Task | Key Tools | Link |
| --- | --- | --- | --- | --- | --- |
| 01 | Real Estate ETL and DVC Training Pipeline | Real estate | Price regression | Airflow orchestration, DVC reproducibility, CatBoost training, PostgreSQL ETL, Docker Compose, S3-compatible remote | [projects/01-real-estate-airflow-dvc-pipeline](projects/01-real-estate-airflow-dvc-pipeline) |
| 02 | Real Estate Model Improvement with MLflow | Real estate | Price regression and experiment tracking | MLflow tracking, model registry workflow, Optuna tuning, CatBoost, feature selection, S3 artifact storage | [projects/02-real-estate-mlflow-model-improvement](projects/02-real-estate-mlflow-model-improvement) |
| 03 | Real Estate Price API with Monitoring | Real estate | Online regression inference | FastAPI model serving, Docker Compose, Prometheus metrics, Grafana dashboard, load testing, health checks | [projects/03-real-estate-price-api-monitoring](projects/03-real-estate-price-api-monitoring) |
| 04 | Music Recommendation Service | Streaming media | Implicit-feedback recommendation | ALS candidates, CatBoost ranking, FastAPI services, offline recommendations, feature artifacts, API smoke checks | [projects/04-music-recommendation-service](projects/04-music-recommendation-service) |
| 05 | Food Delivery Promo Uplift Modeling | Food delivery | Uplift modeling | scikit-uplift, causalml, Optuna tuning, treatment-effect metrics, validation workflow, artifact placeholders | [projects/05-food-delivery-uplift-modeling](projects/05-food-delivery-uplift-modeling) |
| 06 | E-commerce Recommendation Platform | E-commerce | Recommendation ranking | Airflow retraining, FastAPI microservices, MLflow logging, ALS retrieval, CatBoost ranking, Docker Compose, online/offline blending | [projects/06-ecommerce-recommendation-platform](projects/06-ecommerce-recommendation-platform) |

## Engineering Focus Areas
- Data pipelines and workflow orchestration.
- Reproducible ML with DVC and parameterized stages.
- Model evaluation with task-specific metrics.
- Experiment tracking and model registry workflows.
- Production-oriented service structure, monitoring, and artifact hygiene.

## Data and Reproducibility
This repository is prepared for public reading: documentation and comments are in English, while private datasets, generated model artifacts, and credentials are intentionally left out. Each project README explains what needs to be configured to reproduce the pipeline. Reported metrics come from the original notebooks, logs, or committed metric files rather than estimates.
