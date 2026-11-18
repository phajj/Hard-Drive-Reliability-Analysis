// Serves the project website (the site/ folder). Run with `npm start` or pm2 (see README).
const path = require("path");
const express = require("express");

const PORT = Number(process.env.PORT) || 3000;
const SITE = path.join(__dirname, "site");

const app = express();
app.disable("x-powered-by");

app.get("/healthz", (req, res) => res.type("text").send("ok"));

// extensions: "/rpm/all_eras" also finds all_eras.html
app.use(express.static(SITE, { extensions: ["html"] }));

app.use((req, res) => {
  res.status(404).type("html").send(
    '<!doctype html><meta charset="utf-8"><title>Not found</title>' +
    '<p style="font-family:system-ui;padding:24px">Page not found. <a href="/">Go to the homepage</a>.</p>'
  );
});

app.listen(PORT, () => console.log(`Site running at http://localhost:${PORT}`));
