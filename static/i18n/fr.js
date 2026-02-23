/**
 * French locale for SMART Goals Tracker.
 */

/* exported LOCALE_FR */
const LOCALE_FR = {
    // General
    headerMeta: (n, d) => `${n} objectifs · ${d}`,
    loadError: "Erreur de chargement.",
    noData: "Aucune donnée.",
    loading: "Chargement...",

    // Parsing errors
    parsingErrors: "Erreurs d'analyse",
    parsingErrorsDesc: "Les problèmes suivants ont été détectés lors de l'analyse du fichier. Veuillez les corriger pour assurer un fonctionnement correct.",
    errorLine: "Ligne",
    errorContext: "Contexte",
    errorLevelError: "Erreur",
    errorLevelWarning: "Avertissement",
    errorsCount: (n) => `${n} problème${n > 1 ? 's' : ''} trouvé${n > 1 ? 's' : ''}`,
    showErrors: "Afficher les détails",
    hideErrors: "Masquer les détails",

    // Statuses
    status_done: "Terminé",
    status_in_progress: "En cours",
    status_not_started: "Non démarré",
    status_paused: "En pause",
    status_cancelled: "Annulé",

    // Priorities
    priority_optional: "Facultative",
    priority_low: "Faible",
    priority_medium: "Moyenne",
    priority_high: "Haute",
    priority_capital: "Capitale",

    // Tracking modes
    modeFixed: "Date fixe",
    modePerformance: "Performance",
    modeCumulative: "Cumulatif",
    modeOpen: "Ouvert",

    // Progress source badges
    badgePartial: "partiel",
    badgePrediction: "prédiction",
    badgeInsufficient: "données insuffisantes",

    // Overview
    activeGoals: "Objectifs actifs",
    deadlineTracking: "Suivi des dates limites",
    onTrackSummary: "en bonne voie",
    onTrackHeader: "✓ En bonne voie",
    offTrackHeader: "⚠ En retard",
    openGoal: "Objectif ouvert",
    deadline: "Date limite",
    prediction: "Prédiction",
    subObjective: "Sous-objectif",
    id: "ID",
    priority: "Priorité",
    mode: "Mode",
    progression: "Progression",
    predictedEnd: "Fin prédite",
    value: "Valeur",

    // Filter bar
    filterPriority: "Priorité",
    filterCategory: "Catégorie",

    // Sort options
    sortFile: "Ordre du fichier",
    sortName: "Par nom",
    sortPriority: "Par priorité et nom",
    sortLabel: "Tri :",

    // Tabs
    tabOverview: "Vue d'ensemble",
    tabGantt: "Gantt",
    tabPredictions: "Prédictions",

    // Timeline / predictions
    cancelled: "Annulé",
    doneOn: (d) => `Terminé le ${d}`,
    fixedEnd: (d) => `Fin: ${d}`,
    predicted: (d) => `Prédit: ${d}`,
    waiting: "En attente",
    insufficientData: "Données insuffisantes",
    remaining: (v, u) => `~${v} ${u} restant`,
    perDay: (v, u) => `${v} ${u}/jour`,
    perDayGain: (v, u) => `+${v} ${u}/jour`,

    // Prediction summary
    onTrackSummaryFull: (d, partial, days) =>
        `<span class="on-track">✓ En bonne voie</span> — prédiction : <strong>${d}</strong>${partial}, ${days}j avant la date limite.`,
    offTrackSummaryFull: (d, partial, days) =>
        `<span class="off-track">⚠ En retard</span> — prédiction : <strong>${d}</strong>${partial}, ${days}j après la date limite.`,
    predictionSummary: (d, partial) =>
        `Prédiction: <strong>${d}</strong>${partial}`,
    notEnoughData: "Pas assez de données.",

    // Gantt
    today: "Aujourd'hui",
    ttProgress: "Progression",
    ttPriority: "Priorité",

    // Month abbreviations
    months: [
        "Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
        "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc",
    ],
};
