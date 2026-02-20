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

  addToggle();
  hookEdits();
  load();
})();
