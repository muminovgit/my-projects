import Anthropic from "@anthropic-ai/sdk";
import fs from "node:fs";
import path from "node:path";
import { Agent } from "./agent.js";
import { config } from "./config.js";
import {
  Dictionaries,
  Draft,
  SourceImage,
  draftProblems,
  extractDraft,
  loadDictionaries,
  publishDraft,
  regionName,
} from "./listing.js";
import { NexthomeMcp } from "./mcp.js";
import { InlineKeyboard, Telegram, TgCallbackQuery, TgMessage, TgUpdate, escapeHtml } from "./telegram.js";

interface PendingDraft {
  id: string;
  /** Chat where the preview lives and results are reported. */
  chatId: number;
  text: string;
  images: SourceImage[];
  location?: { latitude: number; longitude: number };
  sourceKey: string;
  sourceLabel: string;
  corrections: string[];
  draft: Draft;
  previewMessageId?: number;
  busy?: boolean;
}

const HELP = `Nexthome agent.

E'lon joylash: kanaldagi postni (rasmlari bilan) shu yerga forward qiling. Men uni e'longa aylantirib, qoralamani ko'rsataman — "Joylash" tugmasini bossangiz saytga chiqadi (moderatsiyaga tushadi).

Boshqaruv va analitika: oddiy so'z bilan yozing. Masalan:
- Bu hafta nechta e'lon qo'shildi?
- Moderatsiyada kutayotgan e'lonlarni ko'rsat
- Namangan shahrida ijara narxlari qanday?
- 123-e'lonni tasdiqla
- Agentlik statistikasini ber

Buyruqlar:
/new — suhbatni yangidan boshlash
/id — Telegram ID'ingizni ko'rsatish`;

export class Bot {
  private readonly tg = new Telegram(config.telegramToken, config.telegramApi);
  private readonly mcp = new NexthomeMcp(config.nexthomeMcpUrl, config.nexthomeToken);
  private readonly anthropic = new Anthropic();
  private readonly agent = new Agent(this.anthropic, this.mcp);

  private dict!: Dictionaries;
  private canModerate = false;
  private nextId = 1;

  private readonly drafts = new Map<string, PendingDraft>();
  private readonly confirms = new Map<string, (ok: boolean) => void>();
  private readonly awaitingEdit = new Map<number, string>();
  private readonly mediaGroups = new Map<string, { messages: TgMessage[]; timer: NodeJS.Timeout }>();
  private readonly chatQueues = new Map<number, Promise<void>>();
  /** sourceKey -> announcement id, persisted so a post is not published twice. */
  private posted: Record<string, number> = {};
  private readonly postedFile = path.join(config.dataDir, "posted.json");
  private stopped = false;

  async start(): Promise<void> {
    fs.mkdirSync(config.dataDir, { recursive: true });
    if (fs.existsSync(this.postedFile)) this.posted = JSON.parse(fs.readFileSync(this.postedFile, "utf8"));

    const me = await this.tg.getMe();
    const account = await this.mcp.call("api_users_me_retrieve", { query: {} });
    this.dict = await loadDictionaries(this.mcp);
    this.canModerate = await this.mcp
      .callRaw("api_moderation_session_retrieve", { query: {} })
      .then((r) => r.status === 200)
      .catch(() => false);

    console.log(
      `@${me.username} ishga tushdi. Nexthome akkaunt: ${account.name ?? account.phone_number ?? account.id}` +
        ` | moderator: ${this.canModerate ? "ha" : "yo'q"} | hududlar: ${this.dict.regions.length} | model: ${config.model}`,
    );
    if (!config.adminIds.length) {
      console.warn("ADMIN_IDS bo'sh — bot hech kimga xizmat qilmaydi. Botga /id yozib ID'ni oling va .env ga qo'shing.");
    }

    let offset = 0;
    while (!this.stopped) {
      try {
        const updates = await this.tg.getUpdates(offset);
        for (const update of updates) {
          offset = update.update_id + 1;
          this.dispatch(update);
        }
      } catch (e) {
        if (this.stopped) break;
        console.error("getUpdates xatosi:", e instanceof Error ? e.message : e);
        await new Promise((r) => setTimeout(r, 3000));
      }
    }
  }

  stop(): void {
    this.stopped = true;
  }

  // ---------- routing ----------

  private isAdmin(userId: number | undefined): boolean {
    return userId !== undefined && config.adminIds.includes(userId);
  }

  private dispatch(update: TgUpdate): void {
    const fail = (e: unknown) => console.error("Update xatosi:", e);
    if (update.callback_query) {
      // Callbacks bypass the per-chat queue: the agent may be waiting on one.
      this.onCallback(update.callback_query).catch(fail);
    } else if (update.channel_post) {
      const post = update.channel_post;
      if (config.sourceChannelIds.includes(post.chat.id) && config.adminIds.length) {
        this.collect(post, config.adminIds[0]);
      }
    } else if (update.message) {
      const msg = update.message;
      if (msg.chat.type !== "private") return;
      if (!this.isAdmin(msg.from?.id)) {
        this.tg
          .send(msg.chat.id, `Bu bot faqat Nexthome adminlari uchun.\nSizning Telegram ID: ${msg.from?.id}`)
          .catch(fail);
        return;
      }
      if (isListingSource(msg)) this.collect(msg, msg.chat.id);
      else this.enqueue(msg.chat.id, () => this.onText(msg));
    }
  }

  /** Runs tasks for one chat strictly in order. */
  private enqueue(chatId: number, task: () => Promise<void>): void {
    const prev = this.chatQueues.get(chatId) ?? Promise.resolve();
    const next = prev.then(task).catch(async (e) => {
      console.error("Xato:", e);
      await this.tg.send(chatId, `Xatolik: ${e instanceof Error ? e.message : String(e)}`).catch(() => {});
    });
    this.chatQueues.set(chatId, next);
  }

  /** Albums arrive as separate messages sharing media_group_id; wait briefly to gather them. */
  private collect(msg: TgMessage, reportChatId: number): void {
    const key = msg.media_group_id ? `${msg.chat.id}:${msg.media_group_id}` : `${msg.chat.id}:m${msg.message_id}`;
    const flush = () => {
      const group = this.mediaGroups.get(key);
      this.mediaGroups.delete(key);
      if (group) this.enqueue(reportChatId, () => this.intake(group.messages, reportChatId));
    };
    const existing = this.mediaGroups.get(key);
    if (existing) {
      clearTimeout(existing.timer);
      existing.messages.push(msg);
      existing.timer = setTimeout(flush, 1500);
    } else {
      this.mediaGroups.set(key, { messages: [msg], timer: setTimeout(flush, msg.media_group_id ? 1500 : 0) });
    }
  }

  // ---------- Telegram post -> listing ----------

  private async intake(messages: TgMessage[], chatId: number): Promise<void> {
    messages.sort((a, b) => a.message_id - b.message_id);
    const first = messages[0];
    const text = messages
      .map((m) => m.caption ?? m.text ?? "")
      .filter(Boolean)
      .join("\n\n");
    const origin = first.forward_origin;
    const originChat = origin?.chat ?? origin?.sender_chat ?? (first.chat.type === "channel" ? first.chat : undefined);
    const sourceKey = originChat
      ? `${originChat.id}:${origin?.message_id ?? first.message_id}`
      : `${first.chat.id}:${first.message_id}`;
    const sourceLabel = originChat?.title ?? originChat?.username ?? "to'g'ridan-to'g'ri xabar";

    await this.tg.typing(chatId);
    const images: SourceImage[] = [];
    for (const m of messages) {
      if (images.length >= config.maxImages) break;
      const fileId = m.photo?.length
        ? m.photo[m.photo.length - 1].file_id // sizes are ordered small -> large
        : m.document?.mime_type?.startsWith("image/")
          ? m.document.file_id
          : undefined;
      if (!fileId) continue;
      const mime = m.photo ? "image/jpeg" : m.document!.mime_type!;
      if (mime !== "image/jpeg" && mime !== "image/png" && mime !== "image/webp") continue;
      try {
        images.push({ data: await this.tg.downloadFile(fileId), contentType: mime });
      } catch (e) {
        console.error("Rasm yuklab olinmadi:", e);
      }
    }
    if (!text && !images.length) {
      await this.tg.send(chatId, "Bu xabarda matn ham, rasm ham topilmadi.");
      return;
    }

    const draft = await extractDraft(this.anthropic, this.dict, { text, images });
    if (!draft.is_listing) {
      await this.tg.send(
        chatId,
        `Bu post e'longa o'xshamadi${draft.not_listing_reason ? `: ${draft.not_listing_reason}` : "."}\nManba: ${sourceLabel}`,
      );
      return;
    }

    const pending: PendingDraft = {
      id: String(this.nextId++),
      chatId,
      text,
      images,
      location: messages.find((m) => m.location)?.location,
      sourceKey,
      sourceLabel,
      corrections: [],
      draft,
    };
    this.drafts.set(pending.id, pending);

    const fromChannel = first.chat.type === "channel";
    if (fromChannel && config.autoPublish && !draftProblems(draft).length && !(sourceKey in this.posted)) {
      await this.publish(pending);
      return;
    }
    const sent = await this.tg.send(chatId, this.preview(pending), { html: true, keyboard: this.draftKeyboard(pending) });
    pending.previewMessageId = sent.message_id;
  }

  private preview(p: PendingDraft): string {
    const d = p.draft;
    const price =
      d.total_price !== null
        ? `${d.total_price.toLocaleString("ru-RU")} ${d.currency}`
        : d.price_for_one !== null
          ? `${d.price_for_one.toLocaleString("ru-RU")} ${d.currency} (bir kishiga)`
          : "—";
    const amenities = [d.conditioner && "konditsioner", d.washing_machine && "kir yuvish mashinasi", d.fridge && "muzlatgich"]
      .filter(Boolean)
      .join(", ");
    const lessees = d.lessee_type_ids.map((id) => this.dict.lesseeTypes.find((l) => l.id === id)?.name).filter(Boolean);
    const lines: (string | null)[] = [
      `<b>${escapeHtml(d.title)}</b>`,
      `${d.deal_type === "RENT" ? "Ijara" : "Sotuv"}${d.partnership ? ` · sheriklik${d.need_people_count ? ` (${d.need_people_count} kishi kerak)` : ""}` : ""}`,
      `Narx: ${price}`,
      `Xonalar: ${d.room_count ?? "—"} · Qavat: ${d.floor ?? "—"} · Maydon: ${d.area ? `${d.area} m²` : "—"}`,
      `Hudud: ${escapeHtml(regionName(this.dict, d.region_id))}`,
      `Manzil: ${escapeHtml(d.address ?? "—")}`,
      `Ta'mir: ${d.appartment_status}/10${amenities ? ` · ${amenities}` : ""}`,
      lessees.length ? `Kimlar uchun: ${escapeHtml(lessees.join(", "))}` : null,
      `Aloqa: ${escapeHtml(d.contact_phone ?? "—")}`,
      `Rasmlar: ${p.images.length}`,
      "",
      escapeHtml(d.description.length > 900 ? `${d.description.slice(0, 900)}…` : d.description),
      "",
      `<i>Manba: ${escapeHtml(p.sourceLabel)}</i>`,
    ];
    const problems = [...draftProblems(d), ...d.missing.filter((m) => !/narx/i.test(m))];
    if (problems.length) lines.push(`⚠️ Postda yo'q: ${escapeHtml([...new Set(problems)].join(", "))}`);
    if (p.sourceKey in this.posted) lines.push(`⚠️ Bu post avval joylangan: #${this.posted[p.sourceKey]}`);
    return lines.filter((l) => l !== null).join("\n");
  }

  private draftKeyboard(p: PendingDraft): InlineKeyboard {
    return [
      [
        { text: "✅ Joylash", callback_data: `pub:${p.id}` },
        { text: "✏️ Tuzatish", callback_data: `edit:${p.id}` },
        { text: "❌ Bekor", callback_data: `del:${p.id}` },
      ],
    ];
  }

  private async publish(p: PendingDraft): Promise<void> {
    if (p.busy) return;
    p.busy = true;
    const show = async (text: string, keyboard?: InlineKeyboard) => {
      if (p.previewMessageId) await this.tg.edit(p.chatId, p.previewMessageId, text, { html: true, keyboard });
      else p.previewMessageId = (await this.tg.send(p.chatId, text, { html: true, keyboard })).message_id;
    };
    try {
      await show(`${this.preview(p)}\n\n⏳ Joylanmoqda…`);
      const result = await publishDraft(this.mcp, this.dict, p.draft, p.images, p.location);
      this.posted[p.sourceKey] = result.id;
      fs.writeFileSync(this.postedFile, JSON.stringify(this.posted));
      this.drafts.delete(p.id);

      const notes = [
        `Rasmlar: ${result.uploadedImages}${result.failedImages ? ` (${result.failedImages} tasi yuklanmadi)` : ""}`,
        result.located ? "Xaritada joylashuv belgilandi" : "Xaritada joylashuv belgilanmadi",
        "Holat: moderatsiyada",
      ];
      const keyboard: InlineKeyboard = [[{ text: "🔗 Saytda ochish", url: result.url }]];
      if (this.canModerate) {
        keyboard.push([
          { text: "✅ Tasdiqlash", callback_data: `appr:${result.id}` },
          { text: "🚫 Rad etish", callback_data: `rej:${result.id}` },
        ]);
      }
      await show(`✅ <b>E'lon #${result.id} yaratildi</b>\n${escapeHtml(p.draft.title)}\n${notes.join("\n")}`, keyboard);
    } catch (e) {
      p.busy = false;
      await show(
        `${this.preview(p)}\n\n❌ Joylab bo'lmadi: ${escapeHtml(e instanceof Error ? e.message : String(e))}`,
        this.draftKeyboard(p),
      );
    }
  }

  // ---------- callbacks ----------

  private async onCallback(cb: TgCallbackQuery): Promise<void> {
    if (!this.isAdmin(cb.from.id)) return void this.tg.answerCallback(cb.id, "Ruxsat yo'q");
    const [action, id] = (cb.data ?? "").split(":");
    const chatId = cb.message?.chat.id ?? cb.from.id;

    if (action === "ok" || action === "no") {
      const resolve = this.confirms.get(id);
      this.confirms.delete(id);
      await this.tg.answerCallback(cb.id, resolve ? undefined : "Bu so'rov eskirgan");
      if (resolve && cb.message) {
        const verdict = action === "ok" ? "✅ Tasdiqlandi" : "🚫 Rad etildi";
        await this.tg.edit(chatId, cb.message.message_id, `${cb.message.text ?? ""}\n\n${verdict}`);
      }
      resolve?.(action === "ok");
      return;
    }

    if (action === "appr" || action === "rej") {
      await this.tg.answerCallback(cb.id);
      const status = action === "appr" ? "approved" : "rejected";
      try {
        await this.mcp.call("api_moderation_announcement_create", { body: { announcement_id: Number(id), status } });
        await this.tg.send(chatId, `E'lon #${id}: ${status === "approved" ? "tasdiqlandi ✅" : "rad etildi 🚫"}`);
      } catch (e) {
        await this.tg.send(chatId, `Moderatsiya bajarilmadi: ${e instanceof Error ? e.message : String(e)}`);
      }
      return;
    }

    const draft = this.drafts.get(id);
    if (!draft) return void this.tg.answerCallback(cb.id, "Qoralama topilmadi (bot qayta ishga tushgan bo'lishi mumkin)");
    await this.tg.answerCallback(cb.id);
    if (action === "pub") {
      await this.publish(draft);
    } else if (action === "del") {
      this.drafts.delete(id);
      if (draft.previewMessageId) await this.tg.edit(chatId, draft.previewMessageId, "❌ Bekor qilindi.");
    } else if (action === "edit") {
      this.awaitingEdit.set(chatId, id);
      await this.tg.send(chatId, "Nimani tuzatay? Bir xabarda yozing (masalan: \"narxi 350 dollar, 3-qavat, Davlatobod tumani\").");
    }
  }

  private askConfirm(chatId: number, summary: string): Promise<boolean> {
    const id = String(this.nextId++);
    return new Promise<boolean>((resolve) => {
      const timer = setTimeout(() => {
        if (this.confirms.delete(id)) resolve(false);
      }, 10 * 60_000);
      this.confirms.set(id, (ok) => {
        clearTimeout(timer);
        resolve(ok);
      });
      this.tg
        .send(chatId, `Quyidagi amalni bajaraymi?\n\n${summary}`, {
          keyboard: [
            [
              { text: "✅ Ha", callback_data: `ok:${id}` },
              { text: "🚫 Yo'q", callback_data: `no:${id}` },
            ],
          ],
        })
        .catch(() => {
          this.confirms.delete(id);
          clearTimeout(timer);
          resolve(false);
        });
    });
  }

  // ---------- chat ----------

  private async onText(msg: TgMessage): Promise<void> {
    const chatId = msg.chat.id;
    const text = (msg.text ?? "").trim();
    if (!text) return;

    if (text === "/start" || text === "/help") return void (await this.tg.send(chatId, HELP));
    if (text === "/id") return void (await this.tg.send(chatId, `Telegram ID: ${msg.from?.id}`));
    if (text === "/new") {
      this.agent.reset(chatId);
      this.awaitingEdit.delete(chatId);
      return void (await this.tg.send(chatId, "Suhbat yangidan boshlandi."));
    }

    const editId = this.awaitingEdit.get(chatId);
    if (editId) {
      this.awaitingEdit.delete(chatId);
      const pending = this.drafts.get(editId);
      if (pending) {
        await this.tg.typing(chatId);
        pending.corrections.push(text);
        pending.draft = await extractDraft(this.anthropic, this.dict, {
          text: pending.text,
          images: pending.images,
          corrections: pending.corrections,
        });
        const sent = await this.tg.send(chatId, this.preview(pending), { html: true, keyboard: this.draftKeyboard(pending) });
        pending.previewMessageId = sent.message_id;
        return;
      }
    }

    const typing = setInterval(() => void this.tg.typing(chatId), 4500);
    await this.tg.typing(chatId);
    try {
      const reply = await this.agent.ask(chatId, text, (summary) => this.askConfirm(chatId, summary));
      await this.tg.send(chatId, reply);
    } catch (e) {
      // A failed turn can leave a dangling tool call in the history; start clean next time.
      this.agent.reset(chatId);
      throw e;
    } finally {
      clearInterval(typing);
    }
  }
}

/** Forwarded posts and anything with a photo are treated as listing sources; plain text is chat. */
function isListingSource(msg: TgMessage): boolean {
  return Boolean(msg.forward_origin || msg.photo?.length || msg.document?.mime_type?.startsWith("image/"));
}
