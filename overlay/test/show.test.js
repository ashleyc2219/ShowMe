// window.__showme.{show,clear,done} 與完成判定的自動化檢查，跑在 jsdom。
// 用法：cd overlay && npm install && npm test
//
// 對應規格：docs/design/showme.md §11（完成判定）、§12（介面）。
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");

const FIXTURE_PATH = path.join(__dirname, "fixture.html");
const OVERLAY_BUILT_PATH = path.join(__dirname, "..", "overlay.js");
const overlaySrc = fs.readFileSync(OVERLAY_BUILT_PATH, "utf8");

// requestAnimationFrame（rafDebounce 用到）跟 getComputedStyle（isGone 用到）
// 都需要 pretendToBeVisual。每個測試各建一個全新的 window，避免互相汙染
// current 這個 module-level 狀態。
function makeWindow() {
  const dom = new JSDOM(fs.readFileSync(FIXTURE_PATH, "utf8"), {
    runScripts: "dangerously",
    pretendToBeVisual: true,
    url: "http://localhost/fixture.html",
  });
  const { window } = dom;

  // jsdom 沒有實作 innerText（需要真的渲染引擎才能算「看得到的文字」，
  // 這是 jsdom 已知的限制，不是 overlay.js 的 bug）。overlay.src.js 特意選
  // innerText 而不是 textContent，是因為前者比較貼近 spec 說的「頁面文字
  // 出現」（隱藏元素裡的文字不該算數）。這裡用 textContent 頂替只是讓測試
  // 能在 jsdom 下跑，不代表生產環境行為——真的瀏覽器不需要這個 shim。
  Object.defineProperty(window.HTMLElement.prototype, "innerText", {
    configurable: true,
    get() {
      return this.textContent;
    },
  });

  const emits = [];
  window.__showme_emit = (payload) => emits.push(payload);
  window.eval(overlaySrc);
  return { window, emits };
}

function byName(window, name) {
  const r = window.__showme.snapshot(1);
  return r.elements.find((e) => e.name === name);
}

// MutationObserver 是 microtask，rafDebounce 又包了一層 requestAnimationFrame
// （jsdom 用真的 timer 模擬 ~16ms 一個 frame），所以要等一段真時間才會發生。
function tick(ms = 60) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

test("click：目標從 DOM 移除 → step_done", async () => {
  const { window, emits } = makeWindow();
  const el = byName(window, "純文字按鈕");
  window.__showme.show({
    uid: el.uid,
    instruction: "點這個按鈕",
    kind: "click",
    index: 1,
    total: 3,
    expect: "",
  });

  const domEl = window.document.querySelector(`[data-showme-uid="${el.uid}"]`);
  domEl.remove();
  await tick();

  assert.equal(emits.length, 1);
  assert.equal(emits[0].kind, "step_done");
  assert.equal(emits[0].signal, "removed_or_hidden");
});

test("click：目標被 display:none 隱藏 → step_done", async () => {
  const { window, emits } = makeWindow();
  const el = byName(window, "有 aria-label 的按鈕");
  window.__showme.show({
    uid: el.uid,
    instruction: "點這個按鈕",
    kind: "click",
    index: 1,
    total: 1,
    expect: "",
  });

  const domEl = window.document.querySelector(`[data-showme-uid="${el.uid}"]`);
  domEl.style.display = "none";
  await tick();

  assert.equal(emits.length, 1);
  assert.equal(emits[0].signal, "removed_or_hidden");
});

test("click：URL 變了（pushState）→ step_done，不是靠數 mutation", async () => {
  const { window, emits } = makeWindow();
  const el = byName(window, "一般連結");
  window.__showme.show({
    uid: el.uid,
    instruction: "點這個連結",
    kind: "click",
    index: 1,
    total: 1,
    expect: "",
  });

  window.history.pushState({}, "", "/next-page");
  await tick();

  assert.equal(emits.length, 1);
  assert.equal(emits[0].signal, "url_changed");
});

test("click：純粹 DOM mutation（不移除、不隱藏、URL 沒變）不算完成", async () => {
  const { window, emits } = makeWindow();
  const el = byName(window, "純文字按鈕");
  window.__showme.show({
    uid: el.uid,
    instruction: "點這個按鈕",
    kind: "click",
    index: 1,
    total: 1,
    expect: "",
  });

  // 製造一堆跟目標無關的 mutation
  for (let i = 0; i < 5; i++) {
    const div = window.document.createElement("div");
    div.textContent = "noise-" + i;
    window.document.body.appendChild(div);
  }
  await tick();

  assert.equal(emits.length, 0, "不該因為無關的 mutation 就判定完成");
});

test("input：value 有值且 blur → step_done", async () => {
  const { window, emits } = makeWindow();
  const el = byName(window, "只有 placeholder，沒 label");
  window.__showme.show({
    uid: el.uid,
    instruction: "填這個欄位",
    kind: "input",
    index: 1,
    total: 1,
    expect: "",
  });

  const domEl = window.document.querySelector(`[data-showme-uid="${el.uid}"]`);
  domEl.value = "hello";
  domEl.dispatchEvent(new window.Event("blur"));

  assert.equal(emits.length, 1);
  assert.equal(emits[0].kind, "step_done");
  assert.equal(emits[0].signal, "blur");
});

test("input：blur 但沒填值，不算完成", async () => {
  const { window, emits } = makeWindow();
  const el = byName(window, "只有 placeholder，沒 label");
  window.__showme.show({
    uid: el.uid,
    instruction: "填這個欄位",
    kind: "input",
    index: 1,
    total: 1,
    expect: "",
  });

  const domEl = window.document.querySelector(`[data-showme-uid="${el.uid}"]`);
  domEl.dispatchEvent(new window.Event("blur"));

  assert.equal(emits.length, 0);
});

test("select：change → step_done", async () => {
  const { window, emits } = makeWindow();
  const r = window.__showme.snapshot(1);
  const el = r.elements.find((e) => e.role === "combobox");
  window.__showme.show({
    uid: el.uid,
    instruction: "選一個選項",
    kind: "select",
    index: 1,
    total: 1,
    expect: "",
  });

  const domEl = window.document.querySelector(`[data-showme-uid="${el.uid}"]`);
  domEl.dispatchEvent(new window.Event("change"));

  assert.equal(emits.length, 1);
  assert.equal(emits[0].signal, "change");
});

test("observe：頁面文字出現 expect_text → step_done", async () => {
  const { window, emits } = makeWindow();
  const el = byName(window, "這是一個 h2 標題");
  window.__showme.show({
    uid: el.uid,
    instruction: "看這裡",
    kind: "observe",
    index: 1,
    total: 1,
    expect: "訂單已建立",
  });

  const div = window.document.createElement("div");
  div.textContent = "訂單已建立 #1234";
  window.document.body.appendChild(div);
  await tick();

  assert.equal(emits.length, 1);
  assert.equal(emits[0].signal, "expect_text");
});

test("observe：expect_text 一開始就已經在畫面上，立即完成", async () => {
  const { window, emits } = makeWindow();
  const already = window.document.createElement("div");
  already.textContent = "已經完成囉";
  window.document.body.appendChild(already);

  const el = byName(window, "這是一個 h2 標題");
  window.__showme.show({
    uid: el.uid,
    instruction: "看這裡",
    kind: "observe",
    index: 1,
    total: 1,
    expect: "已經完成囉",
  });

  assert.equal(emits.length, 1, "不用等下一次 mutation 才判定完成");
  assert.equal(emits[0].signal, "expect_text");
});

test("不合法的 kind 會被當成 observe 處理", async () => {
  const { window, emits } = makeWindow();
  const el = byName(window, "這是一個 h2 標題");
  window.__showme.show({
    uid: el.uid,
    instruction: "看這裡",
    kind: "totally-not-a-real-kind",
    index: 1,
    total: 1,
    expect: "亂七八糟",
  });

  const div = window.document.createElement("div");
  div.textContent = "亂七八糟的東西";
  window.document.body.appendChild(div);
  await tick();

  assert.equal(emits.length, 1);
  assert.equal(emits[0].kind, "step_done");
});

test("任何 kind 按 Next 都是 step_done", async () => {
  const { window, emits } = makeWindow();
  const el = byName(window, "只有 placeholder，沒 label");
  window.__showme.show({
    uid: el.uid,
    instruction: "填這個欄位",
    kind: "input",
    index: 2,
    total: 5,
    expect: "",
  });

  const nextBtn = window.document.querySelector(".driver-popover-next-btn");
  assert.ok(nextBtn, "popover 應該要有 Next 按鈕");
  nextBtn.click();

  assert.equal(emits.length, 1);
  assert.equal(emits[0].kind, "step_done");
  assert.equal(emits[0].signal, "next_button");
});

test("任何 kind 按 I'm stuck 都是 stuck", async () => {
  const { window, emits } = makeWindow();
  const el = byName(window, "只有 placeholder，沒 label");
  window.__showme.show({
    uid: el.uid,
    instruction: "填這個欄位",
    kind: "input",
    index: 1,
    total: 1,
    expect: "",
  });

  const stuckBtn = window.document.querySelector(".showme-stuck-btn");
  assert.ok(stuckBtn, "popover 應該要有 I'm stuck 按鈕");
  stuckBtn.click();

  assert.equal(emits.length, 1);
  assert.equal(emits[0].kind, "stuck");
  assert.equal(emits[0].signal, "stuck_button");
});

test("每一步只 emit 一次：完成後再觸發同樣的訊號不會再 emit", async () => {
  const { window, emits } = makeWindow();
  const el = byName(window, "只有 placeholder，沒 label");
  window.__showme.show({
    uid: el.uid,
    instruction: "填這個欄位",
    kind: "input",
    index: 1,
    total: 1,
    expect: "",
  });

  const domEl = window.document.querySelector(`[data-showme-uid="${el.uid}"]`);
  domEl.value = "hello";
  domEl.dispatchEvent(new window.Event("blur"));
  domEl.dispatchEvent(new window.Event("change"));
  domEl.dispatchEvent(new window.Event("blur"));

  assert.equal(emits.length, 1, "多次觸發完成訊號只能 emit 一次");
});

test("clear()：拆掉 highlight／listener，不 emit，且不砍 window.__showme", async () => {
  const { window, emits } = makeWindow();
  const el = byName(window, "只有 placeholder，沒 label");
  window.__showme.show({
    uid: el.uid,
    instruction: "填這個欄位",
    kind: "input",
    index: 1,
    total: 1,
    expect: "",
  });

  window.__showme.clear();
  assert.equal(emits.length, 0, "clear 不算完成，不該 emit");
  assert.ok(window.__showme, "clear 之後 window.__showme 本身還在");

  // clear 之後原本掛的 listener 應該已經拆掉，再觸發完成訊號不該有反應
  const domEl = window.document.querySelector(`[data-showme-uid="${el.uid}"]`);
  domEl.value = "hello";
  domEl.dispatchEvent(new window.Event("blur"));
  assert.equal(emits.length, 0);
});

test("done(text)：畫面上出現固定文案的 banner", async () => {
  const { window } = makeWindow();
  window.__showme.done("✅ Done — you created a project");

  const banner = window.document.getElementById("__showme-banner");
  assert.ok(banner);
  assert.equal(banner.textContent, "✅ Done — you created a project");
});

test("show() 換下一步時，前一步的 highlight／listener 會先被清掉", async () => {
  const { window, emits } = makeWindow();
  const first = byName(window, "只有 placeholder，沒 label");
  window.__showme.show({
    uid: first.uid,
    instruction: "第一步",
    kind: "input",
    index: 1,
    total: 2,
    expect: "",
  });

  const second = byName(window, "textarea 也算 textbox");
  window.__showme.show({
    uid: second.uid,
    instruction: "第二步",
    kind: "input",
    index: 2,
    total: 2,
    expect: "",
  });

  // 第一步的欄位再怎麼觸發都不該讓第二步提早完成或重複 emit
  const firstEl = window.document.querySelector(`[data-showme-uid="${first.uid}"]`);
  firstEl.value = "late";
  firstEl.dispatchEvent(new window.Event("blur"));
  assert.equal(emits.length, 0, "第一步的 listener 應該已經被下一次 show() 清掉");

  const secondEl = window.document.querySelector(`[data-showme-uid="${second.uid}"]`);
  secondEl.value = "on time";
  secondEl.dispatchEvent(new window.Event("blur"));
  assert.equal(emits.length, 1);
});
