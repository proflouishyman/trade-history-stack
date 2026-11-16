// ONE line decides where the data comes from: Flask (port 5001) or static files.
const url = (iso) => location.port === "5001" ? `/api/country/${iso}` : `data/${iso}.json`;

let country = null, charts = {};
const $ = (id) => document.getElementById(id);
$("mode").textContent = "data from: " + url("GBR").replace("GBR", "ISO");

// Draw (or redraw) one chart; `pairs` is [[partner_iso, value_gbp], ...]
function draw(id, type, labels, values, label, horizontal) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart($(id), {
    type, data: { labels, datasets: [{ label, data: values, backgroundColor: "#2b6cb0", borderColor: "#2b6cb0" }] },
    options: { indexAxis: horizontal ? "y" : "x", plugins: { legend: { display: false } }, animation: false },
  });
}

function show() {
  const y = $("year").value, d = country.years[y] || { exports: [], imports: [] };
  $("yearLabel").textContent = y;
  draw("exp", "bar", d.exports.map(p => p[0]), d.exports.map(p => p[1]), "GBP", true);
  draw("imp", "bar", d.imports.map(p => p[0]), d.imports.map(p => p[1]), "GBP", true);
}

async function load(iso) {
  country = await (await fetch(url(iso))).json();
  const years = Object.keys(country.years).map(Number);
  const slider = $("year");
  slider.min = Math.min(...years); slider.max = Math.max(...years);
  slider.value = country.years["1913"] ? 1913 : slider.max;
  const sums = years.map(yr => country.years[yr].exports.reduce((s, p) => s + p[1], 0));
  draw("line", "line", years, sums, "GBP", false);
  $("note").textContent = `${country.name || country.iso} (${country.region}). ${country.note}`;
  show();
}

async function start() {
  const list = await (await fetch("data/countries.json")).json();   // same file in both modes
  $("country").innerHTML = list.map(c => `<option value="${c.iso}">${c.name || c.iso}</option>`).join("");
  $("country").value = "GBR";
  $("country").onchange = (e) => load(e.target.value);
  $("year").oninput = show;
  load("GBR");
}
start();
