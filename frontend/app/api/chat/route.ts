import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  type UIMessage,
  type UIMessageChunk,
} from "ai";
import { parseSseStream } from "./sse";

export const runtime = "nodejs";
export const maxDuration = 60;

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

type BackendTokenPayload = { content: string };
type BackendToolCallPayload = { id: string; name: string; args: Record<string, unknown> };
type BackendToolResultPayload = { id: string; content: unknown; is_error: boolean };
type BackendErrorPayload = { message?: string };

export async function POST(req: Request): Promise<Response> {
  let body: { messages?: UIMessage[]; id?: string };
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "invalid_json" }, { status: 400 });
  }

  const userText = extractLastUserText(body.messages ?? []);
  if (!userText) {
    return Response.json({ error: "empty_message" }, { status: 400 });
  }

  const conversationId = typeof body.id === "string" ? body.id : undefined;

  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND_URL}/v1/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ message: userText, conversation_id: conversationId }),
      signal: req.signal,
    });
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
            case "done": {
              if (textOpen) {
                writer.write({ type: "text-end", id: textId } satisfies UIMessageChunk);
                textOpen = false;
              }
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

        if (textOpen) {
          writer.write({ type: "text-end", id: textId } satisfies UIMessageChunk);
          textOpen = false;
        }
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

function extractLastUserText(messages: UIMessage[]): string {
  const last = messages.at(-1);
  if (!last || last.role !== "user") return "";
  return last.parts
    .filter((p): p is { type: "text"; text: string } => p.type === "text")
    .map((p) => p.text)
    .join("")
    .trim();
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
