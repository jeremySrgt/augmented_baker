"use client";

import { useMemo, useState } from "react";
import {
  CheckCircle2,
  CircleSlash,
  ClockIcon,
  ImageIcon,
  Pencil,
  Send,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

export type PantryMatchedRow = {
  page_id: string;
  ingredient: string | null;
  unit: string | null;
  current_quantity: number | null;
  observed_quantity: number;
  delta: number | null;
};

export type PantryUnmatchedRow = {
  ingredient: string;
  observed_quantity: number;
  unit: string | null;
  notes: string | null;
};

export type PantryApprovalDecision =
  | { action: "approve" }
  | { action: "reject" }
  | {
      action: "edit";
      payload: {
        updates: Array<{ page_id: string; new_quantity: number }>;
      };
    };

export type PantryApprovalState =
  | { kind: "pending" }
  | { kind: "responded"; action: "approve" | "reject" | "edit" };

export type PantryStockApprovalCardProps = {
  toolCallId: string;
  matched: PantryMatchedRow[];
  unmatched: PantryUnmatchedRow[];
  state: PantryApprovalState;
  onRespond: (decision: PantryApprovalDecision) => void;
};

function formatQty(qty: number | null, unit: string | null): string {
  if (qty === null || qty === undefined) return "—";
  const trimmed = Number.isInteger(qty) ? qty.toString() : qty.toString();
  return unit ? `${trimmed} ${unit}` : trimmed;
}

function formatDelta(delta: number | null): string {
  if (delta === null || delta === undefined) return "";
  if (delta === 0) return "0";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta}`;
}

export function PantryStockApprovalCard({
  matched,
  unmatched,
  state,
  onRespond,
}: PantryStockApprovalCardProps) {
  const initialDrafts = useMemo(
    () =>
      Object.fromEntries(
        matched.map((row) => [row.page_id, String(row.observed_quantity)]),
      ) as Record<string, string>,
    [matched],
  );
  const [drafts, setDrafts] = useState<Record<string, string>>(initialDrafts);

  const responded = state.kind === "responded";
  const respondedAction = responded ? state.action : null;

  const updates: Array<{ page_id: string; new_quantity: number }> = [];
  for (const row of matched) {
    const raw = drafts[row.page_id];
    if (raw === undefined) continue;
    const parsed = Number.parseFloat(raw);
    if (!Number.isFinite(parsed)) continue;
    if (parsed !== row.observed_quantity) {
      updates.push({ page_id: row.page_id, new_quantity: parsed });
    }
  }
  const hasEdits = updates.length > 0;

  const handleApprove = () => onRespond({ action: "approve" });
  const handleReject = () => onRespond({ action: "reject" });
  const handleSendEdit = () =>
    onRespond({ action: "edit", payload: { updates } });

  return (
    <div className="not-prose mb-4 w-full overflow-hidden rounded-lg border bg-card shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b bg-muted/30 px-4 py-3">
        <div className="flex items-center gap-2">
          <ImageIcon className="size-4 text-muted-foreground" />
          <div>
            <div className="text-sm font-medium leading-none">
              Mise à jour du stock à partir de la photo
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {matched.length} ingrédient{matched.length > 1 ? "s" : ""} reconnu
              {matched.length > 1 ? "s" : ""}
              {unmatched.length > 0
                ? ` · ${unmatched.length} non reconnu${unmatched.length > 1 ? "s" : ""}`
                : ""}
            </div>
          </div>
        </div>
        {respondedAction === "approve" && (
          <Badge variant="secondary" className="gap-1.5">
            <CheckCircle2 className="size-3.5 text-green-600" />
            Mis à jour
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
            Modifié et appliqué
          </Badge>
        )}
        {!responded && (
          <Badge variant="outline" className="gap-1.5">
            <ClockIcon className="size-3.5 text-yellow-600" />
            Validation requise
          </Badge>
        )}
      </div>

      {matched.length > 0 ? (
        <div className="px-4 py-3">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="py-1.5 pr-3 text-left font-medium">Ingrédient</th>
                  <th className="py-1.5 pr-3 text-right font-medium">Stock actuel</th>
                  <th className="py-1.5 pr-3 text-right font-medium">Observé</th>
                  <th className="py-1.5 text-right font-medium">Nouveau</th>
                </tr>
              </thead>
              <tbody>
                {matched.map((row) => {
                  const draft = drafts[row.page_id] ?? String(row.observed_quantity);
                  const parsedDraft = Number.parseFloat(draft);
                  const edited =
                    Number.isFinite(parsedDraft) && parsedDraft !== row.observed_quantity;
                  return (
                    <tr key={row.page_id} className="border-t">
                      <td className="py-2 pr-3">
                        <div className="font-medium">{row.ingredient ?? "?"}</div>
                        {row.delta !== null && row.delta !== 0 && (
                          <div
                            className={cn(
                              "text-xs",
                              row.delta > 0 ? "text-green-600" : "text-orange-600",
                            )}
                          >
                            {formatDelta(row.delta)} vs stock actuel
                          </div>
                        )}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums text-muted-foreground">
                        {formatQty(row.current_quantity, row.unit)}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">
                        {formatQty(row.observed_quantity, row.unit)}
                      </td>
                      <td className="py-2 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Input
                            type="number"
                            inputMode="decimal"
                            step="0.1"
                            min="0"
                            value={draft}
                            onChange={(e) => {
                              const next = e.currentTarget.value;
                              setDrafts((prev) => ({
                                ...prev,
                                [row.page_id]: next,
                              }));
                            }}
                            disabled={responded}
                            className={cn(
                              "h-8 w-20 text-right tabular-nums",
                              edited && "border-blue-500/60 ring-1 ring-blue-500/30",
                            )}
                          />
                          {row.unit && (
                            <span className="text-xs text-muted-foreground">
                              {row.unit}
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="px-4 py-3 text-sm text-muted-foreground">
          Aucun ingrédient connu reconnu sur la photo.
        </div>
      )}

      {unmatched.length > 0 && (
        <div className="border-t bg-muted/20 px-4 py-3">
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Non reconnus
          </div>
          <ul className="mt-1.5 space-y-1 text-sm">
            {unmatched.map((row) => (
              <li key={row.ingredient} className="text-muted-foreground">
                <span className="font-medium text-foreground">{row.ingredient}</span>
                {" — "}
                {formatQty(row.observed_quantity, row.unit)}
                {row.notes ? ` · ${row.notes}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!responded && matched.length > 0 && (
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
            {hasEdits ? (
              <Button size="sm" onClick={handleSendEdit} className="gap-1.5">
                <Send className="size-4" /> Envoyer modifié
              </Button>
            ) : (
              <Button size="sm" onClick={handleApprove} className="gap-1.5">
                <Send className="size-4" /> Valider
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
