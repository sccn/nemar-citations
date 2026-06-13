# NEMAR Citations Dashboard (Astro)

Modern Astro rebuild of the citations dashboard, matching the nemar.org website's
design language. Replaces the Python f-string generator in
`src/dataset_citations/dashboard/`. Epic: issue #127.

## Stack

- **Astro 6**, `output: "static"** (builds from data committed to this repo; no SSR).
- **bun** package manager, **Biome** lint/format (2-space, 100 col, double quotes), TypeScript strict.
- Design tokens vendored from `website/src/styles/` (`tokens.css` / `reset.css` /
  `global.css`) so it matches nemar.org. Keep in sync with the website.
- Deploys to the existing `nemar-dashboard` Cloudflare Pages project at
  `dashboard.nemar.org/citations/` (`base: "/citations"`).

## Data

Reads committed data at build time:

- `citations/json_opencite/*.json` — schema-v2 per-dataset citations (this PR uses these
  for the overview KPIs).
- `dashboard_data/{network,themes,temporal}/` + `*similarities*.csv` — produced by the hallu
  cron; wired in later phases (network, themes, UMAP, temporal).

Nothing in `src/lib/` ships to the client; it runs in node during `astro build`.

## Develop

```bash
cd web
bun install
bun run dev       # local dev server
bun run build     # static build -> web/dist/
bun run lint      # biome check
bun run format    # biome format --write
```

## Status

Phase 1 (#128): scaffold + design system + overview KPIs. Subsequent phases add the
single-source-of-truth data contract, network/UMAP, themes/wordclouds, temporal,
per-dataset views, search, and the deploy cutover (see epic #127).
