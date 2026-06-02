import {
  BRIDGE_ERROR_CODES,
  BridgeUnavailableError,
} from "./bridgeErrors";

type BridgeResolveEnv = {
  PROD: boolean;
  DEV: boolean;
};

export type PywebviewEventTarget = {
  addEventListener(type: string, listener: () => void): void;
  removeEventListener(type: string, listener: () => void): void;
};

export type PywebviewWindow = {
  pywebview?: {
    api?: Record<string, (...args: unknown[]) => Promise<unknown>>;
  };
};

export const PYWEBVIEW_READY_EVENT = "pywebviewready";
export const DEFAULT_PYWEBVIEW_WAIT_MS = 10_000;
const PYWEBVIEW_POLL_MS = 50;

type PyApi = Record<string, (...args: unknown[]) => Promise<unknown>>;

function readApi(win: PywebviewWindow | undefined): PyApi | undefined {
  return win?.pywebview?.api;
}

function bridgeUnavailableCode(env: BridgeResolveEnv): string {
  return env.PROD
    ? BRIDGE_ERROR_CODES.productionUnavailable
    : BRIDGE_ERROR_CODES.devUnavailable;
}

/** Wait until `window.pywebview.api` exists (pywebview injects after `pywebviewready`). */
export function waitForPywebviewApi(
  options: {
    env?: BridgeResolveEnv;
    win?: PywebviewWindow;
    eventTarget?: PywebviewEventTarget;
    timeoutMs?: number;
  } = {},
): Promise<PyApi> {
  const env = options.env ?? import.meta.env;
  const win = options.win;
  const eventTarget = options.eventTarget ?? (typeof window !== "undefined" ? window : undefined);
  const timeoutMs = options.timeoutMs ?? DEFAULT_PYWEBVIEW_WAIT_MS;

  const immediate = readApi(win);
  if (immediate) {
    return Promise.resolve(immediate);
  }

  if (!eventTarget) {
    return Promise.reject(new BridgeUnavailableError(bridgeUnavailableCode(env)));
  }

  return new Promise((resolve, reject) => {
    let settled = false;

    const settle = (action: "resolve" | "reject", value?: PyApi) => {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      if (action === "resolve" && value) {
        resolve(value);
        return;
      }
      reject(new BridgeUnavailableError(bridgeUnavailableCode(env)));
    };

    const tryResolve = () => {
      const api = readApi(win);
      if (api) {
        settle("resolve", api);
        return true;
      }
      return false;
    };

    const onReady = () => {
      tryResolve();
    };

    const cleanup = () => {
      eventTarget.removeEventListener(PYWEBVIEW_READY_EVENT, onReady);
      clearInterval(interval);
      clearTimeout(timeout);
    };

    eventTarget.addEventListener(PYWEBVIEW_READY_EVENT, onReady);
    const interval = setInterval(() => {
      tryResolve();
    }, PYWEBVIEW_POLL_MS);
    const timeout = setTimeout(() => {
      settle("reject");
    }, timeoutMs);
  });
}
