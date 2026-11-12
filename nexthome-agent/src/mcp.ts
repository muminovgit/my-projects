/**
 * Small client for the Nexthome MCP server (Streamable HTTP, JSON-RPC 2.0).
 * Every Nexthome tool returns `{status, data}`; `call()` unwraps it and throws on HTTP errors.
 */

export interface McpTool {
  name: string;
  description?: string;
  inputSchema: Record<string, unknown>;
  annotations?: { readOnlyHint?: boolean; destructiveHint?: boolean };
  _meta?: { securitySchemes?: { type: string; scopes?: string[] }[] };
}

export class NexthomeError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly data?: unknown,
  ) {
    super(message);
  }
}

const PROTOCOL_VERSION = "2025-06-18";

export class NexthomeMcp {
  private nextId = 1;
  private sessionId: string | undefined;
  private initialized: Promise<void> | undefined;
  private toolsCache: McpTool[] | undefined;

  constructor(
    private readonly url: string,
    private readonly token: string | undefined,
  ) {}

  private async rpc(method: string, params?: unknown, notification = false): Promise<any> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
      "MCP-Protocol-Version": PROTOCOL_VERSION,
    };
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    if (this.sessionId) headers["Mcp-Session-Id"] = this.sessionId;

    const body: Record<string, unknown> = { jsonrpc: "2.0", method };
    if (params !== undefined) body.params = params;
    if (!notification) body.id = this.nextId++;

    const res = await fetch(this.url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(120_000),
    });
    const session = res.headers.get("mcp-session-id");
    if (session) this.sessionId = session;
    if (notification) return undefined;

    const text = await res.text();
    let msg: any;
    if ((res.headers.get("content-type") ?? "").includes("text/event-stream")) {
      // Take the JSON-RPC response matching our id from the SSE stream.
      for (const line of text.split(/\r?\n/)) {
        if (!line.startsWith("data:")) continue;
        try {
          const parsed = JSON.parse(line.slice(5));
          if (parsed.id === body.id) msg = parsed;
        } catch {
          /* keep-alive or partial line */
        }
      }
    } else {
      try {
        msg = JSON.parse(text);
      } catch {
        /* handled below */
      }
    }
    if (!msg) throw new NexthomeError(`Nexthome MCP javobi o'qilmadi (HTTP ${res.status})`, res.status);
    if (msg.error) {
      const hint =
        res.status === 401
          ? " — NEXTHOME_MCP_TOKEN noto'g'ri, muddati tugagan yoki kerakli scope yo'q."
          : "";
      throw new NexthomeError(`${msg.error.message ?? "MCP xatosi"}${hint}`, res.status, msg.error);
    }
    return msg.result;
  }

  private init(): Promise<void> {
    this.initialized ??= (async () => {
      await this.rpc("initialize", {
        protocolVersion: PROTOCOL_VERSION,
        capabilities: {},
        clientInfo: { name: "nexthome-agent", version: "1.0.0" },
      });
      await this.rpc("notifications/initialized", undefined, true);
    })();
    this.initialized.catch(() => (this.initialized = undefined));
    return this.initialized;
  }

  async listTools(): Promise<McpTool[]> {
    if (this.toolsCache) return this.toolsCache;
    await this.init();
    const tools: McpTool[] = [];
    let cursor: string | undefined;
    do {
      const page = await this.rpc("tools/list", cursor ? { cursor } : undefined);
      tools.push(...page.tools);
      cursor = page.nextCursor;
    } while (cursor);
    return (this.toolsCache = tools);
  }

  /** Calls a tool and returns the raw `{status, data}` envelope. */
  async callRaw(name: string, args: Record<string, unknown> = {}): Promise<{ status: number; data: any }> {
    await this.init();
    const result = await this.rpc("tools/call", { name, arguments: args });
    let payload = result.structuredContent;
    if (payload === undefined) {
      const text = (result.content ?? []).find((c: any) => c.type === "text")?.text;
      try {
        payload = JSON.parse(text);
      } catch {
        payload = { status: result.isError ? 500 : 200, data: text };
      }
    }
    if (typeof payload?.status !== "number") payload = { status: result.isError ? 500 : 200, data: payload };
    return payload;
  }

  /** Calls a tool and returns its data, throwing NexthomeError for non-2xx API responses. */
  async call<T = any>(name: string, args: Record<string, unknown> = {}): Promise<T> {
    const { status, data } = await this.callRaw(name, args);
    if (status < 200 || status >= 300) {
      throw new NexthomeError(`${name}: HTTP ${status} — ${describeApiError(data)}`, status, data);
    }
    return data as T;
  }
}

export function describeApiError(data: unknown): string {
  if (typeof data === "string") return data.slice(0, 500);
  if (data && typeof data === "object") {
    const d = data as Record<string, unknown>;
    if (typeof d.detail === "string") return d.detail;
    return JSON.stringify(data).slice(0, 500);
  }
  return String(data);
}
