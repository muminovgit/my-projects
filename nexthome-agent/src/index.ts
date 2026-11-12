import { Bot } from "./bot.js";

const bot = new Bot();
for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.on(signal, () => {
    bot.stop();
    setTimeout(() => process.exit(0), 500).unref();
  });
}
bot.start().catch((e) => {
  console.error("Bot ishga tushmadi:", e instanceof Error ? e.message : e);
  process.exit(1);
});
