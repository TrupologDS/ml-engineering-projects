# airflow/dags/retrain_recs.py

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator

BASE = Path("/opt/airflow").resolve()
DATA_DIR = BASE / "data"
PROC_DIR = BASE / "data" / "processed"
MODELS = BASE / "models"
for p in [PROC_DIR, MODELS]:
    p.mkdir(parents=True, exist_ok=True)

SPLIT_DATE = pd.Timestamp("2015-09-01")


# Data preparation.
def prep_data():
    events = pd.read_csv(DATA_DIR / "events.csv")
    events["timestamp"] = pd.to_numeric(events["timestamp"], errors="coerce")
    events["ts"] = pd.to_datetime(events["timestamp"], unit="ms", errors="coerce")
    events = events.dropna(subset=["ts"])

    w = {"view": 1, "addtocart": 3, "transaction": 5}
    events["strength"] = events["event"].map(w).fillna(0).astype(np.int16)

    train = events[events["ts"] < SPLIT_DATE].copy()
    test = events[events["ts"] >= SPLIT_DATE].copy()

    ui_train = train.groupby(["visitorid", "itemid"], as_index=False)["strength"].sum()

    u_cnt = ui_train.groupby("visitorid")["itemid"].nunique()
    i_cnt = ui_train.groupby("itemid")["visitorid"].nunique()
    ui_train = ui_train[
        ui_train["visitorid"].isin(u_cnt[u_cnt >= 2].index)
        & ui_train["itemid"].isin(i_cnt[i_cnt >= 3].index)
    ].copy()

    allowed_users = set(ui_train["visitorid"].unique())
    allowed_items = set(ui_train["itemid"].unique())
    test = test[test["visitorid"].isin(allowed_users) & test["itemid"].isin(allowed_items)].copy()

    ui_train.to_parquet(PROC_DIR / "ui_train.parquet", index=False)
    test[["visitorid", "itemid", "event", "ts"]].to_parquet(
        PROC_DIR / "events_test.parquet", index=False
    )


# Candidate generation and item similarities.
def build_candidates():
    # Deferred imports keep DAG parsing lightweight.
    import scipy.sparse as sp
    from implicit.als import AlternatingLeastSquares

    ui = pd.read_parquet(PROC_DIR / "ui_train.parquet")
    test = pd.read_parquet(PROC_DIR / "events_test.parquet")

    users = sorted(ui["visitorid"].unique())
    items = sorted(ui["itemid"].unique())
    u2e = {u: i for i, u in enumerate(users)}
    i2e = {it: i for i, it in enumerate(items)}
    e2u = {i: u for u, i in u2e.items()}
    e2i = {i: it for it, i in i2e.items()}

    ui["u"] = ui["visitorid"].map(u2e)
    ui["i"] = ui["itemid"].map(i2e)

    n_users, n_items = len(users), len(items)
    mat = sp.csr_matrix(
        (ui["strength"].astype(np.float32), (ui["u"], ui["i"])), shape=(n_users, n_items)
    )

    als = AlternatingLeastSquares(factors=64, iterations=25, regularization=0.05, random_state=0)
    als.fit(mat)

    # ALS similar items.
    all_i = np.arange(n_items, dtype=int)
    sim_ids, sim_scores = als.similar_items(all_i, N=51)
    sim = pd.DataFrame(
        {
            "item_id_enc": np.repeat(all_i, 51),
            "sim_item_id_enc": sim_ids.flatten(),
            "score": sim_scores.flatten().astype(float),
        }
    )
    sim = sim[sim["item_id_enc"] != sim["sim_item_id_enc"]].copy()
    sim["item_id_1"] = sim["item_id_enc"].map(e2i)
    sim["item_id_2"] = sim["sim_item_id_enc"].map(e2i)
    sim = sim[["item_id_1", "item_id_2", "score"]].sort_values(
        ["item_id_1", "score"], ascending=[True, False]
    )
    sim.to_parquet(MODELS / "similar_items.parquet", index=False)

    # ALS user recommendations.
    test_users = sorted(test["visitorid"].unique())
    test_users_enc = [u2e[u] for u in test_users if u in u2e]
    if len(test_users_enc) == 0:
        als_recs = pd.DataFrame(columns=["user_id", "item_id", "score"])
    else:
        rec_i, rec_s = als.recommend(
            test_users_enc, mat[test_users_enc], N=100, filter_already_liked_items=True
        )
        als_recs = pd.DataFrame(
            {
                "user_id_enc": np.repeat(test_users_enc, 100),
                "item_id_enc": rec_i.flatten(),
                "score": rec_s.flatten(),
            }
        )
        als_recs["user_id"] = als_recs["user_id_enc"].map(e2u)
        als_recs["item_id"] = als_recs["item_id_enc"].map(e2i)
        als_recs = als_recs[["user_id", "item_id", "score"]]
    als_recs.to_parquet(PROC_DIR / "als_recommendations.parquet", index=False)

    # Co-visitation similarities.
    pairs = ui.merge(ui, on="visitorid")
    pairs = pairs[pairs["i_x"] != pairs["i_y"]]
    covis = pairs.groupby(["i_x", "i_y"]).size().reset_index(name="score")
    covis = covis.sort_values(["i_x", "score"], ascending=[True, False]).groupby("i_x").head(50)
    covis = covis.rename(columns={"i_x": "seed_i", "i_y": "rec_i", "score": "co_score"})

    # Co-visitation recommendations.
    base = ui[ui["u"].isin([u2e[u] for u in test_users if u in u2e])][["u", "i"]].drop_duplicates()
    seed = base.rename(columns={"i": "seed_i"})
    recs = seed.merge(covis, on="seed_i", how="left").dropna(subset=["rec_i"])
    seen = base.assign(seen=1).rename(columns={"i": "rec_i"})
    recs = recs.merge(seen, on=["u", "rec_i"], how="left")
    recs = recs[recs["seen"].isna()][["u", "rec_i", "co_score"]]
    covis_recs = recs.groupby(["u", "rec_i"])["co_score"].sum().reset_index()
    covis_recs = (
        covis_recs.sort_values(["u", "co_score"], ascending=[True, False]).groupby("u").head(100)
    )
    covis_recs["user_id"] = covis_recs["u"].map(e2u)
    covis_recs["item_id"] = covis_recs["rec_i"].map(e2i)
    covis_recs = covis_recs.rename(columns={"co_score": "score"})[["user_id", "item_id", "score"]]
    covis_recs.to_parquet(PROC_DIR / "covis_recommendations.parquet", index=False)

    # Top-popular fallback.
    pop = ui.groupby("itemid")["strength"].sum().sort_values(ascending=False).head(100)
    pd.DataFrame({"item_id": pop.index}).to_parquet(MODELS / "top_recs.parquet", index=False)


# Ranker training and final recommendations.
def train_ranker_and_rank():
    # Deferred import.
    from catboost import CatBoostClassifier

    test = pd.read_parquet(PROC_DIR / "events_test.parquet")

    als_df = pd.read_parquet(PROC_DIR / "als_recommendations.parquet").rename(
        columns={"score": "als_score"}
    )
    covis_df = pd.read_parquet(PROC_DIR / "covis_recommendations.parquet").rename(
        columns={"score": "co_score"}
    )
    top_df = pd.read_parquet(MODELS / "top_recs.parquet")
    test_users = sorted(test["visitorid"].unique())

    # Candidates.
    pop_recs = pd.DataFrame(
        {
            "user_id": np.repeat(test_users, len(top_df)),
            "item_id": np.tile(top_df["item_id"].values, len(test_users)),
            "pop_score": np.tile(np.arange(len(top_df), 0, -1), len(test_users)),
        }
    )

    candidates = als_df.merge(covis_df, on=["user_id", "item_id"], how="outer")
    candidates = candidates.merge(pop_recs, on=["user_id", "item_id"], how="outer")
    for c in ["als_score", "co_score", "pop_score"]:
        if c not in candidates:
            candidates[c] = 0.0
        candidates[c] = candidates[c].fillna(0.0)

    # Labels.
    q = 0.8
    label_split = test["ts"].quantile(q)
    labels_win = test[test["ts"] < label_split]
    infer_win = test[test["ts"] >= label_split]

    labels = labels_win[labels_win["event"] == "addtocart"][
        ["visitorid", "itemid"]
    ].drop_duplicates()
    labels = labels.rename(columns={"visitorid": "user_id", "itemid": "item_id"}).assign(target=1)

    cand_train = candidates[candidates["user_id"].isin(labels["user_id"].unique())].copy()
    cand_train = cand_train.merge(labels, on=["user_id", "item_id"], how="left")
    cand_train["target"] = cand_train["target"].fillna(0).astype(int)
    cand_train = cand_train.groupby("user_id").filter(lambda x: x["target"].sum() > 0)

    neg = (
        cand_train[cand_train["target"] == 0]
        .groupby("user_id", group_keys=False)
        .apply(lambda x: x.sample(min(len(x), 4), random_state=0))
    )
    cand_for_train = pd.concat([cand_train[cand_train["target"] == 1], neg], ignore_index=True)

    feats = ["als_score", "co_score", "pop_score"]
    cb = CatBoostClassifier(
        iterations=800,
        depth=6,
        learning_rate=0.1,
        loss_function="Logloss",
        verbose=False,
        random_seed=0,
    )
    cb.fit(cand_for_train[feats], cand_for_train["target"])
    cb.save_model(str(MODELS / "ranker.cbm"))

    users_infer = sorted(infer_win["visitorid"].unique())
    cand_rank = (
        candidates[candidates["user_id"].isin(users_infer)]
        .drop_duplicates(["user_id", "item_id"])
        .copy()
    )
    if len(cand_rank) == 0:
        pd.DataFrame(columns=["user_id", "item_id", "score"]).to_parquet(
            MODELS / "final_recommendations_feat.parquet", index=False
        )
        return
    cand_rank["score"] = cb.predict_proba(cand_rank[feats])[:, 1]
    final_recs = (
        cand_rank.sort_values(["user_id", "score"], ascending=[True, False])
        .groupby("user_id")
        .head(100)
    )
    final_recs[["user_id", "item_id", "score"]].to_parquet(
        MODELS / "final_recommendations_feat.parquet", index=False
    )


with DAG(
    dag_id="retrain_ecom_recs",
    schedule=timedelta(days=1),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["recsys", "ecommerce"],
) as dag:
    t1 = PythonOperator(task_id="prep_data", python_callable=prep_data)
    t2 = PythonOperator(task_id="build_candidates", python_callable=build_candidates)
    t3 = PythonOperator(task_id="train_ranker_and_rank", python_callable=train_ranker_and_rank)
    t1 >> t2 >> t3
