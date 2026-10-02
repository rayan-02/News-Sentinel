/* Similar Stories page: reads /api/similar_stories. */

(function () {
    "use strict";

    const {
        escapeHTML, linkOrText, fetchJSON, formatNumber, formatPercent, showError, emptyState
    } = window.NS;

    const PAGE_SIZE = 20;

    const pairsBox = document.getElementById("similar-pairs");
    const pairCount = document.getElementById("pair-count");
    const errorBox = document.getElementById("similar-error");
    const moreBox = document.getElementById("pairs-more");
    const moreButton = document.getElementById("pairs-more-button");
    const shownText = document.getElementById("pairs-shown");

    let pairs = [];
    let visibleCount = 0;


    async function loadSimilarStories() {
        try {
            const data = await fetchJSON("similar_stories");

            pairs = data.pairs || [];

            pairCount.textContent = `${formatNumber(data.cross_source_pairs ?? pairs.length)} cross-source pairs`;

            if (!pairs.length) {
                pairsBox.innerHTML = emptyState("No similar stories were found.");
                return;
            }

            pairsBox.innerHTML = "";
            showMore();

        } catch (error) {
            console.error(error);

            showError(errorBox, `Similar story data could not be loaded: ${error.message}`);
            pairCount.textContent = "\u2014";
            pairsBox.innerHTML = emptyState("No similar story data is currently available.");
        }
    }

    function showMore() {
        const next = pairs.slice(visibleCount, visibleCount + PAGE_SIZE);

        pairsBox.insertAdjacentHTML("beforeend", next.map(renderPair).join(""));
        visibleCount += next.length;

        shownText.textContent = `Showing ${formatNumber(visibleCount)} of ${formatNumber(pairs.length)} pairs`;
        moreBox.hidden = pairs.length <= PAGE_SIZE;
        moreButton.hidden = visibleCount >= pairs.length;
    }

    function renderPair(pair) {
        const similarity = Number(pair.similarity || 0);

        return `
            <article class="card similar-card">

                <div class="similar-header">

                    <div>
                        <span class="eyebrow">Semantic match</span>

                        <div class="similar-sources">
                            ${escapeHTML(pair.source_i || "Source")}
                            <span>\u2194</span>
                            ${escapeHTML(pair.source_j || "Source")}
                        </div>
                    </div>

                    <div class="similar-score">
                        ${formatPercent(similarity)}
                        <small>similarity</small>
                    </div>

                </div>

                <div class="similar-articles">

                    <div class="similar-article">
                        <span class="source-label">
                            <span class="side-mark">A</span>
                            ${escapeHTML(pair.source_i || "Source")}
                        </span>

                        ${linkOrText(pair.url_i, pair.title_i || "Untitled article", "article-text")}
                    </div>

                    <div class="similar-divider"><span>vs</span></div>

                    <div class="similar-article is-b">
                        <span class="source-label">
                            <span class="side-mark">B</span>
                            ${escapeHTML(pair.source_j || "Source")}
                        </span>

                        ${linkOrText(pair.url_j, pair.title_j || "Untitled article", "article-text")}
                    </div>

                </div>

                <div class="similar-meter">
                    <div class="track">
                        <div class="fill" style="width:${Math.min(similarity * 100, 100)}%"></div>
                    </div>

                    <span>Cosine similarity</span>
                </div>

            </article>
        `;
    }

    moreButton.addEventListener("click", showMore);
    document.addEventListener("DOMContentLoaded", loadSimilarStories);
})();
