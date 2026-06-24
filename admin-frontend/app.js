"use strict";

// API base: same-origin in production (nginx proxies /admin/api on the admin host).
// Override for local dev with ?api=http://localhost:8000/admin/api
const API = new URLSearchParams(location.search).get("api") || "/admin/api";

const $ = (sel) => document.querySelector(sel);
const charts = {};
const fmtUSD = (n) => "$" + Number(n || 0).toFixed(4);
const fmtNum = (n) => Number(n || 0).toLocaleString("pt-BR");
const pct = (n) => (Number(n || 0) * 100).toFixed(1) + "%";
const fmtMs = (n) => {
  const v = Number(n || 0);
  return v >= 1000 ? (v / 1000).toFixed(2) + " s" : Math.round(v) + " ms";
};

// Dark-theme defaults so Chart.js axes/legends are legible on navy.
if (window.Chart) {
  Chart.defaults.color = "#93a4bd";
  Chart.defaults.borderColor = "rgba(148,163,184,0.14)";
}

function token() {
  return sessionStorage.getItem("admin_token") || "";
}

async function api(path) {
  const res = await fetch(API + path, {
    headers: { Authorization: "Bearer " + token() },
  });
  if (res.status === 401) {
    showLogin(true);
    throw new Error("unauthorized");
  }
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

async function apiSend(path, method, body) {
  const res = await fetch(API + path, {
    method,
    headers: {
      Authorization: "Bearer " + token(),
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) {
    showLogin(true);
    throw new Error("unauthorized");
  }
  if (!res.ok) {
    let detail = "HTTP " + res.status;
    try {
      detail = (await res.json()).detail || detail;
    } catch (e) {}
    throw new Error(detail);
  }
  return res.json();
}

function showLogin(error) {
  $("#app").hidden = true;
  $("#login").hidden = false;
  $("#login-error").hidden = !error;
}

function showApp() {
  $("#login").hidden = true;
  $("#app").hidden = false;
}

function days() {
  return $("#range").value;
}

function setStatus(msg) {
  $("#status").textContent = msg;
}

// --- chart helpers ---------------------------------------------------------
function line(canvasId, labels, datasets) {
  draw(canvasId, "line", labels, datasets, { y: { beginAtZero: true } });
}
function bar(canvasId, labels, datasets, stacked) {
  draw(canvasId, "bar", labels, datasets, {
    x: { stacked: !!stacked },
    y: { beginAtZero: true, stacked: !!stacked },
  });
}
function hbar(canvasId, labels, data, color) {
  if (charts[canvasId]) charts[canvasId].destroy();
  charts[canvasId] = new Chart($("#" + canvasId), {
    type: "bar",
    data: { labels, datasets: [{ data, backgroundColor: color || "#36c98f" }] },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true } },
    },
  });
}
function doughnut(canvasId, labels, data) {
  if (charts[canvasId]) charts[canvasId].destroy();
  charts[canvasId] = new Chart($("#" + canvasId), {
    type: "doughnut",
    data: {
      labels,
      datasets: [{ data, backgroundColor: ["#1f7a4d", "#5b9bd5", "#e0a458"] }],
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } },
  });
}
function draw(canvasId, type, labels, datasets, scales) {
  if (charts[canvasId]) charts[canvasId].destroy();
  charts[canvasId] = new Chart($("#" + canvasId), {
    type,
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: datasets.length > 1 } },
      scales,
    },
  });
}

const dayLabel = (d) => d.slice(6, 8) + "/" + d.slice(4, 6);

// --- renderers -------------------------------------------------------------
// Escape untrusted API strings before any innerHTML interpolation (#133).
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function card(label, valueHtml) {
  // Labels are static/trusted; values may include safe HTML spans we build ourselves
  // (fmt* helpers only emit numbers/currency). Still escape the label.
  return `<div class="card"><div class="label">${esc(label)}</div><div class="value">${valueHtml}</div></div>`;
}

async function loadOverview() {
  const o = await api("/overview");
  const badge = $("#mode-badge");
  if (o.use_mock_sefaz || o.use_mock_llm) {
    badge.hidden = false;
    badge.className = "badge warn";
    badge.textContent = "modo mock · custo estimado";
  } else {
    badge.hidden = false;
    badge.className = "badge";
    badge.textContent = "produção · " + (o.llm_model || "");
  }
  $("#overview-cards").innerHTML = [
    card("Buscas (total)", esc(fmtNum(o.total_searches))),
    card("Buscas (hoje)", esc(fmtNum(o.today_searches))),
    card("Usuários únicos (est.)", esc(fmtNum(o.estimated_unique_users))),
    card("Custo de IA (total)", esc(fmtUSD(o.total_llm_cost_usd))),
    card("Custo médio / busca", esc(fmtUSD(o.avg_cost_per_search_usd))),
    card("Taxa de acerto", esc(pct(o.overall_match_rate))),
    card("Qualidade tamanho/qtd", esc(pct(o.overall_quantity_parse_rate))),
  ].join("");
  const hours = o.hours_today || [];
  bar("chart-hours", hours.map((_, h) => String(h).padStart(2, "0") + "h"),
    [{ label: "Buscas", data: hours, backgroundColor: "#1f7a4d" }]);
}

async function loadQuality() {
  const q = await api("/quality?days=" + days());
  const labels = q.days.map(dayLabel);
  line("chart-match", labels, [
    { label: "Taxa de acerto", data: q.match_rate, borderColor: "#1f7a4d", tension: 0.3 },
  ]);
  line("chart-parse", labels, [
    { label: "Qualidade tamanho/qtd", data: q.quantity_parse_rate, borderColor: "#5b9bd5", tension: 0.3 },
  ]);
  const m = q.parse_method_distribution || {};
  doughnut("chart-method",
    ["unidadeMedida", "descrição", "fallback"],
    [m.unidade_medida || 0, m.description || 0, m.fallback || 0]);
}

async function loadCosts() {
  const c = await api("/costs?days=" + days());
  const labels = c.days.map(dayLabel);
  bar("chart-cost", labels, [
    { label: "Custo (USD)", data: c.cost_usd, backgroundColor: "#1f7a4d" },
  ]);
  bar("chart-tokens", labels, [
    { label: "Entrada", data: c.input_tokens, backgroundColor: "#5b9bd5" },
    { label: "Saída", data: c.output_tokens, backgroundColor: "#e0a458" },
  ], true);
  $("#model-table tbody").innerHTML = (c.per_model || []).map((m) =>
    `<tr><td>${esc(m.model)}</td><td>${esc(fmtNum(m.calls))}</td><td>${esc(fmtNum(m.input_tokens))}</td>
     <td>${esc(fmtNum(m.output_tokens))}</td><td>${esc(fmtUSD(m.cost_usd))}</td></tr>`).join("")
    || `<tr><td colspan="5" class="note">Sem dados ainda.</td></tr>`;
}

async function loadFeedback() {
  const kind = $("#fb-kind").value;
  const f = await api("/feedback?limit=100" + (kind ? "&kind=" + kind : ""));
  const counts = f.counts || {};
  $("#feedback-counts").innerHTML = [
    card("Útil (👍/👎)", esc(fmtNum(counts.helpful))),
    card("Item errado", esc(fmtNum(counts.wrong_item))),
    card("Outro", esc(fmtNum(counts.other))),
  ].join("");
  $("#feedback-table tbody").innerHTML = (f.items || []).map((i) => {
    const help = i.helpful === "1" ? "👍" : i.helpful === "0" ? "👎" : "—";
    return `<tr><td>${esc(when(i.ts))}</td><td>${esc(i.kind)}</td><td>${help}</td>
      <td>${esc(i.item)}</td><td class="note">${esc(i.note)}</td></tr>`;
  }).join("") || `<tr><td colspan="5" class="note">Sem feedback ainda.</td></tr>`;
}

async function loadSearches() {
  const s = await api("/searches?limit=100");
  $("#search-table tbody").innerHTML = (s.items || []).map((i) =>
    `<tr><td>${esc(when(i.ts))}</td><td>${esc(i.n_items)}</td><td>${esc(i.matched)}</td><td>${esc(i.source)}</td></tr>`
  ).join("") || `<tr><td colspan="4" class="note">Sem buscas ainda.</td></tr>`;
}

async function loadItems() {
  const it = await api("/items?days=" + days());
  const rows = (arr) => (arr || []).map((i) =>
    `<tr><td>${esc(i.label)}</td><td>${fmtNum(i.count)}</td></tr>`).join("")
    || `<tr><td colspan="2" class="note">Sem dados ainda.</td></tr>`;
  $("#top-table tbody").innerHTML = rows(it.top_searched);
  $("#notfound-table tbody").innerHTML = rows(it.top_not_found);
}

// Human label for each latency-distribution bucket, derived from the upper bounds.
function bucketLabels(bounds) {
  const labels = bounds.map((hi, i) =>
    (i === 0 ? "≤" : (bounds[i - 1] >= 1000 ? bounds[i - 1] / 1000 + "s" : bounds[i - 1] + "ms") + "–") +
    (hi >= 1000 ? hi / 1000 + "s" : hi + "ms"));
  labels.push("> " + (bounds[bounds.length - 1] >= 1000
    ? bounds[bounds.length - 1] / 1000 + "s" : bounds[bounds.length - 1] + "ms"));
  return labels;
}

const STAGE_LABELS = {
  total: "Total (resposta)", llm: "IA (parse)", sefaz: "SEFAZ",
  cache: "Cache (Redis)", normalize: "Normalização", rank: "Ranking",
  analytics: "Analytics (2º plano)",
};

const WEEKDAY_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

async function loadGrowth() {
  const g = await api("/growth?days=" + days());
  $("#growth-cards").innerHTML = [
    card("Únicos hoje (DAU)", esc(fmtNum(g.dau_today))),
    card("Únicos 7 dias (WAU)", esc(fmtNum(g.wau))),
    card("Únicos 30 dias (MAU)", esc(fmtNum(g.mau))),
    card("Recorrência (DAU/MAU)", esc(pct(g.stickiness))),
    card("Total de usuários (est.)", esc(fmtNum(g.total_unique_users))),
  ].join("");

  const labels = (g.days || []).map(dayLabel);
  // New vs returning stack to the day's unique-user total (DAU).
  bar("chart-dau", labels, [
    { label: "Recorrentes", data: g.returning_users || [], backgroundColor: "#1f7a4d" },
    { label: "Novos", data: g.new_users || [], backgroundColor: "#5b9bd5" },
  ], true);

  const hours = g.hours || [];
  bar("chart-hourofday", hours.map((_, h) => String(h).padStart(2, "0") + "h"),
    [{ label: "Buscas", data: hours, backgroundColor: "#36c98f" }]);

  bar("chart-weekday", WEEKDAY_LABELS,
    [{ label: "Buscas", data: g.weekday || [], backgroundColor: "#e0a458" }]);

  line("chart-engagement", labels, [
    { label: "Buscas / usuário", data: g.searches_per_user || [],
      borderColor: "#36c98f", tension: 0.3 },
  ]);
}

async function loadPerformance() {
  const t = await api("/timings?days=" + days());
  const stages = t.stages || [];
  const total = stages.find((s) => s.stage === "total") || {};
  $("#performance-cards").innerHTML = [
    card("Tempo médio (resposta)", esc(fmtMs(total.avg_ms))),
    card("Mediana (p50)", esc(fmtMs(total.p50_ms))),
    card("p95", esc(fmtMs(total.p95_ms))),
    card("Buscas medidas", esc(fmtNum(total.count))),
  ].join("");

  bar("chart-latency-dist", bucketLabels(t.buckets_ms || []),
    [{ label: "Buscas", data: t.distribution || [], backgroundColor: "#36c98f" }]);

  const labels = (t.days || []).map(dayLabel);
  const series = t.total_series || {};
  line("chart-latency-trend", labels, [
    { label: "Média (ms)", data: series.avg_ms || [], borderColor: "#36c98f", tension: 0.3 },
    { label: "p95 (ms)", data: series.p95_ms || [], borderColor: "#e0a458", tension: 0.3 },
  ]);

  // Subsystem breakdown excludes "total" (it's the sum the others contribute to).
  const subs = stages.filter((s) => s.stage !== "total");
  hbar("chart-subsystems", subs.map((s) => STAGE_LABELS[s.stage] || s.stage),
    subs.map((s) => s.avg_ms), "#5b9bd5");
  $("#subsystem-table tbody").innerHTML = stages.map((s) =>
    `<tr><td>${esc(STAGE_LABELS[s.stage] || s.stage)}</td><td>${esc(fmtNum(s.count))}</td>
     <td>${esc(fmtMs(s.avg_ms))}</td><td>${esc(fmtMs(s.p50_ms))}</td><td>${esc(fmtMs(s.p95_ms))}</td></tr>`
  ).join("") || `<tr><td colspan="5" class="note">Sem dados ainda.</td></tr>`;
}

async function loadProviders() {
  const p = await api("/providers?days=" + days());
  const badge = $("#mode-badge");
  if (p.use_mock_sefaz || p.use_mock_llm) {
    badge.hidden = false;
    badge.className = "badge warn";
    badge.textContent = "modo mock · sem chamadas reais";
  }
  const provs = p.providers || [];
  const NAMES = { sefaz: "SEFAZ (dados NFC-e)", llm: "IA (Claude)" };
  $("#provider-cards").innerHTML = provs.map((x) =>
    card(NAMES[x.name] || x.name,
      `${esc(fmtMs(x.avg_ms))} <span class="sub">méd · ${esc(pct(x.error_rate))} erro</span>`)
  ).join("") || card("Provedores", "—");
  $("#provider-table tbody").innerHTML = provs.map((x) => {
    const errClass = x.error_rate > 0 ? ' class="bad"' : "";
    return `<tr><td>${esc(NAMES[x.name] || x.name)}</td><td>${esc(fmtNum(x.calls))}</td>
      <td${errClass}>${esc(pct(x.error_rate))}</td><td>${esc(fmtMs(x.avg_ms))}</td>
      <td>${esc(fmtMs(x.p95_ms))}</td><td>${esc(when(x.last_error_ts))}</td></tr>`;
  }).join("") || `<tr><td colspan="6" class="note">Sem dados ainda.</td></tr>`;
}

async function loadSettings() {
  const s = await api("/secrets");
  const warn = $("#secrets-warning");
  if (!s.encryption_enabled) {
    warn.hidden = false;
    warn.textContent =
      "Criptografia desativada: defina SECRET_ENCRYPTION_KEY no servidor para gerenciar segredos aqui.";
  } else {
    warn.hidden = true;
  }
  $("#secrets-list").innerHTML = (s.secrets || []).map((sec) => {
    const status = sec.configured
      ? `definido · impressão digital <code>${esc(sec.fingerprint)}</code>` +
        (sec.updated_at ? ` · ${when(sec.updated_at)}` : "")
      : "não definido";
    const disabled = s.encryption_enabled ? "" : "disabled";
    return `<div class="secret-card" data-name="${esc(sec.name)}">
      <div class="label">${esc(sec.label)}</div>
      <div class="note">${status}</div>
      <form class="secret-form">
        <input type="password" autocomplete="off" placeholder="Novo valor"
          class="secret-input" ${disabled} />
        <button type="submit" ${disabled}>Salvar</button>
        ${sec.configured ? `<button type="button" class="secret-clear" ${disabled}>Remover</button>` : ""}
      </form>
      <p class="secret-msg note"></p>
    </div>`;
  }).join("") || `<p class="note">Nenhum segredo gerenciável.</p>`;

  document.querySelectorAll(".secret-card").forEach((cardEl) => {
    const name = cardEl.dataset.name;
    const msg = cardEl.querySelector(".secret-msg");
    cardEl.querySelector(".secret-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const input = cardEl.querySelector(".secret-input");
      const value = input.value.trim();
      if (!value) return;
      msg.textContent = "Salvando…";
      try {
        await apiSend("/secrets/" + encodeURIComponent(name), "PUT", { value });
        input.value = "";
        msg.textContent = "Salvo com segurança.";
        loadSettings();
      } catch (err) {
        msg.textContent = "Erro: " + err.message;
      }
    });
    const clearBtn = cardEl.querySelector(".secret-clear");
    if (clearBtn) {
      clearBtn.addEventListener("click", async () => {
        if (!confirm("Remover este segredo?")) return;
        try {
          await apiSend("/secrets/" + encodeURIComponent(name), "DELETE");
          loadSettings();
        } catch (err) {
          msg.textContent = "Erro: " + err.message;
        }
      });
    }
  });
}

const LOADERS = {
  overview: loadOverview, quality: loadQuality, costs: loadCosts,
  feedback: loadFeedback, searches: loadSearches, items: loadItems,
  growth: loadGrowth,
  performance: loadPerformance, providers: loadProviders,
  settings: loadSettings,
};
let activeTab = "overview";

async function refresh() {
  try {
    setStatus("Carregando…");
    await LOADERS[activeTab]();
    setStatus("Atualizado " + new Date().toLocaleTimeString("pt-BR"));
  } catch (e) {
    if (e.message !== "unauthorized") setStatus("Erro ao carregar dados.");
  }
}

// --- utils -----------------------------------------------------------------
function when(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d) ? String(iso) : d.toLocaleString("pt-BR");
}

// --- wiring ----------------------------------------------------------------
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    activeTab = btn.dataset.tab;
    document.querySelectorAll(".panel").forEach((p) => (p.hidden = true));
    $("#tab-" + activeTab).hidden = false;
    refresh();
  });
});
$("#refresh").addEventListener("click", refresh);
$("#range").addEventListener("change", refresh);
$("#fb-kind").addEventListener("change", loadFeedback);
$("#logout").addEventListener("click", () => {
  sessionStorage.removeItem("admin_token");
  showLogin(false);
});
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  sessionStorage.setItem("admin_token", $("#token").value.trim());
  try {
    await api("/overview");
    showApp();
    refresh();
  } catch (err) {
    sessionStorage.removeItem("admin_token");
    showLogin(true);
  }
});

// Boot: try the stored token, else show the gate.
(async function boot() {
  if (!token()) return showLogin(false);
  try {
    await api("/overview");
    showApp();
    refresh();
  } catch (e) {
    showLogin(false);
  }
})();
