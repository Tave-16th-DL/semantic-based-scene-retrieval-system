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

function toggleExpanded(itemEl) {
  itemEl.classList.toggle("expanded");
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

    setStatus(`결과 ${results.length}개`);

    results.forEach((r, idx) => {
      const item = document.createElement("div");
      item.className = "item";

      item.innerHTML = `
        <div class="itemTop">
          <div class="left">
            <span class="rank">#${r.rank}</span>
            <span class="time">${r.start_time}</span>
          </div>

          <div class="right">
            <span class="score">score ${Number(r.score).toFixed(4)}</span>
            <button class="toggleBtn" type="button" aria-label="설명 펼치기/접기" title="설명 펼치기/접기">
              &#9654;
            </button>
          </div>
        </div>

        <div class="title">${r.title || ""}</div>
      `;

      // 아이템(박스) 클릭: 이동 + 재생
      item.addEventListener("click", () => {
        setActive(idx);
        if (typeof player.fastSeek === "function") player.fastSeek(r.start_sec);
        else player.currentTime = r.start_sec;
        player.play();
      });

      // 세모 버튼 클릭: 설명 토글만 (이동/재생 이벤트 막기)
      const toggleBtn = item.querySelector(".toggleBtn");
      toggleBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        toggleExpanded(item);
      });

      resultsEl.appendChild(item);
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
