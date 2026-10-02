/* Trends page: reads /api/trends. */

(function () {
    "use strict";

    const {
        escapeHTML, fetchJSON, formatNumber, formatDay, topicName, emptyState, showError,
        createLineChart, renderLegend, sparkline, PALETTE
    } = window.NS;

    const chartBox = document.getElementById("trend-chart");
    const legendBox = document.getElementById("trend-legend");
    const tableBox = document.getElementById("trend-table");
    const errorBox = document.getElementById("trends-error");
    const rangeBox = document.getElementById("trend-range");
    const metricNote = document.getElementById("trend-metric-note");
    const metricSwitch = document.getElementById("metric-switch");

    const METRIC_LABELS = {
        counts: "Daily article counts",
        rolling_3d: "3-day rolling average",
        rolling_7d: "7-day rolling average"
    };


    function last(values) {
        const number = Number((values || []).at(-1));
        return Number.isFinite(number) ? number : 0;
    }

    function sum(values) {
        return (values || []).reduce((total, value) => total + (Number(value) || 0), 0);
    }

    async function loadTrends() {
        try {
            const data = await fetchJSON("trends");

            const days = data.days || [];
            const series = (data.series || []).map((item, index) => ({
                ...item,
                id: String(item.cluster_id),
                name: topicName(item),
                color: PALETTE[index % PALETTE.length]
            }));

            renderRange(days);

            if (!days.length || !series.length) {
                chartBox.innerHTML = emptyState("No topic trends were found.");
                tableBox.innerHTML = emptyState("No trend details were found.");
                return;
            }

            renderChart(days, series);
            renderTable(series);

        } catch (error) {
            console.error(error);

            showError(errorBox, `Trend data could not be loaded: ${error.message}`);

            chartBox.innerHTML = emptyState("No trend data is currently available.");
            tableBox.innerHTML = emptyState("No trend details are currently available.");
        }
    }

    function renderRange(days) {
        rangeBox.textContent = days.length
            ? `${formatDay(days[0])} \u2013 ${formatDay(days.at(-1))} \u00B7 ${days.length} days`
            : "\u2014";
    }

    function renderChart(days, series) {
        const ordered = [...series].sort((a, b) => last(b.rolling_3d) - last(a.rolling_3d));

        const chartSeries = ordered.map(item => ({
            id: item.id,
            label: item.name,
            values: item.rolling_3d || [],
            color: item.color
        }));

        chartBox.innerHTML = "";

        const chart = createLineChart(chartBox, {
            days,
            series: chartSeries,
            label: "Line chart of article activity per topic over time"
        });

        renderLegend(legendBox, chart, chartSeries);

        metricSwitch.querySelectorAll("button").forEach(button => {
            button.addEventListener("click", () => {
                const metric = button.dataset.metric;
                const next = {};

                ordered.forEach(item => { next[item.id] = item[metric] || []; });

                chart.setSeries(next);

                metricSwitch.querySelectorAll("button").forEach(other =>
                    other.setAttribute("aria-pressed", String(other === button)));

                metricNote.textContent = METRIC_LABELS[metric];
            });
        });
    }

    function renderTable(series) {
        const ordered = [...series].sort((a, b) => last(b.rolling_3d) - last(a.rolling_3d));

        tableBox.innerHTML = ordered.map(item => `
            <div class="trend-row">

                <div class="trend-name">
                    <span class="trend-dot" style="--c:${item.color}"></span>

                    <div>
                        <strong>${escapeHTML(item.name)}</strong>

                        <div class="article-meta">
                            <span class="article-tag">Topic ${escapeHTML(item.cluster_id)}</span>
                            <span class="article-tag">Latest day: ${formatNumber(last(item.counts))} articles</span>
                            <span class="article-tag">In period: ${formatNumber(sum(item.counts))}</span>
                        </div>
                    </div>
                </div>

                <div style="color:${item.color}">
                    ${sparkline(item.counts, item.color)}
                </div>

                <div class="trend-values">
                    <div>
                        <small>3-day</small>
                        <strong>${last(item.rolling_3d).toFixed(2)}</strong>
                    </div>

                    <div>
                        <small>7-day</small>
                        <strong>${last(item.rolling_7d).toFixed(2)}</strong>
                    </div>
                </div>

            </div>
        `).join("");
    }

    document.addEventListener("DOMContentLoaded", loadTrends);
})();
