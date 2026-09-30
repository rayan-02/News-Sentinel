const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatMessages = document.getElementById("chat-messages");

function addMessage(role, message) {
    const wrapper = document.createElement("div");

    wrapper.className =
        `chat-message ${role}`;

    const label =
        role === "user"
            ? "YOU"
            : "ASSISTANT";

    wrapper.innerHTML = `
        <span class="chat-role">${label}</span>
        <p>${escapeHTML(message)}</p>
    `;

    chatMessages.appendChild(wrapper);

    chatMessages.scrollTop =
        chatMessages.scrollHeight;
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    }[character]));
}

chatForm.addEventListener("submit", event => {
    event.preventDefault();

    const message =
        chatInput.value.trim();

    if (!message) {
        return;
    }

    addMessage("user", message);

    chatInput.value = "";

    addMessage(
        "assistant",
        "The RAG chatbot is not connected yet. The retrieval and question-answering backend will be added in the next stage."
    );
});