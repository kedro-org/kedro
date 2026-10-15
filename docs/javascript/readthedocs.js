document.addEventListener("DOMContentLoaded", function(event) {
    // Trigger Read the Docs' search addon instead of Zensical's default search
    const searchButton = document.querySelector(".md-search__button");
    if (!searchButton) {
        return;
    }
    searchButton.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopImmediatePropagation();
            const event = new CustomEvent("readthedocs-search-show");
            document.dispatchEvent(event);
        }, true);
    });
