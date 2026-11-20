// Draws one scatter per manufacturer from window.MAKERS (pushed by <maker>.data.js,
// written by scripts/plot_makers.py).
(function () {
  "use strict";

  var SVG_NS = "http://www.w3.org/2000/svg";
  var ORDER = ["seagate", "wd", "toshiba"];
  var GROUPS = ["Under 4 TB", "4–6 TB", "8–12 TB", "14–16 TB", "18 TB+"];

  // Shared axes (same as scripts/plot_makers.py)
  var X0 = Date.UTC(2013, 0, 1), X1 = Date.UTC(2027, 0, 1);
  var Y_MAX = 10;
  var W = 900, H = 400, M = { top: 16, right: 16, bottom: 44, left: 52 };
  var PW = W - M.left - M.right, PH = H - M.top - M.bottom;

  function x(ms) { return M.left + (ms - X0) / (X1 - X0) * PW; }
  function y(v) { return M.top + PH - v / Y_MAX * PH; }

  function h(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function s(tag, attrs, parent) {
    var e = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (parent) parent.appendChild(e);
    return e;
  }
  function median(a) {
    var b = a.slice().sort(function (p, q) { return p - q; });
    var m = b.length >> 1;
    return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2;
  }

  function render(maker) {
    var pts = maker.points.map(function (p) {
      var d = p[2].split("-");
      var ms = Date.UTC(+d[0], +d[1] - 1, +d[2]);
      return { model: p[0], tb: p[1], date: p[2], years: p[3], group: p[4], px: x(ms), py: y(p[3]) };
    });

    var card = h("section", "chart-card");
    card.appendChild(h("h2", null, maker.name + ": " + pts.length + " failed drives"));

    // Legend with counts
    var counts = GROUPS.map(function () { return 0; });
    pts.forEach(function (p) { counts[p.group]++; });
    var legend = h("div", "legend");
    legend.appendChild(h("span", "legend-title", "Capacity"));
    GROUPS.forEach(function (g, i) {
      if (!counts[i]) return;
      var item = h("span");
      item.appendChild(h("i", "swatch cap-" + i));
      item.appendChild(document.createTextNode(g + " (" + counts[i] + ")"));
      legend.appendChild(item);
    });
    card.appendChild(legend);

    // Chart
    var wrap = h("div", "chart-wrap");
    var svg = s("svg", { viewBox: "0 0 " + W + " " + H, role: "img",
      "aria-label": maker.name + " failed drives: power-on years at failure by first day in the data" });
    for (var v = 0; v <= Y_MAX; v += 2) {
      s("line", { x1: M.left, x2: W - M.right, y1: y(v), y2: y(v), "class": v ? "grid" : "baseline" }, svg);
      s("text", { x: M.left - 8, y: y(v) + 4, "text-anchor": "end", "class": "tick" }, svg).textContent = v;
    }
    for (var yr = 2014; yr <= 2026; yr += 2) {
      s("text", { x: x(Date.UTC(yr, 0, 1)), y: H - M.bottom + 18, "text-anchor": "middle", "class": "tick" }, svg)
        .textContent = yr;
    }
    s("text", { x: M.left + PW / 2, y: H - 6, "text-anchor": "middle", "class": "axis-title" }, svg)
      .textContent = "First day in the data";
    s("text", { x: 14, y: M.top + PH / 2, "text-anchor": "middle", "class": "axis-title",
      transform: "rotate(-90 14 " + (M.top + PH / 2) + ")" }, svg)
      .textContent = "Power-on time at failure (years)";

    var dots = s("g", {}, svg);
    pts.forEach(function (p) {
      s("circle", { cx: p.px, cy: p.py, r: 4.5, "class": "dot cap-" + p.group }, dots);
    });
    var ring = s("circle", { r: 7, "class": "dot-ring", visibility: "hidden" }, svg);
    wrap.appendChild(svg);

    var tip = h("div", "tip");
    tip.hidden = true;
    wrap.appendChild(tip);
    card.appendChild(wrap);

    // Hover: nearest dot within 16 screen px
    function hide() { tip.hidden = true; ring.setAttribute("visibility", "hidden"); }
    svg.addEventListener("pointermove", function (ev) {
      var r = svg.getBoundingClientRect();
      var k = W / r.width;
      var mx = (ev.clientX - r.left) * k, my = (ev.clientY - r.top) * k;
      var best = null, bd = 16 * 16 * k * k;
      pts.forEach(function (p) {
        var d = (p.px - mx) * (p.px - mx) + (p.py - my) * (p.py - my);
        if (d < bd) { bd = d; best = p; }
      });
      if (!best) return hide();
      ring.setAttribute("cx", best.px);
      ring.setAttribute("cy", best.py);
      ring.setAttribute("visibility", "visible");
      tip.innerHTML = "";
      tip.appendChild(h("div", "q", best.model));
      [["Capacity", best.tb + " TB"], ["First day", best.date],
       ["Power-on at failure", best.years.toFixed(1) + " yrs"]].forEach(function (row) {
        var e = h("div", "row");
        e.appendChild(h("span", null, row[0]));
        e.appendChild(h("span", "cnt", row[1]));
        tip.appendChild(e);
      });
      tip.hidden = false;
      var left = best.px / k + 12, top = best.py / k - 12;
      if (left + tip.offsetWidth > wrap.clientWidth) left = best.px / k - tip.offsetWidth - 12;
      tip.style.transform = "translate(" + Math.max(0, left) + "px," + Math.max(0, top) + "px)";
    });
    svg.addEventListener("pointerleave", hide);

    // Table view
    var det = h("details", "table-view");
    det.appendChild(h("summary", null, "Table: power-on time at failure by capacity"));
    var table = h("table");
    var head = h("tr");
    ["Capacity", "Failed drives", "Median years at failure"].forEach(function (t) {
      head.appendChild(h("th", null, t));
    });
    table.appendChild(head);
    GROUPS.forEach(function (g, i) {
      var ys = pts.filter(function (p) { return p.group === i; }).map(function (p) { return p.years; });
      if (!ys.length) return;
      var tr = h("tr");
      tr.appendChild(h("td", null, g));
      tr.appendChild(h("td", "num", ys.length));
      tr.appendChild(h("td", "num", median(ys).toFixed(1)));
      table.appendChild(tr);
    });
    det.appendChild(table);
    card.appendChild(det);

    return card;
  }

  var box = document.getElementById("makers");
  (window.MAKERS || [])
    .slice()
    .sort(function (a, b) { return ORDER.indexOf(a.maker) - ORDER.indexOf(b.maker); })
    .forEach(function (m) { box.appendChild(render(m)); });
})();
