/* Source Analysis page: reads /api/source_analysis.
   Presents measurable differences only, never a verdict about an outlet. */

(function () {
    "use strict";

    const {
        escapeHTML, safeURL, fetchJSON, formatNumber, formatPercent, formatSigned,
        showError, emptyState
    } = window.NS;

    const sourceSummary = document.getElementById("source-summary");
    const sourceTopics = document.getElementById("source-topics");
    const topicSelect = document.getElementById("topic-select");
    const disclaimer = document.getElementById("source-disclaimer");
    const errorBox = document.getElementById("sources-error");

    let topics = [];


    async function loadSources() {
        try {
            const data = await fetchJSON("source_analysis");

            topics = data.topics || [];

            renderDisclaimer(data);
            renderStats(data);
            renderSources(data.sources || []);
            setupTopicPicker();
            renderTopics();

        } catch (error) {
            console.error(error);

            showError(errorBox, `Source analysis could not be loaded: ${error.message}`);

            disclaimer.hidden = true;
            sourceSummary.innerHTML = emptyState("No source data is currently available.");
            sourceTopics.innerHTML = emptyState("No topic analysis is currently available.");
        }
    }

    function renderDisclaimer(data) {
        disclaimer.textContent =
            data.disclaimer ||
            "These are measurable differences in coverage, not a verdict on whether an outlet is biased.";
    }

    function setStat(key, value) {
        const element = document.querySelector(`#source-stats [data-stat="${key}"]`);

        if (element) {
            element.textContent = formatNumber(value);
        }
    }

    function renderStats(data) {
        const sources = data.sources || [];

        setStat("sources", sources.length);
        setStat("topics", (data.topics || []).length);
        setStat("articles", sources.reduce((total, source) => total + Number(source.articles || 0), 0));
    }

    function renderSources(sources) {
        if (!sources.length) {
            sourceSummary.innerHTML = emptyState("No source summaries were found.");
            return;
        }

        const total = sources.reduce((sum, source) => sum + Number(source.articles || 0), 0) || 1;
        const maxArticles = Math.max(...sources.map(source => Number(source.articles || 0)), 1);

        sourceSummary.innerHTML = `
            <div class="compare-head label" aria-hidden="true">
                <span>Source</span>
                <span>Share of articles</span>
                <span class="right">Articles</span>
                <span class="right">Avg sentiment</span>
            </div>

            ${sources.map(source => {
                const articles = Number(source.articles || 0);
                const sentiment = Number(source.avg_sentiment);
                const hasSentiment = Number.isFinite(sentiment) && source.avg_sentiment !== null && source.avg_sentiment !== "";
                const half = Math.min(Math.abs(sentiment), 1) * 50;

                return `
                    <div class="compare-row">
                        <span class="name">${escapeHTML(source.source || "Unknown source")}</span>

                        <div class="track-cell">
                            <div class="track" title="${formatPercent(articles / total)} of analyzed articles">
                                <div class="fill" style="width:${articles / maxArticles * 100}%"></div>
                            </div>
                        </div>

                        <span class="num">${formatNumber(articles)}</span>

                        <span class="compare-sentiment ${hasSentiment && sentiment < 0 ? "is-neg" : ""}">
                            ${hasSentiment ? `
                                <span class="diverge" aria-hidden="true">
                                    <span class="${sentiment < 0 ? "is-neg" : "is-pos"}" style="width:${half}%"></span>
                                </span>
                            ` : ""}
                            ${hasSentiment ? formatSigned(sentiment, 2) : "\u2014"}
                        </span>
                    </div>
                `;
            }).join("")}
        `;
    }

    function setupTopicPicker() {
        topicSelect.innerHTML = `<option value="">All topics</option>` + topics.map(topic => `
            <option value="${escapeHTML(topic.cluster_id)}">
                ${escapeHTML(topic.label || `Topic ${topic.cluster_id}`)}
            </option>
        `).join("");

        topicSelect.addEventListener("change", renderTopics);
    }

    function renderTopics() {
        if (!topics.length) {
            sourceTopics.innerHTML = emptyState("No topic-level source analysis was found.");
            return;
        }

        const chosen = topicSelect.value;
        const shown = chosen ? topics.filter(topic => String(topic.cluster_id) === chosen) : topics;

        sourceTopics.innerHTML = shown.map(renderTopic).join("");
    }

    function renderTopic(topic) {
        const topicSources = topic.sources || [];

        return `
            <article class="card analysis-topic">

                <div class="card-header">
                    <div>
                        <span class="topic-id">Topic ${String(topic.cluster_id).padStart(2, "0")}</span>
                        <h3 class="topic-title">${escapeHTML(topic.label || "Unnamed topic")}</h3>
                    </div>
                </div>

                ${topicSources.length
                    ? `<div class="analysis-sources">${topicSources.map(renderTopicSource).join("")}</div>`
                    : emptyState("No source comparisons available.")}

            </article>
        `;
    }

    function patternClass(text) {
        const value = String(text || "").toLowerCase();

        if (value.includes("higher") || value.includes("more positive") || value.includes("more negative")) {
            return "is-high";
        }

        if (value.includes("lower")) {
            return "is-low";
        }

        return "";
    }

    function renderTopicSource(source) {
        const keywords = source.distinctive_keywords || [];
        const phrases = source.distinctive_phrases || [];
        const evidence = source.evidence || [];
        const difference = Number(source.sentiment_difference);

        return `
            <div class="analysis-source">

                <div class="analysis-source-head">
                    <h4>${escapeHTML(source.source || "Unknown source")}</h4>
                </div>

                <div class="metric-grid">
                    <div class="metric">
                        <span class="label">Articles</span>
                        <strong>${formatNumber(source.articles)}</strong>
                    </div>

                    <div class="metric">
                        <span class="label">Coverage share</span>
                        <strong>${formatPercent(source.coverage_share)}</strong>
                    </div>

                    <div class="metric">
                        <span class="label">Emphasis ratio</span>
                        <strong>${Number(source.emphasis_ratio || 0).toFixed(2)}\u00D7</strong>
                    </div>

                    <div class="metric">
                        <span class="label">Sentiment difference</span>
                        <strong class="${difference < 0 ? "is-neg" : ""}">${formatSigned(source.sentiment_difference)}</strong>
                    </div>

                    <div class="metric">
                        <span class="label">Same-event matches</span>
                        <strong>${formatNumber(source.same_event_matches)}</strong>
                    </div>
                </div>

                <div class="pattern-row">
                    <span class="tag ${patternClass(source.coverage_pattern)}">
                        ${escapeHTML(source.coverage_pattern || "No coverage pattern")}
                    </span>

                    <span class="tag ${patternClass(source.sentiment_pattern)}">
                        ${escapeHTML(source.sentiment_pattern || "No sentiment pattern")}
                    </span>
                </div>

                ${keywords.length ? `
                    <div class="topic-section">
                        <span class="section-label">Distinctive keywords</span>

                        <div class="chips">
                            ${keywords.map(keyword => `<span class="chip">${escapeHTML(keyword)}</span>`).join("")}
                        </div>
                    </div>
                ` : ""}

                ${phrases.length ? `
                    <div class="topic-section">
                        <span class="section-label">Distinctive phrases</span>

                        <div class="phrases">
                            ${phrases.map(phrase => `<span>${escapeHTML(phrase)}</span>`).join("")}
                        </div>
                    </div>
                ` : ""}

                ${evidence.length ? `
                    <details class="evidence">
                        <summary>Evidence articles (${evidence.length})</summary>

                        <div class="sample-articles">
                            ${evidence.map(evidenceLink).join("")}
                        </div>
                    </details>
                ` : ""}

            </div>
        `;
    }

    function evidenceLink(article) {
        const meta = [article.source, article.date].filter(Boolean).map(escapeHTML).join(" \u00B7 ");
        const safe = safeURL(article.url);
        const target = safe === "#" ? "" : ` href="${safe}" target="_blank" rel="noopener noreferrer"`;

        return `
            <a${target}>
                <strong>${escapeHTML(article.title || "Untitled article")}</strong>
                <small>${meta}</small>
            </a>
        `;
    }

    document.addEventListener("DOMContentLoaded", loadSources);
})();
