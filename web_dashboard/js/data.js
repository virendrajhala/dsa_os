// The python server (scripts/serve_dashboard.py) owns /api/feed. Any http origin
// is allowed to TRY it — no port hardcode — but failures are classified so the
// banner can say exactly what is wrong instead of silently degrading.
export async function fetchFeedStatus() {
  if (window.location.protocol !== "http:" && window.location.protocol !== "https:") {
    return { feed: null, status: "static-server", detail: "Not served over http — run `make web-dashboard`." };
  }
  let response;
  try {
    response = await fetch("/api/feed", { cache: "no-store" });
  } catch (error) {
    return { feed: null, status: "server-down", detail: `No /api/feed at ${window.location.origin} — run \`make web-dashboard\` (port 8765).` };
  }
  if (!response.ok) {
    return { feed: null, status: response.status === 404 ? "static-server" : "feed-error", detail: `/api/feed returned ${response.status} — this origin is not the dashboard server. Run \`make web-dashboard\`.` };
  }
  try {
    const feed = await response.json();
    if (feed && !feed.error) return { feed, status: "ok", detail: "" };
    return { feed: null, status: "feed-error", detail: `Feed error: ${feed?.error || "empty payload"}` };
  } catch (error) {
    return { feed: null, status: "feed-error", detail: `Feed parse failed: ${error.message}` };
  }
}
