# 🤖 TechNova Support Bot — NeamClaw Agent

**A persistent, AI-powered customer support agent for e-commerce — built entirely with the Neam programming language.**

---

## 📌 What Is This Project?

This project is a **fully functional, end-to-end customer support chatbot** for a fictional online electronics store called **TechNova**. It is built using the **Claw Agent** architecture from the **Neam programming language** — a declarative language designed specifically for building AI agents.

The bot ("Nova") can hold multi-turn conversations, remember context across messages, look up real orders from a database, answer policy questions using a knowledge base, create support tickets, and escalate to human agents when needed — all running **100% locally** using Ollama (no paid APIs).

---

## 🌍 Real-World Problem It Solves

### The Problem

E-commerce companies spend **$5–$15 per customer support interaction** when handled by human agents. During peak seasons (sales, holidays), support queues can stretch to **hours-long wait times**, leading to frustrated customers and lost revenue. Small and mid-size businesses often can't afford 24/7 support teams.

Existing chatbot solutions are typically:
- **Rigid rule-based bots** that fail the moment a customer goes off-script
- **Expensive cloud AI APIs** (GPT-4, Claude) that cost $2–$25 per 1M tokens
- **Stateless** — they don't remember what you said 2 messages ago
- **Dumb about your business** — they can't look up orders or check policies

### How This Project Solves It

This bot demonstrates that with the **Neam programming language**, you can build a support agent that is:

| Problem | Our Solution |
|---|---|
| Rigid rule-based bots | LLM-powered natural conversation that handles unexpected questions |
| Expensive cloud APIs | **Ollama + llama3.1** — runs 100% free on your own hardware |
| No conversation memory | **NeamClaw sessions** — persistent JSONL history with auto-compaction |
| Can't access business data | **5 custom skills** — order lookup, ticket creation, product search |
| Doesn't know your policies | **RAG knowledge base** — FAQ, returns, shipping, warranty docs |
| No safety controls | **Sensitive skill flag**, input guards, sandboxed execution |
| Can't handle high traffic | **Concurrency lanes** — default + VIP priority queues |
| No observability | **Traits** — heartbeat monitoring, anomaly detection, sandboxing |

The result is a production-ready support agent that **costs $0/month to run** (vs. $500+/month for cloud AI), **handles unlimited conversations** 24/7, and **actually knows your business**.

---

## 🎯 What I Built

### Core Agent (`support_bot.neam` — 273 lines)

A single Neam source file that defines the entire support system:

**1. Knowledge Base with Hybrid RAG**
```neam
knowledge SupportKB {
  vector_store:       "usearch"
  embedding_model:    "nomic-embed-text"
  retrieval_strategy: "hybrid"          // BM25 + vector search combined
  top_k:              4
  sources: [faq.md, return_policy.md, shipping_info.md, warranty.md]
}
```
- 4 real-world policy documents (~3,000 words total) chunked and indexed
- Hybrid retrieval combines keyword matching (BM25) with semantic vector search
- Top 4 most relevant chunks injected into every LLM call automatically

**2. Five Purpose-Built Skills (Tools)**

| Skill | What It Does | Data Source |
|---|---|---|
| `lookup_order` | Find order by ID (status, tracking, dates) | SQLite query |
| `lookup_order_by_email` | Find all orders for a customer email | SQLite query |
| `create_ticket` | Create support ticket for unresolved issues | Workspace JSON file |
| `check_product` | Check product stock and pricing | SQLite query |
| `escalate_to_human` | Escalate to human agent (**sensitive** — requires approval) | Workspace JSON file |

**3. Persistent Session Management**
```neam
session: {
  storage:            "jsonl"
  idle_reset_minutes: 30
  daily_reset_hour:   4
  max_history_turns:  60
}
```
- Conversations stored as JSONL files, survive server restarts
- Auto-compaction at 80% token budget — keeps recent 20 turns verbatim, summarizes older ones
- Idle sessions reset after 30 minutes, all sessions reset at 4 AM daily

**4. Semantic Memory with Pre-Compaction Flush**
```neam
semantic_memory: {
  backend: "sqlite"
  search:  "hybrid"
  flush_on_compact: true
}
```
- Facts extracted from conversations before compaction (so nothing is truly lost)
- Hybrid search (70% vector + 30% BM25) over accumulated knowledge
- Automatically injected as `[MEMORY CONTEXT]` in every prompt

**5. Multi-Channel Deployment**
- **CLI channel** — terminal interface for development and testing
- **HTTP channel** — REST API at port 8080 for production integration

**6. Concurrency Lanes**
- `default` lane — 4 concurrent requests at normal priority
- `vip` lane — 2 concurrent requests at high priority

**7. Three Trait Implementations**
- **Schedulable** — heartbeat every 5 minutes to monitor ticket directory health
- **Monitorable** — detects escalation spikes (>5/hour triggers alert)
- **Sandboxable** — strict mode: network for DB only, filesystem limited to workspace, no shell commands, 512MB memory cap

### Database (`data/seed.sql`)

A complete SQLite schema with realistic seed data:
- **5 customers** with names, emails, phones
- **10 products** across 5 categories (Audio, Accessories, Wearables, Peripherals, Storage, Home) with stock levels and prices ($39.99–$199.99)
- **7 orders** in all possible states: pending, processing, shipped, delivered, cancelled
- **10 order items** linking orders to products

### Knowledge Documents (`data/`)

Four comprehensive Markdown documents totaling ~3,000 words:
- **faq.md** — 20+ Q&A pairs covering orders, shipping, returns, products, account, contact
- **return_policy.md** — 30-day return window, conditions, restocking fees, refund process, holiday extensions
- **shipping_info.md** — 3 domestic tiers, international rates for 40+ countries, carrier info, delivery issue resolution
- **warranty.md** — 1-year standard warranty, extended plans, claim process, repair vs replacement policy

### Docker Setup

- **Dockerfile** — multi-stage build (compile Neam → minimal runtime with SQLite)
- **docker-compose.yml** — one-command setup: Ollama + model pull + support bot
- **Volume mounts** — sessions and workspace persist across container restarts

---

## 🏗️ Architecture

```
┌──────────────┐       ┌─────────────────────────────────────────────────┐
│   Customer    │       │               NeamClaw Runtime                  │
│  (CLI/HTTP)   │──────▶│                                                 │
└──────────────┘       │  ┌──────────┐  ┌───────────┐  ┌──────────────┐ │
                       │  │ Security │  │  Session   │  │   Context    │ │
                       │  │  Guard   │─▶│  Manager   │─▶│   Builder    │ │
                       │  └──────────┘  │ (JSONL +   │  │ (system +   │ │
                       │                │ compaction) │  │ history +   │ │
                       │                └───────────┘  │ RAG + memory)│ │
                       │                               └──────┬───────┘ │
                       │                                      │         │
                       │                                      ▼         │
                       │                            ┌──────────────┐    │
                       │                            │ 🦙 Ollama    │    │
                       │                            │   llama3.1   │    │
                       │                            └──────┬───────┘    │
                       │                                   │            │
                       │                    ┌──────────────┤            │
                       │                    ▼              ▼            │
                       │              ┌──────────┐  ┌──────────┐       │
                       │              │  Skills   │  │ Response │       │
                       │              │ (5 tools) │  │  Output  │───────▶ 💬
                       │              └─────┬─────┘  └──────────┘       │
                       │                    │                           │
                       │          ┌─────────┼─────────┐                │
                       │          ▼         ▼         ▼                │
                       │     ┌────────┐ ┌────────┐ ┌────────┐         │
                       │     │ SQLite │ │Workspace│ │  RAG   │         │
                       │     │(orders)│ │(tickets)│ │(4 docs)│         │
                       │     └────────┘ └────────┘ └────────┘         │
                       └─────────────────────────────────────────────────┘
```

### Request Pipeline (Step by Step)

1. **Customer sends message** via CLI (terminal) or HTTP POST to `/api/v1/claw/support_bot/sessions/{key}/message`
2. **Security guard** checks input for safety
3. **Lane router** assigns to default or VIP queue based on priority
4. **Session manager** loads conversation history from JSONL, triggers compaction if approaching token limit
5. **Context builder** assembles the prompt: system prompt + conversation history + top-4 RAG chunks + semantic memory context
6. **LLM (Ollama/llama3.1)** generates a response, potentially requesting tool calls
7. **Tool-calling loop** executes requested skills (order lookup → SQLite, ticket creation → workspace, etc.)
8. **Response** sent back to customer through the same channel
9. **Session updated** — new turn appended to JSONL history

---

## 💬 Example Conversation

```
Customer: Hi, I ordered some earbuds last month and they stopped working.
          My email is alice@example.com

Nova:     I'm sorry to hear about your earbuds! Let me look up your orders.
          [calls lookup_order_by_email("alice@example.com")]

          I found your orders:
          • ORD-10001 — Delivered Jan 21 (Earbuds + Power Bank — $129.98)
          • ORD-10003 — Processing (Mechanical Keyboard K7)

          Your earbuds were in order ORD-10001. Since they're defective,
          they should be covered under our 1-year warranty. Let me check...
          [retrieves warranty.md chunks via RAG]

          Good news! Your earbuds are within the 1-year warranty period
          (purchased Jan 15, 2026). Here's what to do:
          1. I'll create a warranty claim ticket for you
          2. Our team will email you a prepaid return label
          3. We'll repair or replace within 10 business days

          Shall I create that ticket now?

Customer: Yes please

Nova:     [calls create_ticket({email: "alice@example.com", subject:
          "Warranty claim - defective Pro Wireless Earbuds",
          priority: "medium"})]

          Done! Ticket TKT-1709234567 has been created. You'll receive
          an email at alice@example.com with next steps.

          Is there anything else I can help with?
```

---

## 🚀 Quick Start

### Option A: Docker (Recommended — Fully Reproducible)

```bash
git clone https://github.com/YOUR_USERNAME/neamclaw-support-bot.git
cd neamclaw-support-bot

cp .env.example .env
docker compose up --build

# First run pulls llama3.1 (~4.7 GB) — takes 5-10 minutes

# Test:
curl -X POST http://localhost:8080/api/v1/claw/support_bot/sessions/test/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-me" \
  -d '{"message": "Hi! What is your return policy?"}'
```

### Option B: Local (Manual Setup)

```bash
git clone https://github.com/YOUR_USERNAME/neamclaw-support-bot.git
cd neamclaw-support-bot

# Start Ollama + pull models
ollama serve &
ollama pull llama3.1
ollama pull nomic-embed-text

# Seed database
sqlite3 ./data/technova.db < ./data/seed.sql

# Compile and run
neamc support_bot.neam -o support_bot.neamb
neam support_bot.neamb          # CLI mode
# OR
neam-api --program support_bot.neamb --port 8080   # HTTP mode
```

---

## 📁 Project Structure

```
neamclaw-support-bot/
├── support_bot.neam          # Complete agent source (273 lines)
│                               ├── MCP server config
│                               ├── Knowledge base (SupportKB)
│                               ├── 5 skill definitions
│                               ├── Claw agent declaration
│                               ├── 3 trait implementations
│                               └── Entry point
├── data/
│   ├── seed.sql              # SQLite schema + seed data
│   ├── faq.md                # FAQ knowledge document (20+ Q&A)
│   ├── return_policy.md      # Return policy document
│   ├── shipping_info.md      # Shipping rates & carriers
│   └── warranty.md           # Warranty terms & claims
├── docker-compose.yml        # Ollama + bot (one command)
├── Dockerfile                # Multi-stage build
├── .env.example              # Environment template
├── .gitignore
└── README.md
```

---

## 🧠 Neam Language Concepts Demonstrated

This project is a comprehensive reference for anyone learning NeamClaw:

| Neam Concept | What It Is | Where Used |
|---|---|---|
| `claw agent` | Persistent conversational agent type | Main agent declaration |
| `knowledge` | RAG knowledge base with vector store | `SupportKB` — 4 docs, hybrid retrieval |
| `skill` with `params` shorthand | Tool/function the agent can call | 5 skills: lookup, ticket, product, escalate |
| `sensitive: true` | Requires human approval before execution | `escalate_to_human` skill |
| `mcp_server` | External tool server via MCP protocol | SQLite database connection |
| `connected_knowledge` | Link RAG knowledge to an agent | `connected_knowledge: [SupportKB]` |
| `session` config | Persistent conversation storage | JSONL, 30min idle reset, 60 turn max |
| `channels` | Input/output interfaces | CLI + HTTP on port 8080 |
| `workspace` | Persistent file storage for agent | Tickets and escalation JSON files |
| `semantic_memory` | Long-term queryable memory | SQLite backend, hybrid search |
| `flush_on_compact` | Extract facts before summarization | Preserves knowledge across compactions |
| `lanes` | Concurrency partitioning with priority | default (4, normal) + vip (2, high) |
| `impl Schedulable` | Periodic heartbeat callbacks | 5-minute health check |
| `impl Monitorable` | Anomaly detection with baselines | Escalation spike detection |
| `impl Sandboxable` | Security sandbox configuration | Strict mode, workspace-only filesystem |
| `workspace_read`/`write` | Native workspace I/O functions | Inside skill implementations |
| `http_post` | HTTP requests from skills | SQLite queries via MCP |
| `json_stringify` | JSON serialization | Ticket creation |
| `timestamp()` | Current time for unique IDs | Ticket and escalation IDs |

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check (no auth required) |
| `GET` | `/api/v1/claw` | List active claw agents |
| `POST` | `/api/v1/claw/support_bot/sessions/{key}/message` | Send message |
| `POST` | `/api/v1/claw/support_bot/sessions/{key}/reset` | Reset session |
| `POST` | `/api/v1/claw/support_bot/compact` | Trigger manual compaction |
| `GET` | `/api/v1/metrics` | Runtime metrics |

All endpoints (except `/health`) require `Authorization: Bearer <NEAM_API_KEY>`.

---

## ⚙️ Configuration Reference

| Parameter | Value | Why |
|---|---|---|
| `provider` | `ollama` | Free, local, no API keys |
| `model` | `llama3.1` | Best open model for tool calling |
| `temperature` | `0.3` | Low = consistent, accurate answers |
| `retrieval_strategy` | `hybrid` | BM25 + vector = best of both worlds |
| `top_k` | `4` | Balances context richness vs noise |
| `idle_reset_minutes` | `30` | Reset stale sessions |
| `max_history_turns` | `60` | Full support conversation length |

---

## 📄 License

MIT License

---

## 🙏 Acknowledgments

- **Neam Language** — [neam-lang/neam](https://github.com/neam-lang/neam)
- **Ollama** — [ollama.com](https://ollama.com) for free local LLM inference
- **Mentor** — Praveen Govindaraj for project guidance
