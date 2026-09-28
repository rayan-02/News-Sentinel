import pandas as pd
import numpy as np
import re
import os

from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer
from sentence_transformers import SentenceTransformer
import spacy


BASE_FOLDER = os.path.join(os.path.dirname(__file__), "..")
DATA_FOLDER = os.path.join(BASE_FOLDER, "data")
RAW_FILE = os.path.join(DATA_FOLDER, "articles.csv")
OUTPUT_FILE = os.path.join(DATA_FOLDER, "articles_nlp.csv")
EMBEDDINGS_FILE = os.path.join(DATA_FOLDER, "article_embeddings.npy")

SOURCE_MAP = {
    "dawn": "Dawn",
    "express tribune": "Express Tribune",
    "tribune": "Express Tribune",
    "geo news": "Geo News",
    "geo": "Geo News",
    "business recorder": "Business Recorder"
}

# NLP models
STOPWORDS = set(stopwords.words("english"))
LEMMATIZER = WordNetLemmatizer()
SENTIMENT = SentimentIntensityAnalyzer()
NLP = spacy.load("en_core_web_sm")
EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

# Entity types we want
WANTED_ENTITY_TYPES = {
    "PERSON": "person",
    "ORG": "organization",
    "GPE": "location",
    "LOC": "location",
    "DATE": "date",
    "MONEY": "money"
}

# Common locations used for NER validation
KNOWN_LOCATIONS = {
    "pakistan", "punjab", "sindh", "balochistan",
    "khyber pakhtunkhwa", "kpk", "islamabad", "karachi",
    "lahore", "rawalpindi", "peshawar", "quetta", "multan",
    "faisalabad", "gujranwala", "hyderabad", "sialkot",
    "bahawalpur", "sukkur"
}

# Common organizations used for NER validation
KNOWN_ORGANIZATIONS = {
    "government of pakistan",
    "state bank of pakistan",
    "supreme court of pakistan",
    "national assembly",
    "senate",
    "election commission of pakistan",
    "foreign office",
    "pakistan army",
    "pakistan navy",
    "pakistan air force",
    "inter-services public relations",
    "ispr",
    "pakistan peoples party",
    "ppp",
    "pakistan tehreek-e-insaf",
    "pti",
    "pakistan muslim league",
    "pml-n"
}


def load_data():
    print("Loading:", RAW_FILE)
    df = pd.read_csv(RAW_FILE)
    print("Loaded", len(df), "rows")
    return df


def clean_text(value):
    if pd.isna(value):
        return ""

    text = str(value)
    text = re.sub(r"<[^>]+>", " ", text)

    for char in ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"]:
        text = text.replace(char, "")

    return re.sub(r"\s+", " ", text).strip()


def clean_source(value):
    if pd.isna(value):
        return "Unknown"

    source = str(value).strip().lower()
    return SOURCE_MAP.get(source, str(value).strip())


def clean_category(value):
    if pd.isna(value) or not str(value).strip():
        return "uncategorized"

    return str(value).strip().lower()


# Clean and prepare the scraped data
def clean_data(df):
    print("\nCleaning data...")

    for column in ["title", "description", "text", "author"]:
        df[column] = df[column].apply(clean_text)

    df["source"] = df["source"].apply(clean_source)
    df["category"] = df["category"].apply(clean_category)
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")

    before = len(df)
    df = df[(df["title"] != "") & (df["text"] != "")]
    print("Removed", before - len(df), "rows with missing title/text")

    before = len(df)
    df = df[df["url"].notna() & (df["url"].str.strip() != "")]
    print("Removed", before - len(df), "rows with missing URL")

    before = len(df)
    df = df.drop_duplicates(subset="url", keep="first")
    print("Removed", before - len(df), "duplicate URLs")

    before = len(df)
    df = df.drop_duplicates(subset=["source", "title"], keep="first")
    print("Removed", before - len(df), "duplicate title/source pairs")

    before = len(df)
    df = df[df["text"].str.len() >= 200]
    print("Removed", before - len(df), "articles that were too short")

    df["author"] = df["author"].replace("", "Unknown")
    df["category"] = df["category"].replace("", "uncategorized")
    df["date_only"] = df["date"].dt.date
    df["word_count"] = df["text"].str.split().str.len()

    return df.sort_values("date", ascending=False).reset_index(drop=True)


def preprocess(text):
    if pd.isna(text):
        return []

    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    tokens = word_tokenize(text)

    return [
        LEMMATIZER.lemmatize(token)
        for token in tokens
        if token not in STOPWORDS and len(token) > 2
    ]


def compute_tfidf(cleaned_texts, top_n=12):
    print("\nComputing TF-IDF...")

    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2)
    )

    matrix = vectorizer.fit_transform(cleaned_texts)
    feature_names = np.array(vectorizer.get_feature_names_out())

    results = []

    for row in matrix:
        scores = row.toarray().flatten()
        top_indices = scores.argsort()[::-1][:top_n]

        keywords = [
            feature_names[i]
            for i in top_indices
            if scores[i] > 0
        ]

        results.append(", ".join(keywords))

    return results


def extract_ngrams(cleaned_texts, ngram_range=(2, 3), top_n=5):
    print("Extracting important phrases...")

    vectorizer = CountVectorizer(
        ngram_range=ngram_range,
        max_features=3000
    )

    matrix = vectorizer.fit_transform(cleaned_texts)
    feature_names = np.array(vectorizer.get_feature_names_out())

    results = []

    for row in matrix:
        scores = row.toarray().flatten()
        top_indices = scores.argsort()[::-1][:top_n]

        phrases = [
            feature_names[i]
            for i in top_indices
            if scores[i] > 0
        ]

        results.append(", ".join(phrases))

    return results


def create_embeddings(texts):
    print("\nCreating semantic embeddings...")

    embeddings = EMBEDDING_MODEL.encode(
        texts,
        show_progress_bar=True
    )

    embeddings = np.array(embeddings)

    np.save(EMBEDDINGS_FILE, embeddings)

    print("Saved embeddings:", EMBEDDINGS_FILE)
    print("Embedding shape:", embeddings.shape)

    return embeddings


def get_sentiment(text):
    if pd.isna(text) or str(text).strip() == "":
        return 0.0, "Neutral"

    score = SENTIMENT.polarity_scores(str(text))["compound"]

    if score >= 0.05:
        label = "Positive"
    elif score <= -0.05:
        label = "Negative"
    else:
        label = "Neutral"

    return score, label


# Extract and validate named entities
def extract_entities(text, source=""):
    result = {
        "person": set(),
        "organization": set(),
        "location": set(),
        "date": set(),
        "money": set()
    }

    if pd.isna(text) or str(text).strip() == "":
        return result

    doc = NLP(str(text)[:5000])

    for ent in doc.ents:
        value = ent.text.strip()

        if not value or len(value) < 2:
            continue

        category = WANTED_ENTITY_TYPES.get(ent.label_)

        if not category:
            continue

        value_lower = value.lower()

        # Ignore the news source itself
        if value_lower == source.lower():
            continue

        # Correct known locations
        if value_lower in KNOWN_LOCATIONS:
            result["location"].add(value)
            continue

        # Correct known organizations
        if value_lower in KNOWN_ORGANIZATIONS:
            result["organization"].add(value)
            continue

        # Prevent obvious location mistakes
        if category in ["person", "organization"] and value_lower in KNOWN_LOCATIONS:
            continue

        result[category].add(value)

    return result


def run_nlp(df):
    print("\nPreparing article text...")

    df["full_text"] = df["title"].fillna("") + ". " + df["text"].fillna("")

    print("Preprocessing text...")

    cleaned_tokens = [
        preprocess(text)
        for text in df["full_text"]
    ]

    cleaned_texts = [
        " ".join(tokens)
        for tokens in cleaned_tokens
    ]

    df["top_keywords"] = compute_tfidf(cleaned_texts)
    df["top_phrases"] = extract_ngrams(cleaned_texts)

    create_embeddings(df["full_text"].tolist())

    print("\nRunning sentiment analysis...")

    sentiment_results = df["full_text"].apply(get_sentiment)

    df["sentiment_score"] = sentiment_results.apply(lambda x: x[0])
    df["sentiment_label"] = sentiment_results.apply(lambda x: x[1])

    print("\nRunning named entity recognition...")

    entity_results = df.apply(
        lambda row: extract_entities(row["full_text"], row["source"]),
        axis=1
    )

    df["entities_person"] = entity_results.apply(
        lambda x: ", ".join(sorted(x["person"]))
    )

    df["entities_organization"] = entity_results.apply(
        lambda x: ", ".join(sorted(x["organization"]))
    )

    df["entities_location"] = entity_results.apply(
        lambda x: ", ".join(sorted(x["location"]))
    )

    df["entities_date"] = entity_results.apply(
        lambda x: ", ".join(sorted(x["date"]))
    )

    df["entities_money"] = entity_results.apply(
        lambda x: ", ".join(sorted(x["money"]))
    )

    return df.drop(columns=["full_text"])


def save_data(df):
    os.makedirs(DATA_FOLDER, exist_ok=True)

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nSaved", len(df), "articles with NLP features")
    print("File:", OUTPUT_FILE)


def print_summary(df):
    print("\nArticles per source:")
    print(df["source"].value_counts().to_string())

    print("\nDate range:", df["date"].min(), "to", df["date"].max())
    print("Missing dates:", df["date"].isna().sum())

    print("\nAverage article length:", round(df["word_count"].mean(), 1), "words")

    print("\nSentiment distribution:")
    print(df["sentiment_label"].value_counts().to_string())


def main():
    print("Starting News Sentinel NLP\n")

    df = load_data()
    df = clean_data(df)
    df = run_nlp(df)

    save_data(df)
    print_summary(df)

    print("\nExample first article:")
    print("Title:", df.loc[0, "title"])
    print("Source:", df.loc[0, "source"])
    print("Keywords:", df.loc[0, "top_keywords"])
    print("Phrases:", df.loc[0, "top_phrases"])
    print("Sentiment:", df.loc[0, "sentiment_label"], df.loc[0, "sentiment_score"])
    print("People:", df.loc[0, "entities_person"])
    print("Organizations:", df.loc[0, "entities_organization"])
    print("Locations:", df.loc[0, "entities_location"])


if __name__ == "__main__":
    main()