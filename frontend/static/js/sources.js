const sourceStats = document.getElementById("source-stats");
const sourceSummary = document.getElementById("source-summary");
const sourceTopics = document.getElementById("source-topics");
const disclaimer = document.getElementById("source-disclaimer");
const errorBox = document.getElementById("sources-error");

async function loadSources() {
    try {
        const response = await fetch("/api/source_analysis");

        if (!response.ok) {
            throw new Error("source_analysis.json could not be loaded");
        }

        const data = await response.json();

        renderDisclaimer(data);
        renderStats(data);
        renderSources(data.sources || []);
        renderTopics(data.topics || []);

    } catch (error) {
        console.error(error);

        errorBox.textContent =
            `Source analysis could not be loaded: ${error.message}`;

        errorBox.hidden = false;

        sourceSummary.innerHTML = `
            <div class="empty">
                No source data is currently available.
            </div>
        `;

        sourceTopics.innerHTML = `
            <div class="empty">
                No topic analysis is currently available.
            </div>
        `;
    }
}

function renderDisclaimer(data) {
    disclaimer.textContent =
        data.disclaimer ||
        "These are measurable differences in coverage, not a verdict on whether an outlet is biased.";
}

function renderStats(data) {
    const sources = data.sources || [];
    const topics = data.topics || [];

    const values = sourceStats.querySelectorAll(".stat-value");

    if (values.length < 3) {
        return;
    }

    values[0].textContent = formatNumber(sources.length);
    values[1].textContent = formatNumber(topics.length);

    const totalArticles = sources.reduce(
        (total, source) => total + Number(source.articles || 0),
        0
    );

    values[2].textContent = formatNumber(totalArticles);
}

function renderSources(sources) {
    if (!sources.length) {
        sourceSummary.innerHTML = `
            <div class="empty">
                No source summaries were found.
            </div>
        `;

        return;
    }

    const maxArticles = Math.max(
        ...sources.map(source => Number(source.articles || 0)),
        1
    );

    sourceSummary.innerHTML = sources.map(source => {
        const articles = Number(source.articles || 0);
        const sentiment = source.avg_sentiment;

        return `
            <div class="source-analysis-topic">

                <div class="source-analysis-header">
                    <h3>
                        ${escapeHTML(source.source || "Unknown source")}
                    </h3>

                    <strong>
                        ${formatNumber(articles)} articles
                    </strong>
                </div>

                <div class="bar-row">

                    <div class="line">
                        <span>Article volume</span>
                        <span class="val">${formatNumber(articles)}</span>
                    </div>

                    <div class="track">
                        <div
                            class="fill"
                            style="width:${articles / maxArticles * 100}%"
                        ></div>
                    </div>

                </div>

                <div class="analysis-grid">

                    <div class="analysis-item">
                        <strong>Average sentiment</strong>
                        <span>
                            ${formatSentiment(sentiment)}
                        </span>
                    </div>

                    <div class="analysis-item">
                        <strong>Coverage</strong>
                        <span>
                            ${formatNumber(articles)} analyzed articles
                        </span>
                    </div>

                </div>

            </div>
        `;
    }).join("");
}

function renderTopics(topics) {
    if (!topics.length) {
        sourceTopics.innerHTML = `
            <div class="empty">
                No topic-level source analysis was found.
            </div>
        `;

        return;
    }

    sourceTopics.innerHTML = topics.map(topic => {
        const topicSources = topic.sources || [];

        return `
            <div class="source-analysis-topic">

                <div class="source-analysis-header">

                    <div>
                        <span class="topic-id">
                            TOPIC ${String(topic.cluster_id).padStart(2, "0")}
                        </span>

                        <h3>
                            ${escapeHTML(topic.label || "Unnamed topic")}
                        </h3>
                    </div>

                </div>

                ${
                    topicSources.length
                        ? topicSources.map(source =>
                            renderTopicSource(source)
                        ).join("")
                        : `
                            <div class="empty">
                                No source comparisons available.
                            </div>
                        `
                }

            </div>
        `;
    }).join("");
}

function renderTopicSource(source) {
    const keywords = source.distinctive_keywords || [];
    const phrases = source.distinctive_phrases || [];
    const evidence = source.evidence || [];

    return `
        <div class="analysis-source">

            <div class="source-analysis-header">

                <strong>
                    ${escapeHTML(source.source || "Unknown source")}
                </strong>

                <span class="badge">
                    ${escapeHTML(source.coverage_pattern || "No pattern")}
                </span>

            </div>

            <div class="analysis-grid">

                <div class="analysis-item">
                    <strong>Articles</strong>
                    <span>
                        ${formatNumber(source.articles)}
                    </span>
                </div>

                <div class="analysis-item">
                    <strong>Coverage share</strong>
                    <span>
                        ${formatPercent(source.coverage_share)}
                    </span>
                </div>

                <div class="analysis-item">
                    <strong>Emphasis ratio</strong>
                    <span>
                        ${formatNumber(source.emphasis_ratio)}
                    </span>
                </div>

                <div class="analysis-item">
                    <strong>Sentiment difference</strong>
                    <span>
                        ${formatSigned(source.sentiment_difference)}
                    </span>
                </div>

            </div>

            <div class="analysis-grid">

                <div class="analysis-item">
                    <strong>Sentiment pattern</strong>
                    <span>
                        ${escapeHTML(
                            source.sentiment_pattern || "No pattern"
                        )}
                    </span>
                </div>

                <div class="analysis-item">
                    <strong>Same-event matches</strong>
                    <span>
                        ${formatNumber(source.same_event_matches)}
                    </span>
                </div>

            </div>

            ${
                keywords.length
                    ? `
                        <div class="topic-section">
                            <span class="section-label">
                                Distinctive keywords
                            </span>

                            <div class="chips">
                                ${keywords.map(keyword => `
                                    <span class="chip">
                                        ${escapeHTML(keyword)}
                                    </span>
                                `).join("")}
                            </div>
                        </div>
                    `
                    : ""
            }

            ${
                phrases.length
                    ? `
                        <div class="topic-section">
                            <span class="section-label">
                                Distinctive phrases
                            </span>

                            <div class="phrases">
                                ${phrases.map(phrase => `
                                    <span>
                                        ${escapeHTML(phrase)}
                                    </span>
                                `).join("")}
                            </div>
                        </div>
                    `
                    : ""
            }

            ${
                evidence.length
                    ? `
                        <div class="topic-section">
                            <span class="section-label">
                                Evidence articles
                            </span>

                            <div class="sample-articles">
                                ${evidence.map(article => `
                                    <a
                                        href="${safeURL(article.url)}"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        <strong>
                                            ${escapeHTML(
                                                article.title ||
                                                "Untitled article"
                                            )}
                                        </strong>

                                        <small>
                                            ${escapeHTML(
                                                article.source || ""
                                            )}
                                            ·
                                            ${escapeHTML(
                                                article.date || ""
                                            )}
                                        </small>
                                    </a>
                                `).join("")}
                            </div>
                        </div>
                    `
                    : ""
            }

        </div>
    `;
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString();
}

function formatPercent(value) {
    return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function formatSentiment(value) {
    if (value === null || value === undefined || value === "") {
        return "—";
    }

    return Number(value).toFixed(3);
}

function formatSigned(value) {
    if (value === null || value === undefined || value === "") {
        return "—";
    }

    const number = Number(value);

    if (number > 0) {
        return `+${number.toFixed(3)}`;
    }

    return number.toFixed(3);
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

document.addEventListener("DOMContentLoaded", loadSources);