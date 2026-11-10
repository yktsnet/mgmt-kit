// 現在地のタブ。Edit のあいだだけ Next axis を選べ、選ぶとすぐ保存する
(() => {
  document.querySelectorAll("select[data-growth]").forEach((sel) => {
    const before = sel.value;
    sel.addEventListener("change", async () => {
      const res = await fetch(`/api/growth/${sel.dataset.growth}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ axis: sel.value }),
      });
      if (res.ok) {
        sessionStorage.setItem("board-toast", "Saved");
        sessionStorage.setItem("board-editing", "next");
        location.reload();
      } else {
        sel.value = before;
        const data = await res.json().catch(() => ({}));
        alert(data.error || "Save failed");
      }
    });
  });
})();
