const articlesList = document.getElementById("articles-list");
const articleCount = document.getElementById("article-count");
const resultCount = document.getElementById("article-result-count");
const sourceFilter = document.getElementById("source-filter");
const topicFilter = document.getElementById("topic-filter");
const sentimentFilter = document.getElementById("sentiment-filter");
const searchInput = document.getElementById("article-search");
const errorBox = document.getElementById("articles-error");

let articles = [];

async function loadArticles() {
    try {
        const response = await fetch("/api/articles");

        if (!response.ok) {
            throw new Error("articles.json could not be loaded");
        }

        const data = await response.json();

        articles = data.articles || [];

        setupFilters(data.filters || {});
        renderArticles(articles);

    } catch (error) {
        console.error(error);

        errorBox.textContent =
            `Article data could not be loaded: ${error.message}`;

        errorBox.hidden = false;

        articlesList.innerHTML = `
            <div class="empty">
                No article data is currently available.
            </div>
        `;
    }
}

function setupFilters(filters) {
    populateSelect(
        sourceFilter,
        filters.sources || []
    );

    populateSelect(
        topicFilter,
        filters.topics || [],
        true
    );

    populateSelect(
        sentimentFilter,
        filters.sentiments || []
    );

    sourceFilter.addEventListener("change", applyFilters);
    topicFilter.addEventListener("change", applyFilters);
    sentimentFilter.addEventListener("change", applyFilters);

    searchInput.addEventListener("input", applyFilters);
}

function populateSelect(select, values, topics = false) {
    values.forEach(value => {
        const option = document.createElement("option");

        if (topics && typeof value === "object") {
            option.value = value.cluster_id;
            option.textContent =
                value.cluster_label ||
                `Topic ${value.cluster_id}`;
        } else {
            option.value = value;
            option.textContent = value;
        }

        select.appendChild(option);
    });
}

function applyFilters() {
    const source = sourceFilter.value;
    const topic = topicFilter.value;
    const sentiment = sentimentFilter.value;
    const search = searchInput.value.trim().toLowerCase();

    const filtered = articles.filter(article => {

        const matchesSource =
            !source ||
            article.source === source;

        const matchesTopic =
            !topic ||
            String(article.cluster_id) === String(topic);

        const matchesSentiment =
            !sentiment ||
            article.sentiment_label === sentiment;

        const title =
            String(article.title || "").toLowerCase();

        const matchesSearch =
            !search ||
            title.includes(search);

        return (
            matchesSource &&
            matchesTopic &&
            matchesSentiment &&
            matchesSearch
        );
    });

    renderArticles(filtered);
}

function renderArticles(items) {
    articleCount.textContent =
        `${formatNumber(items.length)} articles`;

    resultCount.textContent =
        `${formatNumber(items.length)} results`;

    if (!items.length) {
        articlesList.innerHTML = `
            <div class="empty">
                No articles match the selected filters.
            </div>
        `;

        return;
    }

    articlesList.innerHTML = items.map(article => {

        const sentimentClass =
            getSentimentClass(article.sentiment_label);

        const keywords =
            parseKeywords(article.top_keywords);

        return `
            <article class="article-row">

                <div>

                    <a
                        class="article-title"
                        href="${safeURL(article.url)}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        ${escapeHTML(
                            article.title || "Untitled article"
                        )}
                    </a>

                    <div class="article-meta">

                        <span>
                            ${escapeHTML(article.source || "Unknown source")}
                        </span>

                        <span>
                            ${escapeHTML(article.date || "")}
                        </span>

                        ${
                            article.cluster_label
                                ? `
                                    <span class="article-tag">
                                        ${escapeHTML(
                                            article.cluster_label
                                        )}
                                    </span>
                                `
                                : ""
                        }

                        ${
                            keywords.length
                                ? keywords.slice(0, 3).map(keyword => `
                                    <span class="article-tag">
                                        ${escapeHTML(keyword)}
                                    </span>
                                `).join("")
                                : ""
                        }

                    </div>

                </div>

                <div class="article-sentiment ${sentimentClass}">
                    ${escapeHTML(
                        article.sentiment_label || "Unknown"
                    )}
                </div>

            </article>
        `;
    }).join("");
}

function parseKeywords(value) {
    if (Array.isArray(value)) {
        return value;
    }

    if (!value) {
        return [];
    }

    return String(value)
        .split(",")
        .map(item => item.trim())
        .filter(Boolean);
}

function getSentimentClass(value) {
    const sentiment =
        String(value || "").toLowerCase();

    if (sentiment === "positive") {
        return "positive";
    }

    if (sentiment === "negative") {
        return "negative";
    }

    return "neutral";
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

        if (
            url.protocol === "http:" ||
            url.protocol === "https:"
        ) {
            return url.href;
        }

        return "#";

    } catch {
        return "#";
    }
}

document.addEventListener(
    "DOMContentLoaded",
    loadArticles
);