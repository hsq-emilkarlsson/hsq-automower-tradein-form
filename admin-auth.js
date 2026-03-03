const adminLoginForm = document.getElementById("admin-login-form");
const accessTokenInput = document.getElementById("access-token");
const adminLoginMessage = document.getElementById("admin-login-message");

const clearAdminMessage = () => {
  if (adminLoginMessage) {
    adminLoginMessage.textContent = "";
  }
};

adminLoginForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearAdminMessage();

  const token = accessTokenInput?.value.trim();
  if (!token) {
    if (adminLoginMessage) {
      adminLoginMessage.textContent = "Please enter your access token.";
    }
    return;
  }

  try {
    const body = new URLSearchParams();
    body.append("token", token);

    const response = await fetch("/api/admin/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body,
    });

    if (!response.ok) {
      if (adminLoginMessage) {
        adminLoginMessage.textContent = "Invalid access token.";
      }
      return;
    }

    // Try cookie-based auth first; also pass token as query fallback
    const targetUrl = `/admin?token=${encodeURIComponent(token)}`;
    window.location.href = targetUrl;
  } catch (error) {
    if (adminLoginMessage) {
      adminLoginMessage.textContent = "Sign-in failed. Please try again.";
    }
  }
});

