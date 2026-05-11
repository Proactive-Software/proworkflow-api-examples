# ProWorkflow API Examples

Code examples for the [ProWorkflow API v4](https://api.proworkflow.com/api/v4/swagger/index.html).

## Examples

### JavaScript

| Example | Description |
|---------|-------------|
| [dashboard](js/dashboard/) | Active projects and upcoming tasks — open `index.html` in a browser, no build step |

### Python

| Example | Description |
|---------|-------------|
| [data-export](python/data-export/) | Download all account data to JSON files |
| [csv-import](python/csv-import/) | Import contacts from a CSV file |

## Real-world application

[pwf-cli](https://github.com/Proactive-Software/pwf-cli) — a full command-line application built on the ProWorkflow API.

## Authentication

All examples support both authentication methods:

- **API Key** — found in ProWorkflow under Settings → API Keys
- **Bearer Token (JWT)** — obtained via the `/auth` endpoint

## API Reference

- [Swagger UI](https://api.proworkflow.com/api/v4/swagger/index.html)
- [Rate limits](https://api.proworkflow.com/api/v4/swagger/index.html): 500 requests per 30 seconds per API key

