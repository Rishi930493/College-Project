
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("transaction-form");
    const heading = document.getElementById("form-heading");
    const saveButton = document.getElementById("save-button");
    const cancelButton = document.getElementById("cancel-edit");

    const fields = {
        title: document.getElementById("title"),
        amount: document.getElementById("amount"),
        kind: document.getElementById("kind"),
        category: document.getElementById("category"),
        date: document.getElementById("trans_date"),
        note: document.getElementById("note")
    };

    const addUrl = form.action;

    document.querySelectorAll(".edit-btn").forEach(button => {
        button.addEventListener("click", () => {
            fields.title.value = button.dataset.title;
            fields.amount.value = button.dataset.amount;
            fields.kind.value = button.dataset.kind;
            fields.date.value = button.dataset.date;
            fields.note.value = button.dataset.note || "";

            const category = button.dataset.category;
            const existingOption = [...fields.category.options]
                .find(option => option.value === category);

            if (!existingOption) {
                const option = new Option(category, category);
                fields.category.add(option);
            }

            fields.category.value = category;
            form.action = `/edit/${button.dataset.id}`;

            heading.textContent = "Edit Transaction";
            saveButton.textContent = "Save Changes";
            cancelButton.classList.remove("hidden");

            form.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

            fields.title.focus();
        });
    });

    cancelButton.addEventListener("click", resetForm);

    function resetForm() {
        form.reset();
        form.action = addUrl;
        heading.textContent = "Add Transaction";
        saveButton.textContent = "+ Add Transaction";
        cancelButton.classList.add("hidden");
    }

    form.addEventListener("submit", event => {
        const amount = Number(fields.amount.value);

        if (!Number.isFinite(amount) || amount <= 0) {
            event.preventDefault();
            alert("Please enter an amount greater than zero.");
            fields.amount.focus();
            return;
        }

        if (!fields.title.value.trim() || !fields.category.value) {
            event.preventDefault();
            alert("Please complete all required fields.");
        }
    });

    document.querySelectorAll(".delete-form").forEach(deleteForm => {
        deleteForm.addEventListener("submit", event => {
            const confirmed = confirm(
                "Are you sure you want to delete this transaction?"
            );

            if (!confirmed) {
                event.preventDefault();
            }
        });
    });
});
