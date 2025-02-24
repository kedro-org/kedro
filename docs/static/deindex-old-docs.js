// Ensure the correct API version is set
if (document.querySelector("meta[name='readthedocs-addons-api-version']") === null) {
    const meta = document.createElement("meta");
    meta.name = "readthedocs-addons-api-version";
    meta.content = "1";
    document.head.appendChild(meta);
}

// Function to handle RTD data and inject meta tags based on conditions
function _handleReadTheDocsData(data) {
    const projectSlug = data.projects.current.slug;
    const versionSlug = data.versions.current.slug;

    console.log("Project slug:", projectSlug, "| Version:", versionSlug);

    // Ensure the version is updated after each release of kedro-datasets
    if (
        (projectSlug === "kedro-datasets" && versionSlug !== "kedro-datasets-6.0.0") ||
        (projectSlug !== "kedro-datasets" && versionSlug !== "stable")
    ) {
        console.log("Non-indexable version detected, injecting meta tag");
        const meta = document.createElement("meta");
        meta.name = "robots";
        meta.content = "noindex, nofollow";
        document.head.appendChild(meta);
    } else {
        console.log("Indexable version detected, no meta tag added.");
    }
}

// Check if the event has already been fired before this script runs
if (window.ReadTheDocsEventData !== undefined) {
    _handleReadTheDocsData(window.ReadTheDocsEventData.data());
}

// Subscribe to future dispatches of the event (e.g., SPA navigation)
document.addEventListener("readthedocs-addons-data-ready", function (event) {
    _handleReadTheDocsData(event.detail.data());
});
