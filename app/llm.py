"""
LLM integration for TechNova Support Bot.

Anthropic path  — used when ANTHROPIC_API_KEY is set.
  Model: claude-haiku-4-5-20251001 with full tool-use for all 5 skills.

Fallback path   — used when no API key is present.
  Intent-based rule engine that covers the most common support flows
  (order lookup, email lookup, product search, policy questions).
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .database import Database

_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

_SYSTEM_PROMPT = """You are **Nova**, the friendly and professional customer support assistant
for **TechNova**, an online electronics and gadgets store.

Your responsibilities:
1. Greet customers warmly and ask how you can help.
2. Answer questions about products, orders, shipping, returns, and warranties
   using the knowledge base context provided and tools available to you.
3. Look up orders when customers provide an order ID or email.
4. Create support tickets for issues you cannot resolve immediately.
5. Escalate to a human agent ONLY when explicitly requested or when the issue
   is beyond your capabilities.

Guidelines:
- Always be polite, empathetic, and concise.
- Never guess — if you don't know, say so and offer to create a ticket.
- For return/refund/warranty requests, check the knowledge base context first.
- Confirm order details before making any changes.
- End every interaction by asking if there is anything else you can help with."""

_TOOLS = [
    {
        "name": "lookup_order",
        "description": "Look up a customer order by order ID. Returns status, items, tracking, and dates.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "Order ID, e.g. ORD-10001"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "lookup_order_by_email",
        "description": "Look up all orders for a customer using their email address.",
        "input_schema": {
            "type": "object",
            "properties": {"email": {"type": "string", "description": "Customer email address"}},
            "required": ["email"],
        },
    },
    {
        "name": "check_product",
        "description": "Check if a product is in stock and get its current price.",
        "input_schema": {
            "type": "object",
            "properties": {"product_name": {"type": "string", "description": "Full or partial product name"}},
            "required": ["product_name"],
        },
    },
    {
        "name": "create_ticket",
        "description": "Create a support ticket for issues that cannot be resolved immediately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_email": {"type": "string"},
                "subject": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["customer_email", "subject", "description", "priority"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Escalate the conversation to a human support agent. Use only when the customer explicitly requests it or the issue is unresolvable.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "customer_email": {"type": "string"},
            },
            "required": ["reason", "customer_email"],
        },
    },
]


def _execute_tool(name: str, inputs: dict[str, Any], db: Database) -> Any:
    if name == "lookup_order":
        order = db.get_order(inputs["order_id"])
        if not order:
            return {"error": f"Order {inputs['order_id']} not found."}
        items = db.get_order_items(inputs["order_id"])
        return {"order": dict(order), "items": items}

    if name == "lookup_order_by_email":
        orders = db.get_orders_by_email(inputs["email"])
        if not orders:
            return {"error": f"No orders found for {inputs['email']}."}
        return {"orders": orders}

    if name == "check_product":
        products = db.search_products(inputs["product_name"])
        if not products:
            return {"error": f"No products matching '{inputs['product_name']}' found."}
        return {"products": products}

    if name == "create_ticket":
        ticket_id = f"TKT-{int(time.time())}"
        ticket = {
            "id": ticket_id,
            "email": inputs["customer_email"],
            "subject": inputs["subject"],
            "description": inputs["description"],
            "priority": inputs["priority"],
            "status": "open",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        os.makedirs("/tmp/tickets", exist_ok=True)
        with open(f"/tmp/tickets/{ticket_id}.json", "w") as fh:
            json.dump(ticket, fh)
        return {"ticket_id": ticket_id, "message": "Ticket created successfully."}

    if name == "escalate_to_human":
        esc_id = f"ESC-{int(time.time())}"
        esc = {
            "id": esc_id,
            "reason": inputs["reason"],
            "email": inputs["customer_email"],
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        os.makedirs("/tmp/escalations", exist_ok=True)
        with open(f"/tmp/escalations/{esc_id}.json", "w") as fh:
            json.dump(esc, fh)
        return {
            "message": "Escalated. A human agent will contact you within 2 hours.",
            "escalation_id": esc_id,
        }

    return {"error": f"Unknown tool: {name}"}


class LLMClient:
    def backend_name(self) -> str:
        return "anthropic/claude-haiku-4-5-20251001" if _API_KEY else "rule-based-fallback"

    # ── Anthropic path ─────────────────────────────────────────────────────────

    def _chat_anthropic(
        self,
        message: str,
        history: list[dict[str, Any]],
        context: str,
        db: Database,
    ) -> str:
        import anthropic  # lazy import

        client = anthropic.Anthropic(api_key=_API_KEY)
        system = _SYSTEM_PROMPT
        if context:
            system += f"\n\n## Relevant Knowledge Base Context\n\n{context}"

        messages: list[dict[str, Any]] = list(history) + [{"role": "user", "content": message}]

        for _ in range(10):  # max 10 tool-call rounds
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system,
                tools=_TOOLS,
                messages=messages,
            )

            if resp.stop_reason != "tool_use":
                for block in resp.content:
                    if hasattr(block, "text"):
                        return block.text
                return "I'm sorry, I couldn't generate a response. Please try again."

            # Execute each tool call and collect results
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    result = _execute_tool(block.name, block.input, db)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        }
                    )
            messages.append({"role": "user", "content": tool_results})

        return "I'm having trouble processing your request right now. Please try again."

    # ── Rule-based fallback path ───────────────────────────────────────────────

    def _chat_fallback(
        self,
        message: str,
        history: list[dict[str, Any]],
        context: str,
        db: Database,
    ) -> str:
        low = message.lower()

        # Greeting (only on first turn)
        if not history and any(w in low for w in ("hello", "hi", "hey", "howdy", "good morning", "good afternoon", "good evening")):
            return (
                "Hello! I'm Nova, TechNova's customer support assistant. "
                "How can I help you today? I can assist with orders, products, "
                "shipping, returns, and warranties."
            )

        # Order ID lookup — matches ORD-XXXXX pattern
        order_match = re.search(r"\b(ORD-\d+)\b", message.upper())
        if order_match:
            oid = order_match.group(1)
            order = db.get_order(oid)
            if order:
                items = db.get_order_items(oid)
                item_list = ", ".join(f"{i['name']} x{i['quantity']}" for i in items) or "N/A"
                tracking = order.get("tracking_number") or "not yet available"
                lines = [
                    f"Here are the details for order **{oid}**:\n",
                    f"- **Status:** {order['status'].title()}",
                    f"- **Items:** {item_list}",
                    f"- **Total:** ${order['total_amount']:.2f}",
                    f"- **Tracking:** {tracking}",
                    f"- **Ordered:** {order['created_at'][:10]}",
                ]
                if order.get("shipped_at"):
                    lines.append(f"- **Shipped:** {order['shipped_at'][:10]}")
                if order.get("delivered_at"):
                    lines.append(f"- **Delivered:** {order['delivered_at'][:10]}")
                lines.append("\nIs there anything else I can help you with?")
                return "\n".join(lines)
            return (
                f"I couldn't find order **{oid}**. "
                "Please double-check the order ID, or provide the email address "
                "associated with your order."
            )

        # Email + order intent
        email_match = re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", low)
        if email_match and any(w in low for w in ("order", "purchase", "bought", "track", "status")):
            email = email_match.group(0)
            orders = db.get_orders_by_email(email)
            if orders:
                lines = [f"I found {len(orders)} order(s) for **{email}**:\n"]
                for o in orders:
                    tracking = f" | Tracking: {o['tracking_number']}" if o.get("tracking_number") else ""
                    lines.append(
                        f"- **{o['id']}** — {o['status'].title()} | "
                        f"${o['total_amount']:.2f} | {o['created_at'][:10]}{tracking}"
                    )
                lines.append("\nShall I look up the full details for any of these orders?")
                return "\n".join(lines)
            return (
                f"I couldn't find any orders for **{email}**. "
                "Please ensure this is the email address used at checkout."
            )

        # Product search
        product_keywords = [
            "earbuds", "headphones", "headphone", "keyboard", "webcam",
            "smartwatch", "watch", "laptop stand", "ssd", "hub", "lamp",
            "power bank", "powerbank",
        ]
        if any(w in low for w in ("product", "price", "stock", "available", "buy") + tuple(product_keywords)):
            for term in product_keywords:
                if term in low:
                    products = db.search_products(term)
                    if products:
                        lines = [f"Here are the results for **{term}**:\n"]
                        for p in products:
                            stock_str = (
                                f"{p['stock_quantity']} in stock"
                                if p["stock_quantity"] > 0
                                else "Out of stock"
                            )
                            lines.append(
                                f"- **{p['name']}** — ${p['price']:.2f} ({stock_str})\n"
                                f"  {p['description']}"
                            )
                        lines.append("\nIs there anything else I can help you with?")
                        return "\n".join(lines)

        # Knowledge base context available — policy/shipping/warranty questions
        if context and any(
            w in low
            for w in ("return", "refund", "warranty", "ship", "delivery", "cancel", "exchange", "policy", "repair")
        ):
            return (
                f"Here's what our policies say:\n\n{context[:900]}\n\n"
                "Would you like me to look up a specific order, or can I help with anything else?"
            )

        # Generic fallback with any available context
        if context:
            return (
                f"Here's some information that might help:\n\n{context[:600]}\n\n"
                "Would you like me to look up an order, check a product, or create a support ticket?"
            )

        return (
            "I'm Nova, your TechNova support assistant! Here's how I can help:\n\n"
            "- **Order status** — share your order ID (e.g. `ORD-10001`) or email\n"
            "- **Product availability** — ask about any product by name\n"
            "- **Shipping & returns** — policies and timelines\n"
            "- **Warranty** — coverage details and how to file a claim\n"
            "- **Support ticket** — I can create one if your issue needs follow-up\n\n"
            "What can I help you with today?"
        )

    # ── Public interface ───────────────────────────────────────────────────────

    def chat(
        self,
        message: str,
        history: list[dict[str, Any]],
        context: str,
        db: Database,
    ) -> str:
        if _API_KEY:
            try:
                return self._chat_anthropic(message, history, context, db)
            except Exception as exc:
                # Anthropic call failed — degrade gracefully
                prefix = f"*(AI backend temporarily unavailable: {exc})*\n\n"
                return prefix + self._chat_fallback(message, history, context, db)
        return self._chat_fallback(message, history, context, db)
