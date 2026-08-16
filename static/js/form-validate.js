// Client-side validation for event and registration forms (blocks obviously invalid values).

document.addEventListener("DOMContentLoaded", () => {
  const eventForm = document.getElementById("eventForm");
  if (eventForm) {
    eventForm.addEventListener("submit", (e) => {
      const name = eventForm.event_name.value.trim();
      const maxP = Number(eventForm.max_participants.value);
      const fee = Number(eventForm.registration_fee.value);
      const errors = [];

      if (!name) errors.push("Event name cannot be empty.");
      if (!maxP || maxP <= 0) errors.push("Maximum participants must be greater than 0.");
      if (fee < 0) errors.push("Registration fee cannot be negative.");

      if (errors.length) {
        e.preventDefault();
        errors.forEach((msg) => showToast(msg, "error"));
      }
    });
  }

  function validateRegistrationForm(form, e) {
    const email = form.email.value.trim();
    const phone = form.phone.value.trim();
    const errors = [];

    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) errors.push("Please enter a valid email address.");
    if (!/^\d{10}$/.test(phone)) errors.push("Phone number must be exactly 10 digits.");
    if (!form.event_id.value) errors.push("Please select an event.");

    if (errors.length) {
      e.preventDefault();
      errors.forEach((msg) => showToast(msg, "error"));
    }
  }

  const registerForm = document.getElementById("registerForm");
  if (registerForm) {
    registerForm.addEventListener("submit", (e) => validateRegistrationForm(registerForm, e));
  }

  const editRegistrationForm = document.getElementById("editRegistrationForm");
  if (editRegistrationForm) {
    editRegistrationForm.addEventListener("submit", (e) => validateRegistrationForm(editRegistrationForm, e));
  }
});
