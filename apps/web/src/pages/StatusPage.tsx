/**
 * StatusPage — Phase A12.
 *
 * Public-by-design status snapshot. Hits /api/status (no auth)
 * and renders a row per upstream service with a green/red dot.
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { API_BASE_URL } from "@/api/client";

interface Upstream {
  name: string;
  healthy: boolean;
  note: string | null;
}

interface StatusResponse {
  healthy: boolean;
  upstream: Upstream[];
  generated_at: string;
  region: string | null;
}

export default function StatusPage() {
  const [data, setData] = useState<StatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const fetchStatus = async () => {
      try {
        // Bare axios — this is the one endpoint that should not carry
        // auth headers, since we want to verify the platform is up
        // even when the user isn't signed in.
        const base = API_BASE_URL?.replace(/\/$/, "") ?? "";
        const { data } = await axios.get<StatusResponse>(`${base}/api/status`);
        if (!cancelled) {
          setData(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError((err as Error).message ?? "Failed to load status");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void fetchStatus();
    const id = window.setInterval(fetchStatus, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-4 py-8">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">
            TRDR Hub
          </p>
          <h1 className="text-2xl font-semibold mt-1">Platform status</h1>
          {data?.region && (
            <p className="text-xs text-muted-foreground">
              Region: {data.region}
            </p>
          )}
        </div>
        <Button asChild variant="ghost">
          <Link to="/">Back to home</Link>
        </Button>
      </header>

      {loading && (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 inline-block mr-2 animate-spin" />
            Checking…
          </CardContent>
        </Card>
      )}

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      {data && (
        <>
          <Card
            className={
              data.healthy
                ? "border-emerald-300 bg-emerald-50/50"
                : "border-rose-300 bg-rose-50/50"
            }
          >
            <CardContent className="py-5 flex items-center gap-3">
              {data.healthy ? (
                <CheckCircle2 className="w-6 h-6 text-emerald-600" />
              ) : (
                <AlertCircle className="w-6 h-6 text-rose-600" />
              )}
              <div>
                <p className="font-semibold">
                  {data.healthy ? "All systems operational" : "Service issue detected"}
                </p>
                <p className="text-xs text-muted-foreground">
                  Last checked {new Date(data.generated_at).toLocaleString()}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <tbody>
                  {data.upstream.map((u) => (
                    <tr key={u.name} className="border-t border-border first:border-t-0">
                      <td className="px-4 py-3 w-8">
                        {u.healthy ? (
                          <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500" />
                        ) : (
                          <span className="inline-block w-2.5 h-2.5 rounded-full bg-rose-500" />
                        )}
                      </td>
                      <td className="px-4 py-3 font-medium capitalize">
                        {u.name.replace(/_/g, " ")}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {u.note ?? (u.healthy ? "Healthy" : "Unhealthy")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
