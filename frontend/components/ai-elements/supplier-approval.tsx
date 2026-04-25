"use client";

import { useState } from "react";
import {
  CheckCircle2,
  CircleSlash,
  ClockIcon,
  Mail,
  Pencil,
  Send,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export type SupplierApprovalEmail = {
  to?: string;
  subject?: string;
  body?: string;
};

export type SupplierApprovalRow = Record<string, unknown> | null;

export type SupplierApprovalSupplier = {
  name?: string;
  email?: string;
} | null;

export type SupplierApprovalDecision =
  | { action: "approve" }
  | { action: "reject" }
  | {
      action: "edit";
      payload: {
        email?: { subject?: string; body?: string };
        notion_row?: { Notes?: string };
      };
    };

export type SupplierApprovalState =
  | { kind: "pending" }
  | { kind: "responded"; action: "approve" | "reject" | "edit" };

export type SupplierApprovalCardProps = {
  toolCallId: string;
  supplier: SupplierApprovalSupplier;
  email: SupplierApprovalEmail | null;
  notionRow: SupplierApprovalRow;
  state: SupplierApprovalState;
  onRespond: (decision: SupplierApprovalDecision) => void;
};

const STATUS_LABELS: Record<SupplierApprovalState["kind"], string> = {
  pending: "Validation requise",
  responded: "Réponse envoyée",
};

function getNotesFromRow(row: SupplierApprovalRow): string {
  if (!row) return "";
  const notes = (row as { Notes?: { rich_text?: Array<{ text?: { content?: string } }> } }).Notes;
  const first = notes?.rich_text?.[0]?.text?.content;
  return typeof first === "string" ? first : "";
}

function getProductsFromRow(row: SupplierApprovalRow): string {
  if (!row) return "";
  const prods = (row as { ["Produits commandés"]?: { rich_text?: Array<{ text?: { content?: string } }> } })[
    "Produits commandés"
  ];
  const first = prods?.rich_text?.[0]?.text?.content;
  return typeof first === "string" ? first : "";
}

export function SupplierApprovalCard({
  supplier,
  email,
  notionRow,
  state,
  onRespond,
}: SupplierApprovalCardProps) {
  const initialBody = email?.body ?? "";
  const initialNotes = getNotesFromRow(notionRow);

  const [editing, setEditing] = useState(false);
  const [bodyDraft, setBodyDraft] = useState(initialBody);
  const [notesDraft, setNotesDraft] = useState(initialNotes);

  const responded = state.kind === "responded";
  const respondedAction = responded ? state.action : null;

  const products = getProductsFromRow(notionRow);

  const handleApprove = () => onRespond({ action: "approve" });
  const handleReject = () => onRespond({ action: "reject" });
  const handleSendEdit = () => {
    const payload: SupplierApprovalDecision = {
      action: "edit",
      payload: {
        email: bodyDraft !== initialBody ? { body: bodyDraft } : undefined,
        notion_row: notesDraft !== initialNotes ? { Notes: notesDraft } : undefined,
      },
    };
    onRespond(payload);
  };

  return (
    <div className="not-prose mb-4 w-full overflow-hidden rounded-lg border bg-card shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b bg-muted/30 px-4 py-3">
        <div className="flex items-center gap-2">
          <Mail className="size-4 text-muted-foreground" />
          <div>
            <div className="text-sm font-medium leading-none">
              Brouillon de commande fournisseur
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {supplier?.name ?? "Fournisseur inconnu"}
              {supplier?.email ? ` · ${supplier.email}` : ""}
            </div>
          </div>
        </div>
        {respondedAction === "approve" && (
          <Badge variant="secondary" className="gap-1.5">
            <CheckCircle2 className="size-3.5 text-green-600" />
            Envoyé
          </Badge>
        )}
        {respondedAction === "reject" && (
          <Badge variant="secondary" className="gap-1.5">
            <CircleSlash className="size-3.5 text-orange-600" />
            Annulé
          </Badge>
        )}
        {respondedAction === "edit" && (
          <Badge variant="secondary" className="gap-1.5">
            <Pencil className="size-3.5 text-blue-600" />
            Modifié et envoyé
          </Badge>
        )}
        {!responded && (
          <Badge variant="outline" className="gap-1.5">
            <ClockIcon className="size-3.5 text-yellow-600" />
            {STATUS_LABELS.pending}
          </Badge>
        )}
      </div>

      <div className="space-y-3 px-4 py-3 text-sm">
        {email?.subject && (
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Objet
            </div>
            <div className="mt-0.5 font-medium">{email.subject}</div>
          </div>
        )}

        <div>
          <div className="flex items-center justify-between">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Mail
            </div>
            {!responded && !editing && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 gap-1 px-2 text-xs"
                onClick={() => setEditing(true)}
              >
                <Pencil className="size-3" /> Modifier
              </Button>
            )}
          </div>
          {editing && !responded ? (
            <Textarea
              value={bodyDraft}
              onChange={(e) => setBodyDraft(e.currentTarget.value)}
              className="mt-1 min-h-[180px] font-mono text-xs"
            />
          ) : (
            <pre
              className={cn(
                "mt-1 whitespace-pre-wrap rounded-md bg-muted/50 p-3 font-mono text-xs",
                responded && "opacity-70",
              )}
            >
              {bodyDraft || "(vide)"}
            </pre>
          )}
        </div>

        {products && (
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Produits
            </div>
            <pre className="mt-1 whitespace-pre-wrap rounded-md bg-muted/30 p-2 font-mono text-xs">
              {products}
            </pre>
          </div>
        )}

        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Notes
          </div>
          {editing && !responded ? (
            <Textarea
              value={notesDraft}
              onChange={(e) => setNotesDraft(e.currentTarget.value)}
              placeholder="Notes (optionnel)"
              className="mt-1 min-h-[60px] text-xs"
            />
          ) : (
            <div
              className={cn(
                "mt-1 rounded-md bg-muted/30 p-2 text-xs",
                responded && "opacity-70",
                !notesDraft && "italic text-muted-foreground",
              )}
            >
              {notesDraft || "(aucune)"}
            </div>
          )}
        </div>
      </div>

      {!responded && (
        <>
          <Separator />
          <div className="flex flex-wrap items-center justify-end gap-2 px-4 py-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReject}
              className="gap-1.5"
            >
              <XCircle className="size-4" /> Annuler
            </Button>
            {editing ? (
              <Button size="sm" onClick={handleSendEdit} className="gap-1.5">
                <Send className="size-4" /> Envoyer modifié
              </Button>
            ) : (
              <Button size="sm" onClick={handleApprove} className="gap-1.5">
                <Send className="size-4" /> Valider et envoyer
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
