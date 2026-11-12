/** Minimal Telegram Bot API client (long polling) — only what the agent needs. */

export interface TgUser {
  id: number;
  first_name?: string;
  username?: string;
}
export interface TgChat {
  id: number;
  type: "private" | "group" | "supergroup" | "channel";
  title?: string;
  username?: string;
}
export interface TgPhotoSize {
  file_id: string;
  file_unique_id: string;
  width: number;
  height: number;
  file_size?: number;
}
export interface TgMessage {
  message_id: number;
  date: number;
  chat: TgChat;
  from?: TgUser;
  text?: string;
  caption?: string;
  photo?: TgPhotoSize[];
  document?: { file_id: string; mime_type?: string; file_name?: string; file_size?: number };
  media_group_id?: string;
  location?: { latitude: number; longitude: number };
  forward_origin?: {
    type: "channel" | "user" | "hidden_user" | "chat";
    chat?: TgChat;
    sender_chat?: TgChat;
    message_id?: number;
    date?: number;
  };
  reply_to_message?: TgMessage;
}
export interface TgCallbackQuery {
  id: string;
  from: TgUser;
  message?: TgMessage;
  data?: string;
}
export interface TgUpdate {
  update_id: number;
  message?: TgMessage;
  channel_post?: TgMessage;
  callback_query?: TgCallbackQuery;
}
export type InlineKeyboard = { text: string; callback_data?: string; url?: string }[][];

export class Telegram {
  constructor(
    private readonly token: string,
    private readonly apiBase: string,
  ) {}

  private async api<T>(method: string, params: Record<string, unknown> = {}, timeoutMs = 30_000): Promise<T> {
    for (let attempt = 0; ; attempt++) {
      const res = await fetch(`${this.apiBase}/bot${this.token}/${method}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
        signal: AbortSignal.timeout(timeoutMs),
      });
      const json: any = await res.json().catch(() => ({ ok: false, description: `HTTP ${res.status}` }));
      if (json.ok) return json.result as T;
      const retryAfter = json.parameters?.retry_after;
      if (res.status === 429 && retryAfter && attempt < 3) {
        await new Promise((r) => setTimeout(r, (retryAfter + 1) * 1000));
        continue;
      }
      throw new Error(`Telegram ${method}: ${json.description ?? res.status}`);
    }
  }

  getMe(): Promise<TgUser> {
    return this.api("getMe");
  }

  getUpdates(offset: number, timeoutSec = 50): Promise<TgUpdate[]> {
    return this.api(
      "getUpdates",
      { offset, timeout: timeoutSec, allowed_updates: ["message", "channel_post", "callback_query"] },
      (timeoutSec + 15) * 1000,
    );
  }

  /** Sends text, splitting anything over Telegram's 4096-character limit. Returns the last message. */
  async send(
    chatId: number,
    text: string,
    opts: { html?: boolean; keyboard?: InlineKeyboard; replyTo?: number } = {},
  ): Promise<TgMessage> {
    const chunks = splitText(text || "…");
    let last!: TgMessage;
    for (let i = 0; i < chunks.length; i++) {
      const isLast = i === chunks.length - 1;
      last = await this.api<TgMessage>("sendMessage", {
        chat_id: chatId,
        text: chunks[i],
        ...(opts.html ? { parse_mode: "HTML" } : {}),
        link_preview_options: { is_disabled: true },
        ...(opts.replyTo && i === 0
          ? { reply_parameters: { message_id: opts.replyTo, allow_sending_without_reply: true } }
          : {}),
        ...(isLast && opts.keyboard ? { reply_markup: { inline_keyboard: opts.keyboard } } : {}),
      });
    }
    return last;
  }

  async edit(
    chatId: number,
    messageId: number,
    text: string,
    opts: { html?: boolean; keyboard?: InlineKeyboard } = {},
  ): Promise<void> {
    await this.api("editMessageText", {
      chat_id: chatId,
      message_id: messageId,
      text: text.slice(0, 4096),
      ...(opts.html ? { parse_mode: "HTML" } : {}),
      link_preview_options: { is_disabled: true },
      reply_markup: { inline_keyboard: opts.keyboard ?? [] },
    }).catch((e) => {
      // "message is not modified" is harmless.
      if (!String(e).includes("not modified")) throw e;
    });
  }

  answerCallback(id: string, text?: string): Promise<unknown> {
    return this.api("answerCallbackQuery", { callback_query_id: id, ...(text ? { text } : {}) }).catch(() => {});
  }

  typing(chatId: number): Promise<unknown> {
    return this.api("sendChatAction", { chat_id: chatId, action: "typing" }).catch(() => {});
  }

  async downloadFile(fileId: string): Promise<Buffer> {
    const file = await this.api<{ file_path: string }>("getFile", { file_id: fileId });
    const res = await fetch(`${this.apiBase}/file/bot${this.token}/${file.file_path}`, {
      signal: AbortSignal.timeout(120_000),
    });
    if (!res.ok) throw new Error(`Telegram faylini yuklab bo'lmadi: HTTP ${res.status}`);
    return Buffer.from(await res.arrayBuffer());
  }
}

export function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function splitText(text: string, limit = 4000): string[] {
  const chunks: string[] = [];
  let rest = text;
  while (rest.length > limit) {
    let cut = rest.lastIndexOf("\n", limit);
    if (cut < limit / 2) cut = limit;
    chunks.push(rest.slice(0, cut));
    rest = rest.slice(cut).replace(/^\n/, "");
  }
  chunks.push(rest);
  return chunks;
}
