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

    if (values[0]) values[0].textContent = formatNumber(statsData.articles);
    if (values[1]) values[1].textContent = formatNumber(statsData.topics);
    if (values[2]) values[2].textContent = formatNumber(statsData.emerging);
    if (values[3]) values[3].textContent = formatNumber(statsData.sources);
}

function renderEmerging(data) {
    const box = $("emerging-topics");
    if (!box) return;

    const topics = data.emerging_topics || [];
    if (!topics.length) {
        box.innerHTML = '<div class="empty">No emerging topics detected.</div>';
        return;
    }

    box.innerHTML = topics.map(topic => {
        const name = topic.topic_name || topic.cluster_label || `Topic ${topic.cluster_id}`;
        const lift = Number(topic.share_lift || 0);
        return `
            <div class="bar-chart-row">
                <span class="bar-chart-label" title="${name}">${name}</span>
                <div class="bar-chart-track">
                    <div class="bar-chart-fill" style="width: ${Math.min(lift * 20, 100)}%; background: var(--coral);"></div>
                </div>
                <span class="bar-chart-val">${lift.toFixed(2)}×</span>
            </div>
            <div style="font-size: 11px; color: var(--muted); margin: -4px 0 8px 152px;">
                ${formatNumber(topic.recent_articles)} recent / ${formatNumber(topic.baseline_articles)} baseline
            </div>
        `;
    }).join("");
}

// 1. GRAPH: Articles by Source (Horizontal Bar Chart)
function renderSourceDistribution(data) {
    const box = $("source-distribution");
    if (!box) return;

    const sources = data.articles_per_source || [];
    if (!sources.length) {
        box.innerHTML = '<div class="empty">No source distribution data.</div>';
        return;
    }

    const maxCount = Math.max(...sources.map(s => Number(s.articles || 0)), 1);

    box.innerHTML = sources.map((item, idx) => {
        const count = Number(item.articles || 0);
        const percent = ((count / maxCount) * 100).toFixed(1);
        const colors = ['#2563eb', '#0284c7', '#0d9488', '#475569'];
        const color = colors[idx % colors.length];

        return `
            <div class="bar-chart-row">
                <span class="bar-chart-label" title="${item.source}">${item.source}</span>
                <div class="bar-chart-track">
                    <div class="bar-chart-fill" style="width: ${percent}%; background: ${color};"></div>
                </div>
                <span class="bar-chart-val">${formatNumber(count)}</span>
            </div>
        `;
    }).join("");
}

// 2. GRAPH: Articles by Topic (Horizontal Bar Chart with Topic Names)
function renderTopicDistribution(data) {
    const box = $("topic-distribution");
    if (!box) return;

    const topics = data.topic_sizes || [];
    if (!topics.length) {
        box.innerHTML = '<div class="empty">No topic size data.</div>';
        return;
    }

    const maxCount = Math.max(...topics.map(t => Number(t.article_count || 0)), 1);

    box.innerHTML = topics.map((item, idx) => {
        const count = Number(item.article_count || 0);
        const name = item.topic_name || item.cluster_label || `Topic ${item.cluster_id}`;
        const percent = ((count / maxCount) * 100).toFixed(1);

        return `
            <div class="bar-chart-row">
                <span class="bar-chart-label" title="${name}">TOPIC ${item.cluster_id}: ${name}</span>
                <div class="bar-chart-track">
                    <div class="bar-chart-fill" style="width: ${percent}%; background: var(--blue);"></div>
                </div>
                <span class="bar-chart-val">${formatNumber(count)}</span>
            </div>
        `;
    }).join("");
}

// 3. GRAPH: Sentiment Distribution (Stacked Bar with Legend)
function renderSentimentDistribution(data) {
    const box = $("sentiment-distribution");
    if (!box) return;

    const sentiment = data.sentiment_counts || {};
    const pos = Number(sentiment.Positive || 0);
    const neu = Number(sentiment.Neutral || 0);
    const neg = Number(sentiment.Negative || 0);
    const total = pos + neu + neg;

    if (!total) {
        box.innerHTML = '<div class="empty">No sentiment data available.</div>';
        return;
    }

    const posPct = ((pos / total) * 100).toFixed(1);
    const neuPct = ((neu / total) * 100).toFixed(1);
    const negPct = ((neg / total) * 100).toFixed(1);

    box.innerHTML = `
        <div style="height: 24px; border-radius: 999px; display: flex; overflow: hidden; margin-bottom: 16px; background: #f1f5f9;">
            <div style="width: ${posPct}%; background: var(--green);" title="Positive: ${pos} (${posPct}%)"></div>
            <div style="width: ${neuPct}%; background: #94a3b8;" title="Neutral: ${neu} (${neuPct}%)"></div>
            <div style="width: ${negPct}%; background: var(--coral);" title="Negative: ${neg} (${negPct}%)"></div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; text-align: center;">
            <div style="padding: 10px; background: var(--green-soft); border-radius: var(--radius-sm);">
                <div style="font-size: 11px; font-weight: 600; color: var(--green); text-transform: uppercase;">Positive</div>
                <div style="font-family: var(--display-font); font-size: 18px; font-weight: 700; color: var(--green);">${formatNumber(pos)}</div>
                <div style="font-size: 10px; color: var(--muted);">${posPct}% of total</div>
            </div>
            <div style="padding: 10px; background: #f1f5f9; border-radius: var(--radius-sm);">
                <div style="font-size: 11px; font-weight: 600; color: var(--muted); text-transform: uppercase;">Neutral</div>
                <div style="font-family: var(--display-font); font-size: 18px; font-weight: 700; color: var(--text);">${formatNumber(neu)}</div>
                <div style="font-size: 10px; color: var(--muted);">${neuPct}% of total</div>
            </div>
            <div style="padding: 10px; background: var(--coral-soft); border-radius: var(--radius-sm);">
                <div style="font-size: 11px; font-weight: 600; color: var(--coral); text-transform: uppercase;">Negative</div>
                <div style="font-family: var(--display-font); font-size: 18px; font-weight: 700; color: var(--coral);">${formatNumber(neg)}</div>
                <div style="font-size: 10px; color: var(--muted);">${negPct}% of total</div>
            </div>
        </div>
    `;
}

// 4. GRAPH: Activity Over Time (SVG Sparkline / Area Chart)
function renderActivityTimeline(trendsData) {
    const box = $("activity-timeline");
    if (!box) return;

    const days = trendsData.days || [];
    const series = trendsData.series || [];

    if (!days.length || !series.length) {
        box.innerHTML = '<div class="empty">No timeline data available.</div>';
        return;
    }

    // Aggregate daily counts across all topics
    const dailyTotals = days.map((_, dayIdx) => {
        return series.reduce((sum, s) => sum + (Number(s.counts?.[dayIdx]) || 0), 0);
    });

    const maxDaily = Math.max(...dailyTotals, 1);
    const width = 500;
    const height = 120;
    const padding = 15;

    // Create SVG path points
    const points = dailyTotals.map((val, idx) => {
        const x = padding + (idx / (dailyTotals.length - 1)) * (width - 2 * padding);
        const y = height - padding - (val / maxDaily) * (height - 2 * padding);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
    });

    const pathD = `M ${points.join(" L ")}`;
    const areaD = `M ${points[0]} L ${points.join(" L ")} L ${width - padding},${height - padding} L ${padding},${height - padding} Z`;

    const startDate = days[0] || "";
    const endDate = days[days.length - 1] || "";
    const totalArticles = dailyTotals.reduce((a, b) => a + b, 0);

    box.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" class="svg-chart" style="width: 100%; height: 120px;">
            <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#2563eb" stop-opacity="0.3"/>
                    <stop offset="100%" stop-color="#2563eb" stop-opacity="0.0"/>
                </linearGradient>
            </defs>
            <path d="${areaD}" fill="url(#areaGrad)"/>
            <path d="${pathD}" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); margin-top: 6px; font-family: var(--data-font);">
            <span>${startDate}</span>
            <span>Peak: ${maxDaily} articles/day (${totalArticles} total)</span>
            <span>${endDate}</span>
        </div>
    `;
}

// 5. GRAPH: Topic Activity (Multi-Topic Trend Chart)
function renderTopicActivity(data) {
    const box = $("trend-chart");
    if (!box) return;

    if (!data.days || !data.days.length || !data.series || !data.series.length) {
        box.innerHTML = '<div class="empty">No trend data available.</div>';
        return;
    }

    const latest = data.series
        .map(series => ({
            id: series.cluster_id,
            label: series.topic_name || series.label || `Topic ${series.cluster_id}`,
            value: Number(series.rolling_3d?.at(-1) || 0)
        }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 6);

    const maxValue = Math.max(...latest.map(item => item.value), 1);
    const colors = ['#2563eb', '#0284c7', '#0d9488', '#16a34a', '#d97706', '#dc2626'];

    box.innerHTML = latest.map((item, idx) => `
        <div class="bar-chart-row">
            <span class="bar-chart-label" title="${item.label}">T${item.id}: ${item.label}</span>
            <div class="bar-chart-track">
                <div class="bar-chart-fill" style="width: ${(item.value / maxValue * 100).toFixed(1)}%; background: ${colors[idx % colors.length]};"></div>
            </div>
            <span class="bar-chart-val">${item.value.toFixed(2)}</span>
        </div>
    `).join("");
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
            <div class="pair-title" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span>
                    <strong>${pair.source_i || "Source"}</strong>
                    <span class="arrow">↔</span>
                    <strong>${pair.source_j || "Source"}</strong>
                </span>
                <span class="badge" style="background: var(--blue-soft); color: var(--blue);">
                    ${(Number(pair.similarity || 0) * 100).toFixed(1)}% match
                </span>
            </div>
            <div style="font-size: 12.5px; color: var(--text); line-height: 1.4;">
                <a href="${pair.url_i || '#'}" target="_blank" rel="noopener" style="color: var(--text);">${pair.title_i || "Untitled"}</a>
                <span style="color: var(--muted); margin: 0 4px;">/</span>
                <a href="${pair.url_j || '#'}" target="_blank" rel="noopener" style="color: var(--text-secondary);">${pair.title_j || "Untitled"}</a>
            </div>
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

    const maxArticles = Math.max(...sources.map(source => Number(source.articles || 0)), 1);

    box.innerHTML = sources.map(source => `
        <div class="bar-chart-row">
            <span class="bar-chart-label">${source.source}</span>
            <div class="bar-chart-track">
                <div class="bar-chart-fill" style="width: ${(Number(source.articles) / maxArticles * 100).toFixed(1)}%;"></div>
            </div>
            <span class="bar-chart-val">${formatNumber(source.articles)}</span>
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

    box.innerHTML = articles.slice(0, 6).map(article => `
        <div class="art">
            <a href="${article.url || '#'}" target="_blank" rel="noopener">
                ${article.title || "Untitled article"}
            </a>
            <small>
                <strong>${article.source || ""}</strong> · ${article.date || ""}
                ${article.cluster_label ? ` · <span class="article-tag">${article.cluster_label}</span>` : ""}
            </small>
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
        renderSourceDistribution(overview);
        renderTopicDistribution(overview);
        renderSentimentDistribution(overview);
        renderActivityTimeline(trends);
        renderTopicActivity(trends);
        renderSimilar(overview);
        renderSources(overview);
        renderLatest(articles);

    } catch (error) {
        console.error(error);
        showError(`Dashboard data could not be loaded: ${error.message}`);
    }
}

document.addEventListener("DOMContentLoaded", loadDashboard);
