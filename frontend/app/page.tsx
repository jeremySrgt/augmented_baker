"use client";

import { useState } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, isToolUIPart } from "ai";
import { Croissant } from "lucide-react";

import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  Message,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import {
  PromptInput,
  type PromptInputMessage,
  PromptInputSubmit,
  PromptInputTextarea,
} from "@/components/ai-elements/prompt-input";
import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
  ToolOutput,
} from "@/components/ai-elements/tool";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const { messages, sendMessage, status, error, clearError } = useChat({
    transport: new DefaultChatTransport({ api: "/api/chat" }),
  });

  const handleSubmit = (message: PromptInputMessage) => {
    const text = message.text.trim();
    if (!text) return;
    clearError();
    sendMessage({ text });
    setInput("");
  };

  const submitStatus: "ready" | "streaming" | "error" =
    status === "streaming" || status === "submitted"
      ? "streaming"
      : status === "error"
        ? "error"
        : "ready";

  return (
    <main className="flex h-dvh w-full items-center justify-center bg-muted/30 p-4 sm:p-6">
      <div className="flex h-full w-full max-w-3xl flex-col gap-4">
        <header className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Croissant className="size-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Madeleine</h1>
            <p className="text-sm text-muted-foreground">
              Assistante boulangerie
            </p>
          </div>
        </header>

        <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border bg-card shadow-sm">
          <Conversation className="min-h-0 flex-1">
            <ConversationContent className="mx-auto w-full max-w-2xl">
              {messages.length === 0 ? (
                <ConversationEmptyState
                  icon={<Croissant className="size-10" />}
                  title="Bonjour patronne"
                  description="Pose-moi une question sur tes stocks, tes ventes ou tes commandes."
                />
              ) : (
                messages.map((message) => (
                  <Message from={message.role} key={message.id}>
                    <MessageContent>
                      {message.parts.map((part, i) => {
                        const key = `${message.id}-${i}`;
                        if (part.type === "text") {
                          return (
                            <MessageResponse key={key}>
                              {part.text}
                            </MessageResponse>
                          );
                        }
                        if (isToolUIPart(part)) {
                          return (
                            <Tool
                              key={key}
                              defaultOpen={part.state === "output-error"}
                            >
                              {part.type === "dynamic-tool" ? (
                                <ToolHeader
                                  type={part.type}
                                  state={part.state}
                                  toolName={part.toolName}
                                />
                              ) : (
                                <ToolHeader
                                  type={part.type}
                                  state={part.state}
                                />
                              )}
                              <ToolContent>
                                <ToolInput input={part.input} />
                                <ToolOutput
                                  output={
                                    part.output === undefined ? null : (
                                      <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">
                                        {safeStringify(part.output)}
                                      </pre>
                                    )
                                  }
                                  errorText={part.errorText}
                                />
                              </ToolContent>
                            </Tool>
                          );
                        }
                        return null;
                      })}
                    </MessageContent>
                  </Message>
                ))
              )}
            </ConversationContent>
            <ConversationScrollButton />
          </Conversation>

          <div className="border-t bg-background/60 p-3">
            {error ? (
              <div
                role="alert"
                className="mb-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
              >
                {error.message || "Une erreur est survenue."}
              </div>
            ) : null}

            <PromptInput onSubmit={handleSubmit}>
              <PromptInputTextarea
                value={input}
                onChange={(e) => setInput(e.currentTarget.value)}
                placeholder="Écris ton message..."
              />
              <PromptInputSubmit
                status={submitStatus}
                disabled={!input.trim() && status !== "streaming"}
              />
            </PromptInput>
          </div>
        </section>
      </div>
    </main>
  );
}

function safeStringify(value: unknown): string {
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
