/** Pure build-time chart helpers (no DOM). Shared by the SVG chart components. */

/** A rounded axis: tick values 0..>=max with a 1/2/5 x 10^n step. */
export function niceTicks(max: number, targetCount = 5): { ticks: number[]; max: number } {
  if (!Number.isFinite(max) || max <= 0) {
    return { ticks: [0, 1], max: 1 };
  }
  const rawStep = max / targetCount;
  const mag = 10 ** Math.floor(Math.log10(rawStep));
  const norm = rawStep / mag;
  const niceNorm = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
  const step = niceNorm * mag;
  const niceMax = Math.ceil(max / step) * step;
  const raw: number[] = [];
  for (let v = 0; v <= niceMax + step / 2; v += step) {
    raw.push(Math.round(v));
  }
  // Dedupe: small integer maxima (e.g. max=1) can round adjacent ticks to the
  // same value, which would render overlapping axis labels.
  const ticks = [...new Set(raw)];
  return { ticks, max: niceMax };
}

/** Choose a subset of categorical labels (e.g. years) so at most `maxLabels`
 * are shown; always keeps the first and last. Returns the indexes to label. */
export function labelStride(count: number, maxLabels = 8): Set<number> {
  const keep = new Set<number>();
  if (count <= 0) {
    return keep;
  }
  const stride = Math.max(1, Math.ceil(count / maxLabels));
  for (let i = 0; i < count; i += stride) {
    keep.add(i);
  }
  keep.add(count - 1);
  return keep;
}

export const compact = (n: number): string =>
  n >= 1000 ? `${(n / 1000).toLocaleString("en-US", { maximumFractionDigits: 1 })}k` : `${n}`;

export const withCommas = (n: number): string => n.toLocaleString("en-US");
