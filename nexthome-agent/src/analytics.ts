import { NexthomeMcp } from "./mcp.js";

const MAX_LISTINGS = 2000;

function countBy<T>(items: T[], key: (item: T) => string | number | null | undefined): Record<string, number> {
  const out: Record<string, number> = {};
  for (const item of items) {
    const k = String(key(item) ?? "noma'lum");
    out[k] = (out[k] ?? 0) + 1;
  }
  return out;
}

function priceStats(values: number[]): { count: number; min: number; median: number; avg: number; max: number } | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const median = sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  return {
    count: sorted.length,
    min: sorted[0],
    median,
    avg: Math.round(sorted.reduce((a, b) => a + b, 0) / sorted.length),
    max: sorted[sorted.length - 1],
  };
}

/**
 * Aggregated listing report: pages through /api/announcement/ with the given filters and
 * summarises it, so the model gets totals instead of thousands of raw rows.
 */
export async function listingsReport(mcp: NexthomeMcp, filters: Record<string, unknown>, days = 30) {
  const listings: any[] = [];
  let total = 0;
  for (let page = 1; listings.length < MAX_LISTINGS; page++) {
    const data = await mcp.call("api_announcement_list", { query: { ...filters, page, page_size: 100 } });
    total = data.count ?? total;
    listings.push(...(data.results ?? []));
    if (!data.next || !(data.results ?? []).length) break;
  }

  const since = Date.now() - days * 86_400_000;
  const recent = listings.filter((l) => l.created && Date.parse(l.created) >= since);
  const prices: Record<string, number[]> = {};
  for (const l of listings) {
    if (typeof l.total_price !== "number" || l.total_price <= 0) continue;
    (prices[`${l.deal_type ?? "?"}/${l.currency ?? "?"}`] ??= []).push(l.total_price);
  }

  return {
    filters,
    total_matching: total,
    analysed: listings.length,
    truncated: listings.length < total,
    by_deal_type: countBy(listings, (l) => l.deal_type),
    by_moderation_status: countBy(listings, (l) => l.moderation_status),
    by_active: countBy(listings, (l) => (l.status ? "faol" : "nofaol")),
    by_region_id: countBy(listings, (l) => l.region),
    by_publisher_type: countBy(listings, (l) => l.publisher?.type ?? l.publisher_type),
    by_room_count: countBy(listings, (l) => l.room_count),
    partnership: listings.filter((l) => l.partnership).length,
    without_images: listings.filter((l) => !l.images?.length).length,
    total_price_by_deal_and_currency: Object.fromEntries(
      Object.entries(prices).map(([k, v]) => [k, priceStats(v)]),
    ),
    [`created_last_${days}_days`]: recent.length,
    created_per_day: countBy(recent, (l) => String(l.created).slice(0, 10)),
  };
}
