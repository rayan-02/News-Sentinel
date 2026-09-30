import json
import os

from flask import Flask, abort, jsonify, render_template, send_from_directory

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DASHBOARD_FOLDER = os.path.join(ROOT, "data", "dashboard")

PORT = 5000

PAGES = [
    ("overview", "Overview", "/"),
    ("topics", "Topics", "/topics"),
    ("trends", "Trends", "/trends"),
    ("similar", "Similar Stories", "/similar"),
    ("sources", "Source Analysis", "/sources"),
    ("articles", "Articles", "/articles"),
    ("chat", "AI Chat", "/chat"),
]

TITLES = {key: label for key, label, _ in PAGES}

API_FILES = {
    "overview",
    "topics",
    "trends",
    "similar_stories",
    "source_analysis",
    "articles",
    "manifest",
}

app = Flask(__name__)


@app.context_processor
def layout_data():
    updated = None

    manifest_path = os.path.join(DASHBOARD_FOLDER, "manifest.json")

    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
            updated = manifest.get("generated_at")

            if updated:
                updated = updated.replace("T", " ")[:16]

    except (OSError, ValueError):
        pass

    return {
        "nav": PAGES,
        "titles": TITLES,
        "updated": updated,
    }


@app.route("/")
@app.route("/overview")
def overview():
    return render_template("overview.html", page="overview")


@app.route("/topics")
def topics():
    return render_template("topics.html", page="topics")


@app.route("/trends")
def trends():
    return render_template("trends.html", page="trends")


@app.route("/similar")
def similar():
    return render_template("similar.html", page="similar")


@app.route("/sources")
def sources():
    return render_template("sources.html", page="sources")


@app.route("/articles")
def articles():
    return render_template("articles.html", page="articles")


@app.route("/chat")
def chat():
    return render_template("chat.html", page="chat")


@app.route("/api/<name>")
def api(name):
    if name not in API_FILES:
        abort(404)

    path = os.path.join(DASHBOARD_FOLDER, f"{name}.json")

    if not os.path.exists(path):
        return jsonify({
            "error": f"{name}.json not found. Run: python main.py viz"
        }), 404

    return send_from_directory(
        DASHBOARD_FOLDER,
        f"{name}.json",
        max_age=0
    )


if __name__ == "__main__":
    print(f"News Sentinel running at http://127.0.0.1:{PORT}")
    app.run(
        host="127.0.0.1",
        port=PORT,
        debug=True
    )