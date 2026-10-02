/* Overview page: reads /api/overview, /api/trends and /api/articles. */

(function () {
    "use strict";

    const {
        escapeHTML, linkOrText, fetchJSON, formatNumber, formatSigned, formatPercent,
        topicName, emptyState, showError, articleRow, createLineChart, renderLegend, PALETTE
    } = window.NS;

    const byId = id => document.getElementById(id);

    const TOP_TOPICS_IN_CHART = 5;
    const LATEST_ARTICLES = 8;


    function renderStats(data) {
        const stats = data.stats || {};

        ["articles", "topics", "emerging", "sources"].forEach(key => {
            const element = document.querySelector(`[data-stat="${key}"]`);

            if (element) {
                element.textContent = formatNumber(stats[key]);
            }
        });
    }

    function renderEmerging(data) {
        const box = byId("emerging-topics");
        const topics = data.emerging_topics || [];

        if (!topics.length) {
            box.innerHTML = emptyState("No emerging topics detected.");
            return;
        }

        const lifts = topics.map(topic => Number(topic.share_lift || 0));
        const scaleMax = Math.max(...lifts, 1.5) * 1.08;
        const baseline = 100 / scaleMax;

        box.innerHTML = `
            <div class="bar-list">
                ${topics.map((topic, index) => {
                    const lift = lifts[index];
                    const first = index === 0;

                    return `
                        <div class="bar-row">
                            <div class="line">
                                <span class="name">${escapeHTML(topicName(topic))}</span>
                                <span class="val ${first ? "is-accent" : ""}">${lift.toFixed(2)}\u00D7</span>
                            </div>

                            <div class="track">
                                <div class="fill ${first ? "red" : ""}"
                                     style="width:${Math.min(lift / scaleMax * 100, 100)}%"></div>
                                <span class="tick" style="left:${baseline}%" title="Baseline (1\u00D7)"></span>
                            </div>

                            <small>${formatNumber(topic.recent_articles)} recent articles</small>
                        </div>
                    `;
                }).join("")}
            </div>

            <p class="footnote">The grey tick marks the baseline (1\u00D7): recent coverage equal to its usual share.</p>
        `;
    }

    function renderTopics(data) {
        const box = byId("topic-summary");
        const topics = data.topic_sizes || [];

        if (!topics.length) {
            box.innerHTML = emptyState("No topic data available.");
            return;
        }

        const maxArticles = Math.max(...topics.map(topic => Number(topic.article_count || 0)), 1);

        box.innerHTML = `
            <div class="bar-list">
                ${topics.map(topic => `
                    <div class="bar-row">
                        <div class="line">
                            <span class="name">${escapeHTML(topicName(topic))}</span>
                            <span class="val">${formatNumber(topic.article_count)}</span>
                        </div>

                        <div class="track">
                            <div class="fill" style="width:${Number(topic.article_count || 0) / maxArticles * 100}%"></div>
                        </div>
                    </div>
                `).join("")}
            </div>
        `;
    }

    function renderSentiment(data) {
        const box = byId("sentiment-summary");
        const sentiment = data.sentiment_counts || {};

        const rows = [
            { label: "Positive", value: Number(sentiment.Positive || 0), css: "pos" },
            { label: "Neutral", value: Number(sentiment.Neutral || 0), css: "neu" },
            { label: "Negative", value: Number(sentiment.Negative || 0), css: "neg" }
        ];

        const total = rows.reduce((sum, row) => sum + row.value, 0);

        if (!total) {
            box.innerHTML = emptyState("No sentiment data available.");
            return;
        }

        box.innerHTML = `
            <div class="bar-list">
                <div class="stack" role="img"
                     aria-label="${rows.map(row => `${row.label} ${row.value}`).join(", ")}">
                    ${rows.map(row => `
                        <span class="${row.css}" style="width:${row.value / total * 100}%"
                              title="${row.label}: ${formatNumber(row.value)}"></span>
                    `).join("")}
                </div>

                <div class="legend-list">
                    ${rows.map(row => `
                        <div class="legend-row">
                            <span class="swatch-box ${row.css}"></span>
                            <span>${row.label}</span>
                            <span class="val">${formatNumber(row.value)}</span>
                            <span class="pct">${formatPercent(row.value / total, 0)}</span>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }

    function renderSimilar(data) {
        const box = byId("similar-stories");
        const pairs = data.recent_cross_source_pairs || [];

        if (!pairs.length) {
            box.innerHTML = emptyState("No cross-source stories found.");
            return;
        }

        box.innerHTML = `
            <div class="pair-list">
                ${pairs.map(pair => {
                    const similarity = Number(pair.similarity || 0);

                    return `
                        <div class="pair">
                            <div class="pair-main">
                                <span class="pair-title">
                                    ${escapeHTML(pair.source_i || "Source")}
                                    <span class="arrow">\u2194</span>
                                    ${escapeHTML(pair.source_j || "Source")}
                                </span>

                                <span class="pair-titles">
                                    ${linkOrText(pair.url_i, pair.title_i || "Untitled")}
                                    \u2194
                                    ${linkOrText(pair.url_j, pair.title_j || "Untitled")}
                                </span>
                            </div>

                            <div class="pair-score" title="Cosine similarity">
                                <div class="track">
                                    <div class="fill" style="width:${Math.min(similarity * 100, 100)}%"></div>
                                </div>
                                <span class="val">${formatPercent(similarity)}</span>
                            </div>
                        </div>
                    `;
                }).join("")}
            </div>
        `;
    }

    function renderSources(data) {
        const box = byId("source-summary");
        const sources = data.articles_per_source || [];

        if (!sources.length) {
            box.innerHTML = emptyState("No source data available.");
            return;
        }

        const maxArticles = Math.max(...sources.map(source => Number(source.articles || 0)), 1);

        box.innerHTML = `
            <div class="bar-list">
                ${sources.map(source => `
                    <div class="bar-row">
                        <div class="line">
                            <span class="name">${escapeHTML(source.source || "Unknown source")}</span>
                            <span class="val">${formatNumber(source.articles)}</span>
                        </div>

                        <div class="track">
                            <div class="fill" style="width:${Number(source.articles || 0) / maxArticles * 100}%"></div>
                        </div>

                        ${source.avg_sentiment !== undefined && source.avg_sentiment !== null
                            ? `<small>Average sentiment ${formatSigned(source.avg_sentiment)}</small>`
                            : ""}
                    </div>
                `).join("")}
            </div>
        `;
    }

    function renderLatest(data) {
        const box = byId("latest-articles");
        const articles = data.articles || [];

        if (!articles.length) {
            box.innerHTML = emptyState("No articles available.");
            return;
        }

        box.innerHTML = articles.slice(0, LATEST_ARTICLES).map(article => articleRow(article)).join("");
    }

    function renderTrends(data) {
        const box = byId("trend-chart");
        const legend = byId("trend-legend");
        const days = data.days || [];
        const series = data.series || [];

        if (!days.length || !series.length) {
            box.innerHTML = emptyState("No trend data available.");
            legend.innerHTML = "";
            return;
        }

        // colours follow the order in trends.json so a topic keeps its colour on every page
        const coloured = series.map((item, index) => ({
            id: String(item.cluster_id),
            label: topicName(item),
            values: item.rolling_3d || [],
            color: PALETTE[index % PALETTE.length]
        }));

        const top = [...coloured]
            .sort((a, b) => (b.values.at(-1) || 0) - (a.values.at(-1) || 0))
            .slice(0, TOP_TOPICS_IN_CHART);

        box.innerHTML = "";

        const chart = createLineChart(box, {
            days,
            series: top,
            label: "Line chart of the 3-day rolling average of articles per topic"
        });

        renderLegend(legend, chart, top);
    }


    async function loadDashboard() {
        const errorBox = byId("dashboard-error");

        const [overview, trends, articles] = await Promise.allSettled([
            fetchJSON("overview"),
            fetchJSON("trends"),
            fetchJSON("articles")
        ]);

        const problems = [];

        if (overview.status === "fulfilled") {
            const data = overview.value;

            renderStats(data);
            renderEmerging(data);
            renderTopics(data);
            renderSentiment(data);
            renderSimilar(data);
            renderSources(data);
        } else {
            problems.push(overview.reason.message);

            ["emerging-topics", "topic-summary", "sentiment-summary", "similar-stories", "source-summary"]
                .forEach(id => { byId(id).innerHTML = emptyState("Data is not available."); });
        }

        if (trends.status === "fulfilled") {
            renderTrends(trends.value);
        } else {
            problems.push(trends.reason.message);
            byId("trend-chart").innerHTML = emptyState("Trend data is not available.");
        }

        if (articles.status === "fulfilled") {
            renderLatest(articles.value);
        } else {
            problems.push(articles.reason.message);
            byId("latest-articles").innerHTML = emptyState("Article data is not available.");
        }

        if (problems.length) {
            console.error(problems);
            showError(errorBox, `Some dashboard data could not be loaded: ${problems.join(" \u00B7 ")}`);
        }
    }

    document.addEventListener("DOMContentLoaded", loadDashboard);
})();
