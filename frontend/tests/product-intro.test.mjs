import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const productIntroSource = readFileSync(
  new URL("../app/product-intro/page.tsx", import.meta.url),
  "utf8"
);

test("standalone product intro page adapts roadshow material in star theme", () => {
  assert.match(productIntroSource, /展览路演材料/);
  assert.match(productIntroSource, /让记忆不止于回忆/);
  assert.match(productIntroSource, /为什么需要这个产品/);
  assert.match(productIntroSource, /我们提供什么/);
  assert.match(productIntroSource, /核心能力/);
  assert.match(productIntroSource, /演示闭环/);
  assert.match(productIntroSource, /技术与可信机制/);
  assert.match(productIntroSource, /创建星星/);
  assert.match(productIntroSource, /上传回忆/);
  assert.match(productIntroSource, /审核记忆/);
  assert.match(productIntroSource, /开启互动/);
  assert.match(productIntroSource, /ROUTES\.personasNew/);
  assert.match(productIntroSource, /ROUTES\.dashboard/);
});

test("standalone product intro page uses the shared star design system", () => {
  assert.match(productIntroSource, /StarShell/);
  assert.match(productIntroSource, /StarNav/);
  assert.match(productIntroSource, /StarPanel/);
  assert.match(productIntroSource, /FeatureTile/);
  assert.match(productIntroSource, /star-button/);
  assert.match(productIntroSource, /text-starGold/);
  assert.match(productIntroSource, /text-starCream/);
  assert.match(productIntroSource, /text-starMist/);
});

test("standalone product intro page does not embed raw roadshow HTML", () => {
  assert.doesNotMatch(productIntroSource, /<iframe|dangerouslySetInnerHTML|<style|<html|<body/);
  assert.doesNotMatch(productIntroSource, /className="(?:hero|section-title|pain-card|caps-card)"/);
  assert.doesNotMatch(productIntroSource, /class="(?:hero|section-title|pain-card|caps-card)"/);
});

test("standalone product intro page avoids unsupported roadshow claims", () => {
  assert.doesNotMatch(productIntroSource, /微信\/QQ|一键导入|VRM|视频通话|<1s|1s 内|毫秒级/);
  assert.doesNotMatch(productIntroSource, /生产级|影视级|真实复活/);
});
