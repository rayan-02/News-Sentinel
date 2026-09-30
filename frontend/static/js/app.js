document.addEventListener("DOMContentLoaded", () => {
    document.body.classList.add("ready");

    const currentPage = document.body.dataset.page;

    document.querySelectorAll(".nav-link").forEach(link => {
        const href = link.getAttribute("href");

        if (href === `/${currentPage}` || (currentPage === "overview" && href === "/")) {
            link.classList.add("active");
        }
    });

    document.querySelectorAll("a[href^='http']").forEach(link => {
        link.target = "_blank";
        link.rel = "noopener noreferrer";
    });
});