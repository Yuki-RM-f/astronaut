"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { AvatarModelRead } from "@/src/lib/avatar";

function joinClassNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function AvatarPreview({
  model,
  mouthActive,
  className,
  canvasClassName
}: {
  model: AvatarModelRead | null;
  mouthActive: boolean;
  className?: string;
  canvasClassName?: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    camera.position.set(0, 1.45, 6.2);
    scene.add(new THREE.AmbientLight(0xffffff, 1.7));
    const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
    keyLight.position.set(2.5, 4, 4);
    scene.add(keyLight);

    const group = new THREE.Group();
    scene.add(group);
    const skin = new THREE.MeshStandardMaterial({ color: 0xf1c9a8, roughness: 0.72 });
    const cloth = new THREE.MeshStandardMaterial({
      color: model?.status === "generated_ready" ? 0x52786f : 0x9c7a5f,
      roughness: 0.8
    });
    const hair = new THREE.MeshStandardMaterial({ color: 0x4a3a32, roughness: 0.9 });
    const eye = new THREE.MeshStandardMaterial({ color: 0x202020 });
    const mouthMaterial = new THREE.MeshStandardMaterial({ color: 0x8f3a31 });

    const torso = new THREE.Mesh(new THREE.CylinderGeometry(1.05, 1.35, 1.7, 32), cloth);
    torso.position.y = -1.2;
    group.add(torso);

    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.34, 0.5, 24), skin);
    neck.position.y = -0.28;
    group.add(neck);

    const head = new THREE.Mesh(new THREE.SphereGeometry(0.92, 48, 32), skin);
    head.position.y = 0.62;
    group.add(head);

    const hairCap = new THREE.Mesh(new THREE.SphereGeometry(0.96, 48, 16), hair);
    hairCap.position.set(0, 0.92, -0.08);
    hairCap.scale.set(1, 0.62, 0.82);
    group.add(hairCap);

    const leftEye = new THREE.Mesh(new THREE.SphereGeometry(0.07, 16, 8), eye);
    leftEye.position.set(-0.28, 0.72, 0.8);
    const rightEye = leftEye.clone();
    rightEye.position.x = 0.28;
    group.add(leftEye, rightEye);

    const mouth = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.08, 0.04), mouthMaterial);
    mouth.position.set(0, 0.35, 0.84);
    group.add(mouth);

    const smile = new THREE.Mesh(new THREE.TorusGeometry(0.23, 0.018, 8, 32, Math.PI), mouthMaterial);
    smile.position.set(0, 0.36, 0.86);
    smile.rotation.z = Math.PI;
    group.add(smile);

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
      group.position.y = Math.sin(seconds * 1.2) * 0.04;
      group.rotation.x = Math.sin(seconds * 0.55) * 0.035;
      group.rotation.y = Math.sin(seconds * 0.42) * 0.08;
      const blinking = Math.sin(seconds * 3.6) > 0.94 ? 0.08 : 1;
      leftEye.scale.y = blinking;
      rightEye.scale.y = blinking;
      const mouthOpen = mouthActive ? 0.7 + Math.abs(Math.sin(seconds * 9)) * 1.7 : 0.35;
      mouth.scale.y = mouthOpen;
      smile.visible = !mouthActive;
      renderer.render(scene, camera);
      frame = window.requestAnimationFrame(animate);
    };
    frame = window.requestAnimationFrame(animate);

    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      renderer.dispose();
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
    };
  }, [model?.id, model?.status, mouthActive]);

  return (
    <div
      className={joinClassNames(
        "min-h-[28rem] overflow-hidden rounded-[2rem] border border-starGold/14 bg-[radial-gradient(circle_at_top,_rgba(255,210,138,0.18),_rgba(68,52,122,0.5)_45%,_rgba(9,12,42,0.85))] shadow-[0_22px_70px_rgba(0,0,0,0.28)]",
        className
      )}
    >
      <canvas
        ref={canvasRef}
        className={joinClassNames("block h-[28rem] w-full", canvasClassName)}
        aria-label="mock 3D avatar preview"
      />
    </div>
  );
}
