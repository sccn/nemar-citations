/**
 * Build-time data loader for the citations dashboard.
 *
 * Reads the schema-v2 citation JSON committed to this repo
 * (citations/json_opencite/) and computes the headline overview. Runs in
 * node during `astro build`; nothing here ships to the client. Phase 2 will
 * formalize a typed data contract; this is the minimal proof of the
 * data -> Astro build path (issue #128).
 */
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";

/**
 * Locate citations/json_opencite by walking up from the build working
 * directory. `import.meta.url` is unreliable here because Vite rewrites it
 * during the build, and the data lives outside the Astro project root (web/),
 * so a Vite glob import cannot reach it. This works whether `astro build`
 * runs from web/ or the repo root.
 */
function findCitationsDir(): string | null {
  let dir = process.cwd();
  for (let depth = 0; depth < 8; depth++) {
    const candidate = join(dir, "citations", "json_opencite");
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

export interface CitationOverview {
  datasetCount: number;
  datasetsWithCitations: number;
  totalCitations: number;
  uniqueCitations: number;
}

interface CitationDetail {
  doi?: string | null;
  openalex_id?: string | null;
  pmid?: string | null;
  title?: string | null;
}

interface CitationFile {
  num_citations?: number;
  citation_details?: CitationDetail[];
}

function citingKey(c: CitationDetail): string {
  const raw = c.doi || c.openalex_id || c.pmid || c.title || "";
  return raw.toString().trim().toLowerCase();
}

// Opt-in to build an empty dashboard when no data is present (e.g. an initial
// scaffold checkout). Off by default so a misconfigured build fails loudly
// instead of silently publishing a zero-stat dashboard.
const ALLOW_EMPTY = process.env.CITATIONS_ALLOW_EMPTY === "1";

const EMPTY_HINT =
  "Run the hallu pipeline (or check out a tree with citations/json_opencite/), " +
  "or set CITATIONS_ALLOW_EMPTY=1 to intentionally build an empty dashboard.";

export function loadOverview(): CitationOverview {
  const empty: CitationOverview = {
    datasetCount: 0,
    datasetsWithCitations: 0,
    totalCitations: 0,
    uniqueCitations: 0,
  };
  const citationsDir = findCitationsDir();
  if (!citationsDir) {
    if (ALLOW_EMPTY) {
      console.warn(`[citations] citations/json_opencite/ not found; building empty. ${EMPTY_HINT}`);
      return empty;
    }
    throw new Error(`[citations] Cannot locate citations/json_opencite/. ${EMPTY_HINT}`);
  }

  const files = readdirSync(citationsDir).filter((f) => f.endsWith("_citations.json"));
  if (files.length === 0) {
    if (ALLOW_EMPTY) {
      console.warn(`[citations] ${citationsDir} has no *_citations.json; building empty.`);
      return empty;
    }
    throw new Error(`[citations] ${citationsDir} has no *_citations.json files. ${EMPTY_HINT}`);
  }

  let totalCitations = 0;
  let datasetsWithCitations = 0;
  const unique = new Set<string>();

  for (const name of files) {
    let data: CitationFile;
    try {
      data = JSON.parse(readFileSync(join(citationsDir, name), "utf-8")) as CitationFile;
    } catch (err) {
      // Skip an unreadable/corrupt file but surface it in build output so a bad
      // cron write does not silently shrink the KPIs.
      console.warn(`[citations] skipping ${name}: ${err instanceof Error ? err.message : err}`);
      continue;
    }
    const n = data.num_citations ?? 0;
    totalCitations += n;
    if (n > 0) {
      datasetsWithCitations += 1;
    }
    for (const detail of data.citation_details ?? []) {
      const key = citingKey(detail);
      if (key) {
        unique.add(key);
      }
    }
  }

  return {
    datasetCount: files.length,
    datasetsWithCitations,
    totalCitations,
    uniqueCitations: unique.size,
  };
}
