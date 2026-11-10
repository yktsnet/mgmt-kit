// 設定の画面。区画ごとに Edit で編集に切り替え、Done で読む表示に戻す。設定はアプリが持ち、保存は API に送る
(() => {
  const toast = document.getElementById("toast");
  let timer;
  const say = (msg, error = false) => {
    toast.textContent = msg;
    toast.className = "toast show" + (error ? " error" : "");
    clearTimeout(timer);
    timer = setTimeout(() => (toast.className = "toast" + (error ? " error" : "")), error ? 6000 : 2000);
  };

  async function post(url, body) {
    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Save failed (${res.status})`);
    return data;
  }

  // 書き戻したあとは読み直した内容で描き直す。位置と、編集中だった区画は保つ
  const reload = (msg, keepEditing) => {
    sessionStorage.setItem("board-toast", msg);
    sessionStorage.setItem("board-scroll", String(window.scrollY));
    if (keepEditing) sessionStorage.setItem("board-editing", keepEditing);
    location.reload();
  };
  const pending = sessionStorage.getItem("board-toast");
  const reopen = sessionStorage.getItem("board-editing");
  ["board-toast", "board-editing"].forEach((k) => sessionStorage.removeItem(k));

  const setMode = (frame, editing) => {
    frame.classList.toggle("editing", editing);
    if (!editing) closeEditor();
  };
  document.querySelectorAll('.frame[data-editable="yes"]').forEach((frame) => {
    frame.querySelector('[data-action="edit"]')?.addEventListener("click", () => setMode(frame, true));
    frame.querySelectorAll('[data-action="done"]').forEach((b) =>
      b.addEventListener("click", () => {
        if (frame.id === "requisitions") return location.reload();
        setMode(frame, false);
      }),
    );
    if (reopen === frame.id) setMode(frame, true);
  });
  if (pending) {
    window.scrollTo(0, Number(sessionStorage.getItem("board-scroll") || 0));
    sessionStorage.removeItem("board-scroll");
    say(pending);
  }

  // ---- Ladder
  const ladder = document.getElementById("definition");
  const grid = ladder?.querySelector("table.grid");
  const version = grid ? Number(grid.dataset.version) : null;
  let open = null;

  function closeEditor() {
    if (!open) return;
    open.restore();
    open = null;
  }

  function editor(host, { key, text, evidence }, onRestore) {
    closeEditor();
    const cell = host.closest("td");
    const box = document.createElement("div");
    box.className = "item form";
    box.innerHTML = `
      <label>${key ? `${key} の判定文` : "新しい判定文"}</label><textarea></textarea>
      <label>Evidence</label><input type="text">
      <div class="row">
        <button class="btn primary" type="button" data-do="save">Save</button>
        <button class="btn" type="button" data-do="cancel">Cancel</button>
        ${key ? '<button class="btn danger" type="button" data-do="delete">Delete</button>' : ""}
      </div>`;
    const [ta, ev] = [box.querySelector("textarea"), box.querySelector("input")];
    ta.value = text;
    ev.value = evidence;
    host.replaceWith(box);
    ta.focus();
    const base = { version, axis: cell.dataset.axis, level: Number(cell.dataset.level) };
    open = { restore: () => { box.replaceWith(host); onRestore?.(); } };
    box.addEventListener("click", async (e) => {
      const act = e.target.dataset.do;
      if (!act) return;
      if (act === "cancel") return closeEditor();
      try {
        if (act === "save") {
          await post("/api/definition/item", { ...base, key: key || null, text: ta.value, evidence: ev.value });
          reload("Saved", "definition");
        } else if (act === "delete" && confirm(`${cell.dataset.axis}-L${cell.dataset.level} の ${key} を消しますか`)) {
          await post("/api/definition/item/delete", { ...base, key });
          reload("Deleted", "definition");
        }
      } catch (err) {
        say(err.message, true);
      }
    });
    box.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeEditor();
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) box.querySelector('[data-do="save"]').click();
    });
  }

  if (grid) {
    grid.addEventListener("click", (e) => {
      if (!ladder.classList.contains("editing")) return;
      const item = e.target.closest(".item:not(.form)");
      if (item) return editor(item, item.dataset);
      const add = e.target.closest('[data-action="add-item"]');
      if (add) {
        const placeholder = document.createElement("span");
        add.before(placeholder);
        add.hidden = true;
        editor(placeholder, { key: "", text: "", evidence: "" }, () => (add.hidden = false));
      }
    });
  }

  ladder?.querySelector('[data-action="new-version"]')?.addEventListener("click", async () => {
    if (!confirm("いまの版を複製して、次の版を作りますか。いまの版は残ります")) return;
    try {
      const { result } = await post("/api/definition/version");
      sessionStorage.setItem("board-editing", "definition");
      location.href = `?v=${result}#definition`;
    } catch (err) {
      say(err.message, true);
    }
  });

  // ---- Reviewer と Role と Hiring
  document.querySelectorAll('select[data-action="evaluator"], select[data-action="role"]').forEach((sel) => {
    const before = sel.value;
    sel.addEventListener("change", async () => {
      const field = sel.dataset.action === "role" ? "role" : "evaluator";
      try {
        await post("/api/people", { email: sel.dataset.email, [field]: sel.value });
        reload("Saved", "people");
      } catch (err) {
        sel.value = before;
        say(err.message, true);
      }
    });
  });
  document.querySelectorAll('input[data-action="hiring"]').forEach((box) => {
    box.addEventListener("change", async () => {
      try {
        await post("/api/people", { email: box.dataset.email, hiring: box.checked });
        reload("Saved", "people");
      } catch (err) {
        box.checked = !box.checked;
        say(err.message, true);
      }
    });
  });

  // ---- Openings：行をまとめて Save で送る
  document.querySelector('#requisitions [data-action="save-req"]')?.addEventListener("click", async () => {
    try {
      for (const tr of document.querySelectorAll("tr[data-req]")) {
        const val = (n) => tr.querySelector(`input[name="${n}"]`).value;
        const target = Object.fromEntries(["A", "B", "C", "D", "E"].map((a) => [a, val(a) === "" ? null : Number(val(a))]));
        await post("/api/requisitions", { name: tr.dataset.req, count: Number(val("count") || 0), target });
      }
      reload("Saved");
    } catch (err) {
      say(err.message, true);
    }
  });
})();
