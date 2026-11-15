/* Worlds 2026 • #bunkier Static Archive App (Zero live polling) */

const DAYS = [
  { id: 'day-1', label: 'Dzień 1 (03.11)' },
  { id: 'day-2', label: 'Dzień 2 (04.11)' },
  { id: 'day-3', label: 'Dzień 3 (05.11)' },
  { id: 'day-4', label: 'Dzień 4 (06.11)' },
  { id: 'day-5', label: 'Dzień 5 (07.11)' },
  { id: 'day-6', label: 'Dzień 6 (08.11)' },
  { id: 'day-7', label: 'Finał (14.11)' },
];

const CAROUSEL_SLIDES = [
  { src: 'carousel/carousel_1_turniej_kpi.png', title: '1/6 • Podsumowanie Turnieju (KPI & 3 obozy)' },
  { src: 'carousel/carousel_2_turniej_mecze.png', title: '2/6 • Wszystkie 7 meczów BO5 (Mecz po meczu)' },
  { src: 'carousel/carousel_3_final_14_11.png', title: '3/6 • Wielki Finał 14.11 (BLG 3:1 Gen.G)' },
  { src: 'carousel/carousel_4_x_kpi.png', title: '4/6 • Akcja #bunkier na X (Zasięg & aktywność)' },
  { src: 'carousel/carousel_5_x_top_autorzy.png', title: '5/6 • #bunkier na X — TOP 10 Autorów' },
  { src: 'carousel/carousel_6_x_top_posty.png', title: '6/6 • #bunkier na X — TOP 5 Postów' },
];

const CLASSIC_BOARDS = [
  { src: 'tournament_summary.png', title: 'Podsumowanie Turnieju (1–7)' },
  { src: 'finals_summary.png', title: 'Wielki Finał (14.11)' },
  { src: 'semis_summary.png', title: 'Półfinały (5–6)' },
  { src: 'quarters_summary.png', title: 'Ćwierćfinały (1–4)' },
  { src: 'x_bunkier_summary.png', title: '#bunkier na X (31.10–15.11)' },
  { src: 'x_bunkier_top10.png', title: '#bunkier na X — TOP 10' },
];

const state = {
  view: 'turniej',
  stageId: 'tournament',
  stageMetric: 'peak',
  dayId: 'day-7',
  dayPreset: 'camps_3',
  carouselIdx: 0,
  tournamentData: null,
  xData: null,
  dayCache: {},
  charts: { stage: null, day: null, xDaily: null },
};

const fmt = (n) => Math.round(Number(n) || 0).toLocaleString('pl-PL');
const esc = (s) =>
  String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

async function fetchJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${path}`);
  return res.json();
}

/* --- ROUTER --- */
function switchView(viewId, updateHash = true) {
  state.view = viewId;
  if (updateHash && location.hash !== `#${viewId}`) {
    history.replaceState(null, '', `#${viewId}`);
  }
  document.querySelectorAll('.nav-btn').forEach((b) => {
    b.classList.toggle('active', b.dataset.view === viewId);
  });
  document.querySelectorAll('.view-section').forEach((sec) => {
    sec.classList.toggle('active', sec.id === `view-${viewId}`);
  });

  if (viewId === 'turniej') loadAndRenderTournament();
  if (viewId === 'dni') loadAndRenderDay(state.dayId);
  if (viewId === 'x') loadAndRenderX();
  if (viewId === 'galeria') renderGallery();
}

/* --- VIEW 1: TOURNAMENT & STAGES --- */
async function loadAndRenderTournament() {
  if (!state.tournamentData) {
    state.tournamentData = await fetchJson('./tournament_analytics.json');
  }
  renderStage(state.stageId);
}

function selectStage(stageId) {
  state.stageId = stageId;
  document.querySelectorAll('[data-stage]').forEach((b) => {
    b.classList.toggle('active', b.dataset.stage === stageId);
  });
  renderStage(stageId);
}

function selectStageMetric(metric) {
  state.stageMetric = metric;
  document.querySelectorAll('[data-stage-metric]').forEach((b) => {
    b.classList.toggle('active', b.dataset.stageMetric === metric);
  });
  if (state.tournamentData) renderStageChart(state.tournamentData.stages[state.stageId]);
}

function renderStage(stageId) {
  const stage = state.tournamentData?.stages?.[stageId];
  if (!stage) return;

  document.getElementById('stage-title').innerText = `${stage.icon || '🏆'} ${stage.name}`;
  document.getElementById('stage-sub').innerText =
    `${stage.subtitle || ''} • Próbki telemetryczne: ${fmt(stage.total_points)}`;

  const pngMap = {
    tournament: 'tournament_summary.png',
    quarters: 'quarters_summary.png',
    semis: 'semis_summary.png',
    finals: 'finals_summary.png',
  };
  const pngFile = pngMap[stageId] || 'tournament_summary.png';
  const btnPng = document.getElementById('stage-open-png');
  btnPng.onclick = () => openLightbox(pngFile, `${stage.name} — Infografika`);

  const ms = stage.market_share || {};
  document.getElementById('t-kpi-watch').innerText = `${fmt(stage.total_watch_hours)} h`;
  document.getElementById('t-kpi-watch-sub').innerText = `${stage.matches_count} meczów BO5 • 3 główne obozy`;
  document.getElementById('t-kpi-peak').innerText = fmt(stage.total_scene_peak);
  document.getElementById('t-kpi-peak-sub').innerText = `Mecz: ${stage.total_scene_peak_match || '--'}`;
  document.getElementById('t-kpi-share').innerText = `${(ms.goe ?? 0).toFixed(1)}%`;
  document.getElementById('t-kpi-share-sub').innerText = `${fmt(stage.goe?.watch_hours)} h watch-time Bunkra`;
  document.getElementById('t-kpi-avg').innerText = fmt(stage.goe?.live_avg);
  document.getElementById('t-kpi-avg-sub').innerText = `Na antenie: ${(stage.goe?.duration_hours ?? 0).toFixed(1)} h`;

  // 3-camp cards
  const camps = [
    { key: 'goe', cls: 'goe', title: 'Kielecki Bunkier (GoE)', color: '#ff1824', data: stage.goe, share: ms.goe },
    { key: 'nerva', cls: 'nerva', title: 'Nervarien & Co-streamy', color: '#3b82f6', data: stage.nerva, share: ms.nerva },
    { key: 'tobias', cls: 'tobias', title: 'Tobiasz', color: '#f97316', data: stage.tobias, share: ms.tobias },
  ];
  document.getElementById('stage-camps-grid').innerHTML = camps
    .map(
      (c) => `
      <div class="camp-card ${c.cls}">
        <div class="camp-head">
          <div class="camp-name" style="color:${c.color}">${esc(c.title)}</div>
          <div class="camp-share" style="color:${c.color}">${(c.share ?? 0).toFixed(1)}%</div>
        </div>
        <div class="camp-stats">
          <div><div class="camp-stat-lbl">Watch-time</div><div class="camp-stat-val">${fmt(c.data?.watch_hours)} h</div></div>
          <div><div class="camp-stat-lbl">Pik</div><div class="camp-stat-val">${fmt(c.data?.peak)}</div></div>
          <div><div class="camp-stat-lbl">Śr. live</div><div class="camp-stat-val">${fmt(c.data?.live_avg)}</div></div>
        </div>
      </div>`
    )
    .join('');

  // YT vs Twitch split
  const gp = stage.goe_platforms || {};
  const ytShare = gp.yt_share ?? 0;
  const twShare = gp.tw_share ?? 0;
  document.getElementById('stage-yt-tw-label').innerText = `YouTube ${ytShare.toFixed(1)}% • Twitch ${twShare.toFixed(1)}%`;
  document.getElementById('stage-yt-seg').style.width = `${ytShare}%`;
  document.getElementById('stage-tw-seg').style.width = `${twShare}%`;
  document.getElementById('stage-yt-tw-sub').innerText =
    `YT: ${fmt(gp.yt_watch_hours)} h (pik ${fmt(gp.yt_peak)})  •  Twitch: ${fmt(gp.tw_watch_hours)} h (pik ${fmt(gp.tw_peak)})`;

  renderStageChart(stage);

  // Matches table
  document.getElementById('stage-matches-body').innerHTML = (stage.matches || [])
    .map(
      (m) => `
      <tr>
        <td><strong>${esc(m.name)}</strong><br><span style="color:var(--muted);font-size:12px;">${esc(m.match)}</span></td>
        <td><strong>${esc(m.score)}</strong></td>
        <td>${esc(m.winner)}</td>
        <td><strong style="color:var(--cyan)">${fmt(m.total_peak)}</strong> <span style="color:var(--muted);font-size:12px;">(${esc(m.total_peak_time)})</span></td>
        <td>${fmt(m.goe?.peak)}</td>
        <td>${fmt(m.goe?.live_avg)}</td>
        <td>${fmt(m.goe?.watch_hours)} h</td>
        <td><strong>${(m.market_share?.goe ?? 0).toFixed(1)}%</strong></td>
        <td><button class="pill-btn" onclick="openDayFromTable('${esc(m.day_id)}')">Szczegóły →</button></td>
      </tr>`
    )
    .join('');
}

function renderStageChart(stage) {
  const ctx = document.getElementById('stageChart')?.getContext('2d');
  if (!ctx || !stage) return;
  if (state.charts.stage) state.charts.stage.destroy();

  const matches = stage.matches || [];
  const metric = state.stageMetric;
  const getVal = (obj) => (obj ? obj[metric] || 0 : 0);

  state.charts.stage = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: matches.map((m) => m.match_short || m.name),
      datasets: [
        { label: 'Bunkier GoE', data: matches.map((m) => getVal(m.goe)), backgroundColor: '#ff1824', borderRadius: 5 },
        { label: 'Nervarien & Co-streamy', data: matches.map((m) => getVal(m.nerva)), backgroundColor: '#3b82f6', borderRadius: 5 },
        { label: 'Tobiasz', data: matches.map((m) => getVal(m.tobias)), backgroundColor: '#f97316', borderRadius: 5 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#f4f4f8', font: { family: 'Outfit' } } } },
      scales: {
        x: { ticks: { color: '#9ca3af' }, grid: { display: false } },
        y: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.06)' } },
      },
    },
  });
}

function openDayFromTable(dayId) {
  state.dayId = dayId;
  switchView('dni');
}

/* --- VIEW 2: DAY BY DAY --- */
function initDayButtons() {
  const container = document.getElementById('day-pills');
  container.innerHTML = DAYS.map(
    (d) => `<button class="pill-btn" data-day="${d.id}" onclick="selectDay('${d.id}')">${esc(d.label)}</button>`
  ).join('');
}

function selectDay(dayId) {
  state.dayId = dayId;
  loadAndRenderDay(dayId);
}

function selectDayPreset(preset) {
  state.dayPreset = preset;
  document.querySelectorAll('[data-preset]').forEach((b) => {
    b.classList.toggle('active', b.dataset.preset === preset);
  });
  const cached = state.dayCache[state.dayId];
  if (cached) renderDayChart(cached.history, cached.data);
}

async function loadAndRenderDay(dayId) {
  document.querySelectorAll('[data-day]').forEach((b) => {
    b.classList.toggle('active', b.dataset.day === dayId);
  });

  if (!state.dayCache[dayId]) {
    const [data, history] = await Promise.all([
      fetchJson(`./data_${dayId}.json`),
      fetchJson(`./history_${dayId}.json`),
    ]);
    state.dayCache[dayId] = { data, history };
  }

  const { data, history } = state.dayCache[dayId];
  const st = data.summary_stats || {};

  document.getElementById('day-title').innerText = `${data.day_name || dayId} • ${data.match || ''} (${data.score || ''})`;
  document.getElementById('day-sub').innerText =
    `Zwycięzca: ${data.winner || '--'} • Okno live: ${st.start_time || '--'} – ${st.end_time || '--'} CET • Próbek: ${fmt(history.length)}`;

  document.getElementById('day-open-camps').onclick = () =>
    openLightbox(`camps_summary_${dayId}.png`, `${data.day_name} — 3 Obozy`);
  document.getElementById('day-open-goe').onclick = () =>
    openLightbox(`goe_summary_${dayId}.png`, `${data.day_name} — Bunkier GoE`);
  document.getElementById('day-csv-link').href = `./stream_data_${dayId}.csv`;

  const nervaPeak = st.nerva_camp_peak || st.nerva_peak || 0;
  const nervaPeakTime = st.nerva_camp_peak_time || st.nerva_peak_time || '--';
  document.getElementById('d-kpi-scene').innerText = fmt(st.camp_peak);
  document.getElementById('d-kpi-scene-sub').innerText = `Szczyt sceny o ${st.camp_peak_time || '--'}`;
  document.getElementById('d-kpi-goe').innerText = fmt(st.goe_peak);
  document.getElementById('d-kpi-goe-sub').innerText = `Śr. ${fmt(st.goe_live_avg)} • ${fmt(st.goe_watch_hours)} h`;
  document.getElementById('d-kpi-nerva').innerText = fmt(nervaPeak);
  document.getElementById('d-kpi-nerva-sub').innerText = `Pik ${nervaPeakTime} • Śr. ${fmt(st.nerva_live_avg)} • ${fmt(st.nerva_watch_hours)} h`;
  document.getElementById('d-kpi-tobias').innerText = fmt(st.tobias_peak);
  document.getElementById('d-kpi-tobias-sub').innerText = st.tobias_peak > 0 ? `Śr. ${fmt(st.tobias_live_avg)} • ${fmt(st.tobias_watch_hours)} h` : 'Offline w tym dniu';

  const discBox = document.getElementById('day-disclaimers');
  const discs = data.disclaimers || [];
  if (discs.length) {
    discBox.style.display = 'block';
    discBox.innerHTML = `<strong>Adnotacje danych:</strong><br>${discs.map((x) => `• ${esc(x)}`).join('<br>')}`;
  } else {
    discBox.style.display = 'none';
  }

  renderDayChart(history, data);
}

function renderDayChart(history, data) {
  const ctx = document.getElementById('dayChart')?.getContext('2d');
  if (!ctx || !history?.length) return;
  if (state.charts.day) state.charts.day.destroy();

  // Downsample smoothly to ~220 points for fast interactive rendering
  const maxPts = 220;
  const step = Math.max(1, Math.floor(history.length / maxPts));
  const pts = history.filter((_, idx) => idx % step === 0 || idx === history.length - 1);
  const labels = pts.map((p) => (p.timestamp || '').split(' ').pop().slice(0, 5));

  const getTobias = (p) => p.streams?.ttobias_lol?.viewers || 0;
  const getGoeYt = (p) => Math.max(0, (p.goe_total || 0) - (p.streams?.goe_stream?.viewers || 0));
  const getGoeTw = (p) => p.streams?.goe_stream?.viewers || 0;

  let datasets = [];
  if (state.dayPreset === 'camps_3') {
    datasets = [
      { label: 'Bunkier GoE', data: pts.map((p) => p.goe_total || 0), borderColor: '#ff1824', backgroundColor: 'rgba(255,24,36,0.12)', fill: true, tension: 0.25, pointRadius: 0, borderWidth: 2.5 },
      { label: 'Nervarien & Co-streamy', data: pts.map((p) => p.nerva_total || 0), borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.08)', fill: true, tension: 0.25, pointRadius: 0, borderWidth: 2.5 },
      { label: 'Tobiasz', data: pts.map(getTobias), borderColor: '#f97316', tension: 0.25, pointRadius: 0, borderWidth: 2 },
    ];
  } else if (state.dayPreset === 'goe_only') {
    datasets = [
      { label: 'GoE Łącznie', data: pts.map((p) => p.goe_total || 0), borderColor: '#ff1824', tension: 0.25, pointRadius: 0, borderWidth: 2.5 },
      { label: 'GoE YouTube', data: pts.map(getGoeYt), borderColor: '#ef4444', borderDash: [5, 4], tension: 0.25, pointRadius: 0, borderWidth: 2 },
      { label: 'GoE Twitch', data: pts.map(getGoeTw), borderColor: '#9146ff', tension: 0.25, pointRadius: 0, borderWidth: 2 },
    ];
  } else if (state.dayPreset === 'battle_2v2') {
    datasets = [
      { label: 'Bunkier GoE', data: pts.map((p) => p.goe_total || 0), borderColor: '#ff1824', tension: 0.25, pointRadius: 0, borderWidth: 2.5 },
      { label: 'Nervarien & Co-streamy', data: pts.map((p) => p.nerva_total || 0), borderColor: '#3b82f6', tension: 0.25, pointRadius: 0, borderWidth: 2.5 },
    ];
  } else {
    datasets = [
      { label: 'Łącznie cała scena', data: pts.map((p) => (p.goe_total || 0) + (p.nerva_total || 0) + getTobias(p)), borderColor: '#22d3ee', tension: 0.25, pointRadius: 0, borderWidth: 2.5 },
      { label: 'Bunkier GoE', data: pts.map((p) => p.goe_total || 0), borderColor: '#ff1824', tension: 0.25, pointRadius: 0, borderWidth: 2 },
      { label: 'Nervarien', data: pts.map((p) => p.nerva_total || 0), borderColor: '#3b82f6', tension: 0.25, pointRadius: 0, borderWidth: 2 },
      { label: 'Tobiasz', data: pts.map(getTobias), borderColor: '#f97316', tension: 0.25, pointRadius: 0, borderWidth: 2 },
    ];
  }

  state.charts.day = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { labels: { color: '#f4f4f8', font: { family: 'Outfit' } } } },
      scales: {
        x: { ticks: { color: '#9ca3af', maxTicksLimit: 10 }, grid: { display: false } },
        y: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.06)' } },
      },
    },
  });
}

/* --- VIEW 3: X (#BUNKIER) --- */
async function loadAndRenderX() {
  if (!state.xData) {
    state.xData = await fetchJson('./x_bunkier_analytics.json');
  }
  const xa = state.xData;
  const tot = xa.totals || {};
  const grp = xa.groups || {};
  const dr = xa.date_range || {};

  document.getElementById('x-title').innerText = `𝕏 AKCJA #BUNKIER NA X (${dr.start_label || '31.10'} – ${dr.end_label || '15.11'})`;
  document.getElementById('x-kpi-posts').innerText = fmt(tot.posts);
  document.getElementById('x-kpi-posts-sub').innerText = `${fmt(tot.hashtag_posts)} z #bunkier • +${tot.non_hashtag_posts || 0} Worlds`;
  document.getElementById('x-kpi-views').innerText = fmt(tot.views);
  document.getElementById('x-kpi-authors').innerText = fmt(tot.unique_authors);
  document.getElementById('x-kpi-authors-sub').innerText = `${grp.bunkier?.unique_authors || 0} Bunkier • ${grp.community?.unique_authors || 0} Społeczność`;
  document.getElementById('x-kpi-int').innerText = fmt(tot.interactions);
  document.getElementById('x-kpi-int-sub').innerText = `ER ${tot.engagement_rate_pct || 0}% • ${fmt(tot.likes)} polubień`;

  const pB = grp.bunkier?.posts_pct || 0;
  const pC = grp.community?.posts_pct || 0;
  const vB = grp.bunkier?.views_pct || 0;
  const vC = grp.community?.views_pct || 0;
  document.getElementById('x-split-posts-lbl').innerText = `Bunkier ${pB}% • Społeczność ${pC}%`;
  document.getElementById('x-split-posts-b').style.width = `${pB}%`;
  document.getElementById('x-split-posts-c').style.width = `${pC}%`;
  document.getElementById('x-split-views-lbl').innerText = `Bunkier ${vB}% • Społeczność ${vC}%`;
  document.getElementById('x-split-views-b').style.width = `${vB}%`;
  document.getElementById('x-split-views-c').style.width = `${vC}%`;

  const ctx = document.getElementById('xDailyChart')?.getContext('2d');
  const daily = xa.daily || [];
  if (ctx) {
    if (state.charts.xDaily) state.charts.xDaily.destroy();
    state.charts.xDaily = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: daily.map((d) => d.label),
        datasets: [{
          label: 'Posty',
          data: daily.map((d) => d.posts),
          backgroundColor: daily.map((d) => (d.is_match_day ? '#ff1824' : '#3b82f6')),
          borderRadius: 5,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel: (c) => {
                const d = daily[c.dataIndex];
                return [`Wyświetlenia: ${fmt(d.views)}`, `Interakcje: ${fmt(d.interactions)}`];
              },
            },
          },
        },
        scales: {
          x: { ticks: { color: '#9ca3af' }, grid: { display: false } },
          y: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.06)' } },
        },
      },
    });
  }

  const totViews = Math.max(1, tot.views || 1);
  document.getElementById('x-authors-body').innerHTML = (xa.top_authors || []).slice(0, 10).map((a, idx) => {
    const isB = a.role === 'bunkier';
    return `<tr>
      <td><strong>#${idx + 1}</strong></td>
      <td><a href="https://x.com/${esc(a.handle)}" target="_blank" rel="noopener" style="color:${isB ? '#ff4d5a' : '#60a5fa'};font-weight:700;text-decoration:none;">@${esc(a.handle)}</a></td>
      <td>${isB ? 'Bunkier' : 'Społeczność'}</td>
      <td>${a.posts} (${a.hashtag_posts} #)</td>
      <td><strong style="color:var(--cyan)">${fmt(a.views)}</strong></td>
      <td>${fmt(a.interactions)}</td>
      <td>${((a.views / totViews) * 100).toFixed(1)}%</td>
    </tr>`;
  }).join('');

  document.getElementById('x-posts-body').innerHTML = (xa.top_posts || []).slice(0, 10).map((p, idx) => {
    const isB = p.role === 'bunkier';
    const txt = (p.display_text || p.text || '').replace(/\s+/g, ' ').trim();
    const shortTxt = txt.length > 110 ? `${txt.slice(0, 107)}...` : txt;
    return `<tr>
      <td><strong>#${idx + 1}</strong></td>
      <td><strong style="color:${isB ? '#ff4d5a' : '#60a5fa'};">@${esc(p.author_handle)}</strong><br><span style="color:var(--muted);font-size:12px;">${esc(p.date_label)} • ${esc(p.time_pl)}</span></td>
      <td style="max-width:420px;line-height:1.35;">${esc(shortTxt)}</td>
      <td><strong style="color:var(--cyan)">${fmt(p.views)}</strong></td>
      <td>${fmt(p.likes)} 👍 • ${p.reposts} 🔁 • ${p.replies} 💬</td>
      <td><a class="pill-btn" href="${esc(p.url)}" target="_blank" rel="noopener">Otwórz</a></td>
    </tr>`;
  }).join('');
}

/* --- VIEW 4: CAROUSEL & GALLERY --- */
function setCarouselSlide(idx) {
  state.carouselIdx = (idx + CAROUSEL_SLIDES.length) % CAROUSEL_SLIDES.length;
  const slide = CAROUSEL_SLIDES[state.carouselIdx];
  const img = document.getElementById('carousel-main-img');
  img.src = slide.src;
  img.alt = slide.title;
  img.onclick = () => openLightbox(slide.src, slide.title);
  document.getElementById('carousel-caption').innerText = slide.title;
  const dl = document.getElementById('carousel-download');
  dl.href = slide.src;
  dl.download = slide.src.split('/').pop();

  document.querySelectorAll('.thumb-btn').forEach((btn, i) => {
    btn.classList.toggle('active', i === state.carouselIdx);
  });
}

function renderGallery() {
  const thumbs = document.getElementById('carousel-thumbs');
  if (!thumbs.dataset.built) {
    thumbs.dataset.built = '1';
    thumbs.innerHTML = CAROUSEL_SLIDES.map(
      (s, i) => `
      <button class="thumb-btn" onclick="setCarouselSlide(${i})">
        <img src="${esc(s.src)}" alt="${esc(s.title)}" loading="lazy" />
        <span>Slajd ${i + 1}/6</span>
      </button>`
    ).join('');

    document.getElementById('classic-gallery-grid').innerHTML = CLASSIC_BOARDS.map(
      (b) => `
      <div class="gallery-card">
        <img src="${esc(b.src)}" alt="${esc(b.title)}" loading="lazy" onclick="openLightbox('${esc(b.src)}', '${esc(b.title)}')" />
        <div class="gallery-card-foot">
          <div class="gallery-card-title">${esc(b.title)}</div>
          <a class="pill-btn" href="${esc(b.src)}" download>📥 PNG</a>
        </div>
      </div>`
    ).join('');
  }
  setCarouselSlide(state.carouselIdx);
}

/* --- LIGHTBOX --- */
function openLightbox(src, title) {
  const dlg = document.getElementById('lightbox');
  const img = document.getElementById('lightbox-img');
  const ttl = document.getElementById('lightbox-title');
  const dl = document.getElementById('lightbox-dl');
  img.src = src;
  img.alt = title;
  ttl.innerText = title;
  dl.href = src;
  dl.download = src.split('/').pop();
  dlg.showModal();
}

function closeLightbox() {
  document.getElementById('lightbox').close();
}

/* --- INIT --- */
document.addEventListener('DOMContentLoaded', () => {
  initDayButtons();

  // Swipe support for carousel viewport
  let touchX = 0;
  const vp = document.getElementById('carousel-viewport');
  vp.addEventListener('touchstart', (e) => { touchX = e.changedTouches[0].clientX; }, { passive: true });
  vp.addEventListener('touchend', (e) => {
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 40) setCarouselSlide(state.carouselIdx + (dx < 0 ? 1 : -1));
  }, { passive: true });

  // Keyboard navigation in gallery or lightbox
  document.addEventListener('keydown', (e) => {
    if (document.getElementById('lightbox').open) {
      if (e.key === 'Escape') closeLightbox();
      return;
    }
    if (state.view === 'galeria') {
      if (e.key === 'ArrowRight') setCarouselSlide(state.carouselIdx + 1);
      if (e.key === 'ArrowLeft') setCarouselSlide(state.carouselIdx - 1);
    }
  });

  // Close lightbox on backdrop click
  const dlg = document.getElementById('lightbox');
  dlg.addEventListener('click', (e) => {
    if (e.target === dlg) closeLightbox();
  });

  const hash = location.hash.replace('#', '');
  const validViews = new Set(['turniej', 'dni', 'x', 'galeria']);
  switchView(validViews.has(hash) ? hash : 'turniej', false);
});
