import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

const productIntroSource = readFileSync(
  new URL("../app/product-intro/page.tsx", import.meta.url),
  "utf8"
);

const coverImagePath = new URL(
  "../public/product-intro/cover-starry-girl.png",
  import.meta.url
);

test("product intro is a 12-slide React roadshow deck", () => {
  const slideMatches = productIntroSource.match(/eyebrow: "/g) ?? [];

  assert.equal(slideMatches.length, 12);
  assert.match(productIntroSource, /Product Roadshow/);
  assert.match(productIntroSource, /“复活”亲友，让思念有处安放/);
  assert.match(productIntroSource, /Market Insight/);
  assert.match(productIntroSource, /Competition Gap/);
  assert.match(productIntroSource, /Positioning/);
  assert.match(productIntroSource, /Highlight 01/);
  assert.match(productIntroSource, /Highlight 02/);
  assert.match(productIntroSource, /Highlight 03/);
  assert.match(productIntroSource, /Demo Focus/);
  assert.match(productIntroSource, /Business Model/);
  assert.match(productIntroSource, /Risk Control/);
  assert.match(productIntroSource, /Roadmap/);
  assert.match(productIntroSource, /Closing/);
});

test("product intro keeps the original deck content and local cover asset", () => {
  assert.match(productIntroSource, /失亲哀伤，需要新的陪伴方式/);
  assert.match(productIntroSource, /现有产品，解决得还不够深/);
  assert.match(productIntroSource, /我们不是简单复刻一个 AI 亲友/);
  assert.match(productIntroSource, /低门槛创建数字人格/);
  assert.match(productIntroSource, /多模态互动，更接近真实陪伴/);
  assert.match(productIntroSource, /明确的疗愈路径/);
  assert.match(productIntroSource, /三个演示场景/);
  assert.match(productIntroSource, /商业化设计：分层订阅制/);
  assert.match(productIntroSource, /风险把控：授权、隐私、心理安全/);
  assert.match(productIntroSource, /后续迭代方向/);
  assert.match(productIntroSource, /真正的告别，不是忘记/);
  assert.match(productIntroSource, /\/product-intro\/cover-starry-girl\.png/);
  assert.equal(existsSync(coverImagePath), true);
});

test("product intro deck uses React controls for slide navigation", () => {
  assert.match(productIntroSource, /useState/);
  assert.match(productIntroSource, /useEffect/);
  assert.match(productIntroSource, /showSlide/);
  assert.match(productIntroSource, /goToSlide/);
  assert.match(productIntroSource, /handleKeyDown/);
  assert.match(productIntroSource, /ArrowRight/);
  assert.match(productIntroSource, /PageDown/);
  assert.match(productIntroSource, /ArrowLeft/);
  assert.match(productIntroSource, /PageUp/);
  assert.match(productIntroSource, /Home/);
  assert.match(productIntroSource, /End/);
  assert.match(productIntroSource, /history\.replaceState/);
  assert.match(productIntroSource, /location\.hash/);
  assert.match(productIntroSource, /hashchange/);
  assert.match(productIntroSource, /上一页/);
  assert.match(productIntroSource, /下一页/);
  assert.match(productIntroSource, /\{currentSlide \+ 1\} \/ \{ROADSHOW_SLIDES\.length\}/);
});

test("product intro page uses the shared star shell without raw HTML embedding", () => {
  assert.match(productIntroSource, /StarShell/);
  assert.match(productIntroSource, /StarNav/);
  assert.doesNotMatch(productIntroSource, /<iframe|dangerouslySetInnerHTML|<style|<html|<body|<script/);
});
