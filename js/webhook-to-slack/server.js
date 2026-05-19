import express from "express";

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const CONFIG = {
  port: 3000,
  pwfBaseUrl: "https://api.proworkflow.com/api/v4",
  pwfApiKey: "YOUR-PWF-API-KEY-HERE",
  slackWebhookUrl: "YOUR-SLACK-WEBHOOK-URL-HERE",
};
// ─────────────────────────────────────────────────────────────────────────────

// Events this server handles — any event not listed here is ignored.
// Register a separate webhook subscription in PWF for each event you want:
//   POST /settings/webhooks  { "event": "newproject", "url": "http://yourserver/webhook/newproject" }
const EVENT_HANDLERS = {
  newproject: { type: "project" },
  editproject: { type: "project" },
  completeproject: { type: "project" },
  deleteproject: { type: "project" },
  newtask: { type: "task" },
  edittask: { type: "task" },
  completetask: { type: "task" },
  deletetask: { type: "task" },
};

const app = express();
app.use(express.json());

// Fetch a resource from the ProWorkflow API
async function pwfFetch(path) {
  const response = await fetch(`${CONFIG.pwfBaseUrl}${path}`, {
    headers: { apikey: CONFIG.pwfApiKey },
  });
  if (!response.ok) {
    throw new Error(`PWF API ${response.status}: ${await response.text()}`);
  }
  return response.json();
}

// Post a message to Slack
async function postToSlack(message) {
  const response = await fetch(CONFIG.slackWebhookUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(message),
  });
  if (!response.ok) {
    throw new Error(`Slack ${response.status}: ${await response.text()}`);
  }
}

function buildProjectMessage(event, project) {
  const labels = {
    newproject: "📁 New project created",
    editproject: "✏️ Project updated",
    completeproject: "✅ Project completed",
    deleteproject: "🗑️ Project deleted",
  };

  const title = project.title ?? "(untitled)";
  const number = project.number ? ` #${project.number}` : "";
  const due = project.duedate ? ` · Due ${project.duedate.slice(0, 10)}` : "";

  return { text: `${labels[event] ?? event}: *${title}*${number}${due}` };
}

function buildTaskMessage(event, task) {
  const labels = {
    newtask: "📌 New task added",
    edittask: "✏️ Task updated",
    completetask: "✅ Task completed",
    deletetask: "🗑️ Task deleted",
  };

  const name = task.name ?? "(untitled)";
  const project = task.projecttitle ? ` · ${task.projecttitle}` : "";
  const due = task.duedate ? ` · Due ${task.duedate.slice(0, 10)}` : "";

  return { text: `${labels[event] ?? event}: *${name}*${project}${due}` };
}

// PWF webhook payload: { "id": 123, "url": "https://api.proworkflow.net/..." }
// The url field references the legacy API — use the id to fetch from v4 instead.
app.post("/webhook/:event", async (req, res) => {
  // Acknowledge immediately — PWF retries if it doesn't get a 2xx quickly
  res.sendStatus(200);

  const { event } = req.params;
  const { id } = req.body;

  if (!id) {
    console.error(`[${event}] Missing id in payload`, req.body);
    return;
  }

  const handler = EVENT_HANDLERS[event];
  if (!handler) {
    console.log(`[${event}] No handler configured — skipping`);
    return;
  }

  console.log(`[${event}] id=${id}`);

  try {
    let message;

    if (handler.type === "project") {
      const data = await pwfFetch(
        `/projects/${id}?fields=id,title,number,duedate`,
      );
      message = buildProjectMessage(event, data.data ?? {});
    } else if (handler.type === "task") {
      const data = await pwfFetch(
        `/projects/items/${id}?fields=id,name,projecttitle,duedate,priority`,
      );
      message = buildTaskMessage(event, data.data ?? {});
    }

    if (message) {
      await postToSlack(message);
      console.log(`[${event}] Slack notified: ${message.text}`);
    }
  } catch (err) {
    console.error(`[${event}] id=${id} error:`, err.message);
  }
});

app.listen(CONFIG.port, () => {
  console.log(`Webhook listener on port ${CONFIG.port}`);
});
