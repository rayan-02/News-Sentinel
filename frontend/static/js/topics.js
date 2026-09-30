const topicGrid = document.getElementById("topics-grid");
const topicCount = document.getElementById("topic-count");
const errorBox = document.getElementById("topics-error");

async function loadTopics() {
    try {
        const response = await fetch("/api/topics");

        if (!response.ok) {
            throw new Error("topics.json could not be loaded");
        }

        const data = await response.json();
        renderTopics(data.topics || []);

    } catch (error) {
        console.error(error);

        errorBox.textContent = `Topic data could not be loaded: ${error.message}`;
        errorBox.hidden = false;

        topicGrid.innerHTML = `
            <div class="empty">
                No topic data is currently available.
            </div>
        `;
    }
}

function renderTopics(topics) {
    if (!topics.length) {
        topicCount.textContent = "0 topics";

        topicGrid.innerHTML = `
            <div class="empty">
                No topics were found.
            </div>
        `;

        return;
    }

    topicCount.textContent = `${topics.length} topics`;

    topicGrid.innerHTML = topics.map(topic => {
        const sentiment = topic.sentiment_counts || {};
        const sources = topic.sources || {};
        const keywords = topic.keywords || [];
        const phrases = topic.phrases || [];
        const articles = topic.sample_articles || [];

        const positive = Number(sentiment.Positive || 0);
        const neutral = Number(sentiment.Neutral || 0);
        const negative = Number(sentiment.Negative || 0);

        const total = positive + neutral + negative;

        const positiveWidth = total ? positive / total * 100 : 0;
        const neutralWidth = total ? neutral / total * 100 : 0;
        const negativeWidth = total ? negative / total * 100 : 0;

        return `
            <article class="topic-card">

                <div class="topic-card-header">
                    <div>
                        <span class="topic-id">
                            TOPIC ${String(topic.cluster_id).padStart(2, "0")}
                        </span>

                        <h3>${escapeHTML(topic.label || "Unnamed topic")}</h3>
                    </div>

                    <div class="topic-article-count">
                        ${formatNumber(topic.article_count)}
                        <small>articles</small>
                    </div>
                </div>

                <div class="topic-share">
                    <div class="topic-share-label">
                        <span>Share of analyzed articles</span>
                        <strong>
                            ${(Number(topic.share_of_articles || 0) * 100).toFixed(1)}%
                        </strong>
                    </div>

                    <div class="track">
                        <div
                            class="fill"
                            style="width:${Math.min(
                                Number(topic.share_of_articles || 0) * 100,
                                100
                            )}%"
                        ></div>
                    </div>
                </div>

                <div class="topic-section">
                    <span class="section-label">Keywords</span>

                    <div class="chips">
                        ${
                            keywords.length
                                ? keywords.map(keyword => `
                                    <span class="chip">
                                        ${escapeHTML(keyword)}
                                    </span>
                                `).join("")
                                : `<span class="muted">No keywords available</span>`
                        }
                    </div>
                </div>

                <div class="topic-section">
                    <span class="section-label">Key phrases</span>

                    <div class="phrases">
                        ${
                            phrases.length
                                ? phrases.map(phrase => `
                                    <span>${escapeHTML(phrase)}</span>
                                `).join("")
                                : `<span class="muted">No phrases available</span>`
                        }
                    </div>
                </div>

                <div class="topic-columns">

                    <div>
                        <span class="section-label">Sentiment</span>

                        <div class="sentiment-bar">
                            <span
                                class="positive"
                                style="width:${positiveWidth}%"
                            ></span>

                            <span
                                class="neutral"
                                style="width:${neutralWidth}%"
                            ></span>

                            <span
                                class="negative"
                                style="width:${negativeWidth}%"
                            ></span>
                        </div>

                        <div class="sentiment-values">
                            <span>Positive ${positive}</span>
                            <span>Neutral ${neutral}</span>
                            <span>Negative ${negative}</span>
                        </div>
                    </div>

                    <div>
                        <span class="section-label">Average sentiment</span>

                        <strong class="sentiment-score">
                            ${formatSentiment(topic.avg_sentiment)}
                        </strong>
                    </div>

                </div>

                <div class="topic-section">
                    <span class="section-label">Sources</span>

                    <div class="source-list">
                        ${
                            Object.entries(sources)
                                .sort((a, b) => Number(b[1]) - Number(a[1]))
                                .map(([source, count]) => `
                                    <div class="source-item">
                                        <span>${escapeHTML(source)}</span>
                                        <strong>${formatNumber(count)}</strong>
                                    </div>
                                `)
                                .join("")
                        }
                    </div>
                </div>

                <div class="topic-section">
                    <span class="section-label">Sample articles</span>

                    <div class="sample-articles">
                        ${
                            articles.length
                                ? articles.map(article => `
                                    <a
                                        href="${safeURL(article.url)}"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        <strong>
                                            ${escapeHTML(
                                                article.title || "Untitled article"
                                            )}
                                        </strong>

                                        <small>
                                            ${escapeHTML(article.source || "")}
                                            ·
                                            ${escapeHTML(article.date || "")}
                                        </small>
                                    </a>
                                `).join("")
                                : `<span class="muted">
                                    No sample articles available.
                                </span>`
                        }
                    </div>
                </div>

            </article>
        `;
    }).join("");
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString();
}

function formatSentiment(value) {
    if (value === null || value === undefined || value === "") {
        return "—";
    }

    return Number(value).toFixed(3);
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

document.addEventListener("DOMContentLoaded", loadTopics);