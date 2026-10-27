---
name: lead-finder
description: Free B2B lead finding for selling an ERP (staff attendance, warehouse, payroll, accounting, project management) and IT services (websites, bots). Use when the user asks to find leads, clients, customers, prospects or companies to sell to, or to collect contacts for outreach. Uses only free public sources, no paid tools.
---

# Lead finder (free, public sources only)

## Seller context
- User's firm sells **ERP**: employee attendance, warehouse management, payroll, accounting, project management. Also IT services (websites, Telegram bots).
- Default region: Uzbekistan. Ask for a city/country if the user names none. Write outreach in the user's language (Uzbek/Russian/English).

## Ideal customer
SMEs, roughly 10-300 staff, that have people and stock to manage:
manufacturing, wholesale/distribution, construction, logistics, retail chains, pharmacies, clinics, education centers, agencies.
Strong signals: vacancies for accountant / warehouse keeper / HR / project manager, several branches, "Excel" or "1C" mentions, no modern site or bot.

## Workflow
1. Confirm niche + region + how many leads (default 30).
2. Find companies with WebSearch, e.g. `"<niche> <city> company"`, `"<niche> <city> vakansiya omborchi buxgalter"` (hh.uz and similar job boards show growing firms), `"<niche> <city> directory"`.
3. For each company site run `python3 -I scripts/extract_contacts.py <url> ...` to pull public emails, phones, Telegram links.
4. Optional: OpenStreetMap Overpass for local businesses lacking a `website` tag (may be blocked in sandboxes; try, then fall back).
5. Score each lead 1-5 (size signals, ERP-relevant pain, reachable contact). Drop duplicates and personal numbers.
6. Save a CSV: company, niche, city, website, email, phone, telegram, signal, score, pitch angle. Show top 10 in chat.
7. Offer a short personalized first message per lead (ERP angle or IT-service angle, whichever fits).

## Rules
- Public business contacts only. No LinkedIn/Instagram scraping, no login-walled pages, no guessing private emails.
- Respect robots.txt and rate limits (script waits 1s between requests).
- Never send messages for the user without explicit approval.
- Say honestly how many leads have verified contact data versus none.
