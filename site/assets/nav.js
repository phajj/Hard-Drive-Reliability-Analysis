// Shared site nav. Every page includes this file and a <nav id="site-nav"></nav>.
// To add a topic: add an entry to TOPICS. "soon" topics show as greyed-out cards on the homepage
// and stay out of the nav bar.
(function () {
  "use strict";

  var TOPICS = [
    {
      id: "rpm",
      title: "Spin speed",
      href: "/rpm/",
      blurb: "Do 7200 RPM drives fail more often than 5700 and 5900 RPM drives? Annualized failure rate and failures over time for each speed class.",
      status: "live"
    },
    {
      id: "models",
      title: "Model vs model",
      href: "/models/",
      blurb: "Power-on hours at failure and failures per drive-year for each HDD model and capacity, run for each manufacturer.",
      status: "soon"
    },
    {
      id: "manufacturers",
      title: "Seagate vs Western Digital vs Toshiba",
      href: "/manufacturers/",
      blurb: "The spin speed page for each of the three big manufacturers: failure rate per RPM class and failures over time.",
      status: "live"
    }
  ];

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  // "/rpm/all_eras.html" -> "rpm"; "/" -> "" (home)
  var section = location.pathname.replace(/^\/+/, "").split("/")[0];
  if (section === "index.html") section = "";

  function renderNav(nav) {
    nav.setAttribute("aria-label", "Site");
    var inner = el("div", "site-nav-inner");
    var brand = el("a", "site-nav-brand", "Drive Reliability");
    brand.href = "/";
    inner.appendChild(brand);

    var links = el("div", "site-nav-links");
    var items = [{ id: "", title: "Home", href: "/" }].concat(
      TOPICS.filter(function (t) { return t.status === "live"; })
    );
    items.forEach(function (t) {
      var a = el("a", "site-nav-link", t.title);
      a.href = t.href;
      if (t.id === section) a.setAttribute("aria-current", "page");
      links.appendChild(a);
    });
    inner.appendChild(links);
    nav.appendChild(inner);
  }

  function renderCards(box) {
    TOPICS.forEach(function (t) {
      var live = t.status === "live";
      var card = el(live ? "a" : "div", "topic-card" + (live ? "" : " soon"));
      if (live) card.href = t.href;
      card.appendChild(el("h3", "", t.title));
      card.appendChild(el("p", "", t.blurb));
      card.appendChild(el("span", "topic-cta", live ? "Open →" : "Coming soon"));
      box.appendChild(card);
    });
  }

  function init() {
    var nav = document.getElementById("site-nav");
    if (nav) renderNav(nav);
    var cards = document.getElementById("topic-cards");
    if (cards) renderCards(cards);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
