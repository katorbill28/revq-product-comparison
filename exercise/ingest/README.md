# Ingest

Run all samples and refresh the app data:

```bash
python ingest/ingest.py
```

Run one file:

```bash
python ingest/ingest.py data/blinkit_sample.json
```

The script creates `revq.sqlite` from `schema.sql` and exports `app/public/products.json` for the UI.
