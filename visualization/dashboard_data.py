import json
import os
import hashlib
from dotenv import load_dotenv
from datetime import datetime, timezone

import pandas as pd
load_dotenv()

# Try to import Google Generative AI
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

BASE_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_FOLDER = os.path.join(BASE_FOLDER, "data")
OUTPUT_FOLDER = os.path.join(DATA_FOLDER, "dashboard")

INPUT_FILES = {
    "articles": "articles_ml.csv",
    "clusters": "clusters_summary.csv",
    "pairs": "similarity_top_pairs.csv",
    "trends": "topic_trends.csv",
    "signals": "emerging_signals.csv",
    "sources": "source_analysis.csv",
}

TOP_N = 5
MAX_PAIRS = 500
EVIDENCE_ARTICLES = 3
DISCLAIMER = "These are measurable differences in coverage, not a verdict on whether an outlet is biased."

# Cache file for topic names
TOPIC_NAMES_CACHE = os.path.join(OUTPUT_FOLDER, "topic_names.json")


def load_topic_names_cache():
    """Load the topic names cache from disk."""
    if os.path.exists(TOPIC_NAMES_CACHE):
        try:
            with open(TOPIC_NAMES_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load topic names cache: {e}")
    return {}


def save_topic_names_cache(cache):
    """Save the topic names cache to disk."""
    try:
        with open(TOPIC_NAMES_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: Could not save topic names cache: {e}")


def compute_topic_hash(cluster_data):
    """
    Compute a hash for the topic data to detect changes.
    We'll use keywords, phrases, and maybe sample article titles if available.
    For now, we use keywords and phrases from the cluster data.
    """
    # Create a string representation of the data we want to hash
    hash_str = ""
    if "top_keywords" in cluster_data:
        hash_str += "keywords:" + ",".join(sorted(cluster_data["top_keywords"])) + "|"
    if "top_phrases" in cluster_data:
        hash_str += "phrases:" + ",".join(sorted(cluster_data["top_phrases"])) + "|"
    # We could also include sample article titles, but for simplicity we stick to keywords and phrases
    return hashlib.md5(hash_str.encode()).hexdigest()


def get_topic_name_from_gemini(cluster_data, cache):
    """
    Get a human-readable topic name and description from Gemini, using caching.
    Returns a tuple (name, description).
    If Gemini is not available or fails, returns (None, None).
    """
    if not GENAI_AVAILABLE:
        return None, None

    # Check if we have a valid cached entry
    cluster_id = str(cluster_data.get("cluster_id", ""))
    if cluster_id in cache:
        cached_entry = cache[cluster_id]
        # If we have a hash, compare it to see if the data has changed
        if "hash" in cached_entry:
            current_hash = compute_topic_hash(cluster_data)
            if cached_entry["hash"] == current_hash:
                return cached_entry.get("name"), cached_entry.get("description")

    # If we get here, we need to call Gemini (or use fallback)
    try:
        # Configure Gemini with API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("Warning: GEMINI_API_KEY not set in environment")
            return None, None

        genai.configure(api_key=api_key)

        # Prepare the prompt
        prompt = f"""
        Given the following information about a news topic cluster, generate a short, human-readable topic name and a brief description (one or two sentences).
        The name should be concise and suitable for a dashboard label.
        The description should explain what the topic is about.

        Cluster ID: {cluster_data.get('cluster_id')}
        Keywords: {', '.join(cluster_data.get('top_keywords', []))}
        Phrases: {', '.join(cluster_data.get('top_phrases', []))}
        Sample article titles: {', '.join(cluster_data.get('sample_titles', [])[:3])}
        Article count: {cluster_data.get('article_count', 0)}

        Please respond in JSON format with two fields: "topic_name" and "topic_description".
        Example: {{"topic_name": "Economy & Oil Prices", "topic_description": "Discussions about fuel prices, inflation, and economic indicators."}}
        """

        # Use the Gemini model
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)

        # Try to parse the response as JSON
        response_text = response.text.strip()
        # Remove any markdown code block markers if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        result = json.loads(response_text)
        topic_name = result.get("topic_name")
        topic_description = result.get("topic_description")

        # Update the cache
        if cluster_id not in cache:
            cache[cluster_id] = {}
        cache[cluster_id]["name"] = topic_name
        cache[cluster_id]["description"] = topic_description
        cache[cluster_id]["hash"] = compute_topic_hash(cluster_data)

        return topic_name, topic_description

    except Exception as e:
        print(f"Warning: Gemini API call failed for cluster {cluster_id}: {e}")
        return None, None


def load_inputs():
    data, warnings = {}, []

    for name, filename in INPUT_FILES.items():
        try:
            data[name] = pd.read_csv(os.path.join(DATA_FOLDER, filename))
        except (FileNotFoundError, pd.errors.EmptyDataError):
            data[name] = pd.DataFrame()
            warnings.append(f"{filename} is missing or empty")

    # rows are never dropped, so the row number is the article id
    articles = data["articles"]
    if not articles.empty:
        articles["source"] = articles["source"].fillna("Unknown").astype(str).str.strip()
        articles["date_only"] = articles["date_only"].fillna("").astype(str)
        articles["sentiment_score"] = pd.to_numeric(articles["sentiment_score"], errors="coerce")

    return data, warnings


def records(df):
    # list of plain dicts (NaN becomes null)
    return json.loads(df.to_json(orient="records"))


def split_list(value):
    if pd.isna(value) or not str(value).strip():
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def article_refs(df, n=EVIDENCE_ARTICLES):
    # newest n articles with their URLs, so every number can be traced back
    df = df.sort_values("date_only", ascending=False).head(n)
    return records(df[["title", "url", "source", "date_only"]].rename(columns={"date_only": "date"}))


def build_overview(d):
    articles, clusters, trends, signals, pairs = d["articles"], d["clusters"], d["trends"], d["signals"], d["pairs"]

    flagged = signals[signals["is_emerging_signal"] == 1] if not signals.empty else signals
    dates = articles["date_only"][articles["date_only"] != ""] if not articles.empty else []

    top_trends = []
    if not trends.empty:
        latest = trends[trends["day"] == trends["day"].max()]
        top = latest.sort_values("rolling_3d", ascending=False).head(TOP_N)
        top_trends = records(top[["cluster_id", "cluster_label", "article_count", "rolling_3d", "rolling_7d"]])

    recent_pairs = []
    cross = pairs[pairs["cross_source"] == 1] if not pairs.empty else pairs
    if not cross.empty:
        cross = cross.assign(latest=cross[["date_i", "date_j"]].fillna("").astype(str).max(axis=1))
        cross = cross.sort_values(["latest", "similarity"], ascending=False).head(TOP_N)
        recent_pairs = records(cross[["similarity", "source_i", "source_j", "title_i", "title_j", "url_i", "url_j"]])

    return {
        "stats": {
            "articles": len(articles),
            "topics": len(clusters),
            "emerging": len(flagged),
            "sources": int(articles["source"].nunique()) if not articles.empty else 0,
        },
        "date_range": {"from": min(dates) if len(dates) else None, "to": max(dates) if len(dates) else None},
        "topic_sizes": records(clusters[["cluster_id", "cluster_label", "article_count"]]) if not clusters.empty else [],
        "sentiment_counts": articles["sentiment_label"].value_counts().to_dict() if not articles.empty else {},
        "articles_per_source": [{"source": s, "articles": int(n)} for s, n in articles["source"].value_counts().items()] if not articles.empty else [],
        "top_trends": top_trends,
        "emerging_topics": records(flagged.head(TOP_N)[
            ["cluster_id", "cluster_label", "share_lift", "recent_articles", "baseline_articles", "recent_share"]
        ]) if not flagged.empty else [],
        "recent_cross_source_pairs": recent_pairs,
    }


def build_topics(d):
    articles, clusters = d["articles"], d["clusters"]
    if clusters.empty:
        return {"topics": []}

    total = int(clusters["article_count"].sum())
    topics = []

    # Load the topic names cache
    cache = load_topic_names_cache()

    for row in records(clusters):
        members = articles[articles["cluster_id"] == row["cluster_id"]]

        # "Dawn:12, Geo News:3" -> {"Dawn": 12, "Geo News": 3}
        sources = {}
        for item in split_list(row["sources"]):
            name, _, count = item.rpartition(":")
            sources[name] = int(count)

        # Prepare cluster data for Gemini (we'll add sample article titles later if needed)
        cluster_data = {
            "cluster_id": row["cluster_id"],
            "top_keywords": split_list(row["top_keywords"]),
            "top_phrases": split_list(row["top_phrases"]),
            # We don't have sample article titles in the cluster row, but we can get them from members
            "sample_titles": split_list(row["sample_titles"]) if "sample_titles" in row else [],
            "article_count": row["article_count"],
        }

        # Get human-readable name and description from Gemini (with caching)
        topic_name, topic_description = get_topic_name_from_gemini(cluster_data, cache)

        # Fallback to the ML label if Gemini didn't return a name
        if not topic_name:
            topic_name = row["cluster_label"]
        if not topic_description:
            topic_description = ""  # We can leave it empty or generate a default from keywords

        topics.append({
            "cluster_id": row["cluster_id"],
            "label": row["cluster_label"],  # Keep the original ML label
            "topic_name": topic_name,
            "topic_description": topic_description,
            "article_count": row["article_count"],
            "share_of_articles": round(row["article_count"] / total, 4) if total else 0,
            "keywords": split_list(row["top_keywords"]),
            "phrases": split_list(row["top_phrases"]),
            "avg_sentiment": row["avg_sentiment"],
            "sentiment_counts": {"Positive": row["pos_count"], "Negative": row["neg_count"], "Neutral": row["neu_count"]},
            "sources": sources,
            "sample_articles": article_refs(members) if not members.empty else [],
        })

    # Save the updated cache
    save_topic_names_cache(cache)

    return {"topics": topics}


def build_trends(d):
    trends = d["trends"]
    if trends.empty:
        return {"days": [], "series": []}

    def pivot(column):
        return trends.pivot(index="day", columns="cluster_id", values=column).sort_index().fillna(0)

    counts, roll_3d, roll_7d = pivot("article_count"), pivot("rolling_3d"), pivot("rolling_7d")
    labels = trends.drop_duplicates("cluster_id").set_index("cluster_id")["cluster_label"]

    series = [{
        "cluster_id": int(cid),
        "label": labels[cid],
        "counts": counts[cid].astype(int).tolist(),
        "rolling_3d": roll_3d[cid].round(2).tolist(),
        "rolling_7d": roll_7d[cid].round(2).tolist(),
    } for cid in counts.columns]

    return {"days": [str(day) for day in counts.index], "series": series}


def build_similar_stories(d):
    pairs = d["pairs"]
    if pairs.empty:
        return {"total_pairs": 0, "cross_source_pairs": 0, "pairs": []}

    top = pairs.sort_values("similarity", ascending=False).head(MAX_PAIRS)
    return {"total_pairs": len(pairs), "cross_source_pairs": int(pairs["cross_source"].sum()), "pairs": records(top)}


def build_source_analysis(d):
    articles, sa = d["articles"], d["sources"]
    result = {"disclaimer": DISCLAIMER, "notes": [], "sources": [], "topics": []}

    if not articles.empty:
        summary = (articles.groupby("source")
                   .agg(articles=("title", "size"), avg_sentiment=("sentiment_score", "mean"))
                   .round(4).reset_index().sort_values("articles", ascending=False))
        result["sources"] = records(summary)

    if sa.empty:
        return result

    result["notes"].append("Outlets with very few articles on a topic are left out, so shares may not add up to 100%.")
    sa = sa.assign(coverage_share=(sa["source_topic_articles"] / sa["topic_articles_all_sources"]).round(4))

    # Load the topic names cache to get human-readable names for topics
    cache = load_topic_names_cache()

    for cluster_id, group in sa.groupby("cluster_id"):
        rows = []
        for r in records(group.sort_values("coverage_share", ascending=False)):
            evidence = articles[(articles["source"] == r["source"]) & (articles["cluster_id"] == cluster_id)]
            rows.append({
                "source": r["source"],
                "articles": r["source_topic_articles"],
                "coverage_share": r["coverage_share"],
                "emphasis_ratio": r["topic_emphasis_ratio"],
                "coverage_pattern": r["coverage_pattern"],
                "avg_sentiment": r["source_avg_sentiment"],
                "topic_avg_sentiment": r["topic_avg_sentiment"],
                "sentiment_difference": r["sentiment_difference"],
                "sentiment_pattern": r["sentiment_pattern"],
                "distinctive_keywords": split_list(r["distinctive_keywords"]),
                "distinctive_phrases": split_list(r["distinctive_phrases"]),
                "same_event_matches": r["cross_source_similar_pairs"],
                "evidence": article_refs(evidence) if not evidence.empty else [],
            })

        # Get the human-readable name and description for this topic from the cache
        cluster_id_str = str(cluster_id)
        topic_name = cache.get(cluster_id_str, {}).get("name", group["cluster_label"].iloc[0])
        topic_description = cache.get(cluster_id_str, {}).get("description", "")

        result["topics"].append({
            "cluster_id": int(cluster_id),
            "label": group["cluster_label"].iloc[0],  # Keep the original ML label
            "topic_name": topic_name,
            "topic_description": topic_description,
            "topic_articles": int(group["topic_articles_all_sources"].iloc[0]),
            "sources": rows,
        })

    # Save the updated cache (though we didn't modify it in this function, we might have read it)
    save_topic_names_cache(cache)

    return result


def build_articles(d):
    articles = d["articles"]
    if articles.empty:
        return {"filters": {}, "articles": []}

    columns = ["date_only", "source", "title", "url", "cluster_id", "cluster_label",
               "sentiment_label", "sentiment_score", "top_keywords", "similar_ids"]

    table = articles.reset_index().rename(columns={"index": "id"})
    table = table[["id"] + columns].rename(columns={"date_only": "date"}).sort_values("date", ascending=False)

    rows = records(table)
    for row in rows:
        row["top_keywords"] = split_list(row["top_keywords"])
        row["similar_ids"] = [int(i) for i in split_list(row["similar_ids"])]

    dates = articles["date_only"][articles["date_only"] != ""]
    filters = {
        "sources": sorted(articles["source"].unique().tolist()),
        "topics": records(articles[["cluster_id", "cluster_label"]].drop_duplicates().sort_values("cluster_id")),
        "sentiments": sorted(articles["sentiment_label"].dropna().unique().tolist()),
        "date_from": min(dates) if len(dates) else None,
        "date_to": max(dates) if len(dates) else None,
    }

    return {"filters": filters, "articles": rows}


def save_json(filename, payload):
    path = os.path.join(OUTPUT_FOLDER, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, allow_nan=False)
    print("Saved:", path)


def main():
    print("Building dashboard data\n")

    data, warnings = load_inputs()
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    outputs = {
        "overview.json": build_overview(data),
        "topics.json": build_topics(data),
        "trends.json": build_trends(data),
        "similar_stories.json": build_similar_stories(data),
        "source_analysis.json": build_source_analysis(data),
        "articles.json": build_articles(data),
    }

    for filename, payload in outputs.items():
        save_json(filename, payload)

    save_json("manifest.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stats": outputs["overview.json"]["stats"],
        "files": list(outputs),
        "warnings": warnings,
    })

    for warning in warnings:
        print("Warning:", warning)
    print("\nDone.")


if __name__ == "__main__":
    main()