/**
 * toast.ts — The app's single toast pattern.
 *
 * Every failed API call (via `queryClient`'s global onError, see
 * `queryClient.ts`) and every explicit success confirmation (evidence
 * ingested, brief exported, case created) goes through these three
 * functions rather than components importing `sonner` directly. That keeps
 * copy and styling consistent and gives us one place to change behavior
 * (e.g. dedupe repeated errors) later.
 */

import { toast } from 'sonner';

/** A failed API call. Terracotta surface, never a raw stack trace. */
export function notifyApiError(message: string, opts?: { requestId?: string }): void {
  toast.error(message, {
    description: opts?.requestId ? `Reference: ${opts.requestId}` : undefined,
  });
}

/** A confirmed side effect (upload complete, case created, brief exported). */
export function notifySuccess(message: string, description?: string): void {
  toast.success(message, { description });
}

/** Neutral, low-urgency status update. */
export function notifyInfo(message: string, description?: string): void {
  toast(message, { description });
}
