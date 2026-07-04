import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

async function loadPersonaModule() {
  try {
    return await import("../src/lib/persona.js");
  } catch (error) {
    assert.fail(`Expected persona helpers to be exported: ${error.message}`);
  }
}

function installLocalStorage(token) {
  const storage = new Map([["persona_memory_agent_token", token]]);
  globalThis.window = {
    localStorage: {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: (key) => storage.delete(key)
    }
  };
}

test("delete persona helper calls the existing persona delete endpoint", async () => {
  installLocalStorage("demo-token");
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return new Response(null, { status: 204 });
  };

  const { deletePersona } = await loadPersonaModule();
  await deletePersona("persona id");

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "http://localhost:8000/api/personas/persona%20id");
  assert.equal(calls[0].options.method, "DELETE");
  assert.deepEqual(calls[0].options.headers, {
    Authorization: "Bearer demo-token"
  });
});

test("dashboard persona cards expose a confirmed delete action", () => {
  const source = readFileSync(new URL("../app/dashboard/page.tsx", import.meta.url), "utf8");

  assert.match(source, /deletePersona\(persona\.id\)/);
  assert.match(source, /window\.confirm/);
  assert.match(source, /type="button"/);
  assert.match(source, /aria-label=\{`删除星星 \$\{persona\.name\}`\}/);
  assert.match(source, /删除星星/);
});
