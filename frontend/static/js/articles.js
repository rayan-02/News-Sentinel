/* Articles page: reads /api/articles. Filters by source, topic, sentiment and title. */

(function () {
    "use strict";

    const { escapeHTML, fetchJSON, formatNumber, articleRow, showError, emptyState } = window.NS;

    const PAGE_SIZE = 40;

    const articlesList = document.getElementById("articles-list");
    const articleCount = document.getElementById("article-count");
    const resultCount = document.getElementById("article-result-count");
    const sourceFilter = document.getElementById("source-filter");
    const topicFilter = document.getElementById("topic-filter");
    const sentimentFilter = document.getElementById("sentiment-filter");
    const searchInput = document.getElementById("article-search");
    const clearButton = document.getElementById("clear-filters");
    const errorBox = document.getElementById("articles-error");
    const moreBox = document.getElementById("articles-more");
    const moreButton = document.getElementById("articles-more-button");
    const shownText = document.getElementById("articles-shown");

    let articles = [];
    let filtered = [];
    let visibleCount = 0;


    async function loadArticles() {
        try {
            const data = await fetchJSON("articles");

            articles = data.articles || [];

            setupFilters(data.filters || {});
            applyFilters();

        } catch (error) {
            console.error(error);

            showError(errorBox, `Article data could not be loaded: ${error.message}`);
            articleCount.textContent = "\u2014";
            resultCount.textContent = "\u2014";
            articlesList.innerHTML = emptyState("No article data is currently available.");
        }
    }

    function setupFilters(filters) {
        populateSelect(sourceFilter, filters.sources || []);
        populateSelect(topicFilter, filters.topics || [], true);
        populateSelect(sentimentFilter, filters.sentiments || []);

        [sourceFilter, topicFilter, sentimentFilter].forEach(select =>
            select.addEventListener("change", applyFilters));

        searchInput.addEventListener("input", applyFilters);

        clearButton.addEventListener("click", () => {
            sourceFilter.value = "";
            topicFilter.value = "";
            sentimentFilter.value = "";
            searchInput.value = "";
            applyFilters();
        });
    }

    function populateSelect(select, values, topics = false) {
        values.forEach(value => {
            const option = document.createElement("option");

            if (topics && typeof value === "object") {
                option.value = value.cluster_id;
                option.textContent = value.cluster_label || `Topic ${value.cluster_id}`;
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

        filtered = articles.filter(article => {
            const matchesSource = !source || article.source === source;
            const matchesTopic = !topic || String(article.cluster_id) === String(topic);
            const matchesSentiment = !sentiment || article.sentiment_label === sentiment;
            const matchesSearch = !search || String(article.title || "").toLowerCase().includes(search);

            return matchesSource && matchesTopic && matchesSentiment && matchesSearch;
        });

        renderArticles();
    }

    function renderArticles() {
        articleCount.textContent = `${formatNumber(filtered.length)} articles`;
        resultCount.textContent = `${formatNumber(filtered.length)} results`;

        visibleCount = 0;
        articlesList.innerHTML = "";

        if (!filtered.length) {
            articlesList.innerHTML = emptyState("No articles match the selected filters.");
            moreBox.hidden = true;
            return;
        }

        showMore();
    }

    function showMore() {
        const next = filtered.slice(visibleCount, visibleCount + PAGE_SIZE);

        articlesList.insertAdjacentHTML("beforeend", next.map(article => articleRow(article, { keywords: true })).join(""));
        visibleCount += next.length;

        shownText.textContent = `Showing ${formatNumber(visibleCount)} of ${formatNumber(filtered.length)}`;
        moreBox.hidden = filtered.length <= PAGE_SIZE;
        moreButton.hidden = visibleCount >= filtered.length;
    }

    moreButton.addEventListener("click", showMore);
    document.addEventListener("DOMContentLoaded", loadArticles);
})();
