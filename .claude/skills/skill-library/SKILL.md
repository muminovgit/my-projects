---
name: skill-library
description: Router to ECC skills, agents, commands and rules that are not loaded by default (LIBRARY bucket). Use when the task needs a stack or workflow outside the daily set, such as Python/Django, Go, Rust, Java/Spring, Kotlin/Android, Swift/iOS, Flutter, databases, networking, logistics, healthcare, or other language-specific reviewers and build resolvers.
---

# Skill library

Daily surface (loaded): Vite + React 19 + TypeScript + Tailwind frontend on Netlify, plus sales/lead-gen, docs and marketing work.
Everything else lives in `.claude-library/` (same folder layout: `skills/`, `agents/`, `commands/`, `rules/`). Nothing was deleted.

## How to use
1. Find the item: `ls .claude-library/skills | grep -i <keyword>` (same for agents/commands/rules).
2. Read `.claude-library/skills/<name>/SKILL.md` and follow it, or copy the folder into `.claude/skills/` to load it every session.

## Keywords -> where to look
- Languages: python, django, fastapi, golang, rust, java, springboot, quarkus, kotlin, swift, flutter, dart, cpp, csharp, dotnet, php, laravel, perl, ruby, rails, vue, nuxt, angular
- Data and infra: postgres, mysql, redis, clickhouse, prisma, docker, kubernetes, database-migrations
- Networking: network-*, cisco-ios-patterns, homelab-*
- Business ops: logistics, customs, carrier, inventory, production-scheduling, finance, billing, investor
- Agents and loops: agent-*, autonomous-*, continuous-*, orch-*, team-*, gan-*, ralphinho
- Healthcare, science, ML: healthcare-*, hipaa, scientific-*, pytorch, mle-*
- Rules for other languages: `.claude-library/rules/<language>/`
