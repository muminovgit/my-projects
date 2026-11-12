import fs from "node:fs";
import path from "node:path";

/** Minimal .env loader (KEY=VALUE lines); real environment variables win. */
function loadDotEnv(file: string): void {
  if (!fs.existsSync(file)) return;
  for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const m = /^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/.exec(line);
    if (!m || line.trimStart().startsWith("#")) continue;
    const value = m[2].replace(/^(['"])(.*)\1$/, "$2");
    if (process.env[m[1]] === undefined) process.env[m[1]] = value;
  }
}

loadDotEnv(path.resolve(process.cwd(), ".env"));

function required(name: string): string {
  const v = process.env[name]?.trim();
  if (!v) {
    console.error(`Xato: ${name} sozlanmagan. .env.example faylidan nusxa olib .env ni to'ldiring.`);
    process.exit(1);
  }
  return v;
}

function idList(name: string): number[] {
  return (process.env[name] ?? "")
    .split(/[,\s]+/)
    .filter(Boolean)
    .map(Number)
    .filter((n) => Number.isFinite(n));
}

export const config = {
  telegramToken: required("TELEGRAM_BOT_TOKEN"),
  telegramApi: (process.env.TELEGRAM_API_URL ?? "https://api.telegram.org").replace(/\/$/, ""),
  /** Telegram user IDs allowed to operate the bot. */
  adminIds: idList("ADMIN_IDS"),
  /** Channels where the bot is an admin; their posts are picked up automatically. */
  sourceChannelIds: idList("SOURCE_CHANNEL_IDS"),
  /** Publish channel posts without waiting for an admin's confirmation. */
  autoPublish: /^(1|true|yes)$/i.test(process.env.AUTO_PUBLISH ?? ""),

  nexthomeMcpUrl: process.env.NEXTHOME_MCP_URL ?? "https://api.nexthome.uz/mcp",
  nexthomeToken: required("NEXTHOME_MCP_TOKEN"),
  siteUrl: (process.env.NEXTHOME_SITE_URL ?? "https://nexthome.uz").replace(/\/$/, ""),

  // The Anthropic SDK reads ANTHROPIC_API_KEY itself; checked here for a clear startup error.
  anthropicKey: required("ANTHROPIC_API_KEY"),
  model: process.env.ANTHROPIC_MODEL ?? "claude-opus-5-5",

  dataDir: path.resolve(process.env.DATA_DIR ?? "./data"),
  maxImages: Number(process.env.MAX_IMAGES ?? 10),
};
