/**
 * Static endpoint emitting the map points as /maps/umap.json (under base
 * /citations) at build time. The maps page fetches this client-side to render
 * the interactive canvas, so only the maps page pays for the ~1MB payload.
 *
 * Dataset coordinates come from the UMAP export (dashboard_data/umap_points.json),
 * but the citation COUNT and NAME are taken from the authoritative build-time
 * data layer (lib/data.ts) so the map matches the rest of the dashboard. The
 * raw export count is the unfiltered total (e.g. 263 for ds005752); the
 * authoritative count is high-confidence + methods-excluded (117).
 */
import type { APIRoute } from "astro";
import { loadAll } from "../../lib/data";
import { loadUmapPoints } from "../../lib/maps";

export const GET: APIRoute = () => {
  const { datasets: coords, citations } = loadUmapPoints();
  const { datasets } = loadAll();
  const countById = new Map(datasets.map((d) => [d.id, d.numCitations]));
  const nameById = new Map(datasets.map((d) => [d.id, d.name]));

  const enrichedDatasets = coords.map((p) => ({
    id: p.id,
    x: p.x,
    y: p.y,
    name: nameById.get(p.id) ?? p.name,
    count: countById.get(p.id) ?? 0,
  }));

  return new Response(JSON.stringify({ datasets: enrichedDatasets, citations }), {
    headers: { "content-type": "application/json" },
  });
};
