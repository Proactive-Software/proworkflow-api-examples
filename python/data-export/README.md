# ProWorkflow Data Export

Downloads all account data from the ProWorkflow API v4 to local JSON files.

**What it exports:**
- Core resources: companies, contacts, projects, invoices, quotes, messages, time, files
- Sub-resources: project items/phases/notes, invoice items/phases, quote items/phases, template items/phases
- Settings: account, contacts, projects, invoices, quotes, webhooks, work stages, and more

## Requirements

- Python 3.10+
- `requests` library

```bash
pip install requests
```

## Usage

**With API key:**
```bash
python export.py --base-url https://api.proworkflow.com/api/v4 --api-key YOUR-API-KEY
```

**With JWT token:**
```bash
python export.py --base-url https://api.proworkflow.com/api/v4 --token YOUR-JWT-TOKEN
```

**With config file:**
```bash
cp config.example.json config.json
# edit config.json with your credentials
python export.py --config config.json
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--base-url` | API base URL | required |
| `--api-key` | API key | — |
| `--token` | JWT bearer token | — |
| `--config` | Path to JSON config file | — |
| `--output` | Output directory | `output/` |
| `--only` | Run specific phases only: `lists,simple,settings,nested` | all |
| `--skip-nested` | Skip unique nested endpoint downloads | false |

## Output

All data is saved to the `output/` directory (configurable with `--output`) as JSON files:

```
output/
├── _manifest.json          # export metadata (timestamp, request count, errors)
├── companies.json
├── contacts.json
├── projects.json
├── invoices.json
├── quotes.json
├── messages.json
├── time.json
├── files.json
├── projectitems.json
├── projectphases.json
├── ...
├── settings_account.json
├── settings_projects.json
└── ...
```

## Authentication

Find your API key in ProWorkflow under **Settings → Integrations → API Keys**.

For JWT tokens, authenticate via `POST /auth` — see the [API reference](https://api.proworkflow.com/api/v4/swagger/index.html).
