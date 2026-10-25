// Thin fetch client. All business logic lives in the backend; the UI only renders API data.
// (Run `npm run gen:api` with the backend up to get full OpenAPI types in src/api-schema.d.ts.)
/* eslint-disable @typescript-eslint/no-explicit-any */
export type Any = any;

async function req(method: string, path: string, body?: unknown, isForm = false): Promise<Any> {
  const r = await fetch(`/api${path}`, {
    method,
    credentials: "include",
    headers: isForm || body === undefined ? undefined : { "content-type": "application/json" },
    body: isForm ? (body as FormData) : body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) {
    let msg = `${r.status}`;
    try { msg = (await r.json()).detail ?? msg; } catch { /* not json */ }
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  const ct = r.headers.get("content-type") || "";
  return ct.includes("json") ? r.json() : r.text();
}

export const api = {
  get: (p: string) => req("GET", p),
  post: (p: string, b?: unknown) => req("POST", p, b ?? {}),
  patch: (p: string, b: unknown) => req("PATCH", p, b),
  del: (p: string) => req("DELETE", p),
  upload: (p: string, files: File[], field = "files") => {
    const fd = new FormData();
    files.forEach((f) => fd.append(field, f));
    return req("POST", p, fd, true);
  },
};

export const money = (n?: number | null, ccy = "INR") =>
  n === undefined || n === null ? "—" : `${ccy} ${Math.round(n).toLocaleString("en-IN")}`;

export function nav(page: string, params: Record<string, string | number | undefined> = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && q.set(k, String(v)));
  window.location.hash = `/${page}${q.toString() ? "?" + q : ""}`;
}

export function route(): { page: string; params: URLSearchParams } {
  const h = window.location.hash.replace(/^#\/?/, "");
  const [page, qs] = h.split("?");
  return { page: page || "overview", params: new URLSearchParams(qs || "") };
}
