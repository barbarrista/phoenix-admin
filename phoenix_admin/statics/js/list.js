function addListItem(fieldName) {
  const container = document.getElementById("list-container-" + fieldName);
  const lastItem = container.lastElementChild;
  const newItem = lastItem.cloneNode(true);

  const groups = container.querySelectorAll(".input-group");

  if (groups.length > 0) {
    const lastGroup = groups[groups.length - 1];
    const inputs = lastGroup.querySelectorAll("input, select, textarea");
    let notFilled = false;
    inputs.forEach((input) => {
      if (
        (input.type !== "checkbox" && input.type !== "radio" && !input.value) ||
        ((input.type === "checkbox" || input.type === "radio") &&
          !input.checked)
      ) {
        notFilled = true;
      }
    });
    if (notFilled) {
      alert(
        "Please complete the previous item before adding a new one."
      );
      return;
    }
  }

  newItem.querySelectorAll("input, select, textarea").forEach((el) => {
    if (el.type === "checkbox" || el.type === "radio") {
      el.checked = false;
    } else {
      el.value = "";
    }
  });

  container.appendChild(newItem);

  updateRemoveButtons(container);
}

function removeListItem(btn) {
  const container = btn.closest(".list-container");
  btn.parentElement.remove();
  updateRemoveButtons(container);
}

function updateRemoveButtons(container) {
  const groups = container.querySelectorAll(".input-group");
  groups.forEach((group) => {
    const btn = group.querySelector(".btn-outline-danger");
    if (btn) {
      btn.style.display = groups.length > 1 ? "" : "none";
    }
  });
}

window.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".list-container").forEach((container) => {
    updateRemoveButtons(container);
  });
});
