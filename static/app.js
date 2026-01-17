const player = document.getElementById("player");
const resultsEl = document.getElementById("results");
const statusEl = document.getElementById("status");
const qEl = document.getElementById("q");
const btnEl = document.getElementById("btn");

let activeIdx = -1;

function setStatus(msg) {
  statusEl.textContent = msg;
}

function clearResults() {
  resultsEl.innerHTML = "";
  activeIdx = -1;
}

function setActive(i) {
  const items = resultsEl.querySelectorAll(".item");
  items.forEach((el, idx) => el.classList.toggle("active", idx === i));
  activeIdx = i;
}

async function search() {
  const q = (qEl.value || "").trim();
  if (!q) return;

  setStatus("검색 중...");
  clearResults();

  try {
    const res = await fetch("/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q, top_k: 5 }),
    });

    if (!res.ok) {
      setStatus(`서버 오류: ${res.status}`);
      return;
    }

    const data = await res.json();
    const results = data.results || [];

    if (results.length === 0) {
      setStatus("검색 결과가 없습니다.");
      return;
    }

    setStatus(`결과 ${results.length}개 (클릭하면 해당 시작 시간으로 이동)`);

    results.forEach((r, idx) => {
      const div = document.createElement("div");
      div.className = "item";

      div.innerHTML = `
        <div class="itemTop">
          <div>
            <span class="rank">#${r.rank}</span>
            <span class="time">${r.start_time}</span>
          </div>
          <div class="score">score ${Number(r.score).toFixed(4)}</div>
        </div>
        <div class="title">${(r.title || "").slice(0, 90)}</div>
      `;

      div.addEventListener("click", () => {
        setActive(idx);
        // ✅ start_time만 사용해서 점프 후 계속 재생
        if (typeof player.fastSeek === "function") player.fastSeek(r.start_sec);
        else player.currentTime = r.start_sec;
        player.play();
      });

      resultsEl.appendChild(div);
    });

  } catch (e) {
    console.error(e);
    setStatus("네트워크/클라이언트 오류가 발생했습니다.");
  }
}

btnEl.addEventListener("click", search);
qEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") search();
});
