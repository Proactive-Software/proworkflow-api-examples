# ProWorkflow Webhook → Slack

Receives ProWorkflow webhook events and posts notifications to a Slack channel.

When a project or task is created, completed, or changed, PWF fires a POST to this server. The server fetches the full resource from the v4 API and sends a formatted message to Slack.

## How it works

1. PWF fires `POST /webhook/newproject` with `{ "id": 123, "url": "..." }`
2. Server fetches the project from `GET /projects/123`
3. Server posts a message to your Slack incoming webhook URL

Each event type has its own URL path — you register a separate subscription in PWF for each event you want to receive.

## Setup

**1. Install dependencies**
```bash
npm install
```

**2. Configure `server.js`**

Edit the `CONFIG` block at the top:
```js
const CONFIG = {
  port: 3000,
  pwfBaseUrl: 'https://api.proworkflow.com/api/v4',
  pwfApiKey:  'YOUR-PWF-API-KEY-HERE',
  slackWebhookUrl: 'YOUR-SLACK-WEBHOOK-URL-HERE',
};
```

- PWF API key: **Settings → API Keys** in ProWorkflow
- Slack webhook URL: create an **Incoming Webhook** in your Slack app settings

**3. Start the server**
```bash
npm start
```

**4. Expose to the internet**

PWF needs to reach your server. For local testing use [ngrok](https://ngrok.com):
```bash
ngrok http 3000
# gives you: https://abc123.ngrok.io
```

**5. Register webhook subscriptions in PWF**

Register one subscription per event using the API or Swagger UI:
```bash
# New project notifications
curl -X POST https://api.proworkflow.com/api/v4/settings/webhooks \
  -H 'apikey: YOUR-API-KEY' \
  -H 'Content-Type: application/json' \
  -d '{"event": "newproject", "url": "https://abc123.ngrok.io/webhook/newproject"}'

# Project completed
curl -X POST https://api.proworkflow.com/api/v4/settings/webhooks \
  -H 'apikey: YOUR-API-KEY' \
  -H 'Content-Type: application/json' \
  -d '{"event": "completeproject", "url": "https://abc123.ngrok.io/webhook/completeproject"}'

# New task
curl -X POST https://api.proworkflow.com/api/v4/settings/webhooks \
  -H 'apikey: YOUR-API-KEY' \
  -H 'Content-Type: application/json' \
  -d '{"event": "newtask", "url": "https://abc123.ngrok.io/webhook/newtask"}'

# Task completed
curl -X POST https://api.proworkflow.com/api/v4/settings/webhooks \
  -H 'apikey: YOUR-API-KEY' \
  -H 'Content-Type: application/json' \
  -d '{"event": "completetask", "url": "https://abc123.ngrok.io/webhook/completetask"}'
```

## Supported events

| Event | Trigger |
|-------|---------|
| `newproject` | Project created |
| `editproject` | Project updated |
| `completeproject` | Project marked complete |
| `deleteproject` | Project deleted |
| `newtask` | Task created |
| `edittask` | Task updated |
| `completetask` | Task marked complete |
| `deletetask` | Task deleted |

To handle additional events, add them to `EVENT_HANDLERS` in `server.js`.

## Debugging

View recent webhook delivery attempts (last 7 days):
```bash
curl 'https://api.proworkflow.com/api/v4/settings/webhooks/requests' \
  -H 'apikey: YOUR-API-KEY'
```
