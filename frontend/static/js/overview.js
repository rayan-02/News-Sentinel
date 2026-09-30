const $ = (id) => document.getElementById(id);

async function getData(name) {
    const response = await fetch(`/api/${name}`);

    if (!response.ok) {
        throw new Error(`${name}.json could not be loaded`);
    }

    return response.json();
}

function showError(message) {
    const box = $("dashboard-error");

    if (!box) return;

    box.textContent = message;
    box.hidden = false;
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString();
}

function renderStats(data) {
    const stats = $("stats");
    if (!stats) return;

    const values = stats.querySelectorAll(".stat-value");
    const statsData = data.stats || {};

    values[0].textContent = formatNumber(statsData.articles);
    values[1].textContent = formatNumber(statsData.topics);
    values[2].textContent = formatNumber(statsData.emerging);
    values[3].textContent = formatNumber(statsData.sources);
}

function renderEmerging(data) {
    const box = $("emerging-topics");
    if (!box) return;

    const topics = data.emerging_topics || [];

    if (!topics.length) {
        box.innerHTML = '<div class="empty">No emerging topics detected.</div>';
        return;
    }

    box.innerHTML = topics.map(topic => `
        <div class="bar-row">
            <div class="line">
                <span>${topic.cluster_label || `Topic ${topic.cluster_id}`}</span>
                <span class="val">${Number(topic.share_lift || 0).toFixed(2)}×</span>
            </div>

            <div class="track">
                <div class="fill red"
                     style="width:${Math.min(Number(topic.share_lift || 0) * 20, 100)}%">
                </div>
            </div>

            <small>
                ${formatNumber(topic.recent_articles)} recent articles
            </small>
        </div>
    `).join("");
}

function renderTopics(data) {
    const box = $("topic-summary");
    if (!box) return;

    const topics = data.topic_sizes || [];

    if (!topics.length) {
        box.innerHTML = '<div class="empty">No topic data available.</div>';
        return;
    }

    const maxArticles = Math.max(
        ...topics.map(topic => Number(topic.article_count || 0))
    );

    box.innerHTML = topics.map(topic => `
        <div class="bar-row">
            <div class="line">
                <span>${topic.cluster_label || `Topic ${topic.cluster_id}`}</span>
                <span class="val">${formatNumber(topic.article_count)}</span>
            </div>

            <div class="track">
                <div class="fill"
                     style="width:${maxArticles ? Number(topic.article_count) / maxArticles * 100 : 0}%">
                </div>
            </div>
        </div>
    `).join("");
}

function renderSentiment(data) {
    const box = $("sentiment-summary");
    if (!box) return;

    const sentiment = data.sentiment_counts || {};

    const positive = Number(sentiment.Positive || 0);
    const neutral = Number(sentiment.Neutral || 0);
    const negative = Number(sentiment.Negative || 0);

    const total = positive + neutral + negative;

    if (!total) {
        box.innerHTML = '<div class="empty">No sentiment data available.</div>';
        return;
    }

    const positiveWidth = positive / total * 100;
    const neutralWidth = neutral / total * 100;
    const negativeWidth = negative / total * 100;

    box.innerHTML = `
        <div class="stack">
            <div style="width:${positiveWidth}%"></div>
            <div style="width:${neutralWidth}%"></div>
            <div style="width:${negativeWidth}%"></div>
        </div>

        <div class="bar-row">
            <div class="line">
                <span>Positive</span>
                <span class="val">${formatNumber(positive)}</span>
            </div>
        </div>

        <div class="bar-row">
            <div class="line">
                <span>Neutral</span>
                <span class="val">${formatNumber(neutral)}</span>
            </div>
        </div>

        <div class="bar-row">
            <div class="line">
                <span>Negative</span>
                <span class="val">${formatNumber(negative)}</span>
            </div>
        </div>
    `;
}

function renderSimilar(data) {
    const box = $("similar-stories");
    if (!box) return;

    const pairs = data.recent_cross_source_pairs || [];

    if (!pairs.length) {
        box.innerHTML = '<div class="empty">No cross-source stories found.</div>';
        return;
    }

    box.innerHTML = pairs.map(pair => `
        <div class="pair">
            <div class="pair-title">
                ${pair.source_i || "Source"}
                <span class="arrow">↔</span>
                ${pair.source_j || "Source"}
            </div>

            <small>
                Similarity:
                <strong>${(Number(pair.similarity || 0) * 100).toFixed(1)}%</strong>
            </small>

            <small>
                ${pair.title_i || "Untitled"} ↔ ${pair.title_j || "Untitled"}
            </small>
        </div>
    `).join("");
}

function renderSources(data) {
    const box = $("source-summary");
    if (!box) return;

    const sources = data.articles_per_source || [];

    if (!sources.length) {
        box.innerHTML = '<div class="empty">No source data available.</div>';
        return;
    }

    const maxArticles = Math.max(
        ...sources.map(source => Number(source.articles || 0))
    );

    box.innerHTML = sources.map(source => `
        <div class="bar-row">
            <div class="line">
                <span>${source.source}</span>
                <span class="val">${formatNumber(source.articles)}</span>
            </div>

            <div class="track">
                <div class="fill"
                     style="width:${maxArticles ? Number(source.articles) / maxArticles * 100 : 0}%">
                </div>
            </div>
        </div>
    `).join("");
}

function renderLatest(data) {
    const box = $("latest-articles");
    if (!box) return;

    const articles = data.articles || [];

    if (!articles.length) {
        box.innerHTML = '<div class="empty">No articles available.</div>';
        return;
    }

    box.innerHTML = articles.slice(0, 8).map(article => `
        <div class="art">
            <a href="${article.url || "#"}"
               target="_blank"
               rel="noopener">
                ${article.title || "Untitled article"}
            </a>

            <small>
                ${article.source || ""}
            </small>
        </div>
    `).join("");
}

function renderTrends(data) {
    const box = $("trend-chart");
    if (!box) return;

    if (!data.days || !data.days.length || !data.series || !data.series.length) {
        box.innerHTML = '<div class="empty">No trend data available.</div>';
        return;
    }

    const latest = data.series
        .map(series => ({
            label: series.label,
            value: series.rolling_3d?.at(-1) || 0
        }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 5);

    box.innerHTML = latest.map(item => `
        <div class="bar-row">
            <div class="line">
                <span>${item.label}</span>
                <span class="val">${Number(item.value).toFixed(2)}</span>
            </div>

            <div class="track">
                <div class="fill"
                     style="width:${Math.min(Number(item.value) * 10, 100)}%">
                </div>
            </div>
        </div>
    `).join("");
}

async function loadDashboard() {
    try {
        const overview = await getData("overview");
        const trends = await getData("trends");
        const articles = await getData("articles");

        renderStats(overview);
        renderEmerging(overview);
        renderTopics(overview);
        renderSentiment(overview);
        renderSimilar(overview);
        renderSources(overview);
        renderTrends(trends);
        renderLatest(articles);

    } catch (error) {
        console.error(error);
        showError(`Dashboard data could not be loaded: ${error.message}`);
    }
}

document.addEventListener("DOMContentLoaded", loadDashboard);