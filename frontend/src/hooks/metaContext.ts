import { createContext, useContext } from "react";
import type { ApiError } from "../lib/api";
import type { MetaOut } from "../lib/types";

export interface MetaState {
  meta: MetaOut | null;
  error: ApiError | null;
  /** True once the first request has been pending for >3s (free instances sleep when idle). */
  wakingUp: boolean;
  retry: () => void;
}

export const MetaContext = createContext<MetaState | null>(null);

/** Public server configuration from `GET /api/v1/meta`, loaded once per visit. */
export function useMeta(): MetaState {
  const value = useContext(MetaContext);
  if (!value) throw new Error("useMeta must be used inside <MetaProvider>");
  return value;
}
