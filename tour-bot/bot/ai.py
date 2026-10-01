"""Claude-powered helpers: client Q&A with lead detection, tour drafting and translation."""
import logging
from typing import Protocol

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from bot.db.models import ChatMessage

log = logging.getLogger(__name__)

LANG_NAMES = {"uz": "Uzbek (Latin script)", "ru": "Russian", "en": "English"}


class AssistantReply(BaseModel):
    reply: str  # message for the client
    is_lead: bool = False
    phone: str | None = None
    lead_summary: str = ""  # for the admin only, never shown to the client


class TourDraft(BaseModel):
    category: str = Field(description='One of "domestic", "abroad", "pilgrimage"')
    title: str = Field(description="Title in Uzbek (Latin)")
    description: str = Field(description="Description in Uzbek (Latin): itinerary, what is included")
    title_ru: str
    description_ru: str
    title_en: str
    description_en: str
    price: int = Field(description="Price per person as an integer")
    currency: str = Field(description='"USD" or "UZS"')
    start_date: str | None = Field(default=None, description="DD.MM.YYYY or null if not given")
    seats: int


class Translation(BaseModel):
    title_ru: str
    description_ru: str
    title_en: str
    description_en: str


class AIService(Protocol):
    async def answer(self, lang: str, history: list[ChatMessage], text: str) -> AssistantReply: ...

    async def draft_tour(self, request: str) -> TourDraft: ...

    async def translate(self, title: str, description: str) -> Translation: ...


CHAT_SYSTEM = """You are a creative travel consultant for a travel agency in Uzbekistan, chatting with a client in Telegram.

Your job: understand what the client wants (where, when, how many people, budget, interests, departure city) and design \
a tour tailored to them: a day-by-day route, what to see and do, suggested hotels or areas, flights or transport, \
season tips, visas and documents, and an approximate per-person price range. Use web search to check current flight \
routes, visa rules, prices and events instead of guessing, and say clearly that prices are estimates the manager will confirm.

Rules:
- Reply in {lang_name} unless the client clearly writes in another language; then use that language.
- Ask one or two clarifying questions when key details are missing, but still offer an idea right away.
- Plain text for Telegram: no markdown tables, no links unless asked, keep it readable (short paragraphs or simple lists).
- Payment is not taken in the chat. A manager contacts the client to finalize and book.
- When the client wants to book, asks for a call, shares a phone number, or is clearly ready to buy, call the \
notify_manager tool (once per conversation, again only if they share a phone later), then tell them a manager will \
contact them and, if you do not have their phone yet, ask for it. Never show the client the lead details, \
the word "lead", or what you sent to the manager."""

NOTIFY_TOOL = {
    "name": "notify_manager",
    "description": (
        "Send this client to the agency manager as a lead. Only the manager sees it; the client never does. "
        "Call it when the client wants to book, asks for a call back, shares a phone number, or shows clear buying intent."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "2-4 sentences in Uzbek (Latin) for the manager: destination, dates, people, budget, "
                "the tour you proposed and anything they asked for.",
            },
            "phone": {"type": ["string", "null"], "description": "Client phone number if they shared one, else null"},
        },
        "required": ["summary", "phone"],
        "additionalProperties": False,
    },
    "strict": True,
}

WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 3}

MAX_STEPS = 6


class ClaudeAI:
    def __init__(self, api_key: str, model: str):
        self.client = AsyncAnthropic(api_key=api_key, timeout=120.0, max_retries=1)
        self.model = model

    async def _parse(self, system: str, messages: list[dict], output_format, effort: str = "low"):
        response = await self.client.beta.messages.parse(
            model=self.model,
            max_tokens=4000,
            system=system,
            messages=messages,
            output_format=output_format,
            output_config={"effort": effort},
            # server-side fallback model if a request is declined by safety classifiers
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            raise RuntimeError(f"Claude returned no usable output (stop_reason={response.stop_reason})")
        return response.parsed_output

    async def answer(self, lang: str, history: list[ChatMessage], text: str) -> AssistantReply:
        system = CHAT_SYSTEM.format(lang_name=LANG_NAMES.get(lang, LANG_NAMES["uz"]))
        messages: list[dict] = [{"role": m.role, "content": m.content} for m in history]
        messages.append({"role": "user", "content": text})
        result = AssistantReply(reply="")

        for _ in range(MAX_STEPS):
            response = await self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=system,
                messages=messages,
                tools=[WEB_SEARCH_TOOL, NOTIFY_TOOL],
                output_config={"effort": "low"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            if response.stop_reason == "refusal":
                raise RuntimeError("Claude declined the request")
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "pause_turn":
                continue  # server-side web search loop paused; resend to resume
            if response.stop_reason != "tool_use":
                result.reply = "".join(b.text for b in response.content if b.type == "text").strip()
                return result

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if block.name == "notify_manager":
                    result.is_lead = True
                    result.lead_summary = block.input.get("summary") or ""
                    result.phone = block.input.get("phone") or result.phone
                    content = "Sent to the manager."
                else:
                    content = f"Unknown tool {block.name}"
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": content})
            messages.append({"role": "user", "content": tool_results})

        raise RuntimeError("AI conversation did not finish")

    async def draft_tour(self, request: str) -> TourDraft:
        system = (
            "You create tour listings for a travel agency in Uzbekistan. From the admin's short request, write an "
            "attractive but honest listing in Uzbek (Latin), Russian and English. Use the price, dates and seats the admin "
            "gave; if price or seats are missing, use 0 so the admin notices. Do not invent a start date."
        )
        return await self._parse(system, [{"role": "user", "content": request}], TourDraft, effort="medium")

    async def translate(self, title: str, description: str) -> Translation:
        system = "Translate this Uzbek tour listing into Russian and English. Keep names, prices and dates unchanged."
        content = f"Title: {title}\n\nDescription:\n{description}"
        return await self._parse(system, [{"role": "user", "content": content}], Translation)
