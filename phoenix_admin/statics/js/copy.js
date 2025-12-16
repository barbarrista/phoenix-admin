document.getElementById("copy-btn").addEventListener("click", function() {
  const text = document.getElementById("json-content").textContent;
  navigator.clipboard.writeText(text)
});