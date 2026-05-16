# XMU Donation Tool

Python desktop tool for downloading public donation records from the Xiamen University Education Development Foundation, storing the raw data, importing normalized records into SQLite, and displaying summary queries.

## Run

```bash
python3 main.py
```

## Test

```bash
python3 -m pytest
```

## Data Files

- `data/donations_raw.json`: downloaded raw API response pages.
- `data/donations.db`: SQLite database created by the app.
