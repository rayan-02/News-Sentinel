import json,os,hashlib
from datetime import datetime,timezone
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
DATA=os.path.join(ROOT,"data")
DASHBOARD=os.path.join(DATA,"dashboard")
NLP_FILE=os.path.join(DATA,"articles_nlp.csv")
ML_FILE=os.path.join(DATA,"articles_ml.csv")
EMBEDDINGS=os.path.join(DATA,"article_embeddings.npy")

GEMINI_MODEL="gemini-2.5-flash"
TOPIC_ARTICLES_FOR_AI=8

os.makedirs(DASHBOARD,exist_ok=True)

def save_json(name,data):
    with open(os.path.join(DASHBOARD,name),"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2,default=str)

def load_csv():
    if os.path.exists(ML_FILE):
        return pd.read_csv(ML_FILE)
    return pd.read_csv(NLP_FILE)

def clean_value(value):
    if pd.isna(value):
        return ""
    return str(value).strip()

def split_terms(value):
    return [x.strip() for x in clean_value(value).split(",") if x.strip()]

def compute_topic_hash(keywords,phrases,titles,sources,count):
    data=json.dumps({
        "keywords":keywords,"phrases":phrases,"titles":titles,
        "sources":sources,"count":count
    },sort_keys=True)
    return hashlib.md5(data.encode()).hexdigest()

def load_topic_cache():
    path=os.path.join(DASHBOARD,"topic_names_cache.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path,encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_topic_cache(cache):
    save_json("topic_names_cache.json",cache)

def get_topic_name_from_gemini(cluster_id,keywords,phrases,titles,sources,count,cache):
    topic_hash=compute_topic_hash(keywords,phrases,titles,sources,count)
    if str(cluster_id) in cache and cache[str(cluster_id)].get("hash")==topic_hash:
        return cache[str(cluster_id)]["name"],cache[str(cluster_id)]["description"]

    api_key=os.getenv("GEMINI_API_KEY")
    if not api_key:
        return f"Topic {cluster_id}", "Topic name could not be generated because GEMINI_API_KEY is missing."

    prompt=f"""
You are analyzing Pakistani news articles grouped into one machine-learning topic cluster.

Give this cluster a clear, human-readable topic name based on the ACTUAL ARTICLE TITLES and the supporting terms.

Do NOT:
- combine keywords into a meaningless phrase
- use generic names like "Pakistan News", "Current Affairs", or "Political News"
- invent events that are not supported by the titles

The name should identify the actual subject, event, issue, person, organization, policy, or development covered by the articles.

Return:
1. name: short topic name, preferably 3-8 words
2. description: one short sentence explaining the topic

Cluster ID: {cluster_id}
Article count: {count}
Keywords: {", ".join(keywords)}
Phrases: {", ".join(phrases)}
Sources: {", ".join(sources)}
Actual article titles:
{chr(10).join("- "+x for x in titles)}
"""

    try:
        client=genai.Client(api_key=api_key)
        response=client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type":"object",
                    "properties":{
                        "name":{"type":"string"},
                        "description":{"type":"string"}
                    },
                    "required":["name","description"]
                }
            )
        )
        result=json.loads(response.text)
        name=clean_value(result.get("name")) or f"Topic {cluster_id}"
        description=clean_value(result.get("description"))
        cache[str(cluster_id)]={"hash":topic_hash,"name":name,"description":description}
        return name,description
    except Exception as e:
        print(f"Gemini topic naming failed for cluster {cluster_id}: {e}")
        return f"Topic {cluster_id}", "Topic name could not be generated."

def get_cluster_topic_names(df):
    cache=load_topic_cache()
    names={}

    for cluster_id,group in df.groupby("cluster_id"):
        keywords=[]
        phrases=[]
        titles=[]
        sources=[]

        for value in group.get("keywords",[]):
            keywords.extend(split_terms(value))
        for value in group.get("phrases",[]):
            phrases.extend(split_terms(value))

        if "title" in group:
            titles=group["title"].dropna().astype(str).head(TOPIC_ARTICLES_FOR_AI).tolist()

        if "source" in group:
            sources=group["source"].dropna().astype(str).unique().tolist()

        keywords=list(dict.fromkeys(keywords))[:15]
        phrases=list(dict.fromkeys(phrases))[:10]

        name,description=get_topic_name_from_gemini(
            cluster_id,keywords,phrases,titles,sources,len(group),cache
        )
        names[str(cluster_id)]={"name":name,"description":description}

    save_topic_cache(cache)
    return names

def build_overview(df,topic_names):
    sentiment=df["sentiment_label"].value_counts().to_dict() if "sentiment_label" in df else {}
    topics=[]
    for cluster_id,group in df.groupby("cluster_id"):
        info=topic_names.get(str(cluster_id),{})
        topics.append({
            "cluster_id":int(cluster_id),
            "label":clean_value(group["cluster_label"].iloc[0]) if "cluster_label" in group else f"Topic {cluster_id}",
            "topic_name":info.get("name",f"Topic {cluster_id}"),
            "topic_description":info.get("description",""),
            "article_count":len(group)
        })
    topics.sort(key=lambda x:x["article_count"],reverse=True)

    return {
        "total_articles":len(df),
        "total_topics":df["cluster_id"].nunique(),
        "sources":df["source"].nunique() if "source" in df else 0,
        "sentiment":sentiment,
        "topics":topics,
        "generated_at":datetime.now(timezone.utc).isoformat()
    }

def build_topics(df,topic_names):
    result=[]
    total=len(df)

    for cluster_id,group in df.groupby("cluster_id"):
        info=topic_names.get(str(cluster_id),{})
        keywords=[]
        phrases=[]

        for value in group.get("keywords",[]):
            keywords.extend(split_terms(value))
        for value in group.get("phrases",[]):
            phrases.extend(split_terms(value))

        keyword_counts=pd.Series(keywords).value_counts().head(10).to_dict() if keywords else {}
        phrase_counts=pd.Series(phrases).value_counts().head(10).to_dict() if phrases else {}

        sentiment_counts=group["sentiment_label"].value_counts().to_dict() if "sentiment_label" in group else {}
        sources=group["source"].value_counts().to_dict() if "source" in group else {}

        samples=[]
        for _,row in group.head(5).iterrows():
            samples.append({
                "title":clean_value(row.get("title")),
                "source":clean_value(row.get("source")),
                "url":clean_value(row.get("url"))
            })

        result.append({
            "cluster_id":int(cluster_id),
            "label":clean_value(group["cluster_label"].iloc[0]) if "cluster_label" in group else f"Topic {cluster_id}",
            "topic_name":info.get("name",f"Topic {cluster_id}"),
            "topic_description":info.get("description",""),
            "article_count":len(group),
            "share_of_articles":len(group)/total if total else 0,
            "keywords":keyword_counts,
            "phrases":phrase_counts,
            "sentiment_counts":sentiment_counts,
            "avg_sentiment":float(group["sentiment_score"].mean()) if "sentiment_score" in group else 0,
            "sources":sources,
            "sample_articles":samples
        })

    result.sort(key=lambda x:x["article_count"],reverse=True)
    return {"topics":result}

def build_trends(df,topic_names):
    if "published_at" not in df:
        return {"topics":[],"daily":[]}

    df=df.copy()
    df["published_at"]=pd.to_datetime(df["published_at"],errors="coerce")
    df=df.dropna(subset=["published_at"])
    df["date"]=df["published_at"].dt.date.astype(str)

    daily=df.groupby("date").size().reset_index(name="count")
    daily=daily.sort_values("date")

    topics=[]
    for cluster_id,group in df.groupby("cluster_id"):
        info=topic_names.get(str(cluster_id),{})
        counts=group.groupby("date").size().to_dict()
        topics.append({
            "cluster_id":int(cluster_id),
            "topic_name":info.get("name",f"Topic {cluster_id}"),
            "label":clean_value(group["cluster_label"].iloc[0]) if "cluster_label" in group else f"Topic {cluster_id}",
            "counts":counts,
            "total":len(group)
        })

    return {"daily":daily.to_dict("records"),"topics":topics}

def build_similar(df):
    columns=["source_i","source_j","similarity","url_i","url_j","title_i","title_j"]
    if not all(x in df.columns for x in columns):
        return {"pairs":[]}
    return {"pairs":df[columns].to_dict("records")}

def build_source_analysis(df,topic_names):
    sources=[]

    for source,group in df.groupby("source"):
        sources.append({
            "source":source,
            "articles":len(group),
            "avg_sentiment":float(group["sentiment_score"].mean()) if "sentiment_score" in group else 0
        })

    topics=[]
    for cluster_id,group in df.groupby("cluster_id"):
        info=topic_names.get(str(cluster_id),{})
        overall=len(group)/len(df) if len(df) else 0

        for source,source_group in group.groupby("source"):
            coverage=len(source_group)/len(group) if len(group) else 0
            topics.append({
                "cluster_id":int(cluster_id),
                "topic_name":info.get("name",f"Topic {cluster_id}"),
                "source":source,
                "articles":len(source_group),
                "coverage_share":coverage,
                "emphasis_ratio":coverage/overall if overall else 0,
                "avg_sentiment":float(source_group["sentiment_score"].mean()) if "sentiment_score" in source_group else 0,
                "topic_avg_sentiment":float(group["sentiment_score"].mean()) if "sentiment_score" in group else 0,
                "sentiment_difference":float(source_group["sentiment_score"].mean()-group["sentiment_score"].mean()) if "sentiment_score" in group else 0
            })

    return {"sources":sources,"topics":topics}

def build_articles(df,topic_names):
    articles=[]

    for _,row in df.iterrows():
        cluster_id=row.get("cluster_id")
        info=topic_names.get(str(cluster_id),{})

        articles.append({
            "title":clean_value(row.get("title")),
            "url":clean_value(row.get("url")),
            "source":clean_value(row.get("source")),
            "published_at":clean_value(row.get("published_at")),
            "cluster_id":int(cluster_id) if pd.notna(cluster_id) else None,
            "cluster_label":clean_value(row.get("cluster_label")),
            "topic_name":info.get("name",f"Topic {cluster_id}"),
            "sentiment_label":clean_value(row.get("sentiment_label")),
            "sentiment_score":row.get("sentiment_score"),
            "keywords":split_terms(row.get("keywords")),
            "phrases":split_terms(row.get("phrases"))
        })

    return {"articles":articles}

def main():
    print("Loading articles...")
    df=load_csv()
    print(f"Loaded {len(df)} articles.")

    print("Generating topic names...")
    topic_names=get_cluster_topic_names(df)

    print("Building dashboard data...")
    save_json("overview.json",build_overview(df,topic_names))
    save_json("topics.json",build_topics(df,topic_names))
    save_json("trends.json",build_trends(df,topic_names))
    save_json("similar_stories.json",build_similar(df))
    save_json("source_analysis.json",build_source_analysis(df,topic_names))
    save_json("articles.json",build_articles(df,topic_names))

    save_json("manifest.json",{
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "articles":len(df),
        "topics":len(topic_names)
    })

    print("Dashboard data generated successfully.")

if __name__=="__main__":
    main()