document.addEventListener("DOMContentLoaded", function () {
    // Ensure noindex, nofollow is always present (RTD is inconsistent across projects)
    let robotsMeta = document.querySelector('meta[name="robots"]');

    if (!robotsMeta) {
        robotsMeta = document.createElement("meta");
        robotsMeta.name = "robots";
        document.head.appendChild(robotsMeta);
    }

    robotsMeta.content = "noindex, nofollow";

    // Trigger Read the Docs' search addon instead of Material MkDocs default
    const searchInput = document.querySelector(".md-search__input");
    if (searchInput) {
        searchInput.addEventListener("focus", () => {
            const event = new CustomEvent("readthedocs-search-show");
            document.dispatchEvent(event);
        });
    }
});
