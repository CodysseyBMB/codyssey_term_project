document.querySelectorAll("[data-local-time]").forEach((element) => {
  const date = new Date(element.dateTime);
  if (Number.isNaN(date.getTime())) {
    return;
  }

  element.textContent = new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
});
