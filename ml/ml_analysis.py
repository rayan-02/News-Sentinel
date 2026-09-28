"""
News Sentinel — ML analysis stage.

Inputs:
    data/articles_nlp.csv
    data/article_embeddings.npy

Outputs:
    data/articles_ml.csv
    data/clusters_summary.csv
    data/similarity_top_pairs.csv
    data/topic_trends.csv
    data/emerging_signals.csv
"""

import os
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

BASE_FOLDER = os.path.join(os.path.dirname(__file__), "..")
DATA_FOLDER = os.path.join(BASE_FOLDER, "data")

NLP_FILE = os.path.join(DATA_FOLDER, "articles_nlp.csv")
EMBEDDINGS_FILE = os.path.join(DATA_FOLDER, "article_embeddings.npy")
ARTICLES_ML_FILE = os.path.join(DATA_FOLDER, "articles_ml.csv")
CLUSTERS_FILE = os.path.join(DATA_FOLDER, "clusters_summary.csv")
SIMILARITY_FILE = os.path.join(DATA_FOLDER, "similarity_top_pairs.csv")
TRENDS_FILE = os.path.join(DATA_FOLDER, "topic_trends.csv")
SIGNALS_FILE = os.path.join(DATA_FOLDER, "emerging_signals.csv")

K = 8
TOP_K_SIMILAR = 5
SIMILARITY_THRESHOLD = 0.75
RANDOM_STATE = 42

GENERIC_TERMS = {
    "pakistan",
    "said",
    "year",
    "years",
    "day",
    "days",
    "new",
    "old",
    "one",
    "two",
    "also",
}


def load_data():
    print("Loading NLP data:", NLP_FILE)
    df = pd.read_csv(NLP_FILE)

    print("Loading embeddings:", EMBEDDINGS_FILE)
    embeddings = np.load(EMBEDDINGS_FILE)
    
    if len(df) != embeddings.shape[0]:
        raise ValueError(
            f"Row mismatch: CSV has {len(df)} rows, "
            f"embeddings have {embeddings.shape[0]}"
        )

    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df["date_only"] = df["date"].dt.date

    print(f"Loaded {len(df)} articles | embeddings {embeddings.shape}")
    return df, embeddings


def split_terms(value):
    if pd.isna(value) or not str(value).strip():
        return []
    return [term.strip().lower() for term in str(value).split(",") if term.strip()]


def top_terms(series, n=5):
    counts = Counter()

    for value in series.fillna(""):
        counts.update(split_terms(value))

    terms = []
    for term, _ in counts.most_common():
        if term in GENERIC_TERMS:
            continue
        terms.append(term)
        if len(terms) >= n:
            break

    return terms


def create_cluster_label(terms):
    return ", ".join(terms[:3]) if terms else "Unknown"


def cluster_articles(df, embeddings):
    print(f"\nClustering articles with K-Means (k={K})...")

    X = normalize(embeddings)
    model = KMeans(n_clusters=K, random_state=RANDOM_STATE, n_init=20)
    labels = model.fit_predict(X)

    df = df.copy()
    df["cluster_id"] = labels

    cluster_rows = []
    label_map = {}

    for cluster_id in sorted(df["cluster_id"].unique()):
        cluster = df[df["cluster_id"] == cluster_id]

        keywords = top_terms(cluster["top_keywords"], n=8)
        phrases = top_terms(cluster["top_phrases"], n=5)
        label = create_cluster_label(keywords)
        label_map[int(cluster_id)] = label

        source_counts = cluster["source"].value_counts()
        sources = ", ".join(
            f"{source}:{count}" for source, count in source_counts.items()
        )

        cluster_rows.append(
            {
                "cluster_id": int(cluster_id),
                "cluster_label": label,
                "article_count": len(cluster),
                "top_keywords": ", ".join(keywords),
                "top_phrases": ", ".join(phrases),
                "avg_sentiment": round(float(cluster["sentiment_score"].mean()), 4),
                "pos_count": int((cluster["sentiment_label"] == "Positive").sum()),
                "neg_count": int((cluster["sentiment_label"] == "Negative").sum()),
                "neu_count": int((cluster["sentiment_label"] == "Neutral").sum()),
                "sources": sources,
                "dated_articles": int(cluster["date"].notna().sum()),
                "sample_titles": " | ".join(cluster["title"].head(3).tolist()),
            }
        )

    df["cluster_label"] = df["cluster_id"].map(label_map)

    clusters_df = (
        pd.DataFrame(cluster_rows)
        .sort_values("article_count", ascending=False)
        .reset_index(drop=True)
    )

    silhouette = float(silhouette_score(X, labels, metric="cosine"))

    print(f"Silhouette score: {silhouette:.4f}")
    print(
        clusters_df[["cluster_id", "cluster_label", "article_count"]].to_string(
            index=False
        )
    )

    return df, clusters_df, silhouette


def find_similar_articles(df, embeddings):
    print("\nComputing article similarity...")

    X = normalize(embeddings)
    similarity_matrix = cosine_similarity(X)
    np.fill_diagonal(similarity_matrix, -1.0)

    similar_ids = []
    similar_scores = []
    similar_titles = []

    for i in range(len(df)):
        indexes = np.argsort(similarity_matrix[i])[::-1][:TOP_K_SIMILAR]
        scores = similarity_matrix[i][indexes]

        similar_ids.append(",".join(str(int(j)) for j in indexes))
        similar_scores.append(",".join(f"{score:.3f}" for score in scores))
        similar_titles.append(" | ".join(df.iloc[j]["title"][:80] for j in indexes))

    df = df.copy()
    df["similar_ids"] = similar_ids
    df["similar_scores"] = similar_scores
    df["similar_titles"] = similar_titles

    pairs = []
    n = len(df)

    for i in range(n):
        for j in range(i + 1, n):
            score = float(similarity_matrix[i, j])

            if score < SIMILARITY_THRESHOLD:
                continue

            pairs.append(
                {
                    "article_i": i,
                    "article_j": j,
                    "similarity": round(score, 4),
                    "same_cluster": int(
                        df.iloc[i]["cluster_id"] == df.iloc[j]["cluster_id"]
                    ),
                    "cross_source": int(df.iloc[i]["source"] != df.iloc[j]["source"]),
                    "source_i": df.iloc[i]["source"],
                    "source_j": df.iloc[j]["source"],
                    "cluster_i": int(df.iloc[i]["cluster_id"]),
                    "cluster_j": int(df.iloc[j]["cluster_id"]),
                    "cluster_label_i": df.iloc[i]["cluster_label"],
                    "cluster_label_j": df.iloc[j]["cluster_label"],
                    "title_i": df.iloc[i]["title"],
                    "title_j": df.iloc[j]["title"],
                    "url_i": df.iloc[i]["url"],
                    "url_j": df.iloc[j]["url"],
                    "sentiment_i": df.iloc[i]["sentiment_label"],
                    "sentiment_j": df.iloc[j]["sentiment_label"],
                    "date_i": df.iloc[i]["date_only"],
                    "date_j": df.iloc[j]["date_only"],
                }
            )

    pairs_df = pd.DataFrame(pairs)

    if not pairs_df.empty:
        pairs_df = pairs_df.sort_values("similarity", ascending=False).reset_index(
            drop=True
        )

    print(f"Top-{TOP_K_SIMILAR} neighbors stored per article")
    print(f"High-similarity pairs (>= {SIMILARITY_THRESHOLD}): {len(pairs_df)}")

    if not pairs_df.empty:
        print(f"Cross-source pairs: {int(pairs_df['cross_source'].sum())}")
        print(f"Same-cluster pairs: {int(pairs_df['same_cluster'].sum())}")

    return df, pairs_df


def calculate_trends(df, clusters_df):
    print("\nCalculating topic trends...")

    dated = df[df["date"].notna()].copy()
    print(f"Dated articles available: {len(dated)} / {len(df)}")

    if dated.empty:
        return pd.DataFrame()

    dated["day"] = dated["date"].dt.floor("D")

    counts = (
        dated.groupby(["day", "cluster_id", "cluster_label"])
        .size()
        .reset_index(name="article_count")
    )

    # Create every cluster/day combination so days with zero articles are included
    all_days = pd.date_range(dated["day"].min(), dated["day"].max(), freq="D", tz="UTC")

    cluster_meta = (
        clusters_df[["cluster_id", "cluster_label"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    cluster_meta["key"] = 1
    days_df = pd.DataFrame({"day": all_days, "key": 1})

    trends = (
        cluster_meta.merge(days_df, on="key")
        .drop(columns="key")
        .merge(counts, on=["day", "cluster_id", "cluster_label"], how="left")
    )

    trends["article_count"] = trends["article_count"].fillna(0).astype(int)
    trends = trends.sort_values(["cluster_id", "day"]).reset_index(drop=True)

    trends["count_prev_day"] = trends.groupby("cluster_id")["article_count"].shift(1)

    trends["day_change"] = trends["article_count"] - trends["count_prev_day"]

    trends["rolling_3d"] = trends.groupby("cluster_id")["article_count"].transform(
        lambda x: x.rolling(3, min_periods=1).mean()
    )

    trends["rolling_7d"] = trends.groupby("cluster_id")["article_count"].transform(
        lambda x: x.rolling(7, min_periods=1).mean()
    )

    return trends


def detect_emerging_topics(
    trends, recent_active_days=3, baseline_active_days=7, min_recent=4
):
    print("\nDetecting emerging topic signals...")

    if trends.empty:
        print("No dated trend data — skipping signals.")
        return pd.DataFrame()

    daily_total = trends.groupby("day")["article_count"].sum()
    active_days = daily_total[daily_total > 0].sort_index().index.tolist()

    if len(active_days) < recent_active_days + 2:
        print("Not enough active dated days for reliable signals.")
        return pd.DataFrame(
            columns=[
                "cluster_id",
                "cluster_label",
                "recent_active_days",
                "baseline_active_days",
                "recent_articles",
                "baseline_articles",
                "recent_share",
                "baseline_share",
                "share_lift",
                "is_emerging_signal",
                "note",
            ]
        )

    recent_days = active_days[-recent_active_days:]
    baseline_days = active_days[:-recent_active_days][-baseline_active_days:]

    recent_mask = trends["day"].isin(recent_days)
    baseline_mask = trends["day"].isin(baseline_days)

    recent_all = int(trends.loc[recent_mask, "article_count"].sum())
    baseline_all = int(trends.loc[baseline_mask, "article_count"].sum())

    rows = []

    for cluster_id, group in trends.groupby("cluster_id"):
        label = group["cluster_label"].iloc[0]

        recent_total = int(
            group.loc[group["day"].isin(recent_days), "article_count"].sum()
        )

        baseline_total = int(
            group.loc[group["day"].isin(baseline_days), "article_count"].sum()
        )

        recent_share = recent_total / recent_all if recent_all else 0
        baseline_share = baseline_total / baseline_all if baseline_all else 0

        if baseline_share > 0:
            share_lift = recent_share / baseline_share
        else:
            share_lift = float(recent_share * 10) if recent_share else 0

        is_signal = (
            recent_total >= min_recent
            and share_lift >= 1.5
            and (recent_share >= 0.12 or share_lift >= 2.5)
        )

        rows.append(
            {
                "cluster_id": int(cluster_id),
                "cluster_label": label,
                "recent_active_days": ", ".join(str(d.date()) for d in recent_days),
                "baseline_active_days": ", ".join(str(d.date()) for d in baseline_days),
                "recent_articles": recent_total,
                "baseline_articles": baseline_total,
                "recent_share": round(recent_share, 4),
                "baseline_share": round(baseline_share, 4),
                "share_lift": round(float(share_lift), 3),
                "is_emerging_signal": int(is_signal),
                "note": (
                    "Elevated share of recent coverage vs baseline"
                    if is_signal
                    else "No strong emerging signal"
                ),
            }
        )

    signals = (
        pd.DataFrame(rows)
        .sort_values(
            ["is_emerging_signal", "share_lift", "recent_articles"],
            ascending=[False, False, False],
        )
        .reset_index(drop=True)
    )

    print(f"Emerging signals flagged: {int(signals['is_emerging_signal'].sum())}")

    return signals


def save_results(df, clusters_df, pairs_df, trends_df, signals_df):
    os.makedirs(DATA_FOLDER, exist_ok=True)

    output = df.copy()
    output["date"] = output["date"].astype(str).replace("NaT", "")
    output["date_only"] = (
        output["date_only"].astype(str).replace("NaT", "").replace("None", "")
    )

    output.to_csv(ARTICLES_ML_FILE, index=False)
    clusters_df.to_csv(CLUSTERS_FILE, index=False)
    pairs_df.to_csv(SIMILARITY_FILE, index=False)

    if not trends_df.empty:
        trends_output = trends_df.copy()
        trends_output["day"] = trends_output["day"].dt.date
        trends_output.to_csv(TRENDS_FILE, index=False)
    else:
        pd.DataFrame().to_csv(TRENDS_FILE, index=False)

    signals_df.to_csv(SIGNALS_FILE, index=False)

    print("\nSaved:")
    for file in [
        ARTICLES_ML_FILE,
        CLUSTERS_FILE,
        SIMILARITY_FILE,
        TRENDS_FILE,
        SIGNALS_FILE,
    ]:
        print(file)


def print_summary(df, clusters_df, pairs_df, signals_df, silhouette):
    print("\n========== ML SUMMARY ==========")
    print(f"Articles: {len(df)}")
    print(f"Clusters: {len(clusters_df)} | silhouette={silhouette:.4f}")
    print(f"Similarity pairs: {len(pairs_df)}")

    if not pairs_df.empty:
        print(f"  Cross-source: {int(pairs_df['cross_source'].sum())}")
        print(f"  Same-cluster: {int(pairs_df['same_cluster'].sum())}")

    if not signals_df.empty:
        print(f"Emerging signals: {int(signals_df['is_emerging_signal'].sum())}")

    print("\nClusters:")
    print(
        clusters_df[
            ["cluster_id", "article_count", "cluster_label", "avg_sentiment", "sources"]
        ].to_string(index=False)
    )

    if not pairs_df.empty:
        print("\nTop cross-source similar pairs:")

        cross = pairs_df[pairs_df["cross_source"] == 1].head(5)

        for _, row in cross.iterrows():
            print(
                f"[{row['similarity']:.3f}] "
                f"{row['source_i']}: {row['title_i'][:55]} <-> "
                f"{row['source_j']}: {row['title_j'][:55]}"
            )


def main():
    print("Starting News Sentinel ML analysis\n")

    df, embeddings = load_data()
    df, clusters_df, silhouette = cluster_articles(df, embeddings)
    df, pairs_df = find_similar_articles(df, embeddings)
    trends_df = calculate_trends(df, clusters_df)
    signals_df = detect_emerging_topics(trends_df)

    save_results(df, clusters_df, pairs_df, trends_df, signals_df)

    print_summary(df, clusters_df, pairs_df, signals_df, silhouette)

    print("\nDone.")


if __name__ == "__main__":
    main()
