const form = document.querySelector("#ask");
const question = document.querySelector("#question");
const askButton = form.querySelector("button");
const message = document.querySelector("#message");
const result = document.querySelector("#result");
const sourceList = document.querySelector("#source-list");
const sources = document.querySelector("#sources");
const cases = document.querySelector("#cases");

const headings = { draft: "Unverified draft", answer: "Handbook answer", fallback: "Next step" };

async function loadCases() {
  try {
    const response = await fetch("/api/questions");
    if (!response.ok) throw new Error();
    for (const item of await response.json()) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = item.question;
      button.addEventListener("click", () => {
        question.value = item.question;
        question.focus();
      });
      const row = document.createElement("li");
      row.append(button);
      cases.append(row);
    }
  } catch {
    cases.textContent = "Sample questions could not load.";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  askButton.disabled = true;
  result.hidden = true;
  message.textContent = "Checking the question.";
  try {
    const response = await fetch("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question.value }),
    });
    const reply = await response.json();
    if (!response.ok) throw new Error(reply.error);

    document.querySelector("#result-title").textContent = headings[reply.status] || "Reply";
    document.querySelector("#answer").textContent = reply.answer || "No draft returned.";
    document.querySelector("#source-label").textContent =
      reply.status === "draft" ? "Reported source IDs" : "Handbook sources";
    sources.replaceChildren();
    for (const source of reply.sources) {
      const row = document.createElement("li");
      row.textContent = source;
      sources.append(row);
    }
    sourceList.hidden = reply.sources.length === 0;
    result.hidden = false;
    message.textContent = "";
  } catch (error) {
    message.textContent = error.name === "TypeError" ? "The local server could not be reached." : error.message;
  } finally {
    askButton.disabled = false;
  }
});

loadCases();
