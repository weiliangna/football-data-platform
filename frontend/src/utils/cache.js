const PREFIX = "football-data:";

export function readCached(key) {
  try {
    const raw = localStorage.getItem(`${PREFIX}${key}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

export function writeCached(key, payload) {
  if (!payload || typeof payload !== "object") return;
  try {
    localStorage.setItem(`${PREFIX}${key}`, JSON.stringify({
      payload,
      updatedAt: new Date().toISOString(),
    }));
  } catch {
    // Browser storage is an enhancement; quota/private-mode failures must not
    // affect the live API request.
  }
}

