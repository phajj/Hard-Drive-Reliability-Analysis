// pm2 config: `pm2 start ecosystem.config.cjs`.
module.exports = {
  apps: [
    {
      name: "drive-site",
      script: "server.js",
      env: { PORT: 3000, NODE_ENV: "production" },
    },
  ],
};
