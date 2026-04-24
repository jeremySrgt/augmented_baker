export type SseEvent = {
  event: string;
  data: string;
};

export async function* parseSseStream(
  body: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<SseEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  const onAbort = () => {
    reader.cancel().catch(() => {});
  };
  signal?.addEventListener("abort", onAbort);

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let separatorIndex: number;
      while ((separatorIndex = findSeparator(buffer)) !== -1) {
        const raw = buffer.slice(0, separatorIndex);
        buffer = buffer.slice(separatorIndex + separatorLength(buffer, separatorIndex));
        const parsed = parseRecord(raw);
        if (parsed) yield parsed;
      }
    }

    const tail = buffer.trim();
    if (tail) {
      const parsed = parseRecord(tail);
      if (parsed) yield parsed;
    }
  } finally {
    signal?.removeEventListener("abort", onAbort);
    reader.releaseLock();
  }
}

function findSeparator(buffer: string): number {
  const rn = buffer.indexOf("\r\n\r\n");
  const n = buffer.indexOf("\n\n");
  if (rn === -1) return n;
  if (n === -1) return rn;
  return Math.min(rn, n);
}

function separatorLength(buffer: string, index: number): number {
  return buffer.startsWith("\r\n\r\n", index) ? 4 : 2;
}

function parseRecord(raw: string): SseEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of raw.split(/\r?\n/)) {
    if (line.length === 0) continue;
    if (line.startsWith(":")) continue;
    const colonAt = line.indexOf(":");
    const field = colonAt === -1 ? line : line.slice(0, colonAt);
    const value = colonAt === -1 ? "" : line.slice(colonAt + 1).replace(/^ /, "");
    if (field === "event") event = value;
    else if (field === "data") dataLines.push(value);
  }
  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}
