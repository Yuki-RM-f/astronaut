import { API_PATHS, buildApiUrl, readApiJson } from "./api";

const AUTH_TOKEN_STORAGE_KEY = "persona_memory_agent_token";
const LOCAL_GUEST_TOKEN = "local-guest-session";

type AuthUser = {
  id: string;
  email: string;
  display_name?: string | null;
  plan_type: string;
};

type AuthSession = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

type DemoAuthSession = AuthSession & {
  demo_persona_id: string;
};

export function getAuthToken(): string | null {
  if (!canUseStorage()) {
    return LOCAL_GUEST_TOKEN;
  }

  const token = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)?.trim();
  return token || LOCAL_GUEST_TOKEN;
}

export function setAuthToken(token: string): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
}

export function clearAuthToken(): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

export function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function startDemoSession(): Promise<DemoAuthSession> {
  const response = await fetch(buildApiUrl(API_PATHS.auth.demo), {
    method: "POST"
  });
  const session = await readApiJson<DemoAuthSession>(
    response,
    "无法创建演示会话。"
  );
  setAuthToken(session.access_token);
  return session;
}

export async function ensureDemoSession(): Promise<DemoAuthSession | null> {
  if (getAuthToken()) {
    return null;
  }

  return startDemoSession();
}

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}
