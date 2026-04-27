"use client";

import { useCallback } from "react";
import { useChat } from "@ai-sdk/react";
import {
  DefaultChatTransport,
  isToolUIPart,
  lastAssistantMessageIsCompleteWithApprovalResponses,
  type FileUIPart,
  type UIMessage,
} from "ai";
import { Croissant } from "lucide-react";

import {
  Attachment,
  AttachmentPreview,
  AttachmentRemove,
  Attachments,
} from "@/components/ai-elements/attachments";
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
  PantryStockApprovalCard,
  type PantryApprovalDecision,
  type PantryApprovalState,
  type PantryMatchedRow,
  type PantryUnmatchedRow,
} from "@/components/ai-elements/pantry-stock-approval";
import {
  PromptInput,
  PromptInputActionAddAttachments,
  PromptInputActionAddScreenshot,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuTrigger,
  PromptInputBody,
  PromptInputFooter,
  type PromptInputMessage,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  usePromptInputAttachments,
} from "@/components/ai-elements/prompt-input";
import {
  SupplierApprovalCard,
  type SupplierApprovalDecision,
  type SupplierApprovalEmail,
  type SupplierApprovalRow,
  type SupplierApprovalState,
  type SupplierApprovalSupplier,
} from "@/components/ai-elements/supplier-approval";
import {
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
  ToolOutput,
} from "@/components/ai-elements/tool";

type SupplierApprovalData = {
  toolCallId: string;
  kind: string;
  email: SupplierApprovalEmail | null;
  notionRow: SupplierApprovalRow;
  supplier: SupplierApprovalSupplier;
};

type PantryApprovalData = {
  toolCallId: string;
  kind: string;
  matched: PantryMatchedRow[];
  unmatched: PantryUnmatchedRow[];
};

const SUPPLIER_ORDER_TOOL = "envoyer_commande_fournisseur";
const PANTRY_PHOTO_TOOL = "mettre_a_jour_stock_depuis_photo";
const APPROVAL_TOOL_NAMES = new Set([SUPPLIER_ORDER_TOOL, PANTRY_PHOTO_TOOL]);

const MAX_IMAGE_EDGE = 1024;
const JPEG_QUALITY = 0.8;

async function downscaleImageFile(file: FileUIPart): Promise<FileUIPart> {
  if (!file.mediaType?.startsWith("image/")) return file;
  if (typeof file.url !== "string") return file;
  if (typeof window === "undefined") return file;

  const img = new Image();
  img.decoding = "async";
  const ready = new Promise<HTMLImageElement | null>((resolve) => {
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
  });
  img.src = file.url;
  const loaded = await ready;
  if (!loaded) return file;

  const longestEdge = Math.max(loaded.naturalWidth, loaded.naturalHeight);
  const scale = longestEdge > MAX_IMAGE_EDGE ? MAX_IMAGE_EDGE / longestEdge : 1;
  if (scale === 1 && file.mediaType === "image/jpeg") return file;

  const targetW = Math.max(1, Math.round(loaded.naturalWidth * scale));
  const targetH = Math.max(1, Math.round(loaded.naturalHeight * scale));
  const canvas = document.createElement("canvas");
  canvas.width = targetW;
  canvas.height = targetH;
  const ctx = canvas.getContext("2d");
  if (!ctx) return file;
  ctx.drawImage(loaded, 0, 0, targetW, targetH);

  const dataUrl = canvas.toDataURL("image/jpeg", JPEG_QUALITY);
  return { ...file, mediaType: "image/jpeg", url: dataUrl };
}

function PromptAttachments() {
  const attachments = usePromptInputAttachments();
  if (attachments.files.length === 0) return null;
  return (
    <div className="px-3 pt-3">
      <Attachments variant="inline">
        {attachments.files.map((file) => (
          <Attachment
            key={file.id}
            data={file}
            onRemove={() => attachments.remove(file.id)}
          >
            <AttachmentPreview />
            <AttachmentRemove />
          </Attachment>
        ))}
      </Attachments>
    </div>
  );
}

function MessageAttachments({
  files,
}: {
  files: Array<FileUIPart & { id: string }>;
}) {
  if (files.length === 0) return null;
  return (
    <Attachments variant="grid" className="ml-0">
      {files.map((file) => (
        <Attachment key={file.id} data={file}>
          <AttachmentPreview />
        </Attachment>
      ))}
    </Attachments>
  );
}

export default function ChatPage() {
  const { messages, sendMessage, addToolApprovalResponse, status, error, clearError } = useChat({
    transport: new DefaultChatTransport({ api: "/api/chat" }),
    sendAutomaticallyWhen: lastAssistantMessageIsCompleteWithApprovalResponses,
  });

  const handleSubmit = async (message: PromptInputMessage) => {
    const text = message.text.trim();
    const incomingFiles = message.files ?? [];
    if (!text && incomingFiles.length === 0) return;
    clearError();

    const processedFiles = await Promise.all(incomingFiles.map(downscaleImageFile));
    sendMessage({ text, files: processedFiles });
  };

  const handleSupplierResponse = useCallback(
    (toolCallId: string) => (decision: SupplierApprovalDecision) => {
      if (decision.action === "approve") {
        addToolApprovalResponse({ id: toolCallId, approved: true });
      } else if (decision.action === "reject") {
        addToolApprovalResponse({ id: toolCallId, approved: false });
      } else {
        addToolApprovalResponse({
          id: toolCallId,
          approved: true,
          reason: JSON.stringify(decision.payload),
        });
      }
    },
    [addToolApprovalResponse],
  );

  const handlePantryResponse = useCallback(
    (toolCallId: string) => (decision: PantryApprovalDecision) => {
      if (decision.action === "approve") {
        addToolApprovalResponse({ id: toolCallId, approved: true });
      } else if (decision.action === "reject") {
        addToolApprovalResponse({ id: toolCallId, approved: false });
      } else {
        addToolApprovalResponse({
          id: toolCallId,
          approved: true,
          reason: JSON.stringify(decision.payload),
        });
      }
    },
    [addToolApprovalResponse],
  );

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
                  description="Pose-moi une question sur tes stocks, tes ventes ou tes commandes, ou envoie-moi une photo de ton rayon pour mettre à jour ton stock."
                />
              ) : (
                messages.map((message) => {
                  const imageFiles: Array<FileUIPart & { id: string }> = [];
                  for (const part of message.parts) {
                    if (part.type !== "file") continue;
                    const file = part as FileUIPart;
                    if (!file.mediaType?.startsWith("image/")) continue;
                    if (typeof file.url !== "string") continue;
                    imageFiles.push({ ...file, id: `${message.id}-${file.url.slice(-12)}` });
                  }
                  return (
                    <Message from={message.role} key={message.id}>
                      <MessageContent>
                        {imageFiles.length > 0 && (
                          <MessageAttachments files={imageFiles} />
                        )}
                        {message.parts.map((part, i) => {
                          const key = `${message.id}-${i}`;
                          if (part.type === "text") {
                            return (
                              <MessageResponse key={key}>{part.text}</MessageResponse>
                            );
                          }
                          if (part.type === "file") {
                            return null; // already rendered above as a grid
                          }
                          if (part.type === "data-supplier-approval") {
                            const data = (part as { data: SupplierApprovalData }).data;
                            const cardState = approvalStateFromMessage(message, data.toolCallId);
                            return (
                              <SupplierApprovalCard
                                key={key}
                                toolCallId={data.toolCallId}
                                supplier={data.supplier}
                                email={data.email}
                                notionRow={data.notionRow}
                                state={cardState as SupplierApprovalState}
                                onRespond={handleSupplierResponse(data.toolCallId)}
                              />
                            );
                          }
                          if (part.type === "data-pantry-approval") {
                            const data = (part as { data: PantryApprovalData }).data;
                            const cardState = approvalStateFromMessage(message, data.toolCallId);
                            return (
                              <PantryStockApprovalCard
                                key={key}
                                toolCallId={data.toolCallId}
                                matched={data.matched}
                                unmatched={data.unmatched}
                                state={cardState as PantryApprovalState}
                                onRespond={handlePantryResponse(data.toolCallId)}
                              />
                            );
                          }
                          if (isToolUIPart(part)) {
                            // Approval tools render as card-only experiences;
                            // the generic Tool block here would just duplicate the header.
                            const toolName =
                              "toolName" in part ? part.toolName : part.type.replace(/^tool-/, "");
                            if (APPROVAL_TOOL_NAMES.has(toolName)) return null;
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
                                  <ToolHeader type={part.type} state={part.state} />
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
                  );
                })
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

            <PromptInput onSubmit={handleSubmit} accept="image/*" multiple>
              <PromptAttachments />
              <PromptInputBody>
                <PromptInputTextarea placeholder="Écris ton message ou glisse une photo..." />
              </PromptInputBody>
              <PromptInputFooter>
                <PromptInputTools>
                  <PromptInputActionMenu>
                    <PromptInputActionMenuTrigger />
                    <PromptInputActionMenuContent side="top" sideOffset={8}>
                      <PromptInputActionAddAttachments label="Joindre une photo" />
                      <PromptInputActionAddScreenshot label="Capturer l'écran" />
                    </PromptInputActionMenuContent>
                  </PromptInputActionMenu>
                </PromptInputTools>
                <PromptInputSubmit status={submitStatus} />
              </PromptInputFooter>
            </PromptInput>
          </div>
        </section>
      </div>
    </main>
  );
}

function approvalStateFromMessage(
  message: UIMessage,
  toolCallId: string,
): SupplierApprovalState {
  for (const part of message.parts) {
    if (!isToolUIPart(part)) continue;
    if (part.toolCallId !== toolCallId) continue;
    if (part.state === "approval-responded" || part.state === "output-available") {
      const approval = part.approval;
      if (!approval) return { kind: "pending" };
      if (!approval.approved) return { kind: "responded", action: "reject" };
      return {
        kind: "responded",
        action: approval.reason ? "edit" : "approve",
      };
    }
    if (part.state === "output-error" || part.state === "output-denied") {
      const approval = part.approval;
      if (approval && !approval.approved) {
        return { kind: "responded", action: "reject" };
      }
    }
  }
  return { kind: "pending" };
}

function safeStringify(value: unknown): string {
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
