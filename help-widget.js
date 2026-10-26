(() => {
  const style = document.createElement("style");

  style.textContent = `
    #d2d-help-button {
      position: fixed;
      right: 20px;
      bottom: 20px;
      z-index: 10000;
      padding: 14px 20px;
      border: 0;
      border-radius: 999px;
      background: #2f7569;
      color: white;
      box-shadow: 0 4px 18px rgba(24, 59, 85, .25);
      cursor: pointer;
      font: 700 16px Arial, sans-serif;
    }

    #d2d-help-dialog {
      width: min(440px, calc(100% - 28px));
      max-height: calc(100dvh - 32px);
      padding: 24px;
      overflow-y: auto;
      border: 1px solid #d5dfe4;
      border-radius: 12px;
      background: white;
      color: #33454f;
      font: 14px Arial, sans-serif;
      box-shadow: 0 12px 40px rgba(24, 59, 85, .2);
    }

    #d2d-help-dialog::backdrop {
      background: rgba(24, 59, 85, .4);
    }

    #d2d-help-dialog * {
      box-sizing: border-box;
    }

    #d2d-help-dialog .help-heading {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }

    #d2d-help-dialog h2 {
      margin: 0;
      color: #183b55;
      font-size: 23px;
    }

    #d2d-help-close {
      border: 0;
      background: transparent;
      color: #183b55;
      cursor: pointer;
      padding: 8px;
      font: 14px Arial, sans-serif;
    }

    #d2d-help-dialog p {
      color: #62717a;
      line-height: 1.5;
    }

    #d2d-help-dialog label {
      display: block;
      margin-top: 14px;
      font-weight: 700;
    }

    #d2d-help-dialog input,
    #d2d-help-dialog textarea {
      display: block;
      width: 100%;
      margin-top: 6px;
      padding: 11px;
      border: 1px solid #bbc9cf;
      border-radius: 6px;
      background: white;
      color: #33454f;
      font: 15px Arial, sans-serif;
    }

    #d2d-help-dialog textarea {
      min-height: 120px;
      resize: vertical;
    }

    #d2d-help-dialog :focus-visible {
      outline: 3px solid #c96a3b;
      outline-offset: 2px;
    }

    #d2d-help-send {
      width: 100%;
      margin-top: 18px;
      padding: 13px;
      border: 0;
      border-radius: 7px;
      background: #2f7569;
      color: white;
      cursor: pointer;
      font: 700 15px Arial, sans-serif;
    }

    #d2d-help-send:disabled {
      opacity: .65;
      cursor: wait;
    }

    #d2d-help-status:not(:empty) {
      margin-top: 14px;
      padding: 12px;
      border-radius: 7px;
      background: #edf7f3;
      color: #205d53;
      line-height: 1.5;
    }

    #d2d-help-status[data-error="true"] {
      background: #fff0ed;
      color: #8c3320;
    }
  `;

  document.head.appendChild(style);

  const widget = document.createElement("div");

  widget.innerHTML = `
    <button
      id="d2d-help-button"
      type="button"
      aria-haspopup="dialog"
      aria-controls="d2d-help-dialog"
    >
      ? Help
    </button>

    <dialog
      id="d2d-help-dialog"
      aria-labelledby="d2d-help-title"
      aria-describedby="d2d-help-description"
    >
      <div class="help-heading">
        <h2 id="d2d-help-title">How can we help?</h2>
        <button id="d2d-help-close" type="button">Close</button>
      </div>

      <p id="d2d-help-description">
        Send a question to the Drive2Doc team.
        Please do not include medical records, passwords, or other
        sensitive information. This form is not monitored for emergencies.
      </p>

      <form id="d2d-help-form">
        <label for="d2d-help-name">Your name</label>
        <input
          id="d2d-help-name"
          name="name"
          autocomplete="name"
          maxlength="100"
          required
        >

        <label for="d2d-help-email">Your email address</label>
        <input
          id="d2d-help-email"
          name="email"
          type="email"
          autocomplete="email"
          maxlength="254"
          required
        >

        <label for="d2d-help-subject">Subject</label>
        <input
          id="d2d-help-subject"
          name="subject"
          maxlength="150"
          required
        >

        <label for="d2d-help-message">Your question</label>
        <textarea
          id="d2d-help-message"
          name="message"
          maxlength="4000"
          required
        ></textarea>

        <button id="d2d-help-send" type="submit">
          Send question
        </button>

        <div
          id="d2d-help-status"
          role="status"
          aria-live="polite"
        ></div>
      </form>
    </dialog>
  `;

  document.body.appendChild(widget);

  const button = document.getElementById("d2d-help-button");
  const dialog = document.getElementById("d2d-help-dialog");
  const closeButton = document.getElementById("d2d-help-close");
  const form = document.getElementById("d2d-help-form");
  const sendButton = document.getElementById("d2d-help-send");
  const status = document.getElementById("d2d-help-status");

  let sending = false;

  button.addEventListener("click", () => {
    try {
      const user = JSON.parse(
        localStorage.getItem("drive2doc_signed_in_user") || "null"
      );

      const nameInput = document.getElementById("d2d-help-name");
      const emailInput = document.getElementById("d2d-help-email");

      if (user) {
        if (!nameInput.value) {
          nameInput.value = user.name || "";
        }

        if (
          !emailInput.value &&
          typeof user.identity === "string" &&
          user.identity.includes("@")
        ) {
          emailInput.value = user.identity;
        }
      }
    } catch {
      // Allow the form to work without saved account information.
    }

    dialog.showModal();
  });

  closeButton.addEventListener("click", () => dialog.close());

  dialog.addEventListener("close", () => button.focus());

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (sending || !form.reportValidity()) {
      return;
    }

    const data = {
      name: form.elements.namedItem("name").value.trim(),
      email: form.elements.namedItem("email").value.trim(),
      subject: form.elements.namedItem("subject").value.trim(),
      message: form.elements.namedItem("message").value.trim(),
      page: window.location.pathname
    };

    if (!data.name || !data.subject || !data.message) {
      status.dataset.error = "true";
      status.textContent = "Please complete every required field.";
      return;
    }

    sending = true;
    sendButton.disabled = true;
    sendButton.textContent = "Sending...";
    status.textContent = "";
    status.dataset.error = "false";

    try {
      const response = await fetch("/api/help", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || "Unable to send your question.");
      }

      status.textContent = result.message;

      form.elements.namedItem("subject").value = "";
      form.elements.namedItem("message").value = "";
    } catch (error) {
      status.dataset.error = "true";
      status.textContent =
        error.message || "Unable to send. Please try again later.";
    } finally {
      sending = false;
      sendButton.disabled = false;
      sendButton.textContent = "Send question";
    }
  });
})();