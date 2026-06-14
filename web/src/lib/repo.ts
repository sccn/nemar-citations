/** Walk up from the build working directory to find a repo-relative path.
 * Shared by the build-time data loaders; `import.meta.url` is unreliable under
 * Vite and the data lives outside the Astro project root (web/). */
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

export function findRepoPath(rel: string): string | null {
  let dir = process.cwd();
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
