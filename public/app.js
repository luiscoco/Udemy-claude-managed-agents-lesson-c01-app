const $ = (id) => document.getElementById(id);
let id = "",
  source,
  seen = new Set();
const notice = (message, error = false) => {
  $("notice").hidden = false;
  $("notice").textContent = message;
  $("notice").className = `notice ${error ? "error" : ""}`;
};
async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error || "Request failed");
    error.data = data;
    throw error;
  }
  return data;
}
function enabled(value) {
  for (const el of document.querySelectorAll(
    "#message, #send, #refresh, #interrupt, #eventId, #toolResult, .action",
  ))
    el.disabled = !value;
}
function showEvent(event) {
  if (event.id && seen.has(event.id)) return;
  if (event.id) seen.add(event.id);
  const feed = $("feed");
  feed.querySelector(".empty")?.remove();
  const item = document.createElement("article");
  item.className = "event";
  const top = document.createElement("div");
  top.className = "event-top";
  const name = document.createElement("strong");
  name.textContent = event.type;
  const eventId = document.createElement("span");
  eventId.textContent = event.id || "";
  top.append(name, eventId);
  item.append(top);
  if (event.type === "agent.message" || event.type === "user.message") {
    const content = document.createElement("p");
    content.textContent = (event.content || [])
      .map((x) => x.text || JSON.stringify(x))
      .join("\n");
    item.append(content);
  } else {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "View event details";
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(event, null, 2);
    details.append(summary, pre);
    item.append(details);
  }
  feed.append(item);
  feed.scrollTop = feed.scrollHeight;
  if (event.type === "session.status_idle") {
    const reason = event.stop_reason?.type || "unknown";
    $("status").textContent = "Idle";
    $("reason").textContent = reason;
    $("reasonHelp").textContent =
      {
        end_turn:
          "The turn ended. Verify any claimed result before relying on it.",
        requires_action:
          "The agent is waiting for tool results or confirmation. Inspect the relevant events and respond below.",
        budget_reached: "The session reached its budget and is paused.",
      }[reason] || "Inspect the event for details.";
    if (event.stop_reason?.event_ids?.length)
      $("eventId").value = event.stop_reason.event_ids[0];
  } else if (event.type === "session.status_running") {
    $("status").textContent = "Running";
    $("reason").textContent = "—";
  } else if (event.type === "session.status_terminated") {
    $("status").textContent = "Terminated";
  } else if (
    event.type === "session.error" ||
    event.type === "app.stream_error"
  )
    notice(event.message || JSON.stringify(event.error || event), true);
}
function connect(sessionId) {
  if (!/^sesn_[A-Za-z0-9_-]+$/.test(sessionId))
    throw new Error("Enter a valid session ID beginning with sesn_.");
  if (source) source.close();
  id = sessionId;
  seen = new Set();
  $("feed").innerHTML = "";
  $("eventId").value = "";
  $("toolResult").value = "";
  $("currentId").textContent = id;
  $("sessionId").value = id;
  try {
    sessionStorage.setItem("session-lab-last-session", id);
  } catch {}
  $("reason").textContent = "—";
  $("status").textContent = "Connecting";
  enabled(false);
  source = new EventSource(`/api/sessions/${encodeURIComponent(id)}/stream`);
  source.onopen = () => {
    $("status").textContent = "Connected";
    enabled(true);
  };
  source.onmessage = (e) => showEvent(JSON.parse(e.data));
  source.onerror = () => {
    $("status").textContent = "Reconnecting";
    enabled(false);
  };
}
$("create").onclick = async () => {
  $("create").disabled = true;
  try {
    const session = await api("/api/sessions", { method: "POST" });
    connect(session.id);
    notice("Session created. Send a message to start work.");
  } catch (e) {
    notice(e.message, true);
    if (e.data?.sessionId) {
      $("sessionId").value = e.data.sessionId;
    }
  } finally {
    $("create").disabled = false;
  }
};
$("connect").onclick = () => {
  try {
    connect($("sessionId").value.trim());
  } catch (e) {
    notice(e.message, true);
  }
};
$("messageForm").onsubmit = async (e) => {
  e.preventDefault();
  const text = $("message").value.trim();
  if (!text) return;
  $("send").disabled = true;
  try {
    await api(`/api/sessions/${id}/message`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    $("message").value = "";
  } catch (e) {
    notice(e.message, true);
  } finally {
    $("send").disabled = false;
  }
};
$("interrupt").onclick = async () => {
  try {
    await api(`/api/sessions/${id}/interrupt`, { method: "POST" });
    notice(
      "Interrupt sent. Wait for an idle event or inspect the session to confirm it stopped.",
    );
  } catch (e) {
    notice(e.message, true);
  }
};
$("refresh").onclick = async () => {
  try {
    const session = await api(`/api/sessions/${id}`);
    showEvent({ type: "app.session_snapshot", session });
    notice("Session snapshot added to the activity feed.");
  } catch (e) {
    notice(e.message, true);
  }
};
for (const button of document.querySelectorAll(".action"))
  button.onclick = async () => {
    try {
      await api(`/api/sessions/${id}/action`, {
        method: "POST",
        body: JSON.stringify({
          id: $("eventId").value.trim(),
          result: button.dataset.action,
          text: $("toolResult").value,
        }),
      });
      notice("Response sent to the session.");
    } catch (e) {
      notice(e.message, true);
    }
  };
// Returning from the guide restores the ID without sending a prompt or
// reconnecting automatically. The student explicitly chooses Connect.
try {
  const previousSession = sessionStorage.getItem("session-lab-last-session");
  if (/^sesn_[A-Za-z0-9_-]+$/.test(previousSession || "")) {
    $("sessionId").value = previousSession;
    notice("Your previous session ID is ready. Click Connect to view its events again.");
  }
} catch {}
api("/api/config")
  .then((data) => {
    if (!data.configured)
      notice(
        "Add your Anthropic API key, agent ID, and environment ID to .env, then restart the server.",
        true,
      );
  })
  .catch((e) => notice(e.message, true));
