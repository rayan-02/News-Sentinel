const pairsBox = document.getElementById("similar-pairs");
const pairCount = document.getElementById("pair-count");
const errorBox = document.getElementById("similar-error");

async function loadSimilarStories() {
    try {
        const response = await fetch("/api/similar_stories");

        if (!response.ok) {
            throw new Error("similar_stories.json could not be loaded");
        }

        const data = await response.json();

        renderPairCount(data);
        renderPairs(data.pairs || []);

    } catch (error) {
        console.error(error);

        errorBox.textContent =
            `Similar story data could not be loaded: ${error.message}`;

        errorBox.hidden = false;

        pairsBox.innerHTML = `
            <div class="empty">
                No similar story data is currently available.
            </div>
        `;
    }
}

function renderPairCount(data) {
    const total = Number(data.cross_source_pairs || 0);

    pairCount.textContent = `${formatNumber(total)} cross-source pairs`;
}

function renderPairs(pairs) {
    if (!pairs.length) {
        pairsBox.innerHTML = `
            <div class="empty">
                No similar stories were found.
            </div>
        `;

        return;
    }

    pairsBox.innerHTML = pairs.map(pair => {
        const similarity = Number(pair.similarity || 0) * 100;

        return `
            <article class="similar-card">

                <div class="similar-header">

                    <div>
                        <span class="topic-id">
                            SEMANTIC MATCH
                        </span>

                        <div class="similar-sources">
                            ${escapeHTML(pair.source_i || "Source")}
                            <span>↔</span>
                            ${escapeHTML(pair.source_j || "Source")}
                        </div>
                    </div>

                    <div class="similar-score">
                        ${similarity.toFixed(1)}%
                        <small>similarity</small>
                    </div>

                </div>

                <div class="similar-articles">

                    <div class="similar-article">
                        <span class="source-label">
                            ${escapeHTML(pair.source_i || "Source")}
                        </span>

                        <a
                            href="${safeURL(pair.url_i)}"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            ${escapeHTML(
                                pair.title_i || "Untitled article"
                            )}
                        </a>
                    </div>

                    <div class="similar-divider">
                        <span>VS</span>
                    </div>

                    <div class="similar-article">
                        <span class="source-label">
                            ${escapeHTML(pair.source_j || "Source")}
                        </span>

                        <a
                            href="${safeURL(pair.url_j)}"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            ${escapeHTML(
                                pair.title_j || "Untitled article"
                            )}
                        </a>
                    </div>

                </div>

                <div class="similar-meter">

                    <div class="track">
                        <div
                            class="fill"
                            style="width:${Math.min(similarity, 100)}%"
                        ></div>
                    </div>

                    <span>
                        Cosine similarity
                    </span>

                </div>

            </article>
        `;
    }).join("");
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString();
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    }[character]));
}

function safeURL(value) {
    if (!value) {
        return "#";
    }

    try {
        const url = new URL(value, window.location.origin);

        if (url.protocol === "http:" || url.protocol === "https:") {
            return url.href;
        }

        return "#";
    } catch {
        return "#";
    }
}

document.addEventListener("DOMContentLoaded", loadSimilarStories);