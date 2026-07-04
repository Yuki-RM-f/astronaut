"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { authHeaders } from "@/src/lib/auth";
import { resolveAvatarModelUrl, type AvatarModelRead } from "@/src/lib/avatar";
import { selectAvatarAnimationClipName, type MotionIntent } from "@/src/lib/gesture";

export type AvatarModelLoadState = "idle" | "loading" | "ready" | "error";

function joinClassNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function AvatarPreview({
  model,
  mouthActive,
  motionIntent = "idle",
  className,
  canvasClassName,
  onLoadStateChange
}: {
  model: AvatarModelRead | null;
  mouthActive: boolean;
  motionIntent?: MotionIntent;
  className?: string;
  canvasClassName?: string;
  onLoadStateChange?: (state: AvatarModelLoadState) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const clipsRef = useRef<THREE.AnimationClip[]>([]);
  const activeActionRef = useRef<THREE.AnimationAction | null>(null);
  const motionIntentRef = useRef<MotionIntent>(motionIntent);
  const motionFallbackRef = useRef(false);
  const [loadState, setLoadState] = useState<AvatarModelLoadState>("idle");
  const [motionFallback, setMotionFallback] = useState(false);
  const modelUrl = resolveAvatarModelUrl(model);

  const setMotionFallbackState = useCallback((active: boolean) => {
    motionFallbackRef.current = active;
    setMotionFallback(active);
  }, []);

  const playMotionIntent = useCallback(
    (intent: MotionIntent) => {
      motionIntentRef.current = intent;
      const mixer = mixerRef.current;
      const clips = clipsRef.current;
      const clipName = selectAvatarAnimationClipName(
        clips.map((clip) => clip.name),
        intent
      );

      if (!mixer || !clipName) {
        activeActionRef.current?.fadeOut(0.2);
        activeActionRef.current = null;
        setMotionFallbackState(intent !== "idle");
        return;
      }

      const clip = THREE.AnimationClip.findByName(clips, clipName);
      if (!clip) {
        setMotionFallbackState(intent !== "idle");
        return;
      }

      const nextAction = mixer.clipAction(clip);
      if (activeActionRef.current === nextAction) {
        setMotionFallbackState(false);
        return;
      }

      activeActionRef.current?.fadeOut(0.2);
      nextAction.reset().fadeIn(0.2).play();
      activeActionRef.current = nextAction;
      setMotionFallbackState(false);
    },
    [setMotionFallbackState]
  );

  useEffect(() => {
    playMotionIntent(motionIntent);
  }, [motionIntent, playMotionIntent]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !modelUrl) {
      setLoadState("idle");
      onLoadStateChange?.("idle");
      return;
    }

    let disposed = false;
    let modelRoot: THREE.Object3D | null = null;
    let modelBaseY = 0;
    const clock = new THREE.Clock();
    const updateLoadState = (state: AvatarModelLoadState) => {
      if (disposed) {
        return;
      }
      setLoadState(state);
      onLoadStateChange?.(state);
    };
    updateLoadState("loading");
    setMotionFallbackState(false);

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100);
    camera.position.set(0, 0.65, 5.2);

    const ambient = new THREE.AmbientLight(0xffffff, 1.25);
    scene.add(ambient);

    const keyLight = new THREE.DirectionalLight(0xfff1d0, 3.1);
    keyLight.position.set(3.2, 5, 4.5);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x9eb7ff, 1.2);
    fillLight.position.set(-3.5, 2.2, 3);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0xffffff, 1.5);
    rimLight.position.set(0, 2.5, -4);
    scene.add(rimLight);

    const ground = new THREE.Mesh(
      new THREE.CircleGeometry(1.7, 48),
      new THREE.MeshStandardMaterial({
        color: 0x111a3f,
        roughness: 0.9,
        transparent: true,
        opacity: 0.44
      })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -1.42;
    ground.receiveShadow = true;
    scene.add(ground);

    const loader = new GLTFLoader();
    loader.setRequestHeader(authHeaders());
    loader.setMeshoptDecoder(MeshoptDecoder);
    loader.load(
      modelUrl,
      (gltf) => {
        if (disposed) {
          return;
        }
        modelRoot = gltf.scene;
        normalizeModel(modelRoot);
        modelBaseY = modelRoot.position.y;
        clipsRef.current = gltf.animations ?? [];
        mixerRef.current = clipsRef.current.length > 0 ? new THREE.AnimationMixer(modelRoot) : null;
        modelRoot.traverse((object) => {
          if (object instanceof THREE.Mesh) {
            object.castShadow = true;
            object.receiveShadow = true;
          }
        });
        scene.add(modelRoot);
        playMotionIntent(motionIntentRef.current);
        updateLoadState("ready");
      },
      undefined,
      (error) => {
        console.warn("Avatar GLB model failed to load.", error);
        updateLoadState("error");
      }
    );

    const resize = () => {
      const width = Math.max(canvas.clientWidth, 320);
      const height = Math.max(canvas.clientHeight, 320);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    resize();
    window.addEventListener("resize", resize);

    let frame = 0;
    const animate = (time: number) => {
      const seconds = time / 1000;
      const delta = clock.getDelta();
      mixerRef.current?.update(delta);
      if (modelRoot) {
        applyFallbackMotion(
          modelRoot,
          modelBaseY,
          seconds,
          motionIntentRef.current,
          motionFallbackRef.current
        );
      }
      ground.scale.setScalar(1 + Math.sin(seconds * 0.9) * 0.018);
      renderer.render(scene, camera);
      frame = window.requestAnimationFrame(animate);
    };
    frame = window.requestAnimationFrame(animate);

    return () => {
      disposed = true;
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      activeActionRef.current = null;
      clipsRef.current = [];
      mixerRef.current?.stopAllAction();
      mixerRef.current = null;
      motionFallbackRef.current = false;
      disposeScene(scene);
      renderer.dispose();
    };
  }, [modelUrl, onLoadStateChange, playMotionIntent, setMotionFallbackState]);

  return (
    <div
      className={joinClassNames(
        "relative min-h-[28rem] overflow-hidden rounded-[2rem] border border-starGold/14 bg-[radial-gradient(circle_at_top,_rgba(255,210,138,0.2),_rgba(37,72,109,0.42)_42%,_rgba(9,12,42,0.9))] shadow-[0_22px_70px_rgba(0,0,0,0.28)]",
        className
      )}
    >
      <canvas
        ref={canvasRef}
        className={joinClassNames("block h-[28rem] w-full", canvasClassName)}
        aria-label="GLB 数字人模型预览"
      />
      {loadState === "loading" ? (
        <div className="absolute inset-x-5 bottom-5 rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm font-bold text-starCream backdrop-blur">
          模型加载中
        </div>
      ) : null}
      {loadState === "error" ? (
        <div className="absolute inset-x-5 bottom-5 rounded-2xl border border-rose-300/24 bg-rose-500/18 px-4 py-3 text-sm font-bold text-rose-100 backdrop-blur">
          模型加载失败
        </div>
      ) : null}
      {loadState === "ready" && motionFallback ? (
        <div className="absolute inset-x-5 bottom-5 rounded-2xl border border-starGold/18 bg-black/30 px-4 py-3 text-xs font-bold text-starCream backdrop-blur">
          当前模型不含{motionIntentLabel(motionIntent)}动画，已使用基础动作反馈。
        </div>
      ) : null}
      {mouthActive ? <span className="sr-only">语音播放中</span> : null}
    </div>
  );
}

function applyFallbackMotion(
  root: THREE.Object3D,
  baseY: number,
  seconds: number,
  intent: MotionIntent,
  fallbackActive: boolean
) {
  const idleRotationY = Math.sin(seconds * 0.42) * 0.08;
  root.rotation.set(0, idleRotationY, 0);
  root.position.y = baseY + Math.sin(seconds * 1.1) * 0.035;

  if (!fallbackActive) {
    return;
  }

  if (intent === "attention") {
    root.rotation.y = Math.sin(seconds * 1.4) * 0.12;
    root.position.z = Math.sin(seconds * 1.2) * 0.03;
  } else if (intent === "wave") {
    root.rotation.z = Math.sin(seconds * 6.8) * 0.08;
    root.rotation.y = idleRotationY + Math.sin(seconds * 3.4) * 0.06;
  } else if (intent === "nod") {
    root.rotation.x = Math.sin(seconds * 5.4) * 0.08;
  } else if (intent === "listening") {
    root.rotation.y = -0.06 + Math.sin(seconds * 1.8) * 0.04;
    root.position.y += Math.sin(seconds * 2.4) * 0.015;
  } else if (intent === "thinking") {
    root.rotation.y = Math.sin(seconds * 0.85) * 0.1;
  } else if (intent === "speaking") {
    root.rotation.y = Math.sin(seconds * 2.1) * 0.06;
    root.position.y += Math.sin(seconds * 4.2) * 0.012;
  }
}

function motionIntentLabel(intent: MotionIntent): string {
  switch (intent) {
    case "attention":
      return "注视";
    case "wave":
      return "挥手";
    case "nod":
      return "点头";
    case "listening":
      return "倾听";
    case "thinking":
      return "思考";
    case "speaking":
      return "说话";
    case "idle":
      return "待机";
  }
}

function normalizeModel(root: THREE.Object3D) {
  const box = new THREE.Box3().setFromObject(root);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const maxAxis = Math.max(size.x, size.y, size.z, 1);
  const targetModelSize = 3.15;
  const scale = targetModelSize / maxAxis;

  root.position.sub(center);
  root.scale.setScalar(scale);

  const scaledBox = new THREE.Box3().setFromObject(root);
  root.position.y += -1.32 - scaledBox.min.y;
}

function disposeScene(scene: THREE.Scene) {
  scene.traverse((object) => {
    if (object instanceof THREE.Mesh) {
      object.geometry.dispose();
      const material = object.material;
      if (Array.isArray(material)) {
        material.forEach((item) => item.dispose());
      } else {
        material.dispose();
      }
    }
  });
}
