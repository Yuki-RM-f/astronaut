import { API_PATHS, buildApiUrl, readApiJson } from "./api";

const AUTH_TOKEN_STORAGE_KEY = "persona_memory_agent_token";

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

type LoginPayload = {
  email: string;
  password: string;
};

type RegisterPayload = LoginPayload & {
  display_name?: string;
};

export function getAuthToken(): string | null {
  if (!canUseStorage()) {
    return null;
  }

  const token = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)?.trim();
  return token || null;
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

export async function loginWithPassword(payload: LoginPayload): Promise<AuthSession> {
  return submitAuth(API_PATHS.auth.login, payload, "登录失败。");
}

export async function registerAccount(payload: RegisterPayload): Promise<AuthSession> {
  return submitAuth(API_PATHS.auth.register, payload, "注册失败。");
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

async function submitAuth(
  path: string,
  payload: LoginPayload | RegisterPayload,
  fallbackMessage: string
): Promise<AuthSession> {
  const response = await fetch(buildApiUrl(path), {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  const session = await readApiJson<AuthSession>(response, fallbackMessage);
  setAuthToken(session.access_token);
  return session;
}

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}
