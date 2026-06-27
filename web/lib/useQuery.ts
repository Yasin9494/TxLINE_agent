"use client";
import { useEffect, useState } from "react";

// Read a query-string param client-side (avoids useSearchParams Suspense with static export).
export function useQuery(key: string): string | null {
  const [v, setV] = useState<string | null>(null);
  useEffect(() => {
    setV(new URLSearchParams(window.location.search).get(key));
  }, [key]);
  return v;
}
