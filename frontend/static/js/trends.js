const chartBox = document.getElementById("trend-chart");
const tableBox = document.getElementById("trend-table");
const errorBox = document.getElementById("trends-error");

async function loadTrends() {
    try {
        const response = await fetch("/api/trends");

        if (!response.ok) {
            throw new Error("trends.json could not be loaded");
        }

        const data = await response.json();

        renderTrendChart(data);
        renderTrendTable(data);

    } catch (error) {
        console.error(error);

        errorBox.textContent = `Trend data could not be loaded: ${error.message}`;
        errorBox.hidden = false;

        chartBox.innerHTML = `
            <div class="empty">
                No trend data is currently available.
            </div>
        `;

        tableBox.innerHTML = `
            <div class="empty">
                No trend details are currently available.
            </div>
        `;
    }
}

function renderTrendChart(data) {
    const series = data.series || [];

    if (!series.length) {
        chartBox.innerHTML = `
            <div class="empty">
                No topic trends were found.
            </div>
        `;
        return;
    }

    const rows = series
        .map(item => {
            const values = item.rolling_3d || [];
            const latest = Number(values[values.length - 1] || 0);

            return {
                label: item.label || `Topic ${item.cluster_id}`,
                value: latest
            };
        })
        .sort((a, b) => b.value - a.value);

    const maxValue = Math.max(
        ...rows.map(row => row.value),
        1
    );

    chartBox.innerHTML = rows.map(row => `
        <div class="trend-row">

            <div class="trend-label">
                <span>${escapeHTML(row.label)}</span>
                <span>${row.value.toFixed(2)}</span>
            </div>

            <div class="track">
                <div
                    class="fill"
                    style="width:${row.value / maxValue * 100}%"
                ></div>
            </div>

        </div>
    `).join("");
}

function renderTrendTable(data) {
    const series = data.series || [];

    if (!series.length) {
        tableBox.innerHTML = `
            <div class="empty">
                No trend details were found.
            </div>
        `;
        return;
    }

    tableBox.innerHTML = series.map(item => {
        const counts = item.counts || [];
        const rolling3 = item.rolling_3d || [];
        const rolling7 = item.rolling_7d || [];

        const latestCount = Number(
            counts[counts.length - 1] || 0
        );

        const latest3 = Number(
            rolling3[rolling3.length - 1] || 0
        );

        const latest7 = Number(
            rolling7[rolling7.length - 1] || 0
        );

        return `
            <div class="article-row">

                <div>
                    <strong class="article-title">
                        ${escapeHTML(
                            item.label || `Topic ${item.cluster_id}`
                        )}
                    </strong>

                    <div class="article-meta">
                        <span class="article-tag">
                            Topic ${item.cluster_id}
                        </span>

                        <span class="article-tag">
                            Latest: ${latestCount} articles
                        </span>
                    </div>
                </div>

                <div class="trend-values">
                    <div>
                        <small>3-day</small>
                        <strong>${latest3.toFixed(2)}</strong>
                    </div>

                    <div>
                        <small>7-day</small>
                        <strong>${latest7.toFixed(2)}</strong>
                    </div>
                </div>

            </div>
        `;
    }).join("");
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

document.addEventListener("DOMContentLoaded", loadTrends);