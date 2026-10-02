/* Topics page: reads /api/topics. */

(function () {
    "use strict";

    const {
        escapeHTML, safeURL, fetchJSON, formatNumber, formatSentiment, formatPercent,
        showError, emptyState
    } = window.NS;

    const topicGrid = document.getElementById("topics-grid");
    const topicCount = document.getElementById("topic-count");
    const errorBox = document.getElementById("topics-error");


    /* sources arrive as {name: count}; accept [{source, count}] too */
    function sourceEntries(sources) {
        if (Array.isArray(sources)) {
            return sources.map(item => [item.source, item.count ?? item.articles ?? 0]);
        }

        return Object.entries(sources || {});
    }

    async function loadTopics() {
        try {
            const data = await fetchJSON("topics");
            renderTopics(data.topics || []);
        } catch (error) {
            console.error(error);

            showError(errorBox, `Topic data could not be loaded: ${error.message}`);
            topicCount.textContent = "\u2014";
            topicGrid.innerHTML = emptyState("No topic data is currently available.");
        }
    }

    function renderTopics(topics) {
        if (!topics.length) {
            topicCount.textContent = "0 topics";
            topicGrid.innerHTML = emptyState("No topics were found.");
            return;
        }

        topicCount.textContent = `${topics.length} topics`;
        topicGrid.innerHTML = topics.map(renderTopic).join("");
    }

    function renderTopic(topic) {
        const sentiment = topic.sentiment_counts || {};
        const keywords = topic.keywords || [];
        const phrases = topic.phrases || [];
        const articles = topic.sample_articles || [];
        const sources = sourceEntries(topic.sources).sort((a, b) => Number(b[1]) - Number(a[1]));

        const positive = Number(sentiment.Positive || 0);
        const neutral = Number(sentiment.Neutral || 0);
        const negative = Number(sentiment.Negative || 0);
        const total = positive + neutral + negative;

        const share = Number(topic.share_of_articles || 0);
        const maxSource = Math.max(...sources.map(([, count]) => Number(count || 0)), 1);
        const number = String(topic.cluster_id).padStart(2, "0");
        const average = Number(topic.avg_sentiment);

        return `
            <article class="card topic-card">

                <div class="topic-card-header">
                    <span class="topic-numeral" aria-hidden="true">${escapeHTML(number)}</span>

                    <div>
                        <span class="topic-id">Topic ${escapeHTML(number)}</span>
                        <h3>${escapeHTML(topic.label || "Unnamed topic")}</h3>
                    </div>

                    <div class="topic-article-count">
                        ${formatNumber(topic.article_count)}
                        <small>articles</small>
                    </div>
                </div>

                <div>
                    <div class="topic-share-label">
                        <span>Share of analyzed articles</span>
                        <strong>${formatPercent(share)}</strong>
                    </div>

                    <div class="track">
                        <div class="fill" style="width:${Math.min(share * 100, 100)}%"></div>
                    </div>
                </div>

                <div class="topic-section">
                    <span class="section-label">Keywords</span>

                    <div class="chips">
                        ${keywords.length
                            ? keywords.map(keyword => `<span class="chip">${escapeHTML(keyword)}</span>`).join("")
                            : `<span class="muted">No keywords available</span>`}
                    </div>
                </div>

                <div class="topic-section">
                    <span class="section-label">Key phrases</span>

                    <div class="phrases">
                        ${phrases.length
                            ? phrases.map(phrase => `<span>${escapeHTML(phrase)}</span>`).join("")
                            : `<span class="muted">No phrases available</span>`}
                    </div>
                </div>

                <div class="topic-columns">

                    <div class="topic-section">
                        <span class="section-label">Sentiment</span>

                        <div class="stack" role="img"
                             aria-label="Positive ${positive}, neutral ${neutral}, negative ${negative}">
                            <span class="pos" style="width:${total ? positive / total * 100 : 0}%"></span>
                            <span class="neu" style="width:${total ? neutral / total * 100 : 0}%"></span>
                            <span class="neg" style="width:${total ? negative / total * 100 : 0}%"></span>
                        </div>

                        <div class="sentiment-values">
                            <span>Positive ${formatNumber(positive)}</span>
                            <span>Neutral ${formatNumber(neutral)}</span>
                            <span>Negative ${formatNumber(negative)}</span>
                        </div>
                    </div>

                    <div class="topic-section">
                        <span class="section-label">Average</span>

                        <strong class="sentiment-score ${average < 0 ? "is-neg" : ""}">
                            ${formatSentiment(topic.avg_sentiment)}
                        </strong>
                    </div>

                </div>

                <div class="topic-section">
                    <span class="section-label">Sources</span>

                    <div class="mini-list">
                        ${sources.length
                            ? sources.map(([source, count]) => `
                                <div class="mini-row">
                                    <span class="name">${escapeHTML(source)}</span>
                                    <div class="track thin">
                                        <div class="fill" style="width:${Number(count || 0) / maxSource * 100}%"></div>
                                    </div>
                                    <strong>${formatNumber(count)}</strong>
                                </div>
                            `).join("")
                            : `<span class="muted">No source data available</span>`}
                    </div>
                </div>

                <div class="topic-section">
                    <span class="section-label">Sample articles</span>

                    <div class="sample-articles">
                        ${articles.length
                            ? articles.map(article => sampleArticle(article)).join("")
                            : `<span class="muted">No sample articles available.</span>`}
                    </div>
                </div>

            </article>
        `;
    }

    function sampleArticle(article) {
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

    document.addEventListener("DOMContentLoaded", loadTopics);
})();
