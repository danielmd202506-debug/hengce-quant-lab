const SNAPSHOT_URL =
  "https://raw.githubusercontent.com/danielmd202506-debug/hengce-quant-lab/main/public/quant-signals.json";

export async function GET(request: Request) {
  try {
    const response = await fetch(`${SNAPSHOT_URL}?t=${Date.now()}`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`GitHub snapshot ${response.status}`);
    const snapshot = await response.json();
    return Response.json(snapshot, {
      headers: { "Cache-Control": "no-store, max-age=0" },
    });
  } catch {
    const fallback = new URL("/quant-signals.json", request.url);
    const response = await fetch(fallback, { cache: "no-store" });
    if (!response.ok) {
      return Response.json({ error: "量化快照暂时不可用" }, { status: 503 });
    }
    return new Response(await response.text(), {
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store, max-age=0",
        "X-Quant-Source": "bundled-fallback",
      },
    });
  }
}
