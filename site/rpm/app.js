(function () {
  "use strict";

  // Mark the current sample in the switch.
  var page = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".sample-switch a").forEach(function (a) {
    if (a.getAttribute("href") === page) a.setAttribute("aria-current", "page");
  });

  var DATA = window.DATA;
  var SVG_NS = "http://www.w3.org/2000/svg";
  var META = DATA.meta;
  var SUMMARY = DATA.summary;
  var CLASSES = SUMMARY.map(function (c) { return c.rpm; });
  var QUARTERS = DATA.quarters;
  var N = QUARTERS.length;

  /* Running totals per class: CUM[rpm][i] = failures up to and including quarter i */
  var CUM = {};
  CLASSES.forEach(function (rpm) {
    var run = 0;
    CUM[rpm] = DATA.series[rpm].map(function (v) { run += v; return run; });
  });

  function $(id) { return document.getElementById(id); }
  function fmt(n, digits) {
    return Number(n).toLocaleString("en-US", {
      minimumFractionDigits: digits || 0,
      maximumFractionDigits: digits || 0
    });
  }
  function h(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = text;
    return e;
  }
  function s(tag, attrs, parent) {
    var e = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (parent) parent.appendChild(e);
    return e;
  }
  function label(rpm) { return rpm + " RPM"; }

  /* Subtitle */
  var perClass = Array.from(new Set(SUMMARY.map(function (c) { return c.drives; })));
  var perClassText = perClass.length === 1
    ? fmt(perClass[0])
    : fmt(Math.min.apply(null, perClass)) + "–" + fmt(Math.max.apply(null, perClass));
  $("subtitle").textContent =
    "Backblaze drive stats · " + fmt(META.drives) + " drives, " + perClassText +
    " per speed class · drives first seen " + META.first_seen_min + " to " +
    META.first_seen_max + ", followed through " + META.data_end;

  /* Failure-rate cards */
  var cards = $("cards");
  SUMMARY.forEach(function (c) {
    var card = h("article", "card");
    var lab = h("div", "card-label");
    lab.appendChild(h("span", "swatch rpm-" + c.rpm));
    lab.appendChild(h("span", "", label(c.rpm)));
    card.appendChild(lab);
    card.appendChild(h("div", "afr", c.afr.toFixed(2) + "%"));
    card.appendChild(h("div", "caption", "annualized failure rate"));
    card.appendChild(h("div", "detail",
      fmt(c.failures) + " failures · " + fmt(c.drive_years) + " drive-years · " +
      fmt(c.drives) + " drives"));
    var m = c.models;
    card.appendChild(h("div", "models",
      m.length + (m.length === 1 ? " model: " : " models: ") + m.join(", ")));
    cards.appendChild(card);
  });

  /* Legend */
  var legend = $("legend");
  CLASSES.forEach(function (rpm) {
    var item = h("span");
    item.appendChild(h("span", "swatch rpm-" + rpm));
    item.appendChild(document.createTextNode(label(rpm)));
    legend.appendChild(item);
  });

  /* Chart geometry */
  var W = 900, H = 380;
  var M = { top: 16, right: 16, bottom: 44, left: 48 };
  var plotL = M.left, plotR = W - M.right, plotT = M.top, plotB = H - M.bottom;
  var plotW = plotR - plotL, plotH = plotB - plotT;
  var slotW = plotW / N;
  var OFFSETS = [-4, 0, 4];

  function xCenter(i) { return plotL + (i + 0.5) * slotW; }

  var maxVal = 0;
  CLASSES.forEach(function (rpm) {
    CUM[rpm].forEach(function (v) { if (v > maxVal) maxVal = v; });
  });

  var STEPS = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000];
  function niceScale(maxv) {
    // First pass: the smallest step giving 4-6 ticks (including 0).
    // Second pass: the smallest step giving at most 6 ticks, so the axis never gets crowded.
    var passes = [
      function (count) { return count >= 4 && count <= 6; },
      function (count) { return count <= 6; }
    ];
    for (var p = 0; p < passes.length; p++) {
      for (var k = 0; k < STEPS.length; k++) {
        var step = STEPS[k];
        var top = Math.max(1, Math.ceil(maxv / step)) * step;
        if (passes[p](top / step + 1)) return { step: step, top: top };
      }
    }
    throw new Error("no axis scale fits");
  }
  var scale = niceScale(maxVal);
  function yScale(v) { return plotB - (v / scale.top) * plotH; }

  var svg = $("chart-svg");
  var wrap = $("chart-wrap");
  var tip = $("tip");

  var firstQ = QUARTERS[0], lastQ = QUARTERS[N - 1];
  svg.setAttribute("aria-label",
    "Dot chart of cumulative failures by quarter from " + firstQ + " to " + lastQ + ", one color per RPM class (" +
    CLASSES.map(label).join(", ") + "). Final totals " +
    SUMMARY.map(function (c) { return label(c.rpm) + " " + fmt(c.failures); }).join(", ") +
    ". Use the Left and Right arrow keys to move between quarters and Escape to hide the tooltip.");

  /* Gridlines and y-axis labels */
  for (var t = 0; t <= scale.top; t += scale.step) {
    s("line", { class: "grid", x1: plotL, x2: plotR, y1: yScale(t), y2: yScale(t) }, svg);
    s("text", { class: "tick", x: plotL - 8, y: yScale(t) + 4, "text-anchor": "end" }, svg)
      .textContent = fmt(t);
  }
  var yTitle = s("text", {
    class: "axis-title",
    x: 0, y: 0,
    "text-anchor": "middle",
    transform: "translate(14," + ((plotT + plotB) / 2) + ") rotate(-90)"
  }, svg);
  yTitle.textContent = "Total failures";

  /* X-axis baseline, ticks and year labels */
  s("line", { class: "baseline", x1: plotL, x2: plotR, y1: plotB, y2: plotB }, svg);
  QUARTERS.forEach(function (q, i) {
    var m = q.match(/^(\d{4}) Q1$/);
    var year = m ? m[1] : (i === 0 ? q.slice(0, 4) : null);
    if (year === null) return;
    var x = xCenter(i);
    s("line", { class: "tick-line", x1: x, x2: x, y1: plotB, y2: plotB + 4 }, svg);
    s("text", { class: "tick", x: x, y: plotB + 18, "text-anchor": "middle" }, svg)
      .textContent = year;
  });
  s("text", {
    class: "axis-title",
    x: (plotL + plotR) / 2, y: H - 8,
    "text-anchor": "middle"
  }, svg).textContent = "Quarter";

  /* Dots, including zero counts */
  var dotsByIdx = [];
  for (var i = 0; i < N; i++) dotsByIdx.push([]);
  CLASSES.forEach(function (rpm, ci) {
    var series = CUM[rpm];
    for (var i = 0; i < N; i++) {
      var v = series[i];
      var c = s("circle", {
        class: "dot rpm-" + rpm,
        cx: xCenter(i) + OFFSETS[ci],
        cy: yScale(v),
        r: 4
      }, svg);
      dotsByIdx[i].push(c);
    }
  });

  /* Crosshair */
  var crosshair = s("line", {
    class: "crosshair",
    x1: 0, x2: 0, y1: plotT, y2: plotB,
    visibility: "hidden"
  }, svg);

  /* Hit targets, one per quarter, on top */
  var hitRects = [];
  for (var i = 0; i < N; i++) {
    hitRects.push(s("rect", {
      class: "hit",
      x: plotL + i * slotW, y: plotT, width: slotW, height: plotH
    }, svg));
  }

  /* Tooltip and highlight */
  var shown = null;
  var hoverIdx = null;
  var keyIdx = null;
  var keyFocus = false;

  // Writes "total (+new)" for class rpm in quarter i; the "(+new)" part is muted.
  function appendCount(parent, rpm, i) {
    parent.appendChild(document.createTextNode(fmt(CUM[rpm][i]) + " "));
    parent.appendChild(h("span", "new", "(+" + fmt(DATA.series[rpm][i]) + ")"));
  }

  function setRadius(i, r) {
    dotsByIdx[i].forEach(function (c) { c.setAttribute("r", r); });
  }

  function fillTip(i) {
    while (tip.firstChild) tip.removeChild(tip.firstChild);
    tip.appendChild(h("div", "q", QUARTERS[i]));
    CLASSES.forEach(function (rpm) {
      var row = h("div", "row");
      row.appendChild(h("span", "swatch rpm-" + rpm));
      row.appendChild(h("span", "", label(rpm)));
      var cnt = h("span", "cnt");
      appendCount(cnt, rpm, i);
      row.appendChild(cnt);
      tip.appendChild(row);
    });
  }

  function placeTip(clientX, clientY) {
    var wr = wrap.getBoundingClientRect();
    var tw = tip.offsetWidth, th = tip.offsetHeight;
    var sl = wrap.scrollLeft, st = wrap.scrollTop;
    var visR = sl + wrap.clientWidth;
    var x = clientX - wr.left + sl + 14;
    if (x + tw > visR - 4) x = clientX - wr.left + sl - tw - 14;
    x = Math.max(sl + 4, Math.min(x, visR - tw - 4));
    var y = clientY - wr.top + st + 14;
    y = Math.max(st + 4, Math.min(y, st + wrap.clientHeight - th - 4));
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }

  function update(evt) {
    var idx = null;
    if (hoverIdx !== null) idx = hoverIdx;
    else if (keyFocus && keyIdx !== null) idx = keyIdx;

    if (shown !== null && shown !== idx) setRadius(shown, 4);
    shown = idx;

    if (idx === null) {
      crosshair.setAttribute("visibility", "hidden");
      tip.hidden = true;
      return;
    }

    var xc = xCenter(idx);
    crosshair.setAttribute("x1", xc);
    crosshair.setAttribute("x2", xc);
    crosshair.setAttribute("visibility", "visible");
    setRadius(idx, 6);
    fillTip(idx);
    tip.hidden = false;

    var r = svg.getBoundingClientRect();
    var sc = r.width / W;
    if (evt && typeof evt.clientX === "number") {
      placeTip(evt.clientX, evt.clientY);
    } else {
      placeTip(r.left + xc * sc, r.top + plotT * sc);
    }
  }

  hitRects.forEach(function (rect, i) {
    rect.addEventListener("mouseenter", function (e) { hoverIdx = i; update(e); });
    rect.addEventListener("mousemove", function (e) { hoverIdx = i; update(e); });
    rect.addEventListener("mouseleave", function () { hoverIdx = null; update(); });
  });

  svg.addEventListener("focus", function () {
    // A mouse click also focuses the chart; only keyboard focus should pin a tooltip,
    // otherwise it stays stuck after the mouse leaves.
    if (!svg.matches(":focus-visible")) return;
    keyFocus = true;
    if (keyIdx === null) keyIdx = N - 1;
    update();
  });
  svg.addEventListener("blur", function () {
    keyFocus = false;
    update();
  });
  svg.addEventListener("keydown", function (e) {
    keyFocus = true; // arrow keys after a mouse click still work
    var cur = keyIdx === null ? N - 1 : keyIdx;
    if (e.key === "ArrowLeft") {
      keyIdx = Math.max(0, cur - 1);
    } else if (e.key === "ArrowRight") {
      keyIdx = Math.min(N - 1, cur + 1);
    } else if (e.key === "Escape") {
      keyIdx = null;
      update();
      return;
    } else {
      return;
    }
    e.preventDefault();
    update();
  });


  /* Footer */
  var footer = $("footer");
  footer.appendChild(h("p", "", "A drive’s failure date is the last day it reported. Backblaze marks failure = 1 on that day."));
  footer.appendChild(h("p", "", "AFR (annualized failure rate) = failures ÷ drive-years, where drive-years = days observed ÷ 365."));
  footer.appendChild(h("p", "", "Source: Backblaze Hard Drive Data, sample file " + META.sample_file + "."));
  footer.appendChild(h("p", "", "Generated " + META.generated + "."));
})();
