import assert from "node:assert/strict";
import test from "node:test";

async function loadAuthModule() {
  try {
    return await import("../src/lib/auth.js");
  } catch (error) {
    assert.fail(`Expected auth helpers to be exported: ${error.message}`);
  }
}

test("demo session helper stores token and returns seeded persona id", async () => {
  const storage = new Map();
  globalThis.window = {
    localStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: (key) => storage.delete(key)
    }
  };
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url: String(url), options });
    return {
      ok: true,
      json: async () => ({
        access_token: "demo-token",
        token_type: "bearer",
        demo_persona_id: "persona-demo",
        user: {
          id: "user-demo",
          email: "demo@example.local",
          display_name: "演示用户",
          plan_type: "guest_demo"
        }
      })
    };
  };

  const { getAuthToken, startDemoSession } = await loadAuthModule();
  const session = await startDemoSession();

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "http://localhost:8000/api/auth/demo");
  assert.equal(calls[0].options.method, "POST");
  assert.equal(getAuthToken(), "demo-token");
  assert.equal(session.demo_persona_id, "persona-demo");
});

test("ensureDemoSession creates a demo token only when no token exists", async () => {
  const storage = new Map();
  globalThis.window = {
    localStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: (key) => storage.delete(key)
    }
  };

  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url: String(url), options });
    return {
      ok: true,
      json: async () => ({
        access_token: `demo-token-${calls.length}`,
        token_type: "bearer",
        demo_persona_id: "persona-demo",
        user: {
          id: "user-demo",
          email: "demo@example.local",
          display_name: "演示用户",
          plan_type: "guest_demo"
        }
      })
    };
  };

  const { ensureDemoSession, getAuthToken } = await loadAuthModule();

  const created = await ensureDemoSession();
  const reused = await ensureDemoSession();

  assert.equal(calls.length, 1);
  assert.equal(created.demo_persona_id, "persona-demo");
  assert.equal(reused, null);
  assert.equal(getAuthToken(), "demo-token-1");
});
