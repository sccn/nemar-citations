/**
 * Per-dataset citation detail, emitted as a static file at build time:
 *   dashboard.nemar.org/citations/api/dataset/<id>.json
 *
 * This is the payload the nemar.org dataset page fetches lazily when a user
 * opens the "citations: N" modal (Phase 3, issue #170). The COUNT lives on
 * nemar-cli's D1 so the catalog can order datasets by it without loading
 * citations; the DETAIL stays here as JSON so D1 isn't inflated with per-paper
 * rows. Includes only the counted (high-confidence, methods-excluded) citations
 * — low-confidence ones are deliberately omitted; each carries its confidence
 * score. CORS is set in public/_headers (static files can't carry per-response
 * headers).
 */
import type { APIRoute } from "astro";
import { loadAll } from "../../../lib/data";

export function getStaticPaths() {
  const { datasets } = loadAll();
  return datasets.map((d) => ({ params: { id: d.id } }));
}

export const GET: APIRoute = ({ params }) => {
  const { datasets } = loadAll();
  const d = datasets.find((x) => x.id === params.id);
  // Unreachable: getStaticPaths enumerates exactly these ids, so static output
  // only invokes GET for a known dataset. Guard as a build-time invariant.
  if (!d) {
    throw new Error(`dataset ${params.id} not present in loadAll()`);
  }
  const body = {
    dataset_id: d.id,
    name: d.name,
    num_citations: d.numCitations,
    num_dataset_citations: d.numDatasetCitations,
    num_datapaper_citations: d.numDataPaperCitations,
    // Highest-cited first (already sorted in the data layer).
    citations: d.citations.map((c) => ({
      title: c.title,
      authors: c.authors,
      year: c.year,
      venue: c.venue,
      url: c.url,
      doi: c.doi,
      cited_by: c.citedBy,
      // Relevance score (>= 0.4 here; the counted set is high-confidence only).
      confidence: c.confidence,
      // "dataset" = cites the dataset (accession mention / version / own DOI);
      // "paper" = cites a publication.
      kind: c.provenance.kind,
    })),
  };
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
  });
};
