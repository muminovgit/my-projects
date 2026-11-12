/**
 * One-time setup: logs in to Nexthome with the owner's phone + password and creates
 * an MCP connection token for the bot (NEXTHOME_MCP_TOKEN). Nothing is stored except
 * what you copy into .env yourself.
 *
 *   npm run connect
 */
import readline from "node:readline";

const API = (process.env.NEXTHOME_API_URL ?? "https://api.nexthome.uz").replace(/\/$/, "");

function ask(question: string, hidden = false): Promise<string> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: true });
  return new Promise((resolve) => {
    if (hidden) {
      // Do not echo the password while it is typed.
      (rl as any)._writeToOutput = (s: string) => {
        if (s.includes(question)) process.stdout.write(question);
      };
    }
    rl.question(question, (answer) => {
      rl.close();
      if (hidden) process.stdout.write("\n");
      resolve(answer.trim());
    });
  });
}

async function post(path: string, body: unknown, token?: string): Promise<any> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status} ${JSON.stringify(data)}`);
  return data;
}

const phone = await ask("Nexthome telefon raqami (masalan +998901234567): ");
const password = await ask("Parol: ", true);
const moderate = /^(h|ha|y|yes)/i.test(await ask("Moderatsiya huquqi ham berilsinmi? (ha/yo'q): "));
const days = Number(await ask("Token necha kun amal qilsin? [365]: ")) || 365;

const { access } = await post("/api/token/", { phone_number: phone, password });
const scopes = ["nexthome:read", "nexthome:write", ...(moderate ? ["nexthome:moderate"] : [])];
const connection = await post("/api/mcp/connections/", { name: "Telegram agent", scopes, days }, access);

const token = Object.entries(connection).find(
  ([key, value]) => /token|secret|key/i.test(key) && key !== "token_prefix" && typeof value === "string",
)?.[1];

if (token) {
  console.log(`\nTayyor. .env fayliga qo'shing:\n\nNEXTHOME_MCP_TOKEN=${token}\n`);
  console.log(`Amal qilish muddati: ${connection.expires_at}. Token faqat bir marta ko'rsatiladi.`);
} else {
  console.log("\nUlanish yaratildi, lekin javobda token maydoni topilmadi. To'liq javob:");
  console.log(JSON.stringify(connection, null, 2));
}
