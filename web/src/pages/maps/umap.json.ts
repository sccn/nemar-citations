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
  // Maps are an enhancement: if the citations corpus is absent, fall back to the
  // raw export counts rather than failing the build (mirrors loadUmapPoints).
  let authoritative: ReturnType<typeof loadAll> | null = null;
  try {
    authoritative = loadAll();
  } catch (err) {
    console.warn(
      `[maps] authoritative counts unavailable, using raw export: ${err instanceof Error ? err.message : err}`,
    );
  }
  const hasAuth = authoritative !== null;
  const countById = new Map((authoritative?.datasets ?? []).map((d) => [d.id, d.numCitations]));
  const nameById = new Map((authoritative?.datasets ?? []).map((d) => [d.id, d.name]));

  const enrichedDatasets = coords.map((p) => ({
    id: p.id,
    x: p.x,
    y: p.y,
    name: nameById.get(p.id) ?? p.name,
    // With the corpus present, a dataset absent from the authoritative set has 0
    // high-confidence citations; only when the whole corpus is missing do we use
    // the (unfiltered) raw export count so the map still renders.
    count: hasAuth ? (countById.get(p.id) ?? 0) : p.count,
  }));

  return new Response(JSON.stringify({ datasets: enrichedDatasets, citations }), {
    headers: { "content-type": "application/json" },
  });
};
