/**
 * Citation counts manifest, emitted as a static file at build time:
 *   dashboard.nemar.org/citations/api/index.json
 *
 * One row per dataset with citations. nemar-cli ingests this into D1 (citation
 * count columns) so the catalog can order datasets by citation count without
 * loading any per-paper detail (Phase 3, issue #170). The detail lives in the
 * per-dataset endpoints; this manifest stays small (counts only).
 */
import type { APIRoute } from "astro";
import { loadAll } from "../../lib/data";

export const GET: APIRoute = () => {
  const { datasets, overview } = loadAll();
  const body = {
    schema: "nemar-citations/counts@1",
    last_updated: overview.lastUpdated,
    datasets: datasets.map((d) => ({
      dataset_id: d.id,
      num_citations: d.numCitations,
      num_dataset_citations: d.numDatasetCitations,
      num_datapaper_citations: d.numDataPaperCitations,
    })),
  };
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
  });
};
