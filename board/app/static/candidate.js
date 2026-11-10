// 候補者のページ。選考の段階の切り替えとメモの追加を API に送り、読み直す
(() => {
  const me = document.currentScript;
  const base = `/api/hiring/${encodeURIComponent(me.dataset.email)}`;
  const toast = document.getElementById("toast");
  const say = (msg, error = false) => {
    toast.textContent = msg;
    toast.className = "toast show" + (error ? " error" : "");
    setTimeout(() => (toast.className = "toast"), error ? 6000 : 2000);
  };
  async function post(path, body) {
    const res = await fetch(base + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Failed (${res.status})`);
  }
  document.querySelectorAll("[data-stage]").forEach((b) =>
    b.addEventListener("click", async () => {
      const stage = b.dataset.stage;
      if (!confirm(`段階を ${stage} にしますか。変えたことは記録に残ります`)) return;
      try {
        await post("/stage", { stage });
        location.reload();
      } catch (err) {
        say(err.message, true);
      }
    }),
  );
  document.querySelector("[data-memo]")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const ta = e.target.querySelector("textarea");
    try {
      await post("/memo", { body: ta.value });
      location.reload();
    } catch (err) {
      say(err.message, true);
    }
  });
})();
