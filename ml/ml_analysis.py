import os
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

BASE_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_FOLDER = os.path.join(BASE_FOLDER, "data")

NLP_FILE = os.path.join(DATA_FOLDER, "articles_nlp.csv")
EMBEDDINGS_FILE = os.path.join(DATA_FOLDER, "article_embeddings.npy")
ARTICLES_ML_FILE = os.path.join(DATA_FOLDER, "articles_ml.csv")
CLUSTERS_FILE = os.path.join(DATA_FOLDER, "clusters_summary.csv")
SIMILARITY_FILE = os.path.join(DATA_FOLDER, "similarity_top_pairs.csv")
TRENDS_FILE = os.path.join(DATA_FOLDER, "topic_trends.csv")
SIGNALS_FILE = os.path.join(DATA_FOLDER, "emerging_signals.csv")
SOURCE_ANALYSIS_FILE = os.path.join(DATA_FOLDER, "source_analysis.csv")

SOURCE_MIN_ARTICLES = 5
SOURCE_TOP_TERMS = 10
SOURCE_MIN_TOPIC_ARTICLES = 3

K = 8
TOP_K_SIMILAR = 5
SIMILARITY_THRESHOLD = 0.75
RANDOM_STATE = 42

GENERIC_TERMS = {"pakistan", "said", "year", "years", "day", "days", "new", "old", "one", "two", "also"}


def load_data():
    print("Loading NLP data:", NLP_FILE)
    df = pd.read_csv(NLP_FILE)

    print("Loading embeddings:", EMBEDDINGS_FILE)
    embeddings = np.load(EMBEDDINGS_FILE)

    if len(df) != embeddings.shape[0]:
        raise ValueError(f"Row mismatch: CSV has {len(df)} rows, embeddings have {embeddings.shape[0]}")

    required = ["date", "source", "title", "url", "top_keywords", "top_phrases",
                "sentiment_score", "sentiment_label"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df["date_only"] = df["date"].dt.date

    # normalise once here so clustering and similarity both use unit vectors
    embeddings = normalize(embeddings)

    print(f"Loaded {len(df)} articles | embeddings {embeddings.shape}")
    return df, embeddings


def split_terms(value):
    if pd.isna(value) or not str(value).strip():
        return []
    return [t.strip().lower() for t in str(value).split(",") if t.strip()]


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


def cluster_articles(df, X):
    print(f"\nClustering articles with K-Means (k={K})...")

    actual_k = min(K, len(df))
    if actual_k < 2:
        raise ValueError("At least 2 articles are required for clustering.")

    model = KMeans(n_clusters=actual_k, random_state=RANDOM_STATE, n_init=20)
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

        source_counts = cluster["source"].fillna("Unknown").value_counts()
        sources = ", ".join(f"{s}:{c}" for s, c in source_counts.items())

        cluster_rows.append({
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
            "sample_titles": " | ".join(cluster["title"].fillna("").head(3).tolist()),
        })

    df["cluster_label"] = df["cluster_id"].map(label_map)

    clusters_df = (pd.DataFrame(cluster_rows)
                   .sort_values("article_count", ascending=False)
                   .reset_index(drop=True))

    if len(set(labels)) > 1 and len(df) > len(set(labels)):
        silhouette = float(silhouette_score(X, labels, metric="cosine"))
    else:
        silhouette = 0.0

    print(f"Silhouette score: {silhouette:.4f}")
    print(clusters_df[["cluster_id", "cluster_label", "article_count"]].to_string(index=False))

    return df, clusters_df, silhouette


def find_similar_articles(df, X):
    print("\nComputing article similarity...")

    # X is already normalised, so a dot product is the cosine similarity
    sim = X @ X.T
    np.fill_diagonal(sim, -1.0)

    # top-k neighbours for every article
    k = min(TOP_K_SIMILAR, len(df) - 1)
    top = np.argsort(-sim, axis=1)[:, :k]
    titles = df["title"].astype(str).str[:80].tolist()

    df = df.copy()
    df["similar_ids"] = [",".join(map(str, row)) for row in top]
    df["similar_scores"] = [",".join(f"{s:.3f}" for s in sim[n][row]) for n, row in enumerate(top)]
    df["similar_titles"] = [" | ".join(titles[j] for j in row) for row in top]

    # all pairs above the threshold (upper triangle so each pair appears once)
    i, j = np.where(np.triu(sim, 1) >= SIMILARITY_THRESHOLD)
    a = df.iloc[i].reset_index(drop=True)
    b = df.iloc[j].reset_index(drop=True)

    pairs_df = pd.DataFrame({
        "article_i": i,
        "article_j": j,
        "similarity": sim[i, j].round(4),
        "same_cluster": (a["cluster_id"] == b["cluster_id"]).astype(int),
        "cross_source": (a["source"] != b["source"]).astype(int),
        "source_i": a["source"], "source_j": b["source"],
        "cluster_i": a["cluster_id"], "cluster_j": b["cluster_id"],
        "cluster_label_i": a["cluster_label"], "cluster_label_j": b["cluster_label"],
        "title_i": a["title"], "title_j": b["title"],
        "url_i": a["url"], "url_j": b["url"],
        "sentiment_i": a["sentiment_label"], "sentiment_j": b["sentiment_label"],
        "date_i": a["date_only"], "date_j": b["date_only"],
    }).sort_values("similarity", ascending=False).reset_index(drop=True)

    print(f"Top-{k} neighbors stored per article")
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

    counts = (dated.groupby(["day", "cluster_id", "cluster_label"])
              .size().reset_index(name="article_count"))

    all_days = pd.date_range(dated["day"].min(), dated["day"].max(), freq="D", tz="UTC")
    cluster_meta = clusters_df[["cluster_id", "cluster_label"]].drop_duplicates()

    # every topic x every day, so quiet days show as 0 instead of missing
    trends = (cluster_meta.merge(pd.DataFrame({"day": all_days}), how="cross")
              .merge(counts, on=["day", "cluster_id", "cluster_label"], how="left"))

    trends["article_count"] = trends["article_count"].fillna(0).astype(int)
    trends = trends.sort_values(["cluster_id", "day"]).reset_index(drop=True)

    by_cluster = trends.groupby("cluster_id")["article_count"]
    trends["count_prev_day"] = by_cluster.shift(1)
    trends["day_change"] = (trends["article_count"] - trends["count_prev_day"]).fillna(0).astype(int)
    trends["rolling_3d"] = by_cluster.transform(lambda x: x.rolling(3, min_periods=1).mean()).round(2)
    trends["rolling_7d"] = by_cluster.transform(lambda x: x.rolling(7, min_periods=1).mean()).round(2)

    return trends


def detect_emerging_topics(trends, recent_active_days=3, baseline_active_days=7, min_recent=4):
    print("\nDetecting emerging topic signals...")

    if trends.empty:
        print("No dated trend data — skipping signals.")
        return pd.DataFrame()

    daily_total = trends.groupby("day")["article_count"].sum()
    active_days = daily_total[daily_total > 0].sort_index().index.tolist()

    if len(active_days) < recent_active_days + 2:
        print("Not enough active dated days for reliable signals.")
        return pd.DataFrame(columns=[
            "cluster_id", "cluster_label", "recent_active_days", "baseline_active_days",
            "recent_articles", "baseline_articles", "recent_share", "baseline_share",
            "share_lift", "is_emerging_signal", "note",
        ])

    # "days" here means days that actually had articles, so gaps don't distort the baseline
    recent_days = active_days[-recent_active_days:]
    baseline_days = active_days[:-recent_active_days][-baseline_active_days:]

    recent_all = int(trends.loc[trends["day"].isin(recent_days), "article_count"].sum())
    baseline_all = int(trends.loc[trends["day"].isin(baseline_days), "article_count"].sum())

    rows = []

    for cluster_id, group in trends.groupby("cluster_id"):
        recent_total = int(group.loc[group["day"].isin(recent_days), "article_count"].sum())
        baseline_total = int(group.loc[group["day"].isin(baseline_days), "article_count"].sum())

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

        rows.append({
            "cluster_id": int(cluster_id),
            "cluster_label": group["cluster_label"].iloc[0],
            "recent_active_days": ", ".join(str(d.date()) for d in recent_days),
            "baseline_active_days": ", ".join(str(d.date()) for d in baseline_days),
            "recent_articles": recent_total,
            "baseline_articles": baseline_total,
            "recent_share": round(recent_share, 4),
            "baseline_share": round(baseline_share, 4),
            "share_lift": round(float(share_lift), 3),
            "is_emerging_signal": int(is_signal),
            "note": "Elevated share of recent coverage vs baseline" if is_signal else "No strong emerging signal",
        })

    signals = (pd.DataFrame(rows)
               .sort_values(["is_emerging_signal", "share_lift", "recent_articles"],
                            ascending=[False, False, False])
               .reset_index(drop=True))

    print(f"Emerging signals flagged: {int(signals['is_emerging_signal'].sum())}")
    return signals


def distinctive_terms(source_values, other_values, n=SOURCE_TOP_TERMS):
    """Terms that show up in more of this source's articles than in other outlets' articles."""
    source_counts, other_counts = Counter(), Counter()

    for value in source_values.fillna(""):
        source_counts.update(set(split_terms(value)))
    for value in other_values.fillna(""):
        other_counts.update(set(split_terms(value)))

    rows = []
    for term, count in source_counts.items():
        if term in GENERIC_TERMS:
            continue
        # +1 / +2 smoothing so rare terms don't get huge lifts from tiny counts
        source_rate = (count + 1) / (len(source_values) + 2)
        other_rate = (other_counts[term] + 1) / (len(other_values) + 2)
        lift = source_rate / other_rate
        if lift > 1:
            rows.append((term, lift, count))

    rows.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return [term for term, _, _ in rows[:n]]


def analyze_source_framing(df, pairs_df):
    print("\nAnalyzing source coverage and framing...")

    required = ["source", "cluster_id", "cluster_label", "sentiment_score", "top_keywords", "top_phrases"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing columns required for source analysis: " + ", ".join(missing))

    working = df.copy()
    working["source"] = working["source"].fillna("Unknown").astype(str).str.strip()
    working["cluster_label"] = working["cluster_label"].fillna("Unknown").astype(str)
    working["sentiment_score"] = pd.to_numeric(working["sentiment_score"], errors="coerce").fillna(0)

    source_counts = working["source"].value_counts()
    valid_sources = source_counts[source_counts >= SOURCE_MIN_ARTICLES].index.tolist()

    if len(valid_sources) < 2:
        print("Not enough sources for source comparison.")
        return pd.DataFrame()

    working = working[working["source"].isin(valid_sources)].copy()
    overall_articles = len(working)
    topic_counts = working["cluster_id"].value_counts().to_dict()
    topic_sentiment = working.groupby("cluster_id")["sentiment_score"].agg(["mean", "std"]).fillna(0)

    rows = []

    for source in valid_sources:
        source_df = working[working["source"] == source]
        source_total = len(source_df)

        for cluster_id in sorted(topic_counts):
            topic_df = working[working["cluster_id"] == cluster_id]
            source_topic_df = source_df[source_df["cluster_id"] == cluster_id]
            source_topic_count = len(source_topic_df)

            if source_topic_count < SOURCE_MIN_TOPIC_ARTICLES:
                continue

            # how much of this outlet's coverage is this topic, vs the topic's share overall
            topic_total = len(topic_df)
            source_topic_share = source_topic_count / source_total
            overall_topic_share = topic_total / overall_articles
            emphasis_ratio = source_topic_share / overall_topic_share if overall_topic_share > 0 else 0

            # how far this outlet's sentiment sits from the topic average
            source_sentiment = float(source_topic_df["sentiment_score"].mean())
            topic_avg_sentiment = float(topic_sentiment.loc[cluster_id, "mean"])
            sentiment_difference = source_sentiment - topic_avg_sentiment
            topic_std = float(topic_sentiment.loc[cluster_id, "std"])
            sentiment_divergence = abs(sentiment_difference) / max(topic_std, 0.05)

            # words and phrases this outlet uses more than the others on the same topic
            other_topic_df = topic_df[topic_df["source"] != source]
            keywords = distinctive_terms(source_topic_df["top_keywords"], other_topic_df["top_keywords"])
            phrases = distinctive_terms(source_topic_df["top_phrases"], other_topic_df["top_phrases"])

            rows.append({
                "source": source,
                "cluster_id": int(cluster_id),
                "cluster_label": source_topic_df["cluster_label"].iloc[0],
                "source_articles": source_total,
                "topic_articles_all_sources": topic_total,
                "source_topic_articles": source_topic_count,
                "source_topic_share": round(source_topic_share, 4),
                "overall_topic_share": round(overall_topic_share, 4),
                "topic_emphasis_ratio": round(float(emphasis_ratio), 3),
                "source_avg_sentiment": round(source_sentiment, 4),
                "topic_avg_sentiment": round(topic_avg_sentiment, 4),
                "sentiment_difference": round(sentiment_difference, 4),
                "sentiment_divergence": round(float(sentiment_divergence), 3),
                "distinctive_keywords": ", ".join(keywords),
                "distinctive_phrases": ", ".join(phrases),
            })

    analysis = pd.DataFrame(rows)

    if analysis.empty:
        print("No source/topic comparisons generated.")
        return analysis

    # same-event matches per (source, topic): cross-outlet similar pairs this outlet is part of
    pair_counts = Counter()
    if not pairs_df.empty:
        cross = pairs_df[pairs_df["cross_source"] == 1]
        for s, c in zip(cross["source_i"], cross["cluster_i"]):
            pair_counts[(s, c)] += 1
        for s, c in zip(cross["source_j"], cross["cluster_j"]):
            pair_counts[(s, c)] += 1

    analysis["cross_source_similar_pairs"] = [
        pair_counts[(s, c)] for s, c in zip(analysis["source"], analysis["cluster_id"])
    ]
    analysis["cross_source_similarity_rate"] = (
        analysis["cross_source_similar_pairs"] / analysis["source_topic_articles"]
    ).round(4)

    analysis["coverage_deviation"] = (analysis["topic_emphasis_ratio"] - 1).abs().round(4)
    analysis["framing_signal"] = (analysis["coverage_deviation"] + analysis["sentiment_divergence"]).round(4)

    analysis["coverage_pattern"] = np.select(
        [analysis["topic_emphasis_ratio"] >= 1.5, analysis["topic_emphasis_ratio"] <= 0.67],
        ["Higher-than-typical topic coverage", "Lower-than-typical topic coverage"],
        default="Near overall topic coverage",
    )

    analysis["sentiment_pattern"] = np.select(
        [analysis["sentiment_difference"] >= 0.15, analysis["sentiment_difference"] <= -0.15],
        ["More positive than topic average", "More negative than topic average"],
        default="Close to topic average",
    )

    analysis = analysis.sort_values(
        ["source", "framing_signal", "source_topic_articles"], ascending=[True, False, False]
    ).reset_index(drop=True)

    print(f"Sources analyzed: {len(valid_sources)}")
    print(f"Source/topic comparisons: {len(analysis)}")
    print("\nTop source framing signals:")
    print(analysis[["source", "cluster_label", "topic_emphasis_ratio", "sentiment_difference",
                    "framing_signal", "distinctive_keywords"]].head(10).to_string(index=False))

    return analysis


def save_results(df, clusters_df, pairs_df, trends_df, signals_df, source_analysis_df):
    os.makedirs(DATA_FOLDER, exist_ok=True)

    output = df.copy()
    output["date"] = output["date"].astype(str).replace("NaT", "")
    output["date_only"] = output["date_only"].astype(str).replace("NaT", "").replace("None", "")

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
    source_analysis_df.to_csv(SOURCE_ANALYSIS_FILE, index=False)

    print("\nSaved:")
    for file in [ARTICLES_ML_FILE, CLUSTERS_FILE, SIMILARITY_FILE, TRENDS_FILE, SIGNALS_FILE, SOURCE_ANALYSIS_FILE]:
        print(file)


def print_summary(df, clusters_df, pairs_df, signals_df, silhouette, source_analysis_df):
    print("\n========== ML SUMMARY ==========")
    print(f"Articles: {len(df)}")
    print(f"Clusters: {len(clusters_df)} | silhouette={silhouette:.4f}")
    print(f"Similarity pairs: {len(pairs_df)}")

    if not pairs_df.empty:
        print(f"  Cross-source: {int(pairs_df['cross_source'].sum())}")
        print(f"  Same-cluster: {int(pairs_df['same_cluster'].sum())}")

    if not signals_df.empty:
        print(f"Emerging signals: {int(signals_df['is_emerging_signal'].sum())}")

    if not source_analysis_df.empty:
        print("\nTop source framing signals:")
        print(source_analysis_df[["source", "cluster_label", "topic_emphasis_ratio",
                                  "sentiment_difference", "framing_signal"]].head(10).to_string(index=False))

    print("\nClusters:")
    print(clusters_df[["cluster_id", "article_count", "cluster_label", "avg_sentiment", "sources"]].to_string(index=False))

    if not pairs_df.empty:
        print("\nTop cross-source similar pairs:")
        for _, row in pairs_df[pairs_df["cross_source"] == 1].head(5).iterrows():
            print(f"[{row['similarity']:.3f}] "
                  f"{row['source_i']}: {str(row['title_i'])[:55]} <-> "
                  f"{row['source_j']}: {str(row['title_j'])[:55]}")


def main():
    print("Starting News Sentinel ML analysis\n")

    df, embeddings = load_data()
    df, clusters_df, silhouette = cluster_articles(df, embeddings)
    df, pairs_df = find_similar_articles(df, embeddings)
    trends_df = calculate_trends(df, clusters_df)
    signals_df = detect_emerging_topics(trends_df)
    source_analysis_df = analyze_source_framing(df, pairs_df)

    save_results(df, clusters_df, pairs_df, trends_df, signals_df, source_analysis_df)
    print_summary(df, clusters_df, pairs_df, signals_df, silhouette, source_analysis_df)

    print("\nDone.")


if __name__ == "__main__":
    main()