# Savia MVP

Telegram bot + web storefront. A seller sends a photo and a short note to the bot; Claude writes the product card
and translates it to Uzbek/Russian/English. Buyers open the shop link and ask each product questions; the AI answers
only from the seller's data and forwards unknown questions to the seller in Telegram.

## Run
```bash
cp .env.example .env   # fill BOT_TOKEN and ANTHROPIC_API_KEY
npm install
npm start              # export the .env vars first, e.g.  set -a; . ./.env; set +a
npm test               # smoke test (mock AI, no keys needed)
```
Without `ANTHROPIC_API_KEY` a mock AI is used; without `BOT_TOKEN` only the storefront runs.

## Not in v1
Voice input, cart/payments, image agents, PDF catalog, WhatsApp, multi-user shops.
