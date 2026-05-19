# ProWorkflow Dashboard

A single-file browser dashboard showing active projects and upcoming tasks.

## What it shows

- **Active Projects** — total count of active projects in your account
- **Due This Week** — tasks with a due date in the next 7 days
- **Overdue Tasks** — tasks past their due date
- **Task table** — all active tasks due in the next 14 days, sorted by due date, with overdue rows highlighted

## Usage

1. Open `index.html` in a text editor
2. Set your API key and base URL at the top of the `<script>` block:

```js
const CONFIG = {
  baseUrl: 'https://api.proworkflow.com/api/v4',
  apiKey:  'YOUR-API-KEY-HERE',
};
```

3. Open `index.html` in a browser

No build step, no server, no dependencies.

## API calls made

```
GET /projects?status=active&fields=id,name&pagesize=500
GET /projects/items?status=active&duedateto=<+14 days>&sortby=duedate&sortorder=asc&fields=id,name,duedate,priorityid,projectid,projecttitle&pagesize=100
```

Both calls run in parallel via `Promise.all`. The dashboard demonstrates:
- API key authentication via request header
- `fields` parameter to limit response payload
- Date filter params (`duedateto`)
- `meta.total` for accurate counts
- Joining two resources (task `projectid` → project name)

## Finding your API key

In ProWorkflow: **Settings → API Keys**
