(() => {
  const RESET_DELAY_MS = 1800;

  const fallbackCopy = (text) => {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.setAttribute("readonly", "");
    textArea.style.position = "fixed";
    textArea.style.opacity = "0";
    document.body.appendChild(textArea);
    textArea.select();

    try {
      if (!document.execCommand("copy")) {
        throw new Error("The browser rejected the copy command.");
      }
    } finally {
      textArea.remove();
    }
  };

  const copyText = async (text) => {
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text);
        return;
      } catch (error) {
        console.warn("Clipboard API unavailable; using copy fallback.", error);
      }
    }

    fallbackCopy(text);
  };

  const showResult = (button, succeeded) => {
    const label = button.querySelector(".bibtex-copy-label");
    const previousTimer = Number(button.dataset.resetTimer);

    if (previousTimer) {
      window.clearTimeout(previousTimer);
    }

    button.classList.toggle("is-copied", succeeded);
    button.classList.toggle("is-copy-error", !succeeded);
    label.textContent = succeeded ? "Copied!" : "Copy failed";

    const timer = window.setTimeout(() => {
      button.classList.remove("is-copied", "is-copy-error");
      label.textContent = "BibTeX";
      delete button.dataset.resetTimer;
    }, RESET_DELAY_MS);

    button.dataset.resetTimer = String(timer);
  };

  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-bibtex-copy]");
    if (!button) return;

    const source = document.getElementById(button.dataset.bibtexTarget);
    if (!source) {
      showResult(button, false);
      return;
    }

    button.disabled = true;
    try {
      await copyText(source.textContent.trim());
      showResult(button, true);
    } catch (error) {
      console.error("Unable to copy BibTeX citation:", error);
      showResult(button, false);
    } finally {
      button.disabled = false;
    }
  });
})();
