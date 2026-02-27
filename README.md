# 🤖 TechNova Support Bot — NeamClaw Agent

A production-ready, persistent conversational customer support agent built with [Neam](https://github.com/neam-lang/neam) using the **Claw Agent** architecture. Powers the support channel for **TechNova**, a fictional e-commerce electronics store.

> Built as an end-to-end demonstration of NeamClaw capabilities including session persistence, RAG knowledge retrieval, tool calling, semantic memory, trait implementations, and multi-channel deployment.

---

## ✨ Features

| Feature | Implementation |
|---|---|
| **Persistent Sessions** | JSONL storage with auto-compaction at 80% token budget |
| **RAG Knowledge Base** | Hybrid retrieval (BM25 + vector) over FAQ, return policy, shipping & warranty docs |
| **Order Lookup** | SQLite database queried via skills (by order ID or email) |
| **Ticket Creation** | Workspace-persisted JSON tickets for unresolved issues |
| **Human Escalation** | Sensitive skill requiring approval before execution |
| **Semantic Memory** | SQLite-backed hybrid search with pre-compaction flush |
| **Multi-Channel** | CLI (dev/testing) + HTTP REST (production) |
| **Concurrency Lanes** | Default + VIP lanes with priority scheduling |
| **Traits** | Schedulable (heartbeat), Monitorable (anomaly detection), Sandboxable (security) |
| **100% Local** | Ollama + llama3.1 — no API keys, no cloud costs |

---

## 📁 Project Structure

```
neamclaw-support-bot/
├── support_bot.neam          # Main Neam source — agent, skills, knowledge, traits
├── data/
│   ├── faq.md                # FAQ knowledge document
│   ├── return_policy.md      # Return policy document
│   ├── shipping_info.md      # Shipping info document
│   ├── warranty.md           # Warranty info document
│   └── seed.sql              # SQLite schema + seed data (customers, products, orders)
├── docker-compose.yml        # One-command setup: Ollama + Support Bot
├── Dockerfile                # Multi-stage build: compile → runtime
├── .env.example              # Environment variable template
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- **OR** local install of:
  - [Neam compiler & runtime](https://github.com/neam-lang/neam) (`neamc`, `neam`, `neam-api`)
  - [Ollama](https://ollama.com/) (for local LLM)
  - SQLite 3

### Option A: Docker (Recommended — Fully Reproducible)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/neamclaw-support-bot.git
cd neamclaw-support-bot

# 2. Copy environment template
cp .env.example .env

# 3. Start everything (Ollama + models + bot)
docker compose up --build

# First run will pull llama3.1 (~4.7 GB) and nomic-embed-text (~274 MB)
# This may take 5–10 minutes on first launch.

# 4. Test it!
curl -X POST http://localhost:8080/api/v1/claw/support_bot/sessions/test-session/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-me" \
  -d '{"message": "Hi! I want to check on my order ORD-10002"}'
```

### Option B: Local (Manual Setup)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/neamclaw-support-bot.git
cd neamclaw-support-bot

# 2. Install & start Ollama, pull models
ollama serve &
ollama pull llama3.1
ollama pull nomic-embed-text

# 3. Seed the database
sqlite3 ./data/technova.db < ./data/seed.sql

# 4. Compile the Neam source
neamc support_bot.neam -o support_bot.neamb

# 5a. Run in CLI mode (interactive terminal)
neam support_bot.neamb

# 5b. OR run as HTTP API server
neam-api --program support_bot.neamb --port 8080
```

---

## 💬 Usage Examples

### CLI Mode

```
========================================
  TechNova Support Bot (Nova) v1.0
  Powered by Neam + Ollama
========================================

You: Hi, I ordered something last week and it hasn't arrived yet.

Nova: I'm sorry to hear that! I'd be happy to help you track your order.
      Could you please share your order ID (e.g., ORD-XXXXX) or the email
      address you used during checkout?

You: My email is bob.m@example.com

Nova: I found your orders! Here's what I see:
      • ORD-10007 — Pending (placed Feb 26) — not yet shipped
      • ORD-10002 — Shipped (placed Feb 20) — tracking: TRK-BB-002

      ORD-10002 is currently in transit. Standard shipping takes 5–7 business
      days, so it should arrive by Feb 28. You can track it with TRK-BB-002.

      Is there anything else I can help with?

You: Actually I want to return the earbuds from my earlier order

Nova: Let me check our return policy for you. Returns are accepted within
      30 days of delivery. Your order ORD-10001 (containing TechNova Pro
      Wireless Earbuds) was delivered on Jan 21. That's 37 days ago,
      which is unfortunately past our 30-day return window.

      I can create a support ticket to see if an exception can be made.
      Would you like me to do that?
```

### HTTP API

```bash
# Start a new session
curl -X POST http://localhost:8080/api/v1/claw/support_bot/sessions/user-123/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-me" \
  -d '{"message": "What is your return policy?"}'

# Continue the conversation (same session)
curl -X POST http://localhost:8080/api/v1/claw/support_bot/sessions/user-123/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-me" \
  -d '{"message": "I want to return order ORD-10004"}'

# Reset a session
curl -X POST http://localhost:8080/api/v1/claw/support_bot/sessions/user-123/reset \
  -H "Authorization: Bearer dev-key-change-me"

# Health check
curl http://localhost:8080/health
```

---

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────────────────────────────────────┐
│   Customer   │      │              NeamClaw Runtime                │
│  (CLI/HTTP)  │─────▶│                                              │
└─────────────┘      │  ┌────────┐   ┌──────────┐   ┌───────────┐  │
                     │  │Session │   │ Knowledge │   │  Semantic  │  │
                     │  │Manager │   │   (RAG)   │   │  Memory    │  │
                     │  └───┬────┘   └─────┬─────┘   └─────┬─────┘  │
                     │      │              │               │         │
                     │      ▼              ▼               ▼         │
                     │  ┌──────────────────────────────────────┐     │
                     │  │          support_bot (Claw)          │     │
                     │  │     provider: ollama / llama3.1      │     │
                     │  └──────┬───────┬───────┬───────┬──────┘     │
                     │         │       │       │       │            │
                     │         ▼       ▼       ▼       ▼            │
                     │  ┌──────┐ ┌────┐ ┌──────┐ ┌──────────┐      │
                     │  │lookup│ │FAQ │ │create│ │ escalate  │      │
                     │  │order │ │RAG │ │ticket│ │ to human  │      │
                     │  └──┬───┘ └────┘ └──┬───┘ └──────────┘      │
                     │     │               │                        │
                     │     ▼               ▼                        │
                     │  ┌──────┐     ┌──────────┐                   │
                     │  │SQLite│     │Workspace │                   │
                     │  │ (DB) │     │(tickets) │                   │
                     │  └──────┘     └──────────┘                   │
                     └──────────────────────────────────────────────┘
```

---

## 🧠 Neam Concepts Demonstrated

| Concept | Where in Code |
|---|---|
| `claw agent` declaration | `support_bot.neam` line ~120 |
| `knowledge` with hybrid RAG | `SupportKB` block |
| `skill` with `params` shorthand | `lookup_order`, `create_ticket`, etc. |
| `sensitive: true` skill | `escalate_to_human` |
| Session config (JSONL, compaction) | `session: { ... }` block |
| Multi-channel (CLI + HTTP) | `channels: [...]` |
| Semantic memory with flush | `semantic_memory: { ... }` |
| Concurrency lanes | `lanes: [...]` |
| `impl Schedulable` trait | Heartbeat monitoring |
| `impl Monitorable` trait | Anomaly detection |
| `impl Sandboxable` trait | Security sandbox |
| `workspace_read` / `workspace_write` | Inside skill implementations |

---

## 🗃️ Database Schema

The SQLite database (`data/technova.db`) contains:

- **customers** — 5 sample customers with names, emails, phones
- **products** — 10 TechNova electronics products with stock levels
- **orders** — 7 orders in various states (pending, processing, shipped, delivered, cancelled)
- **order_items** — Line items linking orders to products

Seeded via `data/seed.sql`. Re-seed anytime:

```bash
rm -f data/technova.db
sqlite3 data/technova.db < data/seed.sql
```

---

## 🔧 Configuration

| Parameter | Default | Description |
|---|---|---|
| `model` | `llama3.1` | Change to `mistral`, `phi3`, `gemma2` etc. |
| `temperature` | `0.3` | Low = consistent; raise for more creative responses |
| `idle_reset_minutes` | `30` | Session resets after N minutes of inactivity |
| `max_history_turns` | `60` | Turns before auto-compaction kicks in |
| `top_k` (RAG) | `4` | Number of knowledge chunks injected per query |
| Lane concurrency | `4` / `2` | Max parallel requests per lane |

---

## 📄 License

MIT License — see [LICENSE](LICENSE).

---

## 🙏 Acknowledgments

- **Neam Language** — [neam-lang/neam](https://github.com/neam-lang/neam)
- **Ollama** — [ollama.com](https://ollama.com)
- Built as an internship project demonstrating NeamClaw agent capabilities.
