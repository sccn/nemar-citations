/**
 * Per-dataset citation detail, emitted as a static file at build time:
 *   dashboard.nemar.org/citations/api/dataset/<id>.json
 *
 * This is the payload the nemar.org dataset page fetches lazily when a user
 * opens the "citations: N" modal (Phase 3, issue #170). The COUNT lives on
 * nemar-cli's D1 so the catalog can order datasets by it without loading
 * citations; the DETAIL stays here as JSON so D1 isn't inflated with per-paper
 * rows. Slimmed to what the modal renders. CORS is set in public/_headers
 * (static files can't carry per-response headers).
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
  if (!d) {
    return new Response(JSON.stringify({ error: "dataset not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
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
      // "dataset" = cites the dataset (accession mention / version / own DOI);
      // "paper" = cites a publication.
      kind: c.provenance.kind,
    })),
  };
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
  });
};
