(function () {
  const RFQ_ID = 1;
  const API = `/api/rfq/${RFQ_ID}`;
  let editOn = false;
  let cache = {};

  const normalizeText = (el) => (el.innerText || el.textContent || "").trim();

  function setText(el, value) {
    if (value == null) return;
    if (el.dataset.field === "grand_total") {
      const prefix = "Grand total:";
      const v = String(value).trim();
      el.textContent = v.startsWith(prefix) ? v : `${prefix} ${v}`;
      return;
    }
    el.textContent = String(value);
  }

  async function load() {
    const res = await fetch(API, { headers: { "Accept": "application/json" } });
    if (!res.ok) return;
    cache = await res.json();
    document.querySelectorAll("[data-field]").forEach(el => {
      const field = el.dataset.field;
      if (field in cache) setText(el, cache[field]);
    });
  }

  function setEditable(on) {
    editOn = on;
    document.querySelectorAll("[data-field]").forEach(el => {
      el.contentEditable = on ? "true" : "false";
      if (on) el.setAttribute("spellcheck", "false");
      else el.removeAttribute("spellcheck");
    });
    const btn = document.getElementById("rfqEditToggle");
    // Re-render Scope Order Lines so cells become editable/non-editable
    try { renderSolt(); } catch (e) {}
    if (btn) btn.dataset.on = on ? "1" : "0";
  }

  async function patch(field, value) {
    const res = await fetch(API, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ [field]: value })
    });
    if (res.ok) cache = await res.json();
  }

  function hookEdits() {
    document.querySelectorAll("[data-field]").forEach(el => {
      el.addEventListener("blur", async () => {
        if (!editOn) return;
        const field = el.dataset.field;
        const text = normalizeText(el);
        if (cache[field] !== text) await patch(field, text);
      }, true);
    });
  }

  function addToggle() {
    const btn = document.createElement("button");
    btn.id = "rfqEditToggle";
    btn.type = "button";
    btn.textContent = "Edit (E)";
    btn.dataset.on = "0";
    btn.addEventListener("click", () => setEditable(!editOn));
    document.body.appendChild(btn);

    document.addEventListener("keydown", (e) => {
      if (e.key.toLowerCase() === "e" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const tag = (document.activeElement && document.activeElement.tagName) ? document.activeElement.tagName.toLowerCase() : "";
        if (["input","textarea","select"].includes(tag)) return;
        setEditable(!editOn);
      }
    });
  }

  
  // ---------------- Scope Order Lines (tabs + subtable) ----------------
  let solt = null;
  let activeTab = 0;

  async function loadSolt() {
    const res = await fetch(`/api/rfq/${RFQ_ID}/solt`, { headers: { "Accept": "application/json" } });
    if (!res.ok) return;
    solt = await res.json();
    renderSolt();
  }

  function renderSolt() {
    const btns = document.getElementById("soltTabButtons");
    const tbody = document.getElementById("soltRows");
    if (!btns || !tbody || !solt) return;

    // Tabs
    btns.innerHTML = "";
    (solt.tabs || []).forEach((t, idx) => {
      const li = document.createElement("li");
      li.className = "solt-tabs__tab" + (t.tab_index === activeTab ? " solt-tabs__tab--active" : "");
      li.dataset.tabIndex = t.tab_index;

      const span = document.createElement("span");
      span.className = "tab-index";
      span.textContent = `Tab ${idx + 1}.`;
      li.appendChild(span);
      li.append(" " + t.name);

      li.addEventListener("click", () => {
        activeTab = t.tab_index;
        renderSolt();
      });

      // Rename tab in edit mode (double click)
      li.addEventListener("dblclick", async () => {
        if (!editOn) return;
        const name = prompt("Rename tab", t.name);
        if (!name) return;
        const r = await fetch(`/api/rfq/${RFQ_ID}/solt/tab/${t.tab_index}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json", "Accept": "application/json" },
          body: JSON.stringify({ name })
        });
        if (r.ok) {
          const updated = await r.json();
          t.name = updated.name;
          renderSolt();
        }
      });

      btns.appendChild(li);
    });

    // Rows for active tab
    const rows = (solt.lines && solt.lines[String(activeTab)]) ? solt.lines[String(activeTab)] : (solt.lines && solt.lines[activeTab]) ? solt.lines[activeTab] : [];
    tbody.innerHTML = "";
    if (!rows || rows.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 8;
      td.textContent = "No lines in this tab.";
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }

    rows.forEach((r) => {
      const tr = document.createElement("tr");
      tr.dataset.lineId = r.id;

      const tdNo = document.createElement("td");
      tdNo.className = "solt-cell solt-cell--line_no";
      tdNo.textContent = r.line_no ?? "";
      tr.appendChild(tdNo);

      function editableCell(field, value, isNumber=false) {
        const td = document.createElement("td");
        td.className = "solt-cell solt-cell--" + field;
        td.dataset.lineField = field;
        td.textContent = (value ?? "") + "";
        if (editOn) {
          td.contentEditable = "true";
          td.spellcheck = false;
          td.addEventListener("blur", async () => {
            const raw = normalizeText(td);
            const v = isNumber ? (raw === "" ? null : Number(raw)) : raw;
            await patchSoltLine(r.id, { [field]: v });
            await loadSolt(); // refresh totals
          }, { once: true });
        }
        return td;
      }

      tr.appendChild(editableCell("item", r.item));
      tr.appendChild(editableCell("mdf_code", r.mdf_code ?? "3FC"));
      tr.appendChild(editableCell("data_template", (r.data_template ?? "None")));
      tr.appendChild(editableCell("qty", r.qty, true));
      tr.appendChild(editableCell("uom", r.uom ?? "ea"));
      tr.appendChild(editableCell("unit_price", r.unit_price, true));
      tr.appendChild(editableCell("line_total", r.line_total, true));

      tbody.appendChild(tr);
    });
  }

  async function patchSoltLine(lineId, payload) {
    const res = await fetch(`/api/rfq/${RFQ_ID}/solt/line/${lineId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(payload)
    });
    return res.ok;
  }

addToggle();
  hookEdits();
  load();
  loadSolt();
})();
