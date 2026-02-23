/* SMART Goals Tracker — Dashboard logic */

// ── i18n ────────────────────────────────────────────────────────────────
//
// Locale files are loaded as <script> tags before this file.  Each one
// exposes a global LOCALE_XX constant.  Register them below.
//
// To add a new language:
//   1. Copy  static/i18n/en.js  to  static/i18n/xx.js
//   2. Translate every value.
//   3. Add  { code: "xx", data: LOCALE_XX }  to LOCALES below.
//   4. Add  <script src="/static/i18n/xx.js"></script>  in index.html
//      (before app.js).

const LOCALES = [
    { code: "en", data: LOCALE_EN },
    { code: "fr", data: LOCALE_FR },
];

const SUPPORTED_LANGS = new Set(LOCALES.map(l => l.code));
const DEFAULT_LANG = "en";

/**
 * Walk through navigator.languages in priority order and return
 * { code, tag } where code is the primary language ("fr") and tag is
 * the full BCP 47 tag from the browser ("fr-CA").
 * Falls back to DEFAULT_LANG with no regional variant.
 */
function detectLang() {
    const candidates = navigator.languages || [navigator.language || navigator.userLanguage || DEFAULT_LANG];
    for (const tag of candidates) {
        const primary = tag.toLowerCase().split("-")[0];
        if (SUPPORTED_LANGS.has(primary)) return { code: primary, tag: tag };
    }
    return { code: DEFAULT_LANG, tag: DEFAULT_LANG };
}

const detected = detectLang();
const LANG = detected.code;
const t = LOCALES.find(l => l.code === LANG).data;
t.dateLocale = detected.tag;
t.sortLocale = detected.tag;

// ── Apply i18n to static HTML elements ──────────────────────────────────

function applyStaticI18n() {
    document.documentElement.lang = LANG;
    document.getElementById('header-meta').textContent = t.loading;
    document.getElementById('sort-label').title = t.sortLabel;
    document.getElementById('sort-opt-file').textContent = t.sortFile;
    document.getElementById('sort-opt-name').textContent = t.sortName;
    document.getElementById('sort-opt-priority').textContent = t.sortPriority;
    document.getElementById('tab-overview').textContent = t.tabOverview;
    document.getElementById('tab-gantt').textContent = t.tabGantt;
    document.getElementById('tab-predictions').textContent = t.tabPredictions;

    document.querySelectorAll('.view .loading').forEach(el => {
        el.innerHTML = `<div class="spinner"></div> ${t.loading}`;
    });
}

// ── State ───────────────────────────────────────────────────────────────

let goalsData = null;
let ganttData = null;
let parseErrors = [];
let errorsExpanded = true;

// ── Tabs ────────────────────────────────────────────────────────────────

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`view-${tab.dataset.view}`).classList.add('active');
    });
});

// ── Theme ───────────────────────────────────────────────────────────────

function applyTheme() {
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.getElementById('theme-light').disabled = isDark;
    document.getElementById('theme-dark').disabled = !isDark;
}
applyTheme();
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme);

// ── Data fetching ───────────────────────────────────────────────────────

async function fetchData() {
    try {
        const [gr, gnr] = await Promise.all([fetch('/api/goals'), fetch('/api/gantt')]);
        goalsData = await gr.json();
        ganttData = await gnr.json();

        // Collect parsing errors from both responses
        parseErrors = [];
        if (goalsData.errors && goalsData.errors.length > 0) {
            parseErrors = goalsData.errors;
        }

        document.getElementById('header-meta').textContent =
            t.headerMeta(goalsData.goals.length, goalsData.as_of);

        // Check for fatal errors (ERROR level that prevented parsing)
        const fatalErrors = parseErrors.filter(e => e.level === 'error');
        if (fatalErrors.length > 0 && goalsData.goals.length === 0) {
            renderFatalErrors(fatalErrors);
            return;
        }

        renderErrorBanner();
        renderFilterBar();
        renderOverview();
        renderGantt();
        renderPredictions();
    } catch (e) {
        document.getElementById('view-overview').innerHTML =
            `<div class="loading">${t.loadError}</div>`;
    }
}

// ── Error rendering ─────────────────────────────────────────────────────

function renderFatalErrors(errors) {
    const html = `
        <div class="error-panel error-fatal">
            <div class="error-header">
                <span class="error-icon">✕</span>
                <h2>${t.parsingErrors}</h2>
            </div>
            <p class="error-desc">${t.parsingErrorsDesc}</p>
            <div class="error-list">
                ${errors.map(e => renderErrorItem(e)).join('')}
            </div>
        </div>`;

    document.getElementById('view-overview').innerHTML = html;
    document.getElementById('view-gantt').innerHTML = `<div class="loading">${t.noData}</div>`;
    document.getElementById('view-predictions').innerHTML = `<div class="loading">${t.noData}</div>`;
}

function renderErrorBanner() {
    const container = document.getElementById('error-banner');
    if (!container) return;

    if (parseErrors.length === 0) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }

    const errorCount = parseErrors.filter(e => e.level === 'error').length;
    const warningCount = parseErrors.filter(e => e.level === 'warning').length;

    container.style.display = 'block';
    container.innerHTML = `
        <div class="error-banner ${errorCount > 0 ? 'has-errors' : 'warnings-only'}">
            <div class="error-banner-header" onclick="toggleErrorDetails()">
                <div class="error-banner-summary">
                    <span class="error-icon">${errorCount > 0 ? '⚠' : '⚡'}</span>
                    <span class="error-count">${t.errorsCount(parseErrors.length)}</span>
                    ${errorCount > 0 ? `<span class="badge error-badge">${errorCount} ${t.errorLevelError.toLowerCase()}</span>` : ''}
                    ${warningCount > 0 ? `<span class="badge warning-badge">${warningCount} ${t.errorLevelWarning.toLowerCase()}</span>` : ''}
                </div>
                <button class="error-toggle-btn">${errorsExpanded ? t.hideErrors : t.showErrors}</button>
            </div>
            <div class="error-banner-details ${errorsExpanded ? 'expanded' : ''}">
                <p class="error-desc">${t.parsingErrorsDesc}</p>
                <div class="error-list">
                    ${parseErrors.map(e => renderErrorItem(e)).join('')}
                </div>
            </div>
        </div>`;
}

function toggleErrorDetails() {
    errorsExpanded = !errorsExpanded;
    renderErrorBanner();
}

function renderErrorItem(e) {
    const levelClass = e.level === 'error' ? 'level-error' : 'level-warning';
    const levelLabel = e.level === 'error' ? t.errorLevelError : t.errorLevelWarning;
    const lineInfo = e.line ? `<span class="error-line">${t.errorLine} ${e.line}</span>` : '';
    const contextInfo = e.context ? `<span class="error-context">${t.errorContext}: <code>${e.context}</code></span>` : '';

    return `
        <div class="error-item ${levelClass}">
            <span class="error-level-badge">${levelLabel}</span>
            <span class="error-message">${escHtml(e.message)}</span>
            <div class="error-meta">
                ${lineInfo}
                ${contextInfo}
            </div>
        </div>`;
}

// ── Helpers ──────────────────────────────────────────────────────────────

const statusLabels = {
    done: t.status_done, in_progress: t.status_in_progress,
    not_started: t.status_not_started, paused: t.status_paused,
    cancelled: t.status_cancelled,
};
const priorityLabels = {
    optional: t.priority_optional, low: t.priority_low,
    medium: t.priority_medium, high: t.priority_high,
    capital: t.priority_capital,
};

function statusBadge(s) {
    return `<span class="badge status-${s}">${statusLabels[s] || s}</span>`;
}
function priorityBadge(p) {
    return `<span class="badge priority-${p}">${priorityLabels[p] || p}</span>`;
}
function modeBadge(mode, unit) {
    if (mode === 'fixed') return `<span class="mode-text">${t.modeFixed}</span>`;
    const label = mode === 'performance' ? t.modePerformance : t.modeCumulative;
    return `<span class="mode-text">${label}${unit ? ' · ' + unit : ''}</span>`;
}

function fmtDate(d) {
    if (!d) return '—';
    const hasTime = d.includes('T') && !d.endsWith('T00:00:00');
    const dt = new Date(d.includes('T') ? d : d + 'T00:00:00');
    const opts = { year: 'numeric', month: 'short', day: 'numeric' };
    let str = dt.toLocaleDateString(t.dateLocale, opts);
    if (hasTime) {
        const hh = String(dt.getHours()).padStart(2, '0');
        const mm = String(dt.getMinutes()).padStart(2, '0');
        str += ` ${hh}:${mm}`;
    }
    return str;
}

function fmtVal(v, u) {
    if (v == null) return '—';
    return `${v}${u ? ' ' + u : ''}`;
}
function depsStr(deps) {
    if (!deps || !deps.length) return '';
    return deps.map(d => `<span class="dep-link" data-dep="${d}" onmouseenter="highlightDep(this)" onmouseleave="unhighlightDep(this)">→${d}</span>`).join(' ');
}

function checkboxIcon(status) {
    if (status === 'done') return '<span class="checkbox checkbox-done">✓</span>';
    if (status === 'in_progress') return '<span class="checkbox checkbox-progress">◐</span>';
    if (status === 'cancelled') return '<span class="checkbox checkbox-cancelled">✕</span>';
    if (status === 'paused') return '<span class="checkbox checkbox-paused">⏸</span>';
    return '<span class="checkbox checkbox-empty">○</span>';
}

function escHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function smartBadge(node) {
    try {
        if (!node || !node.has_smart || !node.smart) return '';
        const s = node.smart;
        const lines = [];
        if (s.specific) lines.push(`Specific: ${s.specific}`);
        if (s.measurable) lines.push(`Measurable: ${s.measurable}`);
        if (s.actionable) lines.push(`Actionable: ${s.actionable}`);
        if (s.relevant) lines.push(`Relevant: ${s.relevant}`);
        if (s.time_bound) lines.push(`Time-bound: ${s.time_bound}`);
        const tip = escHtml(lines.join('|||'));
        return `<span class="mode-badge smart-badge" onmouseenter="showSmartTT(event,this)" onmouseleave="hideSmartTT()" data-smart="${tip}">SMART</span>`;
    } catch (e) {
        console.error('smartBadge error:', e);
        return '<span class="mode-badge smart-badge">SMART</span>';
    }
}

function fmtPred(node) {
    if (!node.predicted_end) return '—';
    const partial = node.prediction_partial ? ` <span class="partial-badge">${t.badgePartial}</span>` : '';
    return fmtDate(node.predicted_end) + partial;
}

// ── Recursive table rows ────────────────────────────────────────────────

function progressSourceBadge(node) {
    if (!node.progress_source || node.progress_source === 'tracking' || node.progress_source === 'weighted') return '';
    if (node.progress_source === 'predicted') {
        if (node.prediction_partial) return ` <span class="partial-badge">${t.badgePartial}</span>`;
        return ` <span class="partial-badge">${t.badgePrediction}</span>`;
    }
    if (node.progress_source === 'insufficient') return ` <span class="partial-badge">${t.badgeInsufficient}</span>`;
    return '';
}

function renderNodeRows(node, depth) {
    const indent = depth * 1.2;
    const isCancelled = node.status === 'cancelled';
    const isOpen = node.type === 'open';
    const progressColor = node.status === 'done' ? 'var(--accent-green)'
        : isCancelled ? 'var(--accent-red)' : 'var(--accent-blue)';

    let detail = '';
    if (!isOpen && !node.has_children && node.target) {
        const cur = fmtVal(node.current_value, node.unit_label);
        const tgt = fmtVal(node.target, node.unit_label);
        if (node.unit_label !== '%') {
            detail = `<div class="progress-detail">${cur} / ${tgt}</div>`;
        }
    }

    const titleText = isCancelled
        ? `<span class="cancelled-text">${node.title}</span>`
        : node.title;

    const icon = isOpen ? '<span class="checkbox checkbox-empty">—</span>' : checkboxIcon(node.status);
    const modeCol = isOpen ? `<span class="mode-text">${t.modeOpen}</span>` : (node.has_children ? '' : modeBadge(node.tracking_mode, node.unit_label));

    let progressCol;
    if (isOpen) {
        progressCol = '—';
    } else if (node.progress_source === 'insufficient') {
        progressCol = `<span class="partial-badge">${t.badgeInsufficient}</span>`;
    } else {
        progressCol = `<div class="mini-progress">
                <div class="mini-progress-fill" style="width:${node.percent_complete}%;background:${progressColor}"></div>
            </div>
            ${node.percent_complete.toFixed(0)}%${progressSourceBadge(node)}${detail}`;
    }

    let html = `<tr class="${isCancelled ? 'cancelled' : ''}" data-node-id="${node.id}">
        <td style="padding-left:${0.6 + indent}rem">
            ${icon} ${titleText}
            ${node.depends_on.length ? `<span class="deps-hint">${depsStr(node.depends_on)}</span>` : ''}
        </td>
        <td class="mode-text">${node.id}</td>
        <td>${priorityBadge(node.priority)}</td>
        <td>${modeCol}</td>
        <td>${progressCol}</td>
        <td class="mono">${isCancelled || isOpen ? '—' : fmtPred(node)}</td>
    </tr>`;

    for (const child of (node.children || [])) {
        html += renderNodeRows(child, depth + 1);
    }
    return html;
}

// ── Mini timeline (overview cards) ──────────────────────────────────────

function timelineDate(node) {
    if (node.status === 'cancelled') return t.cancelled;
    if (node.status === 'done' && node.end) return t.doneOn(fmtDate(node.end));
    if (node.tracking_mode === 'fixed' && node.predicted_end) return t.fixedEnd(fmtDate(node.predicted_end));
    if (node.predicted_end) return t.predicted(fmtDate(node.predicted_end));
    if (node.status === 'not_started') return t.waiting;
    return t.insufficientData;
}

function renderMiniTimeline(node) {
    const isCancelled = node.status === 'cancelled';
    const titleText = isCancelled
        ? `<span class="cancelled-text">${node.title}</span>`
        : node.title;

    let html = `<div class="prediction-item-icon">
        <span class="pred-icon">${checkboxIcon(node.status)}</span>
        <div class="pred-content">
            <div class="pred-title">${titleText}</div>
            <div class="pred-date">${timelineDate(node)}</div>
        </div>
    </div>`;

    for (const child of (node.children || [])) {
        html += renderMiniTimeline(child);
    }
    return html;
}

// ── Overview ────────────────────────────────────────────────────────────

let currentSort = 'file';
const activeFilters = { priority: new Set(), tag: new Set() };

function sortGoals(goals, mode) {
    if (mode === 'name') {
        return [...goals].sort((a, b) => a.title.localeCompare(b.title, t.sortLocale));
    }
    if (mode === 'priority') {
        return [...goals].sort((a, b) => {
            const p = b.priority_rank - a.priority_rank;
            if (p !== 0) return p;
            return a.title.localeCompare(b.title, t.sortLocale);
        });
    }
    return goals;
}

function filterGoals(goals) {
    return goals.filter(g => {
        if (activeFilters.priority.size > 0 && !activeFilters.priority.has(g.priority)) return false;
        if (activeFilters.tag.size > 0) {
            const tags = g.tags || [];
            if (!tags.some(tg => activeFilters.tag.has(tg))) return false;
        }
        return true;
    });
}

function getGoals() {
    return filterGoals(sortGoals(goalsData.goals, currentSort));
}

function renderFilterBar() {
    const goals = goalsData.goals;

    const usedPriorities = new Set(goals.map(g => g.priority));
    const tags = [...new Set(goals.flatMap(g => g.tags || []))].sort((a, b) => a.localeCompare(b, t.sortLocale));

    let html = '';

    // Priority filter — always show all 5 levels
    html += `<div class="filter-group"><span class="filter-group-label">◆ ${t.filterPriority}</span>`;
    for (const p of ['capital', 'high', 'medium', 'low', 'optional']) {
        const used = usedPriorities.has(p);
        const active = activeFilters.priority.has(p) ? ' active' : '';
        const disabled = !used ? ' disabled' : '';
        html += `<button class="filter-btn filter-btn-priority priority-${p}${active}${disabled}" data-filter="priority" data-value="${p}"${!used ? ' disabled' : ''}>${priorityLabels[p]}</button>`;
    }
    html += `</div>`;

    if (tags.length > 0) {
        html += `<div class="filter-group"><span class="filter-group-label">⏿ ${t.filterCategory}</span>`;
        for (const tg of tags) {
            const active = activeFilters.tag.has(tg) ? ' active' : '';
            html += `<button class="filter-btn${active}" data-filter="tag" data-value="${tg}">${tg}</button>`;
        }
        html += `</div>`;
    }

    document.getElementById('filter-bar').innerHTML = html;

    document.querySelectorAll('.filter-btn:not(.disabled)').forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.dataset.filter;
            const value = btn.dataset.value;
            if (activeFilters[type].has(value)) {
                activeFilters[type].delete(value);
            } else {
                activeFilters[type].add(value);
            }
            renderFilterBar();
            renderOverview();
            renderGantt();
            renderPredictions();
        });
    });
}

function renderOverview() {
    const goals = getGoals();
    const allGoals = goalsData.goals;
    const activeGoals = allGoals.filter(g => g.status === 'in_progress');
    const trackedGoals = allGoals.filter(g => g.on_track !== null);
    const onTrackGoals = trackedGoals.filter(g => g.on_track === true);
    const offTrackGoals = trackedGoals.filter(g => g.on_track === false);

    let html = `<div class="summary-grid">
        <div class="stat-card">
            <div class="stat-label">${t.activeGoals}</div>
            <div class="stat-value">${activeGoals.length}<span class="stat-sub-inline"> / ${goals.length}</span></div>
            ${activeGoals.length ? `<div class="stat-list">${activeGoals.map(g =>
                `<a href="#goal-${g.id}" class="stat-list-item">${g.title} ${g.type !== 'open' ? `<span class="stat-list-pct">${g.percent_complete.toFixed(0)}%</span>` : ''}</a>`
            ).join('')}</div>` : ''}
        </div>
        <div class="stat-card">
            <div class="stat-label">${t.deadlineTracking}</div>
            <div class="stat-value">${onTrackGoals.length}<span class="stat-sub-inline"> / ${trackedGoals.length} ${t.onTrackSummary}</span></div>
            ${onTrackGoals.length ? `<div class="stat-list">
                <div class="stat-list-header on-track">${t.onTrackHeader}</div>
                ${onTrackGoals.map(g =>
                `<a href="#goal-${g.id}" class="stat-list-item on-track">${g.title}</a>`
            ).join('')}</div>` : ''}
            ${offTrackGoals.length ? `<div class="stat-list">
                <div class="stat-list-header off-track">${t.offTrackHeader}</div>
                ${offTrackGoals.map(g =>
                `<a href="#goal-${g.id}" class="stat-list-item off-track">${g.title}</a>`
            ).join('')}</div>` : ''}
        </div>
    </div>`;

    for (const g of goals) {
        const pct = g.percent_complete;

        html += `<div class="goal-card" id="goal-${g.id}">
            <div class="goal-header">
                <div>
                    <div class="goal-title">${g.title}</div>
                    <div class="goal-badges">
                        ${statusBadge(g.status)}
                        ${priorityBadge(g.priority)}
                        ${smartBadge(g)}
                        ${(g.tags || []).map(tg => `<span class="tag">${tg}</span>`).join('')}
                        ${(g.depends_on || []).length ? `<span class="mode-badge">${g.depends_on.map(d => '→' + d).join(' ')}</span>` : ''}
                    </div>
                </div>
                <div style="text-align:right">
                    ${g.type === 'open' ? '' : `<span class="pct-value">${g.progress_source === 'insufficient' ? '—' : pct.toFixed(0) + '%'}</span>${progressSourceBadge(g)}`}
                </div>
            </div>
            ${g.type === 'open' ? '' : `<div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill ${pct >= 100 ? 'complete' : ''}" style="width:${g.progress_source === 'insufficient' ? 0 : pct}%"></div>
                </div>
            </div>`}
            <div class="goal-meta">
                ${g.type === 'open' ? `<div class="meta-item">
                    <div class="meta-value">${t.openGoal}</div>
                </div>` : `<div class="meta-item">
                    <div class="meta-label">${t.deadline}</div>
                    <div class="meta-value">${fmtDate(g.deadline)}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">${t.prediction}</div>
                    <div class="meta-value ${g.on_track === true ? 'on-track' : g.on_track === false ? 'off-track' : ''}">${fmtPred(g)}</div>
                </div>`}
            </div>`;

        if (g.children && g.children.length > 0) {
            html += `<table class="sub-table">
                <thead><tr>
                    <th>${t.subObjective}</th><th>${t.id}</th><th>${t.priority}</th><th>${t.mode}</th>
                    <th>${t.progression}</th><th>${t.predictedEnd}</th>
                </tr></thead>
                <tbody>
                ${g.children.map(c => renderNodeRows(c, 0)).join('')}
                </tbody>
            </table>`;
        } else if (!g.has_children) {
            html += `<div class="goal-meta" style="border-top:none;padding-top:0">
                <div class="meta-item">
                    <div class="meta-label">${t.mode}</div>
                    <div class="meta-value">${modeBadge(g.tracking_mode, g.unit_label)}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">${t.value}</div>
                    <div class="meta-value mono">${fmtVal(g.current_value, g.unit_label)}${g.target ? ' / ' + fmtVal(g.target, g.unit_label) : ''}</div>
                </div>
            </div>`;
        }

        html += `</div>`;
    }

    document.getElementById('view-overview').innerHTML = html;
}

// ── Gantt ────────────────────────────────────────────────────────────────

function renderGantt() {
    const filteredGoalIds = new Set(getGoals().map(g => g.id));
    let tasks = ganttData.tasks.filter(tsk => tsk.status !== 'cancelled');

    if (activeFilters.priority.size > 0 || activeFilters.tag.size > 0) {
        const allTasks = tasks;
        function rootId(task) {
            if (!task.parent) return task.id;
            const p = allTasks.find(tsk => tsk.id === task.parent);
            return p ? rootId(p) : task.id;
        }
        tasks = tasks.filter(tsk => filteredGoalIds.has(rootId(tsk)));
    }
    if (!tasks.length) {
        document.getElementById('view-gantt').innerHTML = `<div class="loading">${t.noData}</div>`;
        return;
    }

    if (currentSort !== 'file') {
        const goalOrder = sortGoals(goalsData.goals, currentSort).map(g => g.id);
        const goalIndex = {};
        goalOrder.forEach((id, i) => goalIndex[id] = i);
        function rootId2(task) {
            if (!task.parent) return task.id;
            const p = tasks.find(tsk => tsk.id === task.parent);
            return p ? rootId2(p) : task.id;
        }
        const taskRoots = {};
        tasks.forEach(tsk => taskRoots[tsk.id] = rootId2(tsk));
        tasks = [...tasks].sort((a, b) => {
            const ra = goalIndex[taskRoots[a.id]] ?? 999;
            const rb = goalIndex[taskRoots[b.id]] ?? 999;
            return ra - rb;
        });
    }

    const allDates = tasks.flatMap(tsk => [new Date(tsk.start), new Date(tsk.end)]);
    const todayDate = new Date(ganttData.as_of + 'T00:00:00');
    allDates.push(todayDate);

    let mn = new Date(Math.min(...allDates));
    let mx = new Date(Math.max(...allDates));
    mn.setDate(mn.getDate() - 14);
    mx.setDate(mx.getDate() + 14);
    mn = new Date(mn.getFullYear(), mn.getMonth(), 1);
    mx = new Date(mx.getFullYear(), mx.getMonth() + 1, 0);
    const td = (mx - mn) / 864e5;

    function pct(d) { return ((new Date(d + 'T00:00:00') - mn) / 864e5) / td * 100; }
    function bw(s, e) { return Math.max(0.5, ((new Date(e + 'T00:00:00') - new Date(s + 'T00:00:00')) / 864e5) / td * 100); }

    const months = [];
    let c = new Date(mn);
    while (c <= mx) {
        months.push(`${t.months[c.getMonth()]} ${c.getFullYear()}`);
        c.setMonth(c.getMonth() + 1);
    }

    const colors = [
        { bg: 'var(--accent-blue)' }, { bg: 'var(--accent-green)' },
        { bg: 'var(--accent-purple)' }, { bg: 'var(--accent-amber)' },
    ];
    let ci = 0;
    const cMap = {};
    const tp = pct(ganttData.as_of);

    const parentMap = {};
    for (const tsk of tasks) {
        if (tsk.type === 'goal') {
            parentMap[tsk.id] = tsk.id;
            cMap[tsk.id] = colors[ci++ % colors.length];
        }
    }
    for (const tsk of tasks) {
        if (tsk.parent && !parentMap[tsk.id]) {
            parentMap[tsk.id] = parentMap[tsk.parent] || tsk.parent;
        }
    }

    let rows = '';
    let lastGoal = '';
    for (const tsk of tasks) {
        const isGoal = tsk.type === 'goal';
        if (isGoal && lastGoal && lastGoal !== tsk.id) {
            rows += '<div class="gantt-divider"></div>';
        }
        if (isGoal) lastGoal = tsk.id;

        const goalId = parentMap[tsk.id] || tsk.id;
        const col = cMap[goalId] || colors[0];
        const depth = isGoal ? 0 : (parentMap[tsk.parent] === tsk.parent ? 1 : 2);
        const labelClass = isGoal ? 'goal-label' : 'sub-label';
        const l = pct(tsk.start);
        const w = bw(tsk.start, tsk.end);

        rows += `<div class="gantt-row">
            <div class="gantt-label ${labelClass}" style="padding-left:${depth * 1}rem" title="${tsk.name}">${tsk.name}</div>
            <div class="gantt-track">
                <div class="gantt-bar" style="left:${l}%;width:${w}%"
                     data-name="${tsk.name}" data-progress="${tsk.progress.toFixed(0)}"
                     data-start="${tsk.start}" data-end="${tsk.end}" data-priority="${tsk.priority}"
                     onmouseenter="showTT(event,this)" onmouseleave="hideTT()">
                    <div class="gantt-bar-bg" style="background:${col.bg}"></div>
                    <div class="gantt-bar-fill" style="width:${tsk.progress}%;background:${col.bg}"></div>
                </div>
            </div>
        </div>`;
    }

    document.getElementById('view-gantt').innerHTML = `
        <div class="gantt-container"><div class="gantt-chart">
            <div class="gantt-header">${months.map(m => `<div class="gantt-month">${m}</div>`).join('')}</div>
            <div style="position:relative">
                ${rows}
                <div class="gantt-today" id="gtl"></div>
            </div>
        </div></div>
        <div class="gantt-legend">
            <span class="gantt-legend-line"></span> ${t.today}
        </div>`;

    requestAnimationFrame(() => {
        const tr = document.querySelector('.gantt-track');
        const li = document.getElementById('gtl');
        if (tr && li) {
            li.style.left = (220 + (tp / 100) * tr.getBoundingClientRect().width) + 'px';
        }
    });
}

// ── Tooltip ─────────────────────────────────────────────────────────────

const tt = document.getElementById('tooltip');
function showTT(e, el) {
    tt.innerHTML = `<strong>${el.dataset.name}</strong><br>
        ${t.ttProgress}: ${el.dataset.progress}%<br>
        ${t.ttPriority}: ${el.dataset.priority}<br>
        ${fmtDate(el.dataset.start)} → ${fmtDate(el.dataset.end)}`;
    tt.classList.add('visible');
    mvTT(e);
}
function mvTT(e) {
    tt.style.left = (e.clientX + 12) + 'px';
    tt.style.top = (e.clientY - 10) + 'px';
}
document.addEventListener('mousemove', e => {
    if (tt.classList.contains('visible')) mvTT(e);
});
function hideTT() { tt.classList.remove('visible'); }

function highlightDep(el) {
    const depId = el.dataset.dep;
    document.querySelectorAll(`tr[data-node-id="${depId}"]`).forEach(row => {
        row.classList.add('dep-highlight');
    });
}
function unhighlightDep(el) {
    document.querySelectorAll('tr.dep-highlight').forEach(row => {
        row.classList.remove('dep-highlight');
    });
}

function showSmartTT(e, el) {
    const parts = el.dataset.smart.split('|||');
    let rows = '';
    for (const part of parts) {
        const sep = part.indexOf(': ');
        if (sep === -1) continue;
        const label = part.substring(0, sep);
        const value = part.substring(sep + 2);
        rows += `<tr><td class="smart-tt-label">${label}</td><td class="smart-tt-value">${value}</td></tr>`;
    }
    tt.innerHTML = `<table class="smart-tt-table">${rows}</table>`;
    tt.classList.add('visible');
    mvTT(e);
}
function hideSmartTT() { tt.classList.remove('visible'); }

// ── Predictions (recursive) ─────────────────────────────────────────────

function renderPredictionItems(node, depth) {
    const isCancelled = node.status === 'cancelled';
    const titleText = isCancelled
        ? `<span class="cancelled-text">${node.title}</span>`
        : node.title;

    const dt = timelineDate(node);

    let note = '';
    if (node.predicted_remaining != null && !['done', 'cancelled'].includes(node.status)) {
        note = t.remaining(node.predicted_remaining, node.unit_label);
    }
    if (node.velocity_per_day && !['done', 'cancelled'].includes(node.status)) {
        const vl = node.tracking_mode === 'performance'
            ? t.perDayGain(node.velocity_per_day, node.unit_label)
            : t.perDay(node.velocity_per_day, node.unit_label);
        note += note ? ` · ${vl}` : vl;
    }

    const modeLabel = node.has_children ? '' : ` ${modeBadge(node.tracking_mode, node.unit_label)}`;
    const indent = depth * 0.8;
    const isOpen = node.type === 'open';
    const icon = isOpen ? '<span class="checkbox checkbox-empty">—</span>' : checkboxIcon(node.status);

    let html = `<div class="prediction-item-icon" style="margin-left:${indent}rem">
        <span class="pred-icon">${icon}</span>
        <div class="pred-content">
            <div class="pred-title">${titleText}${modeLabel}</div>
            <div class="pred-date">${dt}</div>
            ${note ? `<div class="pred-note">${note}</div>` : ''}
        </div>
    </div>`;

    for (const child of (node.children || [])) {
        html += renderPredictionItems(child, depth + 1);
    }
    return html;
}

function renderPredictions() {
    const goals = getGoals();
    let html = '<div class="predictions-grid">';

    for (const g of goals) {
        if (g.type === 'open') {
            html += `<div class="prediction-card">
                <h3>${g.title}</h3>
                <div class="card-badges">
                    ${priorityBadge(g.priority)}
                    ${smartBadge(g)}
                </div>
                <div class="prediction-timeline">`;

            if (g.children && g.children.length > 0) {
                for (const c of g.children) {
                    html += renderPredictionItems(c, 0);
                }
            }

            html += `</div>
                <div class="prediction-summary">${t.openGoal}</div>
            </div>`;
            continue;
        }

        html += `<div class="prediction-card">
            <h3>${g.title}</h3>
            <div class="card-badges">
                ${priorityBadge(g.priority)}
                ${smartBadge(g)}
            </div>
            <div class="prediction-timeline">`;

        if (g.children && g.children.length > 0) {
            for (const c of g.children) {
                html += renderPredictionItems(c, 0);
            }
        } else {
            html += renderPredictionItems(g, 0);
        }

        let sm = '';
        const partialNote = g.prediction_partial ? ` <span class="partial-badge">${t.badgePartial}</span>` : '';
        if (g.predicted_end && g.deadline) {
            const p = new Date(g.predicted_end);
            const d = new Date(g.deadline);
            const df = Math.round((p - d) / 864e5);
            sm = g.on_track
                ? t.onTrackSummaryFull(fmtDate(g.predicted_end), partialNote, Math.abs(df))
                : t.offTrackSummaryFull(fmtDate(g.predicted_end), partialNote, df);
        } else if (g.predicted_end) {
            sm = t.predictionSummary(fmtDate(g.predicted_end), partialNote);
        } else {
            sm = t.notEnoughData;
        }

        html += `</div>
            <div class="prediction-summary">${sm}</div>
        </div>`;
    }

    html += '</div>';
    document.getElementById('view-predictions').innerHTML = html;
}

// ── Init ────────────────────────────────────────────────────────────────

document.getElementById('sort-select').addEventListener('change', function() {
    currentSort = this.value;
    renderOverview();
    renderGantt();
    renderPredictions();
});

applyStaticI18n();
fetchData();
