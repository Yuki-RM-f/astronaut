import assert from "node:assert/strict";
import test from "node:test";
import {
  acceptGestureSignal,
  detectWaveGesture,
  gestureStatusLabel,
  motionIntentForGesture,
  normalizeMediaPipeGesture,
  selectAvatarAnimationClipName
} from "../src/lib/gesture.js";

test("gesture signals map to avatar motion intents", () => {
  assert.equal(motionIntentForGesture("presence"), "attention");
  assert.equal(motionIntentForGesture("wave"), "wave");
  assert.equal(motionIntentForGesture("nod"), "nod");
  assert.equal(motionIntentForGesture("open_palm"), "listening");
  assert.equal(motionIntentForGesture("closed_fist"), "idle");
  assert.equal(motionIntentForGesture("none"), "idle");
});

test("MediaPipe canned gestures normalize to local gesture signals", () => {
  assert.equal(normalizeMediaPipeGesture("Open_Palm"), "open_palm");
  assert.equal(normalizeMediaPipeGesture("Closed_Fist"), "closed_fist");
  assert.equal(normalizeMediaPipeGesture("None"), null);
  assert.equal(normalizeMediaPipeGesture("Unknown"), null);
  assert.equal(normalizeMediaPipeGesture(null), null);
});

test("gesture cooldown blocks repeated triggers but allows new gestures", () => {
  assert.equal(
    acceptGestureSignal({
      signal: "wave",
      lastSignal: "wave",
      nowMs: 2_200,
      lastTriggeredAtMs: 1_000,
      cooldownMs: 1_600
    }),
    false
  );
  assert.equal(
    acceptGestureSignal({
      signal: "wave",
      lastSignal: "wave",
      nowMs: 2_700,
      lastTriggeredAtMs: 1_000,
      cooldownMs: 1_600
    }),
    true
  );
  assert.equal(
    acceptGestureSignal({
      signal: "open_palm",
      lastSignal: "wave",
      nowMs: 1_100,
      lastTriggeredAtMs: 1_000,
      cooldownMs: 1_600
    }),
    true
  );
});

test("wave detection uses horizontal hand movement across recent frames", () => {
  assert.equal(detectWaveGesture([0.2, 0.31, 0.46, 0.58]), true);
  assert.equal(detectWaveGesture([0.2, 0.21, 0.23, 0.25]), false);
  assert.equal(detectWaveGesture([0.2]), false);
});

test("avatar animation clip matching prefers exact and readable names", () => {
  assert.equal(selectAvatarAnimationClipName(["Idle", "Wave_Hand", "Talk"], "wave"), "Wave_Hand");
  assert.equal(selectAvatarAnimationClipName(["Armature|NodYes", "Idle"], "nod"), "Armature|NodYes");
  assert.equal(selectAvatarAnimationClipName(["ListeningLoop", "Idle"], "listening"), "ListeningLoop");
  assert.equal(selectAvatarAnimationClipName(["Idle"], "wave"), null);
});

test("gesture status labels stay user-facing", () => {
  assert.equal(gestureStatusLabel("presence"), "已看到你");
  assert.equal(gestureStatusLabel("wave"), "识别到挥手");
  assert.equal(gestureStatusLabel("open_palm"), "识别到张开手掌");
});
