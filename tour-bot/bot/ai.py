"""Claude-powered helpers: client Q&A with lead detection, tour drafting and translation."""
import logging
from typing import Protocol

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from bot.db.models import ChatMessage, Tour

log = logging.getLogger(__name__)

LANG_NAMES = {"uz": "Uzbek (Latin script)", "ru": "Russian", "en": "English"}


class AssistantReply(BaseModel):
    reply: str = Field(description="Message to send to the client, in the client's language")
    is_lead: bool = Field(description="True when the client wants to book, asks for a call back, or shows clear buying intent")
    phone: str | None = Field(default=None, description="Client phone number if they shared one in this conversation")
    lead_summary: str = Field(default="", description="One or two sentences in Uzbek for the manager: what the client wants")


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
    async def answer(self, lang: str, tours: list[Tour], history: list[ChatMessage], text: str) -> AssistantReply: ...

    async def draft_tour(self, request: str) -> TourDraft: ...

    async def translate(self, title: str, description: str) -> Translation: ...


def catalog_text(tours: list[Tour]) -> str:
    if not tours:
        return "There are no active tours right now."
    lines = []
    for t in tours:
        date = t.start_date.strftime("%d.%m.%Y") if t.start_date else "date by agreement"
        lines.append(
            f"- [{t.category.value}] {t.title} | {t.price} {t.currency} per person | start: {date} | seats: {t.seats}\n"
            f"  {t.description}"
        )
    return "\n".join(lines)


CHAT_SYSTEM = """You are the assistant of a travel agency's Telegram bot. You answer client questions about tours: \
destinations, prices, dates, what is included, visas and documents, and help them choose.

Rules:
- Reply in {lang_name} unless the client clearly writes in another language; then use that language.
- Only state prices, dates and seats that are in the catalog below. If something is not in the catalog, say a manager will clarify it.
- Keep replies short and friendly, suitable for a Telegram chat. Plain text, no markdown.
- Payment is not taken in the bot: a manager contacts the client to finalize.
- When the client wants to book, asks for a call, or is clearly ready to buy, set is_lead to true and, if you do not have \
their phone number yet, ask for it in your reply. They can also use the "Tours" menu button to book directly.

Current tour catalog:
{catalog}"""


class ClaudeAI:
    def __init__(self, api_key: str, model: str):
        self.client = AsyncAnthropic(api_key=api_key)
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

    async def answer(self, lang: str, tours: list[Tour], history: list[ChatMessage], text: str) -> AssistantReply:
        system = CHAT_SYSTEM.format(lang_name=LANG_NAMES.get(lang, LANG_NAMES["uz"]), catalog=catalog_text(tours))
        messages = [{"role": m.role, "content": m.content} for m in history]
        messages.append({"role": "user", "content": text})
        return await self._parse(system, messages, AssistantReply)

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
