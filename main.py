import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(ROOT, "data")

# stages run in this order
STAGES = {
    "scrape": ["scrapers/dawn.py", "scrapers/tribune.py", "scrapers/geo.py", "scrapers/business_recorder.py"],
    "nlp": ["nlp/nlp.py"],
    "ml": ["ml/ml_analysis.py"],
    "viz": ["visualization/dashboard_data.py"],
    "serve": ["frontend/app.py"],  # only runs when asked: python main.py serve
}
PIPELINE = ["scrape", "nlp", "ml", "viz"]

# files a stage needs before it can start
REQUIRED_FILES = {
    "ml": ["articles_nlp.csv", "article_embeddings.npy"],
    "viz": ["articles_ml.csv", "clusters_summary.csv"],
    "serve": ["dashboard/overview.json"],
}


def run_script(path):
    # same Python as main.py (so the venv is used), UTF-8 so Urdu text doesn't crash on Windows
    env = {**os.environ, "PYTHONUTF8": "1"}
    result = subprocess.run([sys.executable, os.path.join(ROOT, path)], cwd=ROOT, env=env)
    return result.returncode == 0


def run_stage(stage):
    missing = [f for f in REQUIRED_FILES.get(stage, []) if not os.path.exists(os.path.join(DATA_FOLDER, f))]
    if missing:
        print(f"Cannot run '{stage}', missing: {', '.join(missing)}. Run the earlier stages first.")
        return False

    results = []
    for script in STAGES[stage]:
        print(f"\n--- {script} ---")
        ok = run_script(script)
        if not ok:
            print(f"FAILED: {script}")
        results.append(ok)

    # if one news site is down the others still count; every other stage must fully pass
    return any(results) if stage == "scrape" else all(results)


def main():
    requested = sys.argv[1:] or PIPELINE
    unknown = [s for s in requested if s not in STAGES]
    if unknown:
        print(f"Unknown stage(s): {', '.join(unknown)}. Choose from: {', '.join(STAGES)}")
        sys.exit(1)

    selected = [s for s in STAGES if s in requested]
    print("News Sentinel pipeline:", " -> ".join(selected))
    start = time.time()

    for stage in selected:
        print(f"\n========== {stage.upper()} ==========")
        if not run_stage(stage):
            print(f"\nStage '{stage}' failed. Stopping.")
            sys.exit(1)

    print(f"\nPipeline finished in {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()