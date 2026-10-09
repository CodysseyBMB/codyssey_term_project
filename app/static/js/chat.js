// 이 스크립트는 /chat 페이지에서만 로드된다 (chat.html 맨 아래 <script> 참고).
// 서버가 그려준 화면(Jinja2) 위에서, 질문 전송만 fetch()로 처리해
// 페이지를 새로고침하지 않고 같은 화면에 응답을 보여준다 (plan.md S4).

const form = document.getElementById("chat-form");
const questionInput = document.getElementById("chat-question");
const submitButton = document.getElementById("chat-submit");
const log = document.getElementById("chat-log");
const errorBox = document.getElementById("chat-error");

// 로그인 페이지의 hidden input과 같은 CSRF 토큰. JSON API는 폼이 아니라서
// 서버가 body의 data 속성에 심어둔 값을 읽어 헤더로 보낸다.
const csrfToken = document.body.dataset.csrfToken;

function appendMessage(role, text) {
  const bubble = document.createElement("p");
  bubble.className = role === "user" ? "chat-message chat-message--user" : "chat-message chat-message--assistant";
  // innerHTML이 아니라 textContent를 쓴다: AI 응답이나 사용자 입력에 <script> 같은
  // 태그가 들어있어도 그대로 "글자"로만 표시되고 실행되지 않는다 (XSS 방지).
  bubble.textContent = text;
  log.appendChild(bubble);
  log.scrollTop = log.scrollHeight;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

function setLoading(isLoading) {
  // 처리 중에는 버튼을 비활성화해서 중복 전송을 막는다 (plan.md 입력 검증 기본값).
  submitButton.disabled = isLoading;
  questionInput.disabled = isLoading;
  submitButton.textContent = isLoading ? "전송 중..." : "전송";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();

  const question = questionInput.value.trim();
  if (!question) {
    showError("질문을 입력해 주세요.");
    return;
  }

  appendMessage("user", question);
  questionInput.value = "";
  setLoading(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify({ question }),
    });

    const data = await response.json();

    if (!response.ok) {
      showError(data.error?.message ?? "요청을 처리하지 못했습니다.");
      return;
    }

    appendMessage("assistant", data.answer);
  } catch (networkError) {
    showError("서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.");
  } finally {
    setLoading(false);
    questionInput.focus();
  }
});
