from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "instance")
RFQ_JSON = os.path.join(DATA_DIR, "rfq.json")
SOLT_JSON = os.path.join(DATA_DIR, "solt.json")

ALLOWED_FIELDS = {'deviations_comments', 'supplier', 'purchaser', 'supplier_comment', 'offer_reference', 'project_cx', 'rfq_number', 'project_country', 'status', 'status_updater', 'project_name', 'supplier_submitter_name', 'updated_date', 'title', 'status_changed_date', 'contact_email', 'creator', 'commodity_mdf', 'valid_until', 'grand_total', 'rfq_due_date', 'supplier_submitted_date', 'wbs', 'currency', 'offer_submitted', 'supplier_gtc_comment', 'first_accepted_date', 'created_date', 'supplier_submitter_email', 'offer_date', 'contact_last_name', 'contact_first_name'}


def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json_atomic(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _extract_seed_from_template() -> Dict[str, Any]:
    """Seed values by reading templates/index.html and extracting [data-field] text."""
    template_path = os.path.join(BASE_DIR, "templates", "index.html")
    if not os.path.exists(template_path):
        return {}
    with open(template_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    seed: Dict[str, Any] = {}
    for el in soup.select("[data-field]"):
        field = el.get("data-field")
        if not field:
            continue
        seed[field] = el.get_text(" ", strip=True)
    return seed


def ensure_seed_json() -> None:
    seed = _extract_seed_from_template()

    rfq_store = _read_json(RFQ_JSON, {})
    if "1" not in rfq_store:
        rec = {"id": 1}
        # fill allowed fields from template seed (or blank)
        for f in ALLOWED_FIELDS:
            rec[f] = seed.get(f, "")
        rec["rfq_number"] = rec.get("rfq_number") or "RFQ-0000-0"
        rec["title"] = rec.get("title") or "RFQ — Demo Screen — Revision 0"
        rec["status"] = rec.get("status") or "Received"
        rfq_store["1"] = rec
        _write_json_atomic(RFQ_JSON, rfq_store)

    solt_store = _read_json(SOLT_JSON, {})
    if "1" not in solt_store:
        solt_store["1"] = {
            "tabs": [
                {"tab_index": 0, "name": "Section 1"},
                {"tab_index": 1, "name": "Section 2"},
            ],
            "lines": [
                {"id": 1, "rfq_id": 1, "tab_index": 0, "line_no": 1, "item": "Line item A", "qty": 1.0, "uom": "EA", "unit_price": 100.0, "currency": "USD", "line_total": 100.0, "note": ""},
                {"id": 2, "rfq_id": 1, "tab_index": 0, "line_no": 2, "item": "Line item B", "qty": 2.0, "uom": "EA", "unit_price": 250.0, "currency": "USD", "line_total": 500.0, "note": ""},
                {"id": 3, "rfq_id": 1, "tab_index": 1, "line_no": 1, "item": "Line item C", "qty": 5.0, "uom": "EA", "unit_price": 50.0,  "currency": "USD", "line_total": 250.0, "note": ""},
            ],
            "next_line_id": 4
        }
        _write_json_atomic(SOLT_JSON, solt_store)


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    ensure_seed_json()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    # --------------------
    # RFQ (flat fields)
    # --------------------
    @app.get("/api/rfq/<int:rfq_id>")
    def get_rfq(rfq_id: int):
        store = _read_json(RFQ_JSON, {})
        rec = store.get(str(rfq_id))
        if not rec:
            return jsonify({"error": "not found"}), 404
        return jsonify(rec)

    @app.patch("/api/rfq/<int:rfq_id>")
    def patch_rfq(rfq_id: int):
        payload: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
        updates = {k: v for k, v in payload.items() if k in ALLOWED_FIELDS}
        if not updates:
            return jsonify({"error": "no valid fields"}), 400

        store = _read_json(RFQ_JSON, {})
        key = str(rfq_id)
        rec = store.get(key, {"id": rfq_id})
        rec.update(updates)
        store[key] = rec
        _write_json_atomic(RFQ_JSON, store)
        return jsonify(rec)

    # --------------------
    # SOLT (tabs + lines)
    # --------------------
    def _get_solt_record(rfq_id: int) -> Dict[str, Any]:
        store = _read_json(SOLT_JSON, {})
        return store.get(str(rfq_id), {"tabs": [], "lines": [], "next_line_id": 1})

    def _save_solt_record(rfq_id: int, rec: Dict[str, Any]) -> Dict[str, Any]:
        store = _read_json(SOLT_JSON, {})
        store[str(rfq_id)] = rec
        _write_json_atomic(SOLT_JSON, store)
        return rec

    @app.get("/api/rfq/<int:rfq_id>/solt")
    def get_solt(rfq_id: int):
        rec = _get_solt_record(rfq_id)
        # group lines by tab_index to match previous response shape
        grouped: Dict[int, List[Dict[str, Any]]] = {}
        for line in rec.get("lines", []):
            grouped.setdefault(int(line.get("tab_index", 0)), []).append(line)
        # sort lines within each group
        for k in grouped:
            grouped[k] = sorted(grouped[k], key=lambda x: (int(x.get("line_no", 0)), int(x.get("id", 0))))
        tabs = sorted(rec.get("tabs", []), key=lambda t: int(t.get("tab_index", 0)))
        return jsonify({"rfq_id": rfq_id, "tabs": tabs, "lines": grouped})

    @app.patch("/api/rfq/<int:rfq_id>/solt/tab/<int:tab_index>")
    def patch_solt_tab(rfq_id: int, tab_index: int):
        payload = request.get_json(force=True, silent=True) or {}
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name required"}), 400

        rec = _get_solt_record(rfq_id)
        tabs = rec.setdefault("tabs", [])
        tab = next((t for t in tabs if int(t.get("tab_index", -1)) == tab_index), None)
        if not tab:
            tab = {"tab_index": tab_index, "name": name}
            tabs.append(tab)
        else:
            tab["name"] = name
        _save_solt_record(rfq_id, rec)
        return jsonify(tab)

    @app.post("/api/rfq/<int:rfq_id>/solt/line")
    def add_solt_line(rfq_id: int):
        payload = request.get_json(force=True, silent=True) or {}
        tab_index = int(payload.get("tab_index", 0))
        item = payload.get("item")
        uom = payload.get("uom")
        currency = payload.get("currency")
        note = payload.get("note", "")

        def to_float(x):
            try:
                return float(x)
            except Exception:
                return 0.0

        qty_f = to_float(payload.get("qty"))
        unit_f = to_float(payload.get("unit_price"))
        total = qty_f * unit_f

        rec = _get_solt_record(rfq_id)
        lines = rec.setdefault("lines", [])

        # next line number in this tab
        existing = [l for l in lines if int(l.get("tab_index", 0)) == tab_index]
        line_no = (max([int(l.get("line_no", 0)) for l in existing], default=0) + 1)

        line_id = int(rec.get("next_line_id", 1))
        rec["next_line_id"] = line_id + 1

        new_line = {
            "id": line_id,
            "rfq_id": rfq_id,
            "tab_index": tab_index,
            "line_no": line_no,
            "item": item,
            "qty": qty_f,
            "uom": uom,
            "unit_price": unit_f,
            "currency": currency,
            "line_total": total,
            "note": note,
        }
        lines.append(new_line)
        _save_solt_record(rfq_id, rec)
        return jsonify(new_line), 201

    @app.patch("/api/rfq/<int:rfq_id>/solt/line/<int:line_id>")
    def patch_solt_line(rfq_id: int, line_id: int):
        payload = request.get_json(force=True, silent=True) or {}
        allowed = {"item","qty","uom","unit_price","currency","note","line_total","line_no","tab_index"}
        updates = {k: payload[k] for k in payload.keys() if k in allowed}
        if not updates:
            return jsonify({"error": "no valid fields"}), 400

        def to_float(x):
            try:
                return float(x)
            except Exception:
                return 0.0

        rec = _get_solt_record(rfq_id)
        lines = rec.setdefault("lines", [])
        line = next((l for l in lines if int(l.get("id", -1)) == line_id), None)
        if not line:
            return jsonify({"error": "not found"}), 404

        # apply updates
        for k, v in updates.items():
            line[k] = v

        # recalc line_total if qty/unit_price changed and caller didn't explicitly set line_total
        if "line_total" not in updates and ("qty" in updates or "unit_price" in updates):
            qty_f = to_float(line.get("qty"))
            unit_f = to_float(line.get("unit_price"))
            line["line_total"] = qty_f * unit_f

        _save_solt_record(rfq_id, rec)
        return jsonify(line)

    @app.delete("/api/rfq/<int:rfq_id>/solt/line/<int:line_id>")
    def delete_solt_line(rfq_id: int, line_id: int):
        rec = _get_solt_record(rfq_id)
        lines = rec.setdefault("lines", [])
        rec["lines"] = [l for l in lines if int(l.get("id", -1)) != line_id]
        _save_solt_record(rfq_id, rec)
        return jsonify({"ok": True})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5012, debug=True)
