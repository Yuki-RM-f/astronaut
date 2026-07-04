export type GestureSignal =
  | "none"
  | "presence"
  | "wave"
  | "nod"
  | "open_palm"
  | "closed_fist";

export type MotionIntent =
  | "idle"
  | "attention"
  | "wave"
  | "nod"
  | "listening"
  | "thinking"
  | "speaking";

type GestureRecognizerModule = typeof import("@mediapipe/tasks-vision");

export type GestureRecognizerInstance = {
  recognizeForVideo: (video: HTMLVideoElement, timestampMs: number) => unknown;
  close?: () => void;
};

type GestureRecognizerResult = {
  gestures?: Array<Array<{ categoryName?: string | null }>>;
  landmarks?: Array<Array<{ x?: number | null }>>;
  handLandmarks?: Array<Array<{ x?: number | null }>>;
};

const MOTION_KEYWORDS: Record<MotionIntent, string[]> = {
  idle: ["idle", "breath", "stand"],
  attention: ["attention", "greet", "look", "turn"],
  wave: ["wave", "waving", "hello"],
  nod: ["nod", "noddy", "nodyes"],
  listening: ["listen", "listening", "ready"],
  thinking: ["think", "thinking"],
  speaking: ["speak", "speaking", "talk", "talking"]
};

const GESTURE_LABELS: Record<GestureSignal, string> = {
  none: "等待手势",
  presence: "已看到你",
  wave: "识别到挥手",
  nod: "识别到点头",
  open_palm: "识别到张开手掌",
  closed_fist: "识别到握拳"
};

export function motionIntentForGesture(signal: GestureSignal): MotionIntent {
  switch (signal) {
    case "presence":
      return "attention";
    case "wave":
      return "wave";
    case "nod":
      return "nod";
    case "open_palm":
      return "listening";
    case "closed_fist":
    case "none":
      return "idle";
  }
}

export function normalizeMediaPipeGesture(
  categoryName: string | null | undefined
): GestureSignal | null {
  switch (categoryName?.toLowerCase()) {
    case "open_palm":
      return "open_palm";
    case "closed_fist":
      return "closed_fist";
    default:
      return null;
  }
}

export function acceptGestureSignal({
  signal,
  lastSignal,
  nowMs,
  lastTriggeredAtMs,
  cooldownMs = 1600
}: {
  signal: GestureSignal;
  lastSignal: GestureSignal | null;
  nowMs: number;
  lastTriggeredAtMs: number;
  cooldownMs?: number;
}): boolean {
  return signal !== lastSignal || nowMs - lastTriggeredAtMs >= cooldownMs;
}

export function detectWaveGesture(handXHistory: number[], minDelta = 0.24): boolean {
  if (handXHistory.length < 3) {
    return false;
  }
  return Math.max(...handXHistory) - Math.min(...handXHistory) >= minDelta;
}

export function gestureStatusLabel(signal: GestureSignal): string {
  return GESTURE_LABELS[signal];
}

export function selectAvatarAnimationClipName(
  clipNames: string[],
  intent: MotionIntent
): string | null {
  const keywords = MOTION_KEYWORDS[intent];
  const normalizedClips = clipNames.map((name) => ({
    name,
    normalizedName: normalizeAnimationName(name)
  }));

  for (const keyword of keywords) {
    const exact = normalizedClips.find((clip) => clip.normalizedName === keyword);
    if (exact) {
      return exact.name;
    }
  }
  for (const keyword of keywords) {
    const partial = normalizedClips.find((clip) => clip.normalizedName.includes(keyword));
    if (partial) {
      return partial.name;
    }
  }
  return null;
}

export async function createGestureRecognizer(): Promise<GestureRecognizerInstance> {
  const { FilesetResolver, GestureRecognizer } =
    (await import("@mediapipe/tasks-vision")) as GestureRecognizerModule;
  const vision = await FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm"
  );
  return GestureRecognizer.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath:
        "https://storage.googleapis.com/mediapipe-tasks/gesture_recognizer/gesture_recognizer.task"
    },
    runningMode: "VIDEO",
    numHands: 1
  });
}

export function gestureSignalFromRecognizerResult(
  result: unknown,
  handXHistory: number[]
): GestureSignal | null {
  const typedResult = result as GestureRecognizerResult | null;
  const categoryName = typedResult?.gestures?.[0]?.[0]?.categoryName;
  const normalizedGesture = normalizeMediaPipeGesture(categoryName);
  const handX = typedResult?.landmarks?.[0]?.[0]?.x ?? typedResult?.handLandmarks?.[0]?.[0]?.x;

  if (typeof handX === "number") {
    handXHistory.push(handX);
    if (handXHistory.length > 6) {
      handXHistory.shift();
    }
  }

  if (detectWaveGesture(handXHistory)) {
    return "wave";
  }
  return normalizedGesture;
}

function normalizeAnimationName(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}
