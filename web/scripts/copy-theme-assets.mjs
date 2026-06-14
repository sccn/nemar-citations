// Copy the Python-generated theme wordcloud PNGs from the repo's
// dashboard_data/themes/ into web/public/themes/ so Astro serves them as static
// assets. Run before `astro build` / `astro dev`. Idempotent; warns (does not
// fail) if the source is absent so a code-only build still works.
//
// Paths are resolved from this file's own location (not process.cwd()) so the
// destination is always web/public/themes/ regardless of where the script is
// invoked from.
import { copyFileSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const webRoot = dirname(scriptDir); // scripts/ -> web/

function findRepoDir(rel) {
  let dir = webRoot;
  for (let depth = 0; depth < 8; depth++) {
    const candidate = join(dir, rel);
    if (existsSync(candidate)) {
      return candidate;
    }
    const parent = dirname(dir);
    if (parent === dir) {
      break;
    }
    dir = parent;
  }
  return null;
}

const src = findRepoDir(join("dashboard_data", "themes"));
const dest = join(webRoot, "public", "themes");

if (!src) {
  console.warn("[copy-theme-assets] dashboard_data/themes not found; skipping wordcloud copy.");
} else {
  mkdirSync(dest, { recursive: true });
  let n = 0;
  for (const file of readdirSync(src)) {
    if (file.endsWith(".png")) {
      copyFileSync(join(src, file), join(dest, file));
      n += 1;
    }
  }
  console.log(`[copy-theme-assets] copied ${n} wordcloud PNG(s) to public/themes/`);
}
