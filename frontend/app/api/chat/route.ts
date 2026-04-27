import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  isToolUIPart,
  type UIMessage,
  type UIMessageChunk,
} from "ai";
import { parseSseStream } from "./sse";

export const runtime = "nodejs";
export const maxDuration = 60;

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const SUPPLIER_ORDER_TOOL = "envoyer_commande_fournisseur";
const PANTRY_PHOTO_TOOL = "mettre_a_jour_stock_depuis_photo";
const APPROVAL_TOOLS = new Set([SUPPLIER_ORDER_TOOL, PANTRY_PHOTO_TOOL]);

type BackendTokenPayload = { content: string };
type BackendToolCallPayload = { id: string; name: string; args: Record<string, unknown> };
type BackendToolResultPayload = { id: string; content: unknown; is_error: boolean };
type BackendInterruptPayload = {
  id: string;
  kind: string;
  email?: { to?: string; subject?: string; body?: string } | null;
  notion_row?: Record<string, unknown> | null;
  supplier?: { name?: string; email?: string } | null;
  data?: Record<string, unknown> | null;
};
type BackendErrorPayload = { message?: string };

type RequestBody = {
  messages?: UIMessage[];
  id?: string;
};

type ApprovalResponse = {
  toolCallId: string;
  approved: boolean;
  reason?: string;
};

export async function POST(req: Request): Promise<Response> {
  let body: RequestBody;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "invalid_json" }, { status: 400 });
  }

  const conversationId = typeof body.id === "string" ? body.id : undefined;
  const messages = body.messages ?? [];
  const approvalResponse = findPendingApprovalResponse(messages);

  let upstream: Response;
  try {
    if (approvalResponse) {
      if (!conversationId) {
        return Response.json({ error: "missing_conversation_id" }, { status: 400 });
      }
      const decision = decisionFromApproval(approvalResponse);
      upstream = await fetch(`${BACKEND_URL}/v1/chat/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({
          conversation_id: conversationId,
          action: decision.action,
          payload: decision.payload ?? null,
        }),
        signal: req.signal,
      });
    } else {
      const userText = extractLastUserText(messages);
      const userImages = extractLastUserImages(messages);
      if (!userText && userImages.length === 0) {
        return Response.json({ error: "empty_message" }, { status: 400 });
      }
      upstream = await fetch(`${BACKEND_URL}/v1/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({
          message: userText || "(photo jointe)",
          conversation_id: conversationId,
          images: userImages,
        }),
        signal: req.signal,
      });
    }
  } catch (err) {
    console.error("[api/chat] upstream fetch failed:", err);
    return Response.json({ error: "backend_unavailable" }, { status: 502 });
  }

  if (!upstream.ok || !upstream.body) {
    console.error("[api/chat] upstream returned non-2xx:", upstream.status);
    return Response.json({ error: "backend_unavailable" }, { status: 502 });
  }

  const upstreamBody = upstream.body;

  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      const textId = crypto.randomUUID();
      let textOpen = false;

      const closeText = () => {
        if (textOpen) {
          writer.write({ type: "text-end", id: textId } satisfies UIMessageChunk);
          textOpen = false;
        }
      };

      try {
        for await (const evt of parseSseStream(upstreamBody, req.signal)) {
          switch (evt.event) {
            case "token": {
              const payload = safeParse<BackendTokenPayload>(evt.data);
              if (!payload || typeof payload.content !== "string") break;
              if (!textOpen) {
                writer.write({ type: "text-start", id: textId } satisfies UIMessageChunk);
                textOpen = true;
              }
              writer.write({
                type: "text-delta",
                id: textId,
                delta: payload.content,
              } satisfies UIMessageChunk);
              break;
            }
            case "tool_call": {
              const payload = safeParse<BackendToolCallPayload>(evt.data);
              if (!payload) break;
              closeText();
              writer.write({
                type: "tool-input-available",
                toolCallId: payload.id,
                toolName: payload.name,
                input: payload.args,
              } satisfies UIMessageChunk);
              break;
            }
            case "tool_result": {
              const payload = safeParse<BackendToolResultPayload>(evt.data);
              if (!payload) break;
              if (payload.is_error) {
                writer.write({
                  type: "tool-output-error",
                  toolCallId: payload.id,
                  errorText:
                    typeof payload.content === "string"
                      ? payload.content
                      : JSON.stringify(payload.content ?? "tool error"),
                } satisfies UIMessageChunk);
              } else {
                writer.write({
                  type: "tool-output-available",
                  toolCallId: payload.id,
                  output: payload.content,
                } satisfies UIMessageChunk);
              }
              break;
            }
            case "interrupt": {
              const payload = safeParse<BackendInterruptPayload>(evt.data);
              if (!payload) break;
              closeText();
              if (payload.kind === "supplier_order_approval") {
                writer.write({
                  type: "tool-approval-request",
                  approvalId: payload.id,
                  toolCallId: payload.id,
                } satisfies UIMessageChunk);
                writer.write({
                  type: "data-supplier-approval",
                  id: payload.id,
                  data: {
                    toolCallId: payload.id,
                    kind: payload.kind,
                    email: payload.email ?? null,
                    notionRow: payload.notion_row ?? null,
                    supplier: payload.supplier ?? null,
                  },
                } as UIMessageChunk);
              } else if (payload.kind === "pantry_stock_approval") {
                const data = (payload.data ?? {}) as {
                  matched?: unknown;
                  unmatched?: unknown;
                };
                writer.write({
                  type: "tool-approval-request",
                  approvalId: payload.id,
                  toolCallId: payload.id,
                } satisfies UIMessageChunk);
                writer.write({
                  type: "data-pantry-approval",
                  id: payload.id,
                  data: {
                    toolCallId: payload.id,
                    kind: payload.kind,
                    matched: Array.isArray(data.matched) ? data.matched : [],
                    unmatched: Array.isArray(data.unmatched) ? data.unmatched : [],
                  },
                } as UIMessageChunk);
              } else {
                console.warn("[api/chat] unknown interrupt kind:", payload.kind);
              }
              break;
            }
            case "done": {
              closeText();
              return;
            }
            case "error": {
              const payload = safeParse<BackendErrorPayload>(evt.data);
              writer.write({
                type: "error",
                errorText: payload?.message ?? "stream failed",
              } satisfies UIMessageChunk);
              return;
            }
          }
        }
        closeText();
      } catch (err) {
        if (isAbort(err)) return;
        console.error("[api/chat] translator crashed:", err);
        writer.write({ type: "error", errorText: "stream failed" } satisfies UIMessageChunk);
      }
    },
    onError: (err) => {
      console.error("[api/chat] stream onError:", err);
      return "stream failed";
    },
  });

  return createUIMessageStreamResponse({ stream });
}

function findPendingApprovalResponse(messages: UIMessage[]): ApprovalResponse | null {
  const last = messages.at(-1);
  if (!last || last.role !== "assistant") return null;
  for (const part of last.parts) {
    if (!isToolUIPart(part)) continue;
    const toolName = "toolName" in part ? part.toolName : part.type.replace(/^tool-/, "");
    if (!APPROVAL_TOOLS.has(toolName)) continue;
    if (part.state !== "approval-responded") continue;
    const approval = part.approval;
    if (!approval) continue;
    return {
      toolCallId: part.toolCallId,
      approved: approval.approved,
      reason: approval.reason,
    };
  }
  return null;
}

type Decision = {
  action: "approve" | "reject" | "edit";
  payload?: Record<string, unknown> | null;
};

function decisionFromApproval(approval: ApprovalResponse): Decision {
  if (!approval.approved) {
    return { action: "reject" };
  }
  if (approval.reason) {
    try {
      const parsed = JSON.parse(approval.reason);
      if (parsed && typeof parsed === "object") {
        return { action: "edit", payload: parsed as Record<string, unknown> };
      }
    } catch {
      // reason wasn't structured JSON — treat as plain approve
    }
  }
  return { action: "approve" };
}

function extractLastUserText(messages: UIMessage[]): string {
  const last = messages.at(-1);
  if (!last || last.role !== "user") return "";
  return last.parts
    .filter((p): p is { type: "text"; text: string } => p.type === "text")
    .map((p) => p.text)
    .join("")
    .trim();
}

function extractLastUserImages(messages: UIMessage[]): string[] {
  const last = messages.at(-1);
  if (!last || last.role !== "user") return [];
  const images: string[] = [];
  for (const part of last.parts) {
    if (part.type !== "file") continue;
    const file = part as { type: "file"; mediaType?: string; url?: string };
    if (!file.mediaType?.startsWith("image/")) continue;
    if (typeof file.url !== "string") continue;
    if (!file.url.startsWith("data:")) continue;
    images.push(file.url);
  }
  return images;
}

function safeParse<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function isAbort(err: unknown): boolean {
  return (
    err instanceof Error &&
    (err.name === "AbortError" || err.name === "ResponseAborted" || err.message.includes("aborted"))
  );
}
