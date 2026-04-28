/**
 * First-session coachmark — Phase A3 part 4.
 *
 * Three-step intro overlay that fires once on first dashboard render.
 * Dismissal stored in localStorage under "lcopilot.seen_tutorial". A
 * backend persistence layer can be added later (User.onboarding_data)
 * if cross-device sync becomes a requirement; for now per-browser is
 * sufficient.
 *
 * Mount near the top of any dashboard page. Self-suppresses if the
 * key is already set.
 */

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, X } from "lucide-react";

const STORAGE_KEY = "lcopilot.seen_tutorial";

interface Step {
  title: string;
  body: string;
}

const STEPS: Step[] = [
  {
    title: "Welcome to LCopilot",
    body:
      "We validate trade-finance documents against your Letter of Credit so you can fix issues before the bank rejects them.",
  },
  {
    title: "Upload your LC + supporting docs",
    body:
      "Drag PDFs onto the upload page. We'll extract every field, compare against UCP 600 + ISBP 745, and surface every discrepancy with an exact LC clause + how to fix it.",
  },
  {
    title: "Resolve, comment, or re-paper",
    body:
      "Each finding has Accept / Reject / Waive / Re-paper buttons. Re-paper sends a no-login link to your supplier; we automatically re-validate when they upload corrected docs.",
  },
];

interface Props {
  /** Override storage key for tests / per-persona variants. */
  storageKey?: string;
}

export function FirstSessionCoachmark({ storageKey = STORAGE_KEY }: Props) {
  const [dismissed, setDismissed] = useState<boolean>(true);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const seen = window.localStorage.getItem(storageKey);
      setDismissed(Boolean(seen));
    } catch {
      // Privacy mode / disabled storage — just don't show.
      setDismissed(true);
    }
  }, [storageKey]);

  const close = useCallback(() => {
    setDismissed(true);
    try {
      window.localStorage.setItem(storageKey, new Date().toISOString());
    } catch {
      // ignore
    }
  }, [storageKey]);

  const goNext = () => {
    if (step >= STEPS.length - 1) {
      close();
    } else {
      setStep((s) => s + 1);
    }
  };

  const goPrev = () => setStep((s) => Math.max(0, s - 1));

  if (dismissed) return null;

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="coachmark-title"
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 px-4"
    >
      <div className="w-full max-w-md rounded-lg bg-white dark:bg-neutral-900 shadow-xl">
        <div className="flex items-start justify-between px-5 py-4 border-b">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
              Quick tour — {step + 1} of {STEPS.length}
            </p>
            <h2 id="coachmark-title" className="mt-1 text-lg font-semibold">
              {current.title}
            </h2>
          </div>
          <Button
            size="icon"
            variant="ghost"
            onClick={close}
            aria-label="Skip"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        <div className="px-5 py-5">
          <p className="text-sm text-muted-foreground leading-relaxed">
            {current.body}
          </p>
        </div>

        <div className="flex items-center justify-between gap-2 px-5 py-3 border-t bg-neutral-50 dark:bg-neutral-800/40 rounded-b-lg">
          <div className="flex items-center gap-1">
            {STEPS.map((_, i) => (
              <span
                key={i}
                className={`h-1.5 w-6 rounded-full ${
                  i === step
                    ? "bg-neutral-900 dark:bg-neutral-100"
                    : "bg-neutral-300 dark:bg-neutral-700"
                }`}
              />
            ))}
          </div>
          <div className="flex items-center gap-2">
            {step > 0 && (
              <Button size="sm" variant="ghost" onClick={goPrev}>
                <ChevronLeft className="w-4 h-4 mr-1" />
                Back
              </Button>
            )}
            <Button size="sm" onClick={goNext}>
              {isLast ? "Got it" : "Next"}
              {!isLast && <ChevronRight className="w-4 h-4 ml-1" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
