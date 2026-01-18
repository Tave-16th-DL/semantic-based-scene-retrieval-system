const player = document.getElementById("player");
const resultsEl = document.getElementById("results");
const statusEl = document.getElementById("status");
const qEl = document.getElementById("q");
const btnEl = document.getElementById("btn");

let activeIdx = -1;

// 검색 요청 겹침 방지용
let reqSeq = 0;
let controller = null;
let isSearching = false;

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

function setLoading(on) {
  isSearching = on;
  btnEl.disabled = on;
  btnEl.textContent = on ? "검색중..." : "검색";
}

function dedupeResults(results) {
  // shot_id가 있으면 그걸로, 없으면 start_sec로 중복 제거
  const seen = new Set();
  const out = [];
  for (const r of results) {
    const key =
      (r.shot_id != null ? `sid:${r.shot_id}` : null) ??
      (r.start_sec != null ? `t:${r.start_sec}` : null) ??
      `rank:${r.rank}-score:${r.score}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(r);
  }
  return out;
}

async function search() {
  const q = (qEl.value || "").trim();
  if (!q) return;

  // 이미 검색중이면, 이전 요청을 취소하고 새 요청으로 교체
  if (controller) controller.abort();
  controller = new AbortController();

  const mySeq = ++reqSeq;

  setLoading(true);
  setStatus("검색 중...");

  try {
    const res = await fetch("/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q, top_k: 5 }),
      signal: controller.signal,
    });

    if (mySeq !== reqSeq) return;

    if (!res.ok) {
      clearResults();
      setStatus(`서버 오류: ${res.status}`);
      return;
    }

    const data = await res.json();

    if (mySeq !== reqSeq) return;

    let results = data.results || [];
    results = dedupeResults(results);

    clearResults();

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
        <div class="title"></div>
      `;

      // title 안전 주입
      item.querySelector(".title").textContent = r.title || "";

      // 박스 클릭: 이동 + 재생
      item.addEventListener("click", () => {
        setActive(idx);
        if (typeof player.fastSeek === "function") player.fastSeek(r.start_sec);
        else player.currentTime = r.start_sec;
        player.play();
      });

      // 세모 클릭: 토글만 (이동/재생 이벤트 막기)
      const toggleBtn = item.querySelector(".toggleBtn");
      toggleBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        item.classList.toggle("expanded");
      });

      resultsEl.appendChild(item);
    });
  } catch (e) {
    if (e.name === "AbortError") {
      // 이전 요청 취소는 정상 동작
      return;
    }
    console.error(e);
    clearResults();
    setStatus("네트워크/클라이언트 오류가 발생했습니다.");
  } finally {
    // 최신 요청일 때만 로딩 해제
    if (mySeq === reqSeq) setLoading(false);
  }
}

btnEl.addEventListener("click", () => {
  // 더블클릭 방지
  if (!isSearching) search();
});

qEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !isSearching) search();
});
