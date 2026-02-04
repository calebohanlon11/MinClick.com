function getUrlParam(name, fallback) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name) || fallback;
}

function hashParams(templateId, params) {
  return templateId + "|" + JSON.stringify(params || {});
}

function normalizeAnswer(value) {
  if (typeof value === "string") {
    return value.trim();
  }
  if (typeof value === "number") {
    return Number(value);
  }
  return value;
}

function renderChoices(question, container, onSelect) {
  container.innerHTML = "";
  question.choices.forEach(choiceValue => {
    const btn = document.createElement("button");
    btn.className = "btn btn-outline-secondary choice-btn";
    btn.textContent = typeof choiceValue === "number" ? choiceValue : String(choiceValue);
    btn.addEventListener("click", () => onSelect(choiceValue));
    container.appendChild(btn);
  });
}

function showFeedback(target, correct, question, userAnswer) {
  target.classList.remove("d-none");
  target.classList.toggle("feedback-correct", correct);
  target.classList.toggle("feedback-wrong", !correct);
  const answerText = question.format === "numeric" ? question.answer : String(question.answer);
  target.innerHTML = `
    <div><strong>${correct ? "Correct" : "Incorrect"}</strong></div>
    <div class="small">Your answer: ${userAnswer}</div>
    <div class="small">Correct answer: ${answerText}</div>
    <div class="mt-2">${question.explanationHtml}</div>
  `;
}

function startQuiz() {
  const root = document.querySelector(".poker-math[data-mode]");
  if (!root) return;

  const mode = root.dataset.mode;
  const moduleId = root.dataset.moduleId;
  const n = parseInt(getUrlParam("n", "10"), 10);
  const difficulty = getUrlParam("difficulty", "easy");
  const seed = parseInt(getUrlParam("seed", String(Date.now() % 100000)), 10);
  const rng = mulberry32(seed);

  const templates = mode === "mixed" ? getAllTemplates() : getTemplatesForModule(moduleId);
  const questions = [];
  const seen = new Set();
  let safety = 0;

  while (questions.length < n && safety < 2000) {
    safety += 1;
    const template = choice(rng, templates);
    let tries = 0;
    let question = null;
    while (tries < 50) {
      tries += 1;
      const q = template.generate(rng);
      q.params = q.params || {};
      const hash = hashParams(template.id, q.params);
      if (!seen.has(hash)) {
        seen.add(hash);
        question = q;
        break;
      }
    }
    if (question) {
      questions.push(question);
    }
  }

  const promptEl = document.getElementById("quizPrompt");
  const choicesEl = document.getElementById("quizChoices");
  const numericWrap = document.getElementById("quizNumeric");
  const numericInput = document.getElementById("quizNumericInput");
  const numericSubmit = document.getElementById("quizNumericSubmit");
  const feedbackEl = document.getElementById("quizFeedback");
  const nextBtn = document.getElementById("quizNext");
  const progressEl = document.getElementById("quizProgress");

  let index = 0;
  const answers = [];

  function renderQuestion() {
    const q = questions[index];
    progressEl.textContent = `${index + 1}/${questions.length}`;
    promptEl.innerHTML = q.promptHtml;
    feedbackEl.classList.add("d-none");
    feedbackEl.innerHTML = "";
    nextBtn.classList.add("d-none");
    choicesEl.innerHTML = "";
    numericInput.value = "";
    if (q.format === "multiple") {
      numericWrap.classList.add("d-none");
      renderChoices(q, choicesEl, handleAnswer);
    } else {
      numericWrap.classList.remove("d-none");
    }
  }

  function isCorrect(q, userValue) {
    if (q.format === "multiple") {
      return normalizeAnswer(userValue) === normalizeAnswer(q.answer);
    }
    const numericValue = parseFloat(userValue);
    if (Number.isNaN(numericValue)) return false;
    const tol = q.tolerance !== undefined ? q.tolerance : 0.05;
    return Math.abs(numericValue - q.answer) <= tol;
  }

  function handleAnswer(value) {
    const q = questions[index];
    const correct = isCorrect(q, value);
    answers.push({
      questionId: q.id,
      moduleId: q.moduleId,
      promptHtml: q.promptHtml,
      answer: q.answer,
      userAnswer: value,
      correct,
      explanationHtml: q.explanationHtml
    });
    showFeedback(feedbackEl, correct, q, value);
    nextBtn.classList.remove("d-none");
  }

  numericSubmit.addEventListener("click", () => handleAnswer(numericInput.value));
  numericInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      handleAnswer(numericInput.value);
    }
  });

  nextBtn.addEventListener("click", () => {
    index += 1;
    if (index >= questions.length) {
      finishQuiz();
    } else {
      renderQuestion();
    }
  });

  function finishQuiz() {
    const correctCount = answers.filter(a => a.correct).length;
    const attempt = {
      id: `attempt_${Date.now()}`,
      timestamp: Date.now(),
      mode,
      moduleId: moduleId || "mixed",
      total: answers.length,
      correct: correctCount,
      answers
    };
    const existing = JSON.parse(localStorage.getItem("pokerMathAttempts") || "[]");
    existing.push(attempt);
    localStorage.setItem("pokerMathAttempts", JSON.stringify(existing));
    window.location.href = `/poker-math/results?attempt=${attempt.id}`;
  }

  renderQuestion();
}

function renderResults() {
  const summaryEl = document.getElementById("resultsSummary");
  const breakdownEl = document.getElementById("resultsBreakdown");
  const missedEl = document.getElementById("resultsMissed");
  if (!summaryEl || !breakdownEl || !missedEl) return;

  const attemptId = getUrlParam("attempt", "");
  const attempts = JSON.parse(localStorage.getItem("pokerMathAttempts") || "[]");
  const attempt = attempts.find(a => a.id === attemptId);
  if (!attempt) {
    summaryEl.innerHTML = "<p class='text-muted'>Attempt not found.</p>";
    return;
  }

  summaryEl.innerHTML = `
    <div class="results-card">
      <h4 class="mb-1">${attempt.correct}/${attempt.total} correct</h4>
      <div class="text-muted">Mode: ${attempt.mode === "mixed" ? "Mixed" : attempt.moduleId}</div>
    </div>
  `;

  const moduleStats = {};
  attempt.answers.forEach(a => {
    if (!moduleStats[a.moduleId]) {
      moduleStats[a.moduleId] = { correct: 0, total: 0 };
    }
    moduleStats[a.moduleId].total += 1;
    if (a.correct) moduleStats[a.moduleId].correct += 1;
  });

  breakdownEl.innerHTML = "";
  Object.keys(moduleStats).forEach(moduleId => {
    const module = POKER_MATH_MODULES.find(m => m.id === moduleId);
    const stats = moduleStats[moduleId];
    const accuracy = stats.total ? roundPct((stats.correct / stats.total) * 100) : 0;
    const recommend = accuracy < 70 ? "Review" : "On track";
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${module ? module.title : moduleId}</td>
      <td>${stats.correct}</td>
      <td>${stats.total}</td>
      <td>${accuracy}%</td>
      <td>${recommend}</td>
    `;
    breakdownEl.appendChild(row);
  });

  const missed = attempt.answers.filter(a => !a.correct);
  if (missed.length === 0) {
    missedEl.innerHTML = "<p class='text-muted'>No missed questions. Nice work.</p>";
    return;
  }
  missedEl.innerHTML = "";
  missed.forEach(item => {
    const card = document.createElement("div");
    card.className = "results-card";
    card.innerHTML = `
      <div>${item.promptHtml}</div>
      <div class="small text-muted">Your answer: ${item.userAnswer}</div>
      <div class="small text-muted">Correct: ${item.answer}</div>
      <div class="mt-2">${item.explanationHtml}</div>
    `;
    missedEl.appendChild(card);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  startQuiz();
  renderResults();
});
