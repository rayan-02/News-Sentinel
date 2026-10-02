/* ==========================================================================
   News Sentinel: shared helpers
   Loaded on every page before the page script. Exposes window.NS.

   - safe rendering helpers (escapeHTML, safeURL, linkOrText)
   - data loading (fetchJSON) and small formatters
   - a dependency-free SVG line chart with hover tooltip and legend
   - sparkline, article row, mobile navigation toggle
   ========================================================================== */

(function () {
    "use strict";

    const PALETTE = [
        "#181818", "#D2402A", "#2F6F8F", "#B8860B",
        "#5B7F4F", "#8A5A83", "#7A766C", "#2A9D8F"
    ];


    /* ---------- safe rendering ---------- */

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

            if (url.protocol === "http:" || url.protocol === "https:") {
                return url.href;
            }

            return "#";
        } catch {
            return "#";
        }
    }

    /* A link when the URL is usable, plain text otherwise. */
    function linkOrText(url, text, className) {
        const href = safeURL(url);
        const label = escapeHTML(text);
        const cls = className ? ` class="${className}"` : "";

        if (href === "#") {
            return `<span${cls}>${label}</span>`;
        }

        return `<a${cls} href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`;
    }


    /* ---------- data and formatting ---------- */

    async function fetchJSON(name) {
        let response;

        try {
            response = await fetch(`/api/${name}`);
        } catch {
            throw new Error(`${name}.json could not be loaded (is the server running?)`);
        }

        if (!response.ok) {
            let detail = "";

            try {
                detail = (await response.json()).error || "";
            } catch {
                /* the response body was not JSON */
            }

            throw new Error(detail || `${name}.json could not be loaded`);
        }

        return response.json();
    }

    function formatNumber(value) {
        return Number(value || 0).toLocaleString();
    }

    function isBlank(value) {
        return value === null || value === undefined || value === "" ||
            Number.isNaN(Number(value));
    }

    function formatSentiment(value, digits = 3) {
        return isBlank(value) ? "\u2014" : Number(value).toFixed(digits);
    }

    function formatSigned(value, digits = 3) {
        if (isBlank(value)) {
            return "\u2014";
        }

        const number = Number(value);

        return `${number > 0 ? "+" : ""}${number.toFixed(digits)}`;
    }

    function formatPercent(ratio, digits = 1) {
        return `${(Number(ratio || 0) * 100).toFixed(digits)}%`;
    }

    function topicName(topic) {
        return topic.cluster_label || topic.label || `Topic ${topic.cluster_id}`;
    }

    function sentimentClass(label) {
        const sentiment = String(label || "").toLowerCase();

        if (sentiment === "positive") return "positive";
        if (sentiment === "negative") return "negative";

        return "neutral";
    }

    function parseDay(day) {
        const text = String(day || "");

        if (!/^\d{4}-\d{2}-\d{2}/.test(text)) {
            return null;
        }

        const date = new Date(`${text.slice(0, 10)}T00:00:00Z`);

        return Number.isNaN(date.getTime()) ? null : date;
    }

    function formatDay(day, long = false) {
        const date = parseDay(day);

        if (!date) {
            return String(day ?? "");
        }

        return date.toLocaleDateString("en-GB", {
            day: "numeric",
            month: "short",
            year: long ? "numeric" : undefined,
            timeZone: "UTC"
        });
    }

    function trimNumber(value, digits = 2) {
        return String(Number(Number(value).toFixed(digits)));
    }


    /* ---------- states ---------- */

    function emptyState(message) {
        return `<div class="empty">${escapeHTML(message)}</div>`;
    }

    function showError(box, message) {
        if (!box) {
            return;
        }

        box.textContent = message;
        box.hidden = false;
    }


    /* ---------- article row (Articles page and Overview) ---------- */

    function articleRow(article, options = {}) {
        const keywordsSource = article.top_keywords ?? article.keywords ?? [];
        const keywords = Array.isArray(keywordsSource)
            ? keywordsSource
            : String(keywordsSource).split(",").map(item => item.trim()).filter(Boolean);

        const tags = [];

        if (article.cluster_label) {
            tags.push(article.cluster_label);
        }

        if (options.keywords) {
            tags.push(...keywords.slice(0, 3));
        }

        return `
            <article class="article-row">
                <div>
                    ${linkOrText(article.url, article.title || "Untitled article", "article-title")}

                    <div class="article-meta">
                        <span class="source-name">${escapeHTML(article.source || "Unknown source")}</span>
                        ${article.date ? `<span>${escapeHTML(article.date)}</span>` : ""}
                        ${tags.map(tag => `<span class="article-tag">${escapeHTML(tag)}</span>`).join("")}
                    </div>
                </div>

                <span class="article-sentiment ${sentimentClass(article.sentiment_label)}">
                    ${escapeHTML(article.sentiment_label || "Unknown")}
                </span>
            </article>
        `;
    }


    /* ---------- chart helpers ---------- */

    /* Round the axis maximum up to a tidy step (1, 2, 2.5, 5 x 10^n). */
    function niceScale(max, maxTicks = 5) {
        if (!(max > 0)) {
            return { top: 1, step: 0.25, ticks: 4 };
        }

        const rawStep = max / maxTicks;
        const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
        const step = [1, 2, 2.5, 5, 10]
            .map(multiple => multiple * magnitude)
            .find(candidate => candidate >= rawStep);

        const ticks = Math.ceil(max / step - 1e-9);

        return { top: step * ticks, step, ticks };
    }

    function createLineChart(host, config) {
        const days = config.days || [];
        const all = (config.series || []).map(series => ({
            ...series,
            values: days.map((_, index) => {
                const number = Number((series.values || [])[index]);
                return Number.isFinite(number) ? number : 0;
            })
        }));

        const state = { hidden: new Set(), focus: null };
        let geometry = null;

        host.classList.add("chart");
        host.innerHTML = `
            <svg class="chart-svg" role="img"></svg>
            <div class="chart-tip" hidden></div>
        `;

        const svg = host.querySelector("svg");
        const tip = host.querySelector(".chart-tip");

        svg.setAttribute("aria-label", config.label || "Line chart of topic activity over time");

        function visible() {
            return all.filter(series => !state.hidden.has(series.id));
        }

        function draw() {
            const width = Math.max(host.clientWidth, 280);
            const height = config.height || (width < 520 ? 240 : 320);
            const shown = visible();
            const max = Math.max(0, ...shown.flatMap(series => series.values));
            const scale = niceScale(max);

            const tickLabels = Array.from({ length: scale.ticks + 1 }, (_, index) =>
                trimNumber(scale.step * index));

            const widest = Math.max(...tickLabels.map(label => label.length));
            const margin = {
                top: 12,
                right: 16,
                bottom: 30,
                left: Math.max(32, widest * 7 + 16)
            };

            const plotW = width - margin.left - margin.right;
            const plotH = height - margin.top - margin.bottom;
            const count = days.length;

            const x = index => margin.left + (count > 1 ? plotW * index / (count - 1) : plotW / 2);
            const y = value => margin.top + plotH - (value / scale.top) * plotH;

            geometry = { width, height, margin, plotW, plotH, count, x, y };

            const grid = tickLabels.map((label, index) => {
                const yy = y(scale.step * index);

                return `
                    <line class="${index === 0 ? "axis-line" : "grid-line"}"
                          x1="${margin.left}" x2="${width - margin.right}" y1="${yy}" y2="${yy}"></line>
                    <text class="axis-label" x="${margin.left - 8}" y="${yy + 4}" text-anchor="end">${label}</text>
                `;
            }).join("");

            const labelCount = Math.min(count, Math.max(2, Math.floor(plotW / 82)));
            const labelIndexes = count <= 1
                ? [0]
                : [...new Set(Array.from({ length: labelCount }, (_, k) =>
                    Math.round(k * (count - 1) / (labelCount - 1))))];

            const xLabels = labelIndexes.map(index => {
                const anchor = index === 0 ? "start" : index === count - 1 ? "end" : "middle";

                return `<text class="axis-label" x="${x(index)}" y="${height - 8}" text-anchor="${anchor}">${escapeHTML(formatDay(days[index]))}</text>`;
            }).join("");

            const lines = shown.map(series => {
                const path = count > 1
                    ? "M" + series.values.map((value, index) => `${x(index).toFixed(1)} ${y(value).toFixed(1)}`).join(" L")
                    : "";

                const single = count === 1
                    ? `<circle cx="${x(0)}" cy="${y(series.values[0])}" r="4" fill="${series.color}"></circle>`
                    : "";

                return `
                    <path class="series-line${state.focus === series.id ? " is-focus" : ""}"
                          data-id="${escapeHTML(series.id)}" d="${path}" stroke="${series.color}"></path>
                    ${single}
                `;
            }).join("");

            svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
            svg.innerHTML = `
                ${grid}
                ${xLabels}
                ${lines}
                <line class="chart-guide" y1="${margin.top}" y2="${margin.top + plotH}" x1="-10" x2="-10" hidden></line>
                <g class="hover-dots"></g>
                <rect class="chart-hit" x="${margin.left}" y="${margin.top}" width="${plotW}" height="${plotH}" fill="transparent"></rect>
            `;

            if (!shown.length) {
                svg.insertAdjacentHTML("beforeend",
                    `<text class="axis-label" x="${width / 2}" y="${height / 2}" text-anchor="middle">Select at least one topic below</text>`);
            }

            host.classList.toggle("has-focus", Boolean(state.focus));
            hideTip();
        }

        function hideTip() {
            tip.hidden = true;

            const guide = svg.querySelector(".chart-guide");
            const dots = svg.querySelector(".hover-dots");

            if (guide) guide.setAttribute("hidden", "");
            if (dots) dots.innerHTML = "";
        }

        function onMove(event) {
            if (!geometry || !geometry.count) {
                return;
            }

            const box = svg.getBoundingClientRect();
            const scaleX = geometry.width / box.width;
            const pointerX = (event.clientX - box.left) * scaleX;
            const { margin, plotW, count, x, y } = geometry;

            if (pointerX < margin.left - 6 || pointerX > margin.left + plotW + 6) {
                hideTip();
                return;
            }

            const index = count > 1
                ? Math.min(count - 1, Math.max(0, Math.round((pointerX - margin.left) / plotW * (count - 1))))
                : 0;

            const rows = visible()
                .map(series => ({ series, value: series.values[index] }))
                .sort((a, b) => b.value - a.value)
                .slice(0, 8);

            const guide = svg.querySelector(".chart-guide");
            guide.setAttribute("x1", x(index));
            guide.setAttribute("x2", x(index));
            guide.removeAttribute("hidden");

            svg.querySelector(".hover-dots").innerHTML = rows.map(({ series, value }) =>
                `<circle class="hover-dot" cx="${x(index)}" cy="${y(value)}" r="4.5" fill="${series.color}"></circle>`
            ).join("");

            tip.innerHTML = `
                <strong>${escapeHTML(formatDay(days[index], true))}</strong>
                ${rows.map(({ series, value }) => `
                    <div class="tip-row">
                        <span class="tip-swatch" style="background:${series.color}"></span>
                        <span class="tip-name">${escapeHTML(series.label)}</span>
                        <span class="tip-val">${trimNumber(value)}</span>
                    </div>
                `).join("")}
            `;
            tip.hidden = false;

            const pixelX = x(index) / scaleX;
            const tipWidth = tip.offsetWidth;
            let left = pixelX + 14;

            if (left + tipWidth > box.width) {
                left = pixelX - tipWidth - 14;
            }

            tip.style.left = `${Math.max(0, left)}px`;
        }

        svg.addEventListener("pointermove", onMove);
        svg.addEventListener("pointerdown", onMove);
        svg.addEventListener("pointerleave", hideTip);

        let lastWidth = 0;

        if ("ResizeObserver" in window) {
            new ResizeObserver(() => {
                if (host.clientWidth !== lastWidth) {
                    lastWidth = host.clientWidth;
                    draw();
                }
            }).observe(host);
        } else {
            window.addEventListener("resize", draw);
        }

        draw();

        return {
            toggle(id) {
                if (state.hidden.has(id)) {
                    state.hidden.delete(id);
                } else {
                    state.hidden.add(id);
                }

                draw();

                return !state.hidden.has(id);
            },

            highlight(id) {
                state.focus = id;
                host.classList.toggle("has-focus", Boolean(id));

                svg.querySelectorAll(".series-line").forEach(line => {
                    line.classList.toggle("is-focus", line.dataset.id === id);
                });
            },

            setSeries(nextValues) {
                all.forEach(series => {
                    if (nextValues[series.id]) {
                        series.values = days.map((_, index) => {
                            const number = Number(nextValues[series.id][index]);
                            return Number.isFinite(number) ? number : 0;
                        });
                    }
                });

                draw();
            },

            redraw: draw
        };
    }

    /* Toggle buttons that show, hide and highlight chart lines. */
    function renderLegend(container, chart, series) {
        container.innerHTML = series.map(item => `
            <button type="button" class="legend-btn" aria-pressed="true"
                    data-id="${escapeHTML(item.id)}" style="--c:${item.color}">
                <span class="swatch"></span>
                <span class="legend-label">${escapeHTML(item.label)}</span>
            </button>
        `).join("");

        container.querySelectorAll(".legend-btn").forEach(button => {
            const id = button.dataset.id;

            button.addEventListener("click", () => {
                const on = chart.toggle(id);
                button.setAttribute("aria-pressed", String(on));
            });

            button.addEventListener("mouseenter", () => chart.highlight(id));
            button.addEventListener("focus", () => chart.highlight(id));
            button.addEventListener("mouseleave", () => chart.highlight(null));
            button.addEventListener("blur", () => chart.highlight(null));
        });
    }

    function sparkline(values, color) {
        const numbers = (values || []).map(value => {
            const number = Number(value);
            return Number.isFinite(number) ? number : 0;
        });

        if (numbers.length < 2) {
            return "";
        }

        const width = 120;
        const height = 34;
        const pad = 3;
        const max = Math.max(...numbers, 1);

        const points = numbers.map((value, index) => {
            const px = pad + index / (numbers.length - 1) * (width - pad * 2);
            const py = height - pad - value / max * (height - pad * 2);

            return `${px.toFixed(1)},${py.toFixed(1)}`;
        }).join(" ");

        const stroke = color || "currentColor";

        return `
            <svg class="sparkline" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none"
                 aria-hidden="true" focusable="false">
                <polygon points="${pad},${height - pad} ${points} ${width - pad},${height - pad}"
                         fill="${stroke}" opacity="0.1"></polygon>
                <polyline points="${points}" fill="none" stroke="${stroke}" stroke-width="1.8"
                          stroke-linejoin="round" stroke-linecap="round"
                          vector-effect="non-scaling-stroke"></polyline>
            </svg>
        `;
    }


    /* ---------- page behaviour ---------- */

    function setupNavigation() {
        const toggle = document.querySelector(".nav-toggle");
        const sidebar = document.getElementById("sidebar");

        if (toggle && sidebar) {
            toggle.addEventListener("click", () => {
                const open = sidebar.classList.toggle("is-open");
                toggle.setAttribute("aria-expanded", String(open));
            });

            document.addEventListener("keydown", event => {
                if (event.key === "Escape" && sidebar.classList.contains("is-open")) {
                    sidebar.classList.remove("is-open");
                    toggle.setAttribute("aria-expanded", "false");
                    toggle.focus();
                }
            });
        }

        document.querySelectorAll("a[href^='http']").forEach(link => {
            link.target = "_blank";
            link.rel = "noopener noreferrer";
        });
    }

    document.addEventListener("DOMContentLoaded", setupNavigation);


    window.NS = {
        PALETTE,
        escapeHTML,
        safeURL,
        linkOrText,
        fetchJSON,
        formatNumber,
        formatSentiment,
        formatSigned,
        formatPercent,
        formatDay,
        trimNumber,
        topicName,
        sentimentClass,
        emptyState,
        showError,
        articleRow,
        createLineChart,
        renderLegend,
        sparkline
    };
})();
