# ProWorkflow CSV Importer

Import contacts into ProWorkflow from a CSV file.

## Requirements

- Python 3.10+
- `requests` library

```bash
pip install requests
```

## Usage

**With API key:**
```bash
python import_contacts.py --base-url https://api.proworkflow.com/api/v4 --api-key YOUR-API-KEY --file contacts.csv
```

**Preview without creating (dry run):**
```bash
python import_contacts.py --base-url https://api.proworkflow.com/api/v4 --api-key YOUR-API-KEY --file contacts.csv --dry-run
```

**With config file:**
```bash
cp ../data-export/config.example.json config.json
# edit config.json with your credentials
python import_contacts.py --config config.json --file contacts.csv
```

## CSV format

Use `contacts_template.csv` as your starting point. Column headers:

| Column | Required | Description |
|--------|----------|-------------|
| `firstname` | one of firstname/lastname | Contact first name |
| `lastname` | one of firstname/lastname | Contact last name |
| `type` | | `client`, `contractor`, `staff`, `other`, or `supplier` |
| `email` | | Email address |
| `workphone` | | Work phone number |
| `mobilephone` | | Mobile phone number |
| `title` | | Job title |
| `companyid` | | ID of an existing company to link to |
| `divisionid` | | Division ID (Advanced plan only) |
| `address1` | | Street address line 1 |
| `address2` | | Street address line 2 |
| `city` | | City |
| `state` | | State / province |
| `zipcode` | | Postal / zip code |
| `country` | | Country |
| `allowlogin` | | `true` or `false` — whether the contact can log in (defaults to `false`) |

Blank columns are ignored — only populate what you have.

> **Note:** The script has no duplicate detection. Running it twice on the same file will create duplicate contacts.

## Options

| Flag | Description |
|------|-------------|
| `--base-url` | API base URL |
| `--api-key` | API key |
| `--token` | JWT bearer token |
| `--config` | Path to JSON config file |
| `--file` | Path to CSV file (required) |
| `--dry-run` | Preview rows without creating contacts |

## Finding your company IDs

If you want to link contacts to existing companies, you'll need the company IDs first:

```bash
curl 'https://api.proworkflow.com/api/v4/companies?fields=id,name&pagesize=200' \
  -H 'apikey: your-api-key'
```
