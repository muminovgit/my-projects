# VEX — Hero Section

A full-screen video hero section built with React, TypeScript, Tailwind CSS, and Vite.

## Features

- Full-bleed autoplaying background video (no overlay/dimming)
- Liquid-glass navbar and UI elements
- Character-by-character animated heading (`AnimatedHeading`)
- Staggered fade-in content (`FadeIn`)
- Inter font loaded via Google Fonts, wired into Tailwind's `font-sans`

## Getting started

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
npm run preview
```

## Deploy

This project includes a `netlify.toml`. Connect the repository at
[app.netlify.com](https://app.netlify.com) and it will build with
`npm run build` and publish the `dist` directory automatically.

## Instagram search

The navbar search icon opens an Instagram search (`@username` or `#hashtag`).
It calls a Netlify Function (`netlify/functions/instagram-search.mjs`) that
talks to the Instagram Graph API, so the token never reaches the browser.

Set these in Netlify → Site settings → Environment variables:

- `IG_ACCESS_TOKEN` — long-lived token for an Instagram Business/Creator account
- `IG_USER_ID` — that account's Instagram user id

Limits of the official API: username search only finds Business/Creator
accounts; hashtag search needs the `instagram_basic` permission (+ app review)
and allows 30 unique hashtags per 7 days.

Local testing: `npx netlify dev`.
