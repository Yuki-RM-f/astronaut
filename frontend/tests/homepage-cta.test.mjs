import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const homePageSource = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
const globalStylesSource = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

function sourceBetween(start, end) {
  const startIndex = homePageSource.indexOf(start);
  assert.notEqual(startIndex, -1, `missing start marker ${start}`);
  const endIndex = homePageSource.indexOf(end, startIndex);
  assert.notEqual(endIndex, -1, `missing end marker ${end}`);
  return homePageSource.slice(startIndex, endIndex);
}

test("homepage hero groups create and dashboard CTAs together", () => {
  const heroSource = sourceBetween("star-hero-copy", 'id="product-intro"');

  assert.match(heroSource, /href=\{ROUTES\.personasNew\}/);
  assert.match(heroSource, /创建属于TA的星星/);
  assert.match(heroSource, /href=\{ROUTES\.dashboard\}/);
  assert.match(heroSource, /进入我的星空/);
});

test("homepage hero CTAs use symmetric sizing and unified button styling", () => {
  const heroSource = sourceBetween("star-hero-copy", 'id="product-intro"');
  const buttonClasses = Array.from(
    heroSource.matchAll(/className="([^"]*\bhome-hero-action\b[^"]*)"/g),
    (match) => match[1]
  );

  assert.match(heroSource, /home-hero-actions/);
  assert.equal(buttonClasses.length, 2);
  assert.equal(buttonClasses[0], buttonClasses[1]);
  assert.equal(heroSource.match(/star-button/g)?.length, 2);
  assert.doesNotMatch(heroSource, /home-hero-secondary/);
  assert.doesNotMatch(heroSource, /sm:min-w-\[12\.5rem\]/);
  assert.match(globalStylesSource, /@media \(min-width: 640px\)[\s\S]*\.home-hero-action[\s\S]*width: 15\.5rem;/);
  assert.doesNotMatch(globalStylesSource, /\.home-hero-action[\s\S]*width: auto;/);
  assert.doesNotMatch(globalStylesSource, /\.home-hero-secondary/);
});

test("homepage hero does not show the AI simulation notice card", () => {
  const heroSource = sourceBetween("star-hero-copy", 'id="product-intro"');

  assert.doesNotMatch(heroSource, /AI 模拟体验/);
  assert.doesNotMatch(heroSource, /回复基于你上传和审核过的资料生成/);
  assert.doesNotMatch(heroSource, /rounded-full border border-starGold\/18/);
});

test("homepage product intro keeps the restored three-card overview", () => {
  const productIntroSource = sourceBetween('id="product-intro"', 'id="memory-review"');

  assert.match(productIntroSource, /把重要的人，整理成可信的星光档案。/);
  assert.match(
    productIntroSource,
    /星记围绕人物档案、资料解析与审核、回忆讲述和第一人称互动建立闭环。/
  );
  assert.match(productIntroSource, /创建档案/);
  assert.match(productIntroSource, /补充资料/);
  assert.match(productIntroSource, /开启陪伴/);
  assert.match(productIntroSource, /FeatureTile/);
  assert.doesNotMatch(productIntroSource, /展览路演材料/);
  assert.doesNotMatch(productIntroSource, /让记忆不止于回忆/);
  assert.doesNotMatch(productIntroSource, /创建星星|上传回忆|审核记忆/);
});

test("memory review section does not repeat the dashboard CTA", () => {
  const reviewSource = sourceBetween('id="memory-review"', "</main>");

  assert.doesNotMatch(reviewSource, /href=\{ROUTES\.dashboard\}/);
  assert.doesNotMatch(reviewSource, /进入我的星空/);
});

test("memory review copy describes functional audit actions", () => {
  const reviewSource = sourceBetween('id="memory-review"', "</main>");

  assert.doesNotMatch(reviewSource, /记忆档案馆用于/);
  assert.match(
    reviewSource,
    /上传资料后，在资料页面审查解析出的记忆卡片，确认、修正或删除后再进入后续互动。/
  );
  assert.match(reviewSource, /回忆讲述与搜索保留在记忆档案馆。/);
});
