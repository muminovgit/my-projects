/**
 * End-to-end smoke test against local fakes of Telegram, the Nexthome MCP server and the
 * Anthropic API. Covers: forwarded album -> draft preview -> publish, access control,
 * and an agent write action gated by a confirmation button.
 *
 *   npm test                 (fakes only)
 *   LIVE=1 npm test          (also checks the public tools of the real Nexthome MCP server)
 */
import assert from "node:assert/strict";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import fs from "node:fs";

const ADMIN = 111;
const sent: { method: string; body: any }[] = [];
const updates: any[] = [];
const mcpCalls: { name: string; args: any }[] = [];
const anthropicRequests: any[] = [];
let updateId = 1;

function readBody(req: http.IncomingMessage): Promise<any> {
  return new Promise((resolve) => {
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", () => resolve(raw ? JSON.parse(raw) : {}));
  });
}
const json = (res: http.ServerResponse, body: unknown, status = 200) => {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
};

const DRAFT = {
  is_listing: true,
  not_listing_reason: null,
  title: "2 xonali kvartira, Davlatobod",
  deal_type: "RENT",
  partnership: false,
  need_people_count: null,
  room_count: 2,
  floor: 3,
  area: 54,
  currency: "USD",
  total_price: 300,
  price_for_one: null,
  appartment_status: 8,
  conditioner: true,
  washing_machine: false,
  fridge: true,
  address: "1-kichik nohiya",
  region_id: 16,
  lessee_type_ids: [1, 99],
  contact_phone: "+998901112233",
  description: "2 xonali kvartira ijaraga beriladi.",
  missing: [],
};

function mcpTool(name: string, args: any): { status: number; data: any } {
  mcpCalls.push({ name, args });
  switch (name) {
    case "api_users_me_retrieve":
      return { status: 200, data: { id: 1, name: "Owner" } };
    case "api_regions_list":
      return {
        status: 200,
        data: {
          count: 2,
          next: null,
          results: [
            { id: 14, name: "Namangan viloyati", level: 1, parent: null },
            { id: 16, name: "Davlatobod tumani", level: 2, parent: 14 },
          ],
        },
      };
    case "api_lessee_types_list":
      return { status: 200, data: { count: 1, results: [{ id: 1, name: "Oila" }] } };
    case "api_moderation_session_retrieve":
      return { status: 200, data: { id: 1 } };
    case "api_images_create":
      return { status: 201, data: { id: mcpCalls.length, uuid: `uuid-${mcpCalls.length}` } };
    case "api_geocode_retrieve":
      return { status: 200, data: { results: [{ label: "x", latitude: 41.0, longitude: 71.58 }] } };
    case "api_announcement_create":
      return { status: 201, data: { id: 77, ...args.body } };
    case "api_moderation_announcement_create":
      return { status: 200, data: { ok: true } };
    default:
      return { status: 404, data: { detail: "not found" } };
  }
}

const TOOLS = [
  { name: "api_users_me_retrieve", inputSchema: { type: "object", properties: {} }, annotations: { readOnlyHint: true } },
  {
    name: "api_moderation_announcement_create",
    description: "Approve or reject",
    inputSchema: { type: "object", properties: { body: { type: "object" } } },
    annotations: { readOnlyHint: false },
  },
  { name: "register_create", inputSchema: { type: "object", properties: {} }, annotations: { readOnlyHint: false } },
];

const server = http.createServer(async (req, res) => {
  const url = req.url ?? "";
  // --- Telegram ---
  const tg = /^\/bot[^/]+\/(\w+)/.exec(url);
  if (tg) {
    const body = await readBody(req);
    const method = tg[1];
    if (method === "getUpdates") {
      await new Promise((r) => setTimeout(r, 50));
      return json(res, { ok: true, result: updates.splice(0) });
    }
    if (method === "getMe") return json(res, { ok: true, result: { id: 1, username: "nexthome_test_bot" } });
    if (method === "getFile") return json(res, { ok: true, result: { file_path: `photos/${body.file_id}.jpg` } });
    sent.push({ method, body });
    return json(res, { ok: true, result: { message_id: 1000 + sent.length, chat: { id: body.chat_id }, text: body.text } });
  }
  if (url.startsWith("/file/bot")) {
    res.writeHead(200, { "Content-Type": "image/jpeg" });
    return res.end(Buffer.from([0xff, 0xd8, 0xff, 0xd9]));
  }
  // --- Nexthome MCP ---
  if (url === "/mcp") {
    const body = await readBody(req);
    if (req.headers.authorization !== "Bearer test-token") {
      return json(res, { jsonrpc: "2.0", id: body.id, error: { code: -32001, message: "auth" } }, 401);
    }
    if (body.method === "notifications/initialized") return json(res, {}, 202);
    if (body.method === "initialize") return json(res, { jsonrpc: "2.0", id: body.id, result: { capabilities: {} } });
    if (body.method === "tools/list") return json(res, { jsonrpc: "2.0", id: body.id, result: { tools: TOOLS } });
    const payload = mcpTool(body.params.name, body.params.arguments);
    // Answer as SSE to exercise that code path too.
    res.writeHead(200, { "Content-Type": "text/event-stream" });
    return res.end(
      `event: message\ndata: ${JSON.stringify({ jsonrpc: "2.0", id: body.id, result: { structuredContent: payload, content: [] } })}\n\n`,
    );
  }
  // --- Anthropic ---
  if (url.startsWith("/v1/messages")) {
    const body = await readBody(req);
    anthropicRequests.push(body);
    const last = body.messages[body.messages.length - 1];
    let content: any[];
    let stop_reason = "end_turn";
    if (body.output_config?.format) {
      content = [{ type: "text", text: JSON.stringify(DRAFT) }];
    } else if (Array.isArray(last.content) && last.content[0]?.type === "tool_result") {
      content = [{ type: "text", text: `Natija: ${last.content[0].content}` }];
    } else {
      stop_reason = "tool_use";
      content = [
        {
          type: "tool_use",
          id: "toolu_1",
          name: "api_moderation_announcement_create",
          input: { body: { announcement_id: 77, status: "approved" } },
        },
      ];
    }
    return json(res, {
      id: "msg_1",
      type: "message",
      role: "assistant",
      model: body.model,
      content,
      stop_reason,
      stop_sequence: null,
      usage: { input_tokens: 1, output_tokens: 1 },
    });
  }
  json(res, { error: "unexpected " + url }, 404);
});

async function waitFor<T>(what: string, probe: () => T | undefined | false, ms = 8000): Promise<T> {
  const until = Date.now() + ms;
  while (Date.now() < until) {
    const v = probe();
    if (v) return v;
    await new Promise((r) => setTimeout(r, 30));
  }
  throw new Error(`Timeout: ${what}\nSent so far: ${JSON.stringify(sent, null, 1).slice(0, 3000)}`);
}

const push = (u: object) => updates.push({ update_id: updateId++, ...u });
const adminMsg = (extra: object) => ({
  message: { message_id: updateId, date: 0, chat: { id: ADMIN, type: "private" }, from: { id: ADMIN }, ...extra },
});

await new Promise<void>((r) => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${(server.address() as any).port}`;
Object.assign(process.env, {
  TELEGRAM_BOT_TOKEN: "123:TEST",
  TELEGRAM_API_URL: base,
  ADMIN_IDS: String(ADMIN),
  NEXTHOME_MCP_URL: `${base}/mcp`,
  NEXTHOME_MCP_TOKEN: "test-token",
  ANTHROPIC_API_KEY: "sk-test",
  ANTHROPIC_BASE_URL: base,
  DATA_DIR: fs.mkdtempSync(path.join(os.tmpdir(), "nexthome-agent-")),
});

const { Bot } = await import("../src/bot.js");
const bot = new Bot();
const running = bot.start();

// 1. Forwarded album (2 photos, caption on the first) -> one draft preview.
const origin = { type: "channel", chat: { id: -100500, type: "channel", title: "Namangan uylar" }, message_id: 42 };
const photo = (id: string) => [{ file_id: `${id}s`, file_unique_id: "a", width: 90, height: 90 }, { file_id: id, file_unique_id: "b", width: 1280, height: 960 }];
push(adminMsg({ media_group_id: "g1", forward_origin: origin, photo: photo("p1"), caption: "2 xonali kvartira ijaraga, 300$" }));
push(adminMsg({ media_group_id: "g1", forward_origin: origin, photo: photo("p2") }));
const preview = await waitFor("draft preview", () => sent.find((s) => s.body.reply_markup?.inline_keyboard?.[0]?.[0]?.callback_data?.startsWith("pub:")));
assert.match(preview.body.text, /2 xonali kvartira, Davlatobod/);
assert.match(preview.body.text, /Namangan viloyati, Davlatobod tumani/);
assert.match(preview.body.text, /Rasmlar: 2/);
assert.equal(sent.filter((s) => s.body.reply_markup?.inline_keyboard?.[0]?.[0]?.callback_data?.startsWith("pub:")).length, 1, "album must yield one draft");
const extractReq = anthropicRequests[0];
assert.equal(extractReq.messages[0].content.filter((b: any) => b.type === "image").length, 2);
assert.equal(extractReq.fallbacks, "default");

// 2. Publish.
push({ callback_query: { id: "cb1", from: { id: ADMIN }, message: { message_id: preview.body.message_id ?? 1, chat: { id: ADMIN } }, data: preview.body.reply_markup.inline_keyboard[0][0].callback_data } });
const done = await waitFor("publish result", () => sent.find((s) => s.method === "editMessageText" && /E'lon #77 yaratildi/.test(s.body.text)));
const create = mcpCalls.find((c) => c.name === "api_announcement_create")!;
assert.equal(mcpCalls.filter((c) => c.name === "api_images_create").length, 2);
assert.deepEqual(create.args.body.images.length, 2);
assert.equal(create.args.body.region, 16);
assert.equal(create.args.body.location_x, 41.0);
assert.equal(create.args.body.location_y, 71.58);
assert.deepEqual(create.args.body.lessee_types, [1], "unknown tenant-type ids must be dropped");
assert.match(create.args.body.description, /\+998901112233/);
assert.ok(!("price_for_one" in create.args.body), "absent facts are not sent");
assert.ok(done.body.reply_markup.inline_keyboard.flat().some((b: any) => b.callback_data === "appr:77"));

// 3. Strangers are refused and nothing reaches Claude.
const before = anthropicRequests.length;
push({ message: { message_id: 900, date: 0, chat: { id: 222, type: "private" }, from: { id: 222 }, text: "salom" } });
const refusal = await waitFor("refusal", () => sent.find((s) => s.body.chat_id === 222));
assert.match(refusal.body.text, /222/);
assert.equal(anthropicRequests.length, before);

// 4. Agent write action waits for the confirmation button.
push(adminMsg({ text: "77-e'lonni tasdiqla" }));
const confirm = await waitFor("confirmation prompt", () => sent.find((s) => s.body.reply_markup?.inline_keyboard?.[0]?.[0]?.callback_data?.startsWith("ok:")));
assert.ok(!mcpCalls.some((c) => c.name === "api_moderation_announcement_create"), "write must not run before approval");
const agentReq = anthropicRequests[anthropicRequests.length - 1];
assert.ok(!agentReq.tools.some((t: any) => t.name === "register_create"), "blocked tools are hidden from the agent");
assert.ok(agentReq.tools.some((t: any) => t.name === "listings_report"));
push({ callback_query: { id: "cb2", from: { id: ADMIN }, message: { message_id: 5, chat: { id: ADMIN }, text: "?" }, data: confirm.body.reply_markup.inline_keyboard[0][0].callback_data } });
await waitFor("agent reply", () => sent.find((s) => s.method === "sendMessage" && /^Natija:/.test(s.body.text)));
assert.deepEqual(mcpCalls.find((c) => c.name === "api_moderation_announcement_create")!.args, { body: { announcement_id: 77, status: "approved" } });

bot.stop();
await running;
server.close();
console.log("OK: fake end-to-end flow passed");

// Optional: the real server's public tools (no token needed).
if (process.env.LIVE) {
  const { NexthomeMcp } = await import("../src/mcp.js");
  const { loadDictionaries } = await import("../src/listing.js");
  const live = new NexthomeMcp("https://api.nexthome.uz/mcp", undefined);
  const tools = await live.listTools();
  const dict = await loadDictionaries(live);
  const geo = await live.call("api_geocode_retrieve", { query: { q: "Davlatobod" } });
  assert.ok(tools.some((t) => t.name === "api_announcement_create"));
  assert.ok(dict.regions.length > 10 && dict.lesseeTypes.length > 0);
  assert.ok(Array.isArray(geo.results));
  console.log(`OK: live MCP — ${tools.length} tools, ${dict.regions.length} regions, ${dict.lesseeTypes.length} tenant types`);
}
process.exit(0);
