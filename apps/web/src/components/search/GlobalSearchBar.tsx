/**
 * GlobalSearchBar — Phase A12.
 *
 * Lives in the dashboard header. Type to search across LCs,
 * suppliers, and services clients in one shot. Hits /api/search
 * with a 300ms debounce.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2, Search, X } from "lucide-react";

import { api } from "@/api/client";
import { Input } from "@/components/ui/input";

interface SearchHit {
  kind: string;
  id: string;
  label: string;
  detail: string | null;
  href: string | null;
}

interface SearchResponse {
  query: string;
  total: number;
  hits: SearchHit[];
}

const KIND_LABEL: Record<string, string> = {
  validation_session: "LC",
  supplier: "Supplier",
  services_client: "Client",
};

export function GlobalSearchBar() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced fetch
  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setHits([]);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const handle = window.setTimeout(async () => {
      try {
        const { data } = await api.get<SearchResponse>(
          `/api/search?q=${encodeURIComponent(trimmed)}&limit=10`,
        );
        if (!cancelled) {
          setHits(data.hits ?? []);
        }
      } catch {
        if (!cancelled) setHits([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 300);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [query]);

  // Click-outside
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const handleHit = useCallback(
    (hit: SearchHit) => {
      setOpen(false);
      setQuery("");
      if (hit.href) navigate(hit.href);
    },
    [navigate],
  );

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          placeholder="Search LCs, suppliers, clients…"
          className="pl-7 pr-7 h-8 text-sm"
        />
        {query && (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setHits([]);
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label="Clear search"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {open && query.trim().length >= 2 && (
        <div className="absolute right-0 left-0 top-full mt-1 z-50 rounded-md border border-border bg-popover shadow-md max-h-96 overflow-y-auto">
          {loading && (
            <div className="px-3 py-2 text-xs text-muted-foreground flex items-center gap-2">
              <Loader2 className="w-3 h-3 animate-spin" />
              Searching…
            </div>
          )}
          {!loading && hits.length === 0 && (
            <div className="px-3 py-3 text-xs text-muted-foreground">
              No results.
            </div>
          )}
          {hits.length > 0 && (
            <ul className="divide-y divide-border">
              {hits.map((hit) => (
                <li key={`${hit.kind}-${hit.id}`}>
                  {hit.href ? (
                    <Link
                      to={hit.href}
                      onClick={() => handleHit(hit)}
                      className="block px-3 py-2 hover:bg-neutral-100 dark:hover:bg-neutral-800/50"
                    >
                      <HitRow hit={hit} />
                    </Link>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleHit(hit)}
                      className="block w-full text-left px-3 py-2 hover:bg-neutral-100 dark:hover:bg-neutral-800/50"
                    >
                      <HitRow hit={hit} />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function HitRow({ hit }: { hit: SearchHit }) {
  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium truncate">{hit.label}</span>
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider shrink-0">
          {KIND_LABEL[hit.kind] ?? hit.kind}
        </span>
      </div>
      {hit.detail && (
        <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
          {hit.detail}
        </p>
      )}
    </div>
  );
}
