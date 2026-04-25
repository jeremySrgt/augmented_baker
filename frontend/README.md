# frontend

Minimal Next.js chat UI for Madeleine, built with [Vercel AI Elements](https://ai-sdk.dev/elements).

- `app/page.tsx` — the `/` page. Composes `Conversation` + `Message` + `PromptInput` + `Tool` from `components/ai-elements/` and wires them to `useChat()` from `@ai-sdk/react`.
- `app/api/chat/route.ts` — the BFF. Receives the AI SDK `UIMessage[]`, POSTs the last user message to `${BACKEND_URL}/v1/chat/stream`, then translates the FastAPI SSE events (`token` / `tool_call` / `tool_result` / `done` / `error`) into AI SDK UI message chunks (`text-delta` / `tool-input-available` / `tool-output-available` / `tool-output-error` / `error`).
- `app/api/chat/sse.ts` — tiny SSE parser used by the BFF.

## Run

```bash
cp .env.example .env.local   # set BACKEND_URL if not http://localhost:8000
pnpm install
pnpm dev
```

`BACKEND_URL` is **server-only** — do not prefix it with `NEXT_PUBLIC_`. The browser only ever talks to `/api/chat`; the FastAPI hostname never reaches the client bundle.
