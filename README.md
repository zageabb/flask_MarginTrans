# RFQ / Quotation Demo (Flask + SQLite)

This wraps your saved RFQ page into Flask and links key fields to SQLite.

## Run (Linux)

```bash
cd rfq_flask_demo_user
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: http://localhost:5000

## Edit + demo

- Click **Edit (E)** (bottom-right) or press **E** to toggle edit mode.
- Click a field, change the text, click away.
- The browser will PATCH to `/api/rfq/1` and the page will reflect DB values on refresh.

## Add more bound fields

1) Edit `templates/index.html` and add `data-field="some_column"` to any element.
2) Add the column to the `rfq` table + `ALLOWED_FIELDS` in `app.py`.

## Assets

Your saved files are in `static/RFQ for Test - SOQ -  Perfect Engineers & Consultants - ProjectProcure_files/`.
