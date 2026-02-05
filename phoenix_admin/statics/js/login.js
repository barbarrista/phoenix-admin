document
  .getElementById("togglePassword")
  .addEventListener("click", function () {
    const passwordInput = document.getElementById("password");
    const icon = this.querySelector("i");

    if (passwordInput.type === "password") {
      passwordInput.type = "text";
      icon.classList.remove("ti-eye");
      icon.classList.add("ti-eye-off");
    } else {
      passwordInput.type = "password";
      icon.classList.remove("ti-eye-off");
      icon.classList.add("ti-eye");
    }
  });
