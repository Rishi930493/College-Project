
document.addEventListener("DOMContentLoaded", () => {
    // =====================================
    // 1. TAB NAVIGATION
    // =====================================
    const tabs = document.querySelectorAll(".tab");
    const panels = document.querySelectorAll(".panel");

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((item) => item.classList.remove("active"));

            panels.forEach((panel) => {
                panel.hidden = true;
            });

            tab.classList.add("active");

            const target = document.getElementById(tab.dataset.target);

            if (target) {
                target.hidden = false;
            }
        });
    });

    // =====================================
    // 2. EDIT BOOK
    // =====================================
    const editArea = document.getElementById("edit-area");
    const editForm = document.getElementById("edit-form");

    document.querySelectorAll(".edit-book").forEach((button) => {
        button.addEventListener("click", () => {
            document.getElementById("edit-title").value =
                button.dataset.title || "";

            document.getElementById("edit-author").value =
                button.dataset.author || "";

            document.getElementById("edit-category").value =
                button.dataset.category || "";

            document.getElementById("edit-quantity").value =
                button.dataset.quantity || "0";

            editForm.action = `/books/update/${button.dataset.id}`;

            editArea.hidden = false;

            editArea.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });
        });
    });

    // Cancel editing
    const cancelEdit = document.getElementById("cancel-edit");

    if (cancelEdit) {
        cancelEdit.addEventListener("click", () => {
            editArea.hidden = true;
            editForm.reset();
        });
    }

    // =====================================
    // 3. BOOK SEARCH
    // =====================================
    const searchInput = document.getElementById("book-search");
    const searchButton = document.getElementById("search-button");
    const resetButton = document.getElementById("reset-search");
    const tableBody = document.getElementById("books-table");

    // Save original server-rendered rows
    const originalRows = tableBody.innerHTML;

    function addCell(row, value) {
        const cell = document.createElement("td");
        cell.textContent = value ?? "";
        row.appendChild(cell);
    }

    async function searchBooks() {
        const query = searchInput.value.trim();

        if (!query) {
            tableBody.innerHTML = originalRows;
            return;
        }

        searchButton.disabled = true;
        searchButton.textContent = "Searching...";

        try {
            const response = await fetch(
                `/books/search?q=${encodeURIComponent(query)}`
            );

            if (!response.ok) {
                throw new Error("Search request failed");
            }

            const books = await response.json();

            tableBody.replaceChildren();

            if (books.length === 0) {
                const row = document.createElement("tr");
                const cell = document.createElement("td");

                cell.colSpan = 6;
                cell.textContent = "No books found.";

                row.appendChild(cell);
                tableBody.appendChild(row);
                return;
            }

            books.forEach((book) => {
                const row = document.createElement("tr");

                addCell(row, book.id);
                addCell(row, book.title);
                addCell(row, book.author);
                addCell(row, book.category);
                addCell(row, book.quantity);

                const actions = document.createElement("td");
                actions.textContent =
                    "Click Show All to edit or delete.";

                row.appendChild(actions);
                tableBody.appendChild(row);
            });

        } catch (error) {
            console.error(error);
            alert("Unable to search books. Please try again.");
        } finally {
            searchButton.disabled = false;
            searchButton.textContent = "Search";
        }
    }

    searchButton.addEventListener("click", searchBooks);

    searchInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            searchBooks();
        }
    });

    resetButton.addEventListener("click", () => {
        searchInput.value = "";
        tableBody.innerHTML = originalRows;
    });

    // =====================================
    // 4. DELETE CONFIRMATION
    // =====================================
    document.querySelectorAll("form").forEach((form) => {
        if (
            form.action.includes("/books/delete/") ||
            form.action.includes("/students/delete/")
        ) {
            form.addEventListener("submit", (event) => {
                const confirmed = confirm(
                    "Are you sure you want to delete this record?"
                );

                if (!confirmed) {
                    event.preventDefault();
                }
            });
        }
    });

    // =====================================
    // 5. FORM VALIDATION
    // =====================================
    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!form.checkValidity()) {
                event.preventDefault();
                form.reportValidity();
            }
        });
    });

    // =====================================
    // 6. SUCCESSFUL PAGE INITIALIZATION
    // =====================================
    console.log("Library Management System loaded successfully.");
});
