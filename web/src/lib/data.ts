/**
 * Build-time data layer for the citations dashboard.
 *
 * Reads the schema-v2 citation JSON committed to this repo
 * (citations/json_opencite/) plus dataset names from datasets/, and exposes a
 * typed contract the pages render. Runs in node during `astro build`; nothing
 * here ships to the client. Phases P2+P3 of epic #127.
 */
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";

// Opt-in to build an empty dashboard when no data is present. Off by default so
// a misconfigured build fails loudly instead of shipping zero-stat pages.
const ALLOW_EMPTY = process.env.CITATIONS_ALLOW_EMPTY === "1";
const EMPTY_HINT =
  "Run the hallu pipeline (or check out a tree with citations/json_opencite/), " +
  "or set CITATIONS_ALLOW_EMPTY=1 to intentionally build an empty dashboard.";

/** Walk up from the build CWD to locate a repo-relative data dir. */
function findRepoDir(sub: string): string | null {
  let dir = process.cwd();
  for (let depth = 0; depth < 8; depth++) {
    const candidate = join(dir, sub);
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

const citationsDir = findRepoDir(join("citations", "json_opencite"));
const datasetsDir = findRepoDir("datasets");

export interface Citation {
  title: string;
  authors: string;
  year: number | null;
  venue: string;
  url: string | null;
  doi: string | null;
  citedBy: number;
  confidence: number | null;
}

export interface DatasetDetail {
  id: string;
  name: string;
  numCitations: number;
  citations: Citation[];
}

export interface Overview {
  datasetCount: number;
  datasetsWithCitations: number;
  totalCitations: number;
  uniqueCitations: number;
}

export interface LoadedData {
  overview: Overview;
  datasets: DatasetDetail[];
}

interface RawCitation {
  title?: string | null;
  author?: string | null;
  venue?: string | null;
  year?: number | null;
  url?: string | null;
  doi?: string | null;
  pmid?: string | null;
  openalex_id?: string | null;
  cited_by?: number | null;
  confidence_scoring?: { confidence_score?: number | null } | null;
}

interface RawFile {
  dataset_id?: string;
  num_citations?: number;
  citation_details?: RawCitation[];
}

/** DOI-first identity for a citing paper (matches the attribution audit's dedup). */
function citingKey(c: RawCitation): string {
  const doi = c.doi;
  if (doi) {
    return `doi:${doi
      .trim()
      .toLowerCase()
      .replace(/^doi:/, "")
      .replace(/[.,;:]+$/, "")}`;
  }
  if (c.openalex_id) {
    return `openalex:${c.openalex_id.trim().toLowerCase()}`;
  }
  if (c.pmid) {
    return `pmid:${String(c.pmid).trim()}`;
  }
  return `title:${(c.title ?? "").trim().toLowerCase().replace(/\s+/g, " ")}`;
}

function toCitation(c: RawCitation): Citation {
  return {
    title: c.title?.trim() || "Untitled",
    authors: c.author?.trim() || "",
    year: typeof c.year === "number" && c.year > 0 ? c.year : null,
    venue: c.venue?.trim() || "",
    url: c.url?.trim() || null,
    doi: c.doi?.trim() || null,
    citedBy: typeof c.cited_by === "number" ? c.cited_by : 0,
    confidence: c.confidence_scoring?.confidence_score ?? null,
  };
}

function readDatasetName(id: string): string {
  if (!datasetsDir) {
    return id;
  }
  const path = join(datasetsDir, `${id}_datasets.json`);
  if (!existsSync(path)) {
    return id;
  }
  try {
    const meta = JSON.parse(readFileSync(path, "utf-8")) as {
      dataset_description?: { Name?: string } | null;
    };
    return meta.dataset_description?.Name?.trim() || id;
  } catch {
    return id;
  }
}

let cache: LoadedData | null = null;

/** Load the full dataset + overview once (memoized across page builds). */
export function loadAll(): LoadedData {
  if (cache) {
    return cache;
  }
  const empty: LoadedData = {
    overview: {
      datasetCount: 0,
      datasetsWithCitations: 0,
      totalCitations: 0,
      uniqueCitations: 0,
    },
    datasets: [],
  };

  if (!citationsDir) {
    if (ALLOW_EMPTY) {
      console.warn(`[data] citations/json_opencite/ not found; building empty. ${EMPTY_HINT}`);
      cache = empty;
      return cache;
    }
    throw new Error(`[data] Cannot locate citations/json_opencite/. ${EMPTY_HINT}`);
  }

  const files = readdirSync(citationsDir).filter((f) => f.endsWith("_citations.json"));
  if (files.length === 0) {
    if (ALLOW_EMPTY) {
      console.warn(`[data] ${citationsDir} has no *_citations.json; building empty.`);
      cache = empty;
      return cache;
    }
    throw new Error(`[data] ${citationsDir} has no *_citations.json files. ${EMPTY_HINT}`);
  }

  let totalCitations = 0;
  let datasetsWithCitations = 0;
  const unique = new Set<string>();
  const datasets: DatasetDetail[] = [];

  for (const fileName of files) {
    let raw: RawFile;
    try {
      raw = JSON.parse(readFileSync(join(citationsDir, fileName), "utf-8")) as RawFile;
    } catch (err) {
      console.warn(`[data] skipping ${fileName}: ${err instanceof Error ? err.message : err}`);
      continue;
    }
    const id = raw.dataset_id || fileName.replace("_citations.json", "");
    const details = raw.citation_details ?? [];
    const num = raw.num_citations ?? details.length;
    totalCitations += num;
    for (const c of details) {
      unique.add(citingKey(c));
    }
    // Count + render only datasets with renderable citation_details (a file can
    // carry num_citations > 0 with empty details after a partial fetch).
    if (details.length > 0) {
      datasetsWithCitations += 1;
      const citations = details.map(toCitation).sort((a, b) => b.citedBy - a.citedBy);
      datasets.push({ id, name: readDatasetName(id), numCitations: num, citations });
    }
  }

  datasets.sort((a, b) => b.numCitations - a.numCitations);
  cache = {
    overview: {
      datasetCount: files.length,
      datasetsWithCitations,
      totalCitations,
      uniqueCitations: unique.size,
    },
    datasets,
  };
  return cache;
}
