import { createServer } from "./server.js";
import { createBot } from "./bot.js";
import { isMockAI } from "./ai.js";

const port = Number(process.env.PORT ?? 3000);
createServer().listen(port, () => console.log(`storefront on :${port}`));
if (isMockAI) console.warn("ANTHROPIC_API_KEY not set: using mock AI");

const token = process.env.BOT_TOKEN;
if (token) createBot(token).start({ onStart: (me) => console.log(`bot @${me.username} started`) });
else console.warn("BOT_TOKEN not set: Telegram bot disabled");
