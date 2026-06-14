import { defineConfig } from "astro/config";

// Static build: the dashboard renders from data committed to this repo
// (dashboard_data/ + citations/json_opencite/), produced by the hallu cron.
// No SSR is needed, unlike the nemar.org website. Output is a static dist/
// deployed to the existing nemar-dashboard Cloudflare Pages project at
// dashboard.nemar.org/citations/.
export default defineConfig({
  site: "https://dashboard.nemar.org",
  base: "/citations",
  output: "static",
  trailingSlash: "ignore",
  // /trends was folded into the overview (#159); keep the previously-public URL
  // working by redirecting old links to the overview instead of 404ing.
  // Destination is an absolute path (base is not auto-prepended), so target
  // /citations/ explicitly.
  redirects: {
    "/trends": "/citations/",
  },
});
