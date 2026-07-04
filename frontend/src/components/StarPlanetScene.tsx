"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

export function StarPlanetScene() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      canvas,
      preserveDrawingBuffer: true
    });
    renderer.setClearColor(0x000000, 0);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
    camera.position.set(0, 0.05, 7.8);

    const group = new THREE.Group();
    group.position.set(0, 0.18, 0);
    scene.add(group);

    const planetMaterial = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color("#443075"),
      emissive: new THREE.Color("#2c1d55"),
      emissiveIntensity: 0.5,
      metalness: 0.04,
      roughness: 0.42,
      transmission: 0.18,
      transparent: true,
      opacity: 0.78,
      clearcoat: 0.55,
      clearcoatRoughness: 0.22
    });
    const planet = new THREE.Mesh(new THREE.SphereGeometry(1.85, 96, 96), planetMaterial);
    group.add(planet);

    const wire = new THREE.Mesh(
      new THREE.SphereGeometry(1.865, 48, 24),
      new THREE.MeshBasicMaterial({
        color: 0xffd28a,
        opacity: 0.075,
        transparent: true,
        wireframe: true
      })
    );
    group.add(wire);

    const core = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.42, 1),
      new THREE.MeshStandardMaterial({
        color: 0xffd28a,
        emissive: 0xffbd72,
        emissiveIntensity: 1.8,
        roughness: 0.28
      })
    );
    core.scale.set(1.05, 1.05, 1.05);
    group.add(core);

    const glow = new THREE.Sprite(
      new THREE.SpriteMaterial({
        color: 0xffc979,
        opacity: 0.38,
        transparent: true,
        blending: THREE.AdditiveBlending
      })
    );
    glow.scale.set(2.6, 2.6, 1);
    group.add(glow);

    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(2.42, 0.012, 16, 180),
      new THREE.MeshBasicMaterial({
        color: 0xf0a875,
        opacity: 0.64,
        transparent: true
      })
    );
    ring.rotation.set(1.22, 0.25, -0.38);
    group.add(ring);

    const ringGlow = new THREE.Mesh(
      new THREE.TorusGeometry(2.43, 0.032, 16, 180),
      new THREE.MeshBasicMaterial({
        color: 0xffd28a,
        opacity: 0.12,
        transparent: true,
        blending: THREE.AdditiveBlending
      })
    );
    ringGlow.rotation.copy(ring.rotation);
    group.add(ringGlow);

    function createMessenger() {
      const messenger = new THREE.Group();
      const material = new THREE.MeshStandardMaterial({
        color: 0xffe6b8,
        emissive: 0xffbd72,
        emissiveIntensity: 0.9,
        metalness: 0.05,
        roughness: 0.34,
        side: THREE.DoubleSide
      });
      const leftWing = new THREE.Mesh(
        new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(0, 0, 0.24),
          new THREE.Vector3(-0.34, 0, -0.2),
          new THREE.Vector3(0.05, 0.04, -0.06)
        ]),
        material
      );
      const rightWing = new THREE.Mesh(
        new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(0, 0, 0.24),
          new THREE.Vector3(0.34, 0, -0.2),
          new THREE.Vector3(-0.05, 0.04, -0.06)
        ]),
        material
      );
      const body = new THREE.Mesh(
        new THREE.ConeGeometry(0.055, 0.5, 4),
        new THREE.MeshStandardMaterial({
          color: 0xffd28a,
          emissive: 0xffa85f,
          emissiveIntensity: 1.2,
          roughness: 0.28
        })
      );
      body.rotation.x = Math.PI / 2;
      body.position.z = 0.02;
      messenger.add(leftWing, rightWing, body);
      messenger.scale.setScalar(0.38);
      return { messenger, material };
    }

    const orbiters: Array<{
      mesh: THREE.Group;
      material: THREE.Material;
      radiusX: number;
      radiusY: number;
      radiusZ: number;
      speed: number;
      phase: number;
      tilt: number;
    }> = [];
    const trailLines: Array<THREE.Line> = [];

    for (let index = 0; index < 8; index += 1) {
      const { messenger, material } = createMessenger();
      const radiusX = 2.45 + index * 0.18;
      const radiusY = 0.42 + (index % 3) * 0.16;
      const radiusZ = 0.95 + (index % 4) * 0.12;
      const tilt = -0.4 + index * 0.13;
      const speed = 0.18 + index * 0.035;
      const phase = (Math.PI * 2 * index) / 8;
      messenger.rotation.z = tilt;
      group.add(messenger);
      orbiters.push({ mesh: messenger, material, radiusX, radiusY, radiusZ, speed, phase, tilt });

      const trailPoints: THREE.Vector3[] = [];
      for (let step = 0; step <= 128; step += 1) {
        const angle = (step / 128) * Math.PI * 2;
        trailPoints.push(
          new THREE.Vector3(
            Math.cos(angle) * radiusX,
            Math.sin(angle + tilt) * radiusY,
            Math.sin(angle) * radiusZ
          )
        );
      }
      const trail = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(trailPoints),
        new THREE.LineBasicMaterial({
          color: 0xffd28a,
          opacity: 0.1 + (index % 2) * 0.035,
          transparent: true,
          blending: THREE.AdditiveBlending
        })
      );
      trail.rotation.z = tilt;
      group.add(trail);
      trailLines.push(trail);
    }

    const particlesCount = 260;
    const positions = new Float32Array(particlesCount * 3);
    for (let index = 0; index < particlesCount; index += 1) {
      const radius = 2.6 + Math.random() * 3.2;
      const angle = Math.random() * Math.PI * 2;
      const y = (Math.random() - 0.5) * 3.8;
      positions[index * 3] = Math.cos(angle) * radius;
      positions[index * 3 + 1] = y;
      positions[index * 3 + 2] = Math.sin(angle) * radius * 0.55;
    }
    const particlesGeometry = new THREE.BufferGeometry();
    particlesGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const particles = new THREE.Points(
      particlesGeometry,
      new THREE.PointsMaterial({
        color: 0xffdfaa,
        size: 0.032,
        transparent: true,
        opacity: 0.72,
        blending: THREE.AdditiveBlending
      })
    );
    group.add(particles);

    scene.add(new THREE.AmbientLight(0xb9a8ff, 1.25));
    const keyLight = new THREE.PointLight(0xffd28a, 18, 14);
    keyLight.position.set(1.2, 1.4, 2.2);
    scene.add(keyLight);
    const violetLight = new THREE.PointLight(0x8d6cff, 10, 15);
    violetLight.position.set(-2.5, -1.2, 3);
    scene.add(violetLight);

    let frameId = 0;
    let disposed = false;
    let pointerX = 0;
    let pointerY = 0;
    let smoothPointerX = 0;
    let smoothPointerY = 0;

    function handlePointerMove(event: PointerEvent) {
      pointerX = (event.clientX / window.innerWidth - 0.5) * 2;
      pointerY = (event.clientY / window.innerHeight - 0.5) * 2;
    }

    function resize() {
      if (!canvas) {
        return;
      }
      const rect = canvas.getBoundingClientRect();
      const width = Math.max(1, rect.width);
      const height = Math.max(1, rect.height);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();

      const isSmall = width < 760;
      const isWide = width > 1100;
      group.position.x = 0;
      group.position.y = isSmall ? 0.28 : 0.18;
      group.scale.setScalar(isSmall ? 0.82 : isWide ? 1.12 : 0.98);
    }

    function animate(time: number) {
      if (disposed) {
        return;
      }
      const seconds = time * 0.001;
      smoothPointerX += (pointerX - smoothPointerX) * 0.045;
      smoothPointerY += (pointerY - smoothPointerY) * 0.045;
      group.rotation.y = smoothPointerX * 0.1 + Math.sin(seconds * 0.18) * 0.035;
      group.rotation.x = -smoothPointerY * 0.06;
      group.position.z = Math.sin(seconds * 0.2) * 0.18;
      planet.rotation.y = seconds * 0.18;
      planet.rotation.x = Math.sin(seconds * 0.25) * 0.08;
      wire.rotation.y = seconds * 0.13;
      core.rotation.y = seconds * 0.7;
      core.rotation.z = seconds * 0.35;
      ring.rotation.z = -0.38 + Math.sin(seconds * 0.35) * 0.03;
      ringGlow.rotation.copy(ring.rotation);
      particles.rotation.y = seconds * 0.055;
      particles.rotation.x = Math.sin(seconds * 0.16) * 0.04;
      orbiters.forEach((orbiter, index) => {
        const angle = seconds * orbiter.speed + orbiter.phase;
        const nextAngle = angle + 0.035;
        const current = new THREE.Vector3(
          Math.cos(angle) * orbiter.radiusX,
          Math.sin(angle + orbiter.tilt) * orbiter.radiusY,
          Math.sin(angle) * orbiter.radiusZ
        );
        const next = new THREE.Vector3(
          Math.cos(nextAngle) * orbiter.radiusX,
          Math.sin(nextAngle + orbiter.tilt) * orbiter.radiusY,
          Math.sin(nextAngle) * orbiter.radiusZ
        );
        orbiter.mesh.position.copy(current);
        orbiter.mesh.lookAt(next);
        orbiter.mesh.rotateY(Math.PI / 2);
        const pulse = 0.34 + Math.sin(seconds * 1.7 + index) * 0.06;
        orbiter.mesh.scale.setScalar(pulse);
      });
      glow.material.opacity = 0.28 + Math.sin(seconds * 1.4) * 0.08;
      renderer.render(scene, camera);
      frameId = window.requestAnimationFrame(animate);
    }

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", handlePointerMove);
    frameId = window.requestAnimationFrame(animate);

    return () => {
      disposed = true;
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", handlePointerMove);
      particlesGeometry.dispose();
      planet.geometry.dispose();
      planetMaterial.dispose();
      wire.geometry.dispose();
      (wire.material as THREE.Material).dispose();
      core.geometry.dispose();
      (core.material as THREE.Material).dispose();
      ring.geometry.dispose();
      (ring.material as THREE.Material).dispose();
      ringGlow.geometry.dispose();
      (ringGlow.material as THREE.Material).dispose();
      orbiters.forEach((orbiter) => {
        orbiter.mesh.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.geometry.dispose();
            if (Array.isArray(child.material)) {
              child.material.forEach((material) => material.dispose());
            } else {
              child.material.dispose();
            }
          }
        });
        orbiter.material.dispose();
      });
      trailLines.forEach((trail) => {
        trail.geometry.dispose();
        (trail.material as THREE.Material).dispose();
      });
      glow.material.dispose();
      renderer.dispose();
    };
  }, []);

  return (
    <div className="star-planet-scene" aria-hidden="true">
      <canvas ref={canvasRef} className="h-full w-full" />
    </div>
  );
}
