/* AI Chat page: the RAG backend is not connected yet.
   The form is disabled in chat.html; this handler keeps the page honest if it is enabled early. */

(function () {
    "use strict";

    const { escapeHTML } = window.NS;

    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatMessages = document.getElementById("chat-messages");


    function addMessage(role, message) {
        const wrapper = document.createElement("div");

        wrapper.className = `chat-message ${role}`;
        wrapper.innerHTML = `
            <span class="chat-role">${role === "user" ? "YOU" : "ASSISTANT"}</span>
            <p>${escapeHTML(message)}</p>
        `;

        chatMessages.appendChild(wrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    chatForm.addEventListener("submit", event => {
        event.preventDefault();

        const message = chatInput.value.trim();

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
})();
