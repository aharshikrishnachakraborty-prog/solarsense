// Login page: send username + password to the API; on success go to the page the user wanted.
// In the static demo copy (no server) the check happens in the browser — for show only, not secure.

const STATIC_DEMO_USERS = { operator: "solar123", engineer: "solar123" };   // same as config.DEMO_USERS

/** Where to go after logging in: ?next=plant.html, but only a page of THIS site (never another website). */
function nextPage() {
  const next = new URLSearchParams(window.location.search).get("next") || "";
  return /^[a-z_]+\.html(\?[\w=&.-]*)?$/.test(next) ? next : "index.html";
}

async function logIn(username, password) {
  if (STATIC_SITE) {
    if (STATIC_DEMO_USERS[username] !== password) throw new Error("Wrong username or password.");
    session.set("solarsense-user", username);
    return;
  }
  const response = await fetch("api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error(response.status === 401 ? "Wrong username or password." : `Login failed (${response.status}).`);
  }
}

document.getElementById("login-brand").innerHTML = `${SUN_LOGO}<span>SolarSense</span>`;
document.getElementById("static-note").hidden = !STATIC_SITE;

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  const error = document.getElementById("login-error");
  const button = document.getElementById("login-button");
  if (!username || !password) {
    error.textContent = "Enter your username and password.";
    return;
  }
  error.textContent = "";
  button.disabled = true;
  button.textContent = "Logging in…";
  try {
    await logIn(username, password);
    window.location.href = nextPage();
  } catch (failure) {
    error.textContent = failure.message === "Failed to fetch" ? "Engine offline — start the server." : failure.message;
    button.disabled = false;
    button.textContent = "Log in";
  }
});
