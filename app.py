from __future__ import annotations
import os
import sqlite3
from typing import Any, Dict
from flask import Flask, jsonify, render_template, request, g

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "rfq.db")

ALLOWED_FIELDS = {'status_changed_date', 'updated_date', 'offer_reference', 'offer_submitted', 'creator', 'supplier_comment', 'supplier_submitter_name', 'rfq_number', 'project_cx', 'project_name', 'contact_last_name', 'supplier_submitter_email', 'wbs', 'purchaser', 'title', 'status_updater', 'grand_total', 'commodity_mdf', 'contact_first_name', 'supplier_gtc_comment', 'supplier', 'project_country', 'status', 'offer_date', 'created_date', 'deviations_comments', 'supplier_submitted_date', 'currency', 'first_accepted_date', 'rfq_due_date', 'contact_email', 'valid_until'}

SCHEMA_SQL = 'CREATE TABLE IF NOT EXISTS rfq (\n  id INTEGER PRIMARY KEY,\n  rfq_number TEXT,\n  title TEXT,\n  status TEXT,\n  project_name TEXT,\n  project_country TEXT,\n  commodity_mdf TEXT,\n  wbs TEXT,\n  supplier TEXT,\n  contact_first_name TEXT,\n  contact_last_name TEXT,\n  contact_email TEXT,\n  offer_reference TEXT,\n  offer_submitted TEXT,\n  offer_date TEXT,\n  valid_until TEXT,\n  currency TEXT,\n  creator TEXT,\n  status_updater TEXT,\n  project_cx TEXT,\n  purchaser TEXT,\n  created_date TEXT,\n  updated_date TEXT,\n  status_changed_date TEXT,\n  rfq_due_date TEXT,\n  first_accepted_date TEXT,\n  supplier_submitted_date TEXT,\n  grand_total TEXT,\n  supplier_submitter_name TEXT,\n  supplier_submitter_email TEXT,\n  supplier_comment TEXT,\n  supplier_gtc_comment TEXT,\n  deviations_comments TEXT\n);\n'

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
            if row:
                return
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
            db.close()

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
