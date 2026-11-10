// 設定の画面でクリックして直す。保存は API に送り、シートへの書き戻しはサーバーが行う
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
    if (!res.ok) throw new Error(data.error || `保存できませんでした（${res.status}）`);
    return data;
  }

  // 書き戻したあとは、読み直した内容で描き直す。位置は保つ
  const reload = (msg) => {
    sessionStorage.setItem("board-toast", msg);
    sessionStorage.setItem("board-scroll", String(window.scrollY));
    location.reload();
  };
  const pending = sessionStorage.getItem("board-toast");
  if (pending) {
    window.scrollTo(0, Number(sessionStorage.getItem("board-scroll") || 0));
    sessionStorage.removeItem("board-toast");
    sessionStorage.removeItem("board-scroll");
    say(pending);
  }

  // ---- 定義
  const grid = document.querySelector("table.grid.editable");
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
    box.className = "item editing";
    box.innerHTML = `
      <label>判定文${key ? `（${key}）` : "（新しい細目）"}</label><textarea></textarea>
      <label>読むもの</label><input type="text">
      <div class="row">
        <button class="btn primary" type="button" data-do="save">保存</button>
        <button class="btn" type="button" data-do="cancel">やめる</button>
        ${key ? '<button class="btn danger" type="button" data-do="delete">削除</button>' : ""}
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
          reload("保存しました");
        } else if (act === "delete" && confirm(`細目 ${key} を消しますか`)) {
          await post("/api/definition/item/delete", { ...base, key });
          reload(`細目 ${key} を消しました`);
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
      const item = e.target.closest(".item:not(.editing)");
      if (item) return editor(item, item.dataset);
      const add = e.target.closest('[data-action="add-item"]');
      if (add) {
        const placeholder = document.createElement("span");
        add.before(placeholder);
        add.hidden = true;
        editor(placeholder, { key: "", text: "", evidence: "" }, () => (add.hidden = false));
      }
    });
    grid.addEventListener("keydown", (e) => {
      const item = e.target.closest(".item:not(.editing)");
      if (item && e.key === "Enter") editor(item, item.dataset);
    });
  }

  document.querySelector('[data-action="new-version"]')?.addEventListener("click", async () => {
    if (!confirm("最新の版を複製して、新しい版を作りますか。前の版は残ります")) return;
    try {
      const { result } = await post("/api/definition/version");
      location.href = `?v=${result}#definition`;
    } catch (err) {
      say(err.message, true);
    }
  });

  // ---- 担当
  document.querySelectorAll('select[data-action="evaluator"]').forEach((sel) => {
    const before = sel.value;
    sel.addEventListener("change", async () => {
      try {
        await post("/api/people/evaluator", { email: sel.dataset.email, evaluator: sel.value });
        reload("担当を書き戻しました");
      } catch (err) {
        sel.value = before;
        say(err.message, true);
      }
    });
  });

  // ---- 採用の枠
  document.querySelectorAll("tr[data-req]").forEach((tr) => {
    const btn = tr.querySelector('[data-action="save-req"]');
    tr.addEventListener("input", () => (btn.hidden = false));
    btn.addEventListener("click", async () => {
      const val = (n) => tr.querySelector(`input[name="${n}"]`).value;
      const target = Object.fromEntries(["A", "B", "C", "D", "E"].map((a) => [a, val(a) === "" ? null : Number(val(a))]));
      try {
        await post("/api/requisitions", { name: tr.dataset.req, count: Number(val("count") || 0), target });
        reload("採用の枠を書き戻しました");
      } catch (err) {
        say(err.message, true);
      }
    });
  });
})();
