// 1人の評価のページ。状態の切り替えとメモの追加を API に送り、読み直す
(() => {
  const me = document.currentScript;
  const base = `/api/reviews/${encodeURIComponent(me.dataset.period)}/${encodeURIComponent(me.dataset.email)}`;
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
  const confirmText = {
    submit: "判定を出し終えたものとして Submit しますか",
    approve: "この評価を Approve しますか",
    reopen: "Draft に戻しますか。戻したことは記録に残ります",
  };
  document.querySelectorAll("[data-review-action]").forEach((b) =>
    b.addEventListener("click", async () => {
      const action = b.dataset.reviewAction;
      if (!confirm(confirmText[action])) return;
      try {
        await post("/action", { action });
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
