/**
 * Minimal SEO meta hook for the Vite SPA (no react-helmet dependency).
 *
 * Sets document.title plus description / OG tags on mount, restores the
 * previous title on unmount. Googlebot executes JS, so client-set meta is
 * indexed; if launch SEO later demands prerendering, that's an infra change,
 * not a page change.
 */

import { useEffect } from "react";

export interface SeoMeta {
  title: string;
  description: string;
  /** Canonical path, e.g. /tools/cbam-readiness-check */
  path: string;
}

function upsertMeta(attr: "name" | "property", key: string, content: string): void {
  let el = document.head.querySelector<HTMLMetaElement>(`meta[${attr}="${key}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
}

export function useSeoMeta({ title, description, path }: SeoMeta): void {
  useEffect(() => {
    const prevTitle = document.title;
    document.title = title;
    upsertMeta("name", "description", description);
    upsertMeta("property", "og:title", title);
    upsertMeta("property", "og:description", description);
    upsertMeta("property", "og:url", `https://trdrhub.com${path}`);
    upsertMeta("property", "og:type", "website");
    return () => {
      document.title = prevTitle;
    };
  }, [title, description, path]);
}
