/** Build-time loader for per-dataset primary modality
 * (dashboard_data/dataset_modalities.json, produced by
 * `dataset-citations-export-modalities` from the api.nemar.org catalog).
 * Empty-safe: a missing file yields an empty map and the modality chart is
 * simply omitted. */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { findRepoPath } from "./repo";

/** id (dataset_id or source_id) -> primary modality (eeg/meg/ieeg/emg/nirs/other). */
export function loadModalities(): Map<string, string> {
  const map = new Map<string, string>();
  const path = findRepoPath(join("dashboard_data", "dataset_modalities.json"));
  if (!path) {
    return map;
  }
  try {
    const data = JSON.parse(readFileSync(path, "utf-8")) as {
      modalities?: Record<string, string>;
    };
    for (const [id, modality] of Object.entries(data.modalities ?? {})) {
      map.set(id, modality);
    }
  } catch (err) {
    console.warn(
      `[modality] failed to parse dataset_modalities.json: ${err instanceof Error ? err.message : err}`,
    );
  }
  return map;
}

/** Display label + chart color (NEMAR modality tokens) per modality key. */
export const MODALITY_META: Record<string, { label: string; color: string }> = {
  eeg: { label: "EEG", color: "var(--modality-eeg)" },
  meg: { label: "MEG", color: "var(--modality-meg)" },
  ieeg: { label: "iEEG", color: "var(--modality-ieeg)" },
  emg: { label: "EMG", color: "var(--modality-emg)" },
  nirs: { label: "fNIRS", color: "var(--modality-other)" },
  other: { label: "Other", color: "var(--modality-other)" },
};

/** Stable display order for modality slices. */
export const MODALITY_ORDER = ["eeg", "meg", "ieeg", "emg", "nirs", "other"];
