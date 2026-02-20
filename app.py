from __future__ import annotations
import os
import sqlite3
from typing import Any, Dict
from flask import Flask, jsonify, render_template, request, g

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "rfq.db")

ALLOWED_FIELDS = {'status_changed_date', 'updated_date', 'offer_reference', 'offer_submitted', 'creator', 'supplier_comment', 'supplier_submitter_name', 'rfq_number', 'project_cx', 'project_name', 'contact_last_name', 'supplier_submitter_email', 'wbs', 'purchaser', 'title', 'status_updater', 'grand_total', 'commodity_mdf', 'contact_first_name', 'supplier_gtc_comment', 'supplier', 'project_country', 'status', 'offer_date', 'created_date', 'deviations_comments', 'supplier_submitted_date', 'currency', 'first_accepted_date', 'rfq_due_date', 'contact_email', 'valid_until'}

SCHEMA_SQL = 'CREATE TABLE IF NOT EXISTS rfq (\n  id INTEGER PRIMARY KEY,\n  rfq_number TEXT,\n  title TEXT,\n  status TEXT,\n  project_name TEXT,\n  project_country TEXT,\n  commodity_mdf TEXT,\n  wbs TEXT,\n  supplier TEXT,\n  contact_first_name TEXT,\n  contact_last_name TEXT,\n  contact_email TEXT,\n  offer_reference TEXT,\n  offer_submitted TEXT,\n  offer_date TEXT,\n  valid_until TEXT,\n  currency TEXT,\n  creator TEXT,\n  status_updater TEXT,\n  project_cx TEXT,\n  purchaser TEXT,\n  created_date TEXT,\n  updated_date TEXT,\n  status_changed_date TEXT,\n  rfq_due_date TEXT,\n  first_accepted_date TEXT,\n  supplier_submitted_date TEXT,\n  grand_total TEXT,\n  supplier_submitter_name TEXT,\n  supplier_submitter_email TEXT,\n  supplier_comment TEXT,\n  supplier_gtc_comment TEXT,\n  deviations_comments TEXT\n);\n\nCREATE TABLE IF NOT EXISTS solt_tab (\n  id INTEGER PRIMARY KEY,\n  rfq_id INTEGER NOT NULL,\n  tab_index INTEGER NOT NULL,\n  name TEXT NOT NULL,\n  UNIQUE(rfq_id, tab_index)\n);\n\nCREATE TABLE IF NOT EXISTS solt_line (\n  id INTEGER PRIMARY KEY,\n  rfq_id INTEGER NOT NULL,\n  tab_index INTEGER NOT NULL,\n  line_no INTEGER NOT NULL,\n  item TEXT,\n  qty REAL,\n  uom TEXT,\n  unit_price REAL,\n  currency TEXT,\n  line_total REAL,\n  note TEXT\n);\n'

def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    def init_db():
        db = sqlite3.connect(DB_PATH)
        try:
            db.executescript(SCHEMA_SQL)
            db.commit()
        finally:
            db.close()

    def ensure_seed():
        init_db()
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute("SELECT id FROM rfq WHERE id=1").fetchone()
            if not row:
                seed = {
                    "id": 1,
                    "rfq_number": "RFQ-0000-0",
                    "title": "RFQ — Demo Screen — Revision 0",
                    "status": "Received",
                }
                cols = ", ".join(seed.keys())
                qs = ", ".join(["?"] * len(seed))
                db.execute(f"INSERT INTO rfq ({cols}) VALUES ({qs})", list(seed.values()))
                db.commit()

            # Seed Scope Order Lines tabs + a couple of demo lines (only if empty)
            tab_count = db.execute("SELECT COUNT(*) AS c FROM solt_tab WHERE rfq_id=1").fetchone()["c"]
            if tab_count == 0:
                tabs = [(1, 0, "Equipment"), (1, 1, "Margin transparency")]
                db.executemany("INSERT INTO solt_tab (rfq_id, tab_index, name) VALUES (?,?,?)", tabs)

                lines = [
                    (1, 0, 1, "Transformer refurbishment package", 1, "LOT", 3950000.00, "USD", 3950000.00, ""),
                    (1, 0, 2, "On-site commissioning support", 1, "DAY", 50165.00, "USD", 50165.00, ""),
                    (1, 1, 1, "Margin breakdown – overview (demo)", 1, "EA", 0.00, "USD", 0.00, "Tab 2 example row"),
                ]
                db.executemany(
                    "INSERT INTO solt_line (rfq_id, tab_index, line_no, item, qty, uom, unit_price, currency, line_total, note) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    lines
                )
                db.commit()
        finally:
            db.close()

    @app.before_request
    def _open_db():
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row

    @app.teardown_request
    def _close_db(exc):
        db = getattr(g, "db", None)
        if db is not None:
            db.c
    @app.get("/api/rfq/<int:rfq_id>/solt")
    def get_solt(rfq_id: int):
        tabs = g.db.execute(
            "SELECT tab_index, name FROM solt_tab WHERE rfq_id=? ORDER BY tab_index",
            (rfq_id,),
        ).fetchall()
        lines = g.db.execute(
            "SELECT * FROM solt_line WHERE rfq_id=? ORDER BY tab_index, line_no",
            (rfq_id,),
        ).fetchall()

        grouped = {}
        for r in lines:
            d = dict(r)
            grouped.setdefault(d["tab_index"], []).append(d)

        return jsonify({
            "rfq_id": rfq_id,
            "tabs": [dict(t) for t in tabs],
            "lines": grouped,
        })

    @app.patch("/api/rfq/<int:rfq_id>/solt/tab/<int:tab_index>")
    def patch_solt_tab(rfq_id: int, tab_index: int):
        payload = request.get_json(force=True, silent=True) or {}
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name required"}), 400
        g.db.execute(
            "UPDATE solt_tab SET name=? WHERE rfq_id=? AND tab_index=?",
            (name, rfq_id, tab_index),
        )
        g.db.commit()
        tab = g.db.execute(
            "SELECT tab_index, name FROM solt_tab WHERE rfq_id=? AND tab_index=?",
            (rfq_id, tab_index),
        ).fetchone()
        if not tab:
            return jsonify({"error": "not found"}), 404
        return jsonify(dict(tab))

    @app.post("/api/rfq/<int:rfq_id>/solt/line")
    def add_solt_line(rfq_id: int):
        payload = request.get_json(force=True, silent=True) or {}
        tab_index = int(payload.get("tab_index", 0))
        item = payload.get("item")
        qty = payload.get("qty")
        uom = payload.get("uom")
        unit_price = payload.get("unit_price")
        currency = payload.get("currency")
        note = payload.get("note")

        # next line number in this tab
        row = g.db.execute(
            "SELECT COALESCE(MAX(line_no), 0) AS m FROM solt_line WHERE rfq_id=? AND tab_index=?",
            (rfq_id, tab_index),
        ).fetchone()
        line_no = int(row["m"]) + 1

        def to_float(x):
            try:
                return float(x)
            except Exception:
                return None

        qty_f = to_float(qty) or 0.0
        unit_f = to_float(unit_price) or 0.0
        total = qty_f * unit_f

        g.db.execute(
            "INSERT INTO solt_line (rfq_id, tab_index, line_no, item, qty, uom, unit_price, currency, line_total, note) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (rfq_id, tab_index, line_no, item, qty_f, uom, unit_f, currency, total, note),
        )
        g.db.commit()
        line_id = g.db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        line = g.db.execute("SELECT * FROM solt_line WHERE id=?", (line_id,)).fetchone()
        return jsonify(dict(line)), 201

    @app.patch("/api/rfq/<int:rfq_id>/solt/line/<int:line_id>")
    def patch_solt_line(rfq_id: int, line_id: int):
        payload = request.get_json(force=True, silent=True) or {}

        allowed = {"item","qty","uom","unit_price","currency","note","line_total","line_no","tab_index"}
        updates = {k: payload[k] for k in payload.keys() if k in allowed}
        if not updates:
            return jsonify({"error": "no valid fields"}), 400

        # Recalculate line_total if qty/unit_price edited (unless caller explicitly sets line_total)
        def to_float(x):
            try:
                return float(x)
            except Exception:
                return None

        if "line_total" not in updates and ("qty" in updates or "unit_price" in updates):
            existing = g.db.execute("SELECT qty, unit_price FROM solt_line WHERE id=? AND rfq_id=?", (line_id, rfq_id)).fetchone()
            if existing:
                qty_f = to_float(updates.get("qty", existing["qty"])) or 0.0
                unit_f = to_float(updates.get("unit_price", existing["unit_price"])) or 0.0
                updates["line_total"] = qty_f * unit_f

        sets = ", ".join([f"{k}=?" for k in updates.keys()])
        values = list(updates.values()) + [line_id, rfq_id]
        g.db.execute(f"UPDATE solt_line SET {sets} WHERE id=? AND rfq_id=?", values)
        g.db.commit()
        line = g.db.execute("SELECT * FROM solt_line WHERE id=? AND rfq_id=?", (line_id, rfq_id)).fetchone()
        if not line:
            return jsonify({"error": "not found"}), 404
        return jsonify(dict(line))

    @app.delete("/api/rfq/<int:rfq_id>/solt/line/<int:line_id>")
    def delete_solt_line(rfq_id: int, line_id: int):
        g.db.execute("DELETE FROM solt_line WHERE id=? AND rfq_id=?", (line_id, rfq_id))
        g.db.commit()
        return jsonify({"ok": True})

lose()

    ensure_seed()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    @app.get("/api/rfq/<int:rfq_id>")
    def get_rfq(rfq_id: int):
        row = g.db.execute("SELECT * FROM rfq WHERE id=?", (rfq_id,)).fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        return jsonify(dict(row))

    @app.patch("/api/rfq/<int:rfq_id>")
    def patch_rfq(rfq_id: int):
        payload: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
        updates = {k: v for k, v in payload.items() if k in ALLOWED_FIELDS}
        if not updates:
            return jsonify({"error": "no valid fields"}), 400

        sets = ", ".join([f"{k}=?" for k in updates.keys()])
        values = list(updates.values()) + [rfq_id]
        g.db.execute(f"UPDATE rfq SET {sets} WHERE id=?", values)
        g.db.commit()
        row = g.db.execute("SELECT * FROM rfq WHERE id=?", (rfq_id,)).fetchone()
        return jsonify(dict(row))

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5012, debug=True)
