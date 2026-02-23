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

Your saved files are in `static/pp_files/`.

## Scope Order Lines (tabs + subtable)

The "Scope Order Lines" area is now driven by SQLite tables:

- `solt_tab` (tab_index, name)
- `solt_line` (line_no, item, qty, uom, unit_price, line_total, ...)

API:
- `GET /api/rfq/1/solt` (tabs + grouped lines)
- `PATCH /api/rfq/1/solt/tab/<tab_index>` rename a tab (double-click tab while in Edit mode)
- `PATCH /api/rfq/1/solt/line/<line_id>` update a line cell (edit a cell and click away in Edit mode)

The front-end reuses the saved CSS classes (`solt-tabs__tab`, `solt-tabs__tab--active`, etc.) so it still looks like the original UI.


## Template cleanup
- `templates/base.html` contains the head + linked CSS.
- `templates/index.html` is now a small Flask template that includes `templates/partials/rfq_page.html`.
- Any inline CSS previously in the saved page has been moved to `static/app.css`.
