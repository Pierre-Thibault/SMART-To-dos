/**
 * English locale for SMART Goals Tracker.
 *
 * To add a new language, copy this file, rename it to the ISO 639-1 code
 * (e.g. "es.js" for Spanish), translate every value, then register the
 * code in SUPPORTED_LANGS inside app.js.
 */

/* exported LOCALE_EN */
const LOCALE_EN = {
    // General
    headerMeta: (n, d) => `${n} goals · ${d}`,
    loadError: "Loading error.",
    noData: "No data.",
    loading: "Loading...",

    // Parsing errors
    parsingErrors: "Parsing errors",
    parsingErrorsDesc: "The following issues were found while parsing the goals file. Please fix them to ensure correct behavior.",
    errorLine: "Line",
    errorContext: "Context",
    errorLevelError: "Error",
    errorLevelWarning: "Warning",
    errorsCount: (n) => `${n} issue${n > 1 ? 's' : ''} found`,
    showErrors: "Show details",
    hideErrors: "Hide details",

    // Statuses
    status_done: "Done",
    status_in_progress: "In progress",
    status_not_started: "Not started",
    status_paused: "Paused",
    status_cancelled: "Cancelled",

    // Priorities
    priority_optional: "Optional",
    priority_low: "Low",
    priority_medium: "Medium",
    priority_high: "High",
    priority_capital: "Capital",

    // Tracking modes
    modeFixed: "Fixed date",
    modePerformance: "Performance",
    modeCumulative: "Cumulative",
    modeOpen: "Open",

    // Progress source badges
    badgePartial: "partial",
    badgePrediction: "prediction",
    badgeInsufficient: "insufficient data",

    // Overview
    activeGoals: "Active goals",
    deadlineTracking: "Deadline tracking",
    onTrackSummary: "on track",
    onTrackHeader: "✓ On track",
    offTrackHeader: "⚠ Behind schedule",
    openGoal: "Open goal",
    deadline: "Deadline",
    prediction: "Prediction",
    subObjective: "Sub-objective",
    id: "ID",
    priority: "Priority",
    mode: "Mode",
    progression: "Progress",
    predictedEnd: "Predicted end",
    value: "Value",

    // Filter bar
    filterPriority: "Priority",
    filterCategory: "Category",

    // Sort options
    sortFile: "File order",
    sortName: "By name",
    sortPriority: "By priority & name",
    sortLabel: "Sort:",

    // Tabs
    tabOverview: "Overview",
    tabGantt: "Gantt",
    tabPredictions: "Predictions",

    // Timeline / predictions
    cancelled: "Cancelled",
    doneOn: (d) => `Done on ${d}`,
    fixedEnd: (d) => `End: ${d}`,
    predicted: (d) => `Predicted: ${d}`,
    waiting: "Waiting",
    insufficientData: "Insufficient data",
    remaining: (v, u) => `~${v} ${u} remaining`,
    perDay: (v, u) => `${v} ${u}/day`,
    perDayGain: (v, u) => `+${v} ${u}/day`,

    // Prediction summary
    onTrackSummaryFull: (d, partial, days) =>
        `<span class="on-track">✓ On track</span> — prediction: <strong>${d}</strong>${partial}, ${days}d before deadline.`,
    offTrackSummaryFull: (d, partial, days) =>
        `<span class="off-track">⚠ Behind schedule</span> — prediction: <strong>${d}</strong>${partial}, ${days}d past deadline.`,
    predictionSummary: (d, partial) =>
        `Prediction: <strong>${d}</strong>${partial}`,
    notEnoughData: "Not enough data.",

    // Gantt
    today: "Today",
    ttProgress: "Progress",
    ttPriority: "Priority",

    // Month abbreviations
    months: [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ],
};
