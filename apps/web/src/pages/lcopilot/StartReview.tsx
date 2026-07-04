/**
 * /lcopilot/start-review — the one stable concierge entry point.
 *
 * Every "get your pack checked" CTA lands here (marketing pages, emails,
 * future ads). Signed-in users go straight to the upload page; everyone else
 * gets the fast-path signup (?intent=review — wizard pre-answered, lands on
 * upload after account creation). Keeping this as its own URL means the
 * funnel target never changes even if the steps behind it do.
 */

import { Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";

export default function StartReview() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#00261C] flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-[#B2F273] animate-spin" />
      </div>
    );
  }

  return <Navigate to={user ? "/export-lc-upload" : "/register?intent=review"} replace />;
}
