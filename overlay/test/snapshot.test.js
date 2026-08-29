// window.__showme.snapshot() 的自動化檢查，跑在 jsdom（不需要真的瀏覽器）。
// 用法：cd overlay && npm install && npm test
//
// 對應規格：docs/design/showme.md §10；fixture 頁面在 overlay/test/fixture.html。
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");

const FIXTURE_PATH = path.join(__dirname, "fixture.html");
// 測的是「產物」overlay.js（跑 ../build.sh 產生），不是原始碼 overlay.src.js——
// 這樣才能同時抓到邏輯錯誤跟 build.sh 串接錯誤。改完 overlay.src.js 記得先
// `./build.sh` 再跑測試。
const OVERLAY_BUILT_PATH = path.join(__dirname, "..", "overlay.js");

// 每個 test file 只建一次 DOM，snapshot(1) 的斷言互不修改 DOM，
// 只有截斷那組會另外自己 append 200 個 button 再呼叫 snapshot(2)。
const dom = new JSDOM(fs.readFileSync(FIXTURE_PATH, "utf8"), {
  runScripts: "dangerously",
  url: "http://localhost/fixture.html",
});
// fixture.html 自己的 <script src="../overlay.js"> 在 jsdom 下沒有真的 http
// server 可以載，所以改成直接把產物 eval 進同一個 window。
dom.window.eval(fs.readFileSync(OVERLAY_BUILT_PATH, "utf8"));

const { window } = dom;
const r1 = window.__showme.snapshot(1);

function byName(name) {
  return r1.elements.find((e) => e.name === name);
}
function byTestid(id) {
  return r1.elements.find((e) => e.testid === id);
}

test("snapshot(1) 沒有超過 150 個元素，不用截斷", () => {
  assert.equal(r1.truncated, false);
});

test("純文字 button：role=button，name 來自文字內容", () => {
  const el = byName("純文字按鈕");
  assert.ok(el);
  assert.equal(el.role, "button");
});

test("aria-label 蓋過文字內容", () => {
  assert.ok(byName("有 aria-label 的按鈕"));
});

test("data-testid 有抓到", () => {
  const el = byTestid("submit-btn");
  assert.ok(el);
  assert.equal(el.role, "button");
});

test("input[type=submit]：role=button，name 來自 value", () => {
  const el = byName("input[type=submit]");
  assert.ok(el);
  assert.equal(el.role, "button");
});

test("disabled 的 button 仍然列出（spec 沒說要濾掉）", () => {
  const el = r1.elements.find((e) => e.name.startsWith("disabled 按鈕"));
  assert.ok(el);
});

test("a[href]：role=link", () => {
  const el = byName("一般連結");
  assert.ok(el);
  assert.equal(el.role, "link");
});

test("沒有 href 的 <a> 不列入", () => {
  assert.equal(byName("沒有 href，不該被抓到"), undefined);
});

test("label[for] 解析成 input 的 name", () => {
  const el = byName("姓名");
  assert.ok(el);
  assert.equal(el.role, "textbox");
});

test("沒有 label 時 fallback 用 placeholder", () => {
  assert.ok(byName("只有 placeholder，沒 label"));
});

test("aria-label 優先於 placeholder", () => {
  assert.ok(byName("aria-label 優先於 placeholder"));
  assert.equal(byName("不該出現這個"), undefined);
});

test("textarea 的 placeholder 也會被抓（迴歸測試：曾經漏抓）", () => {
  const el = byName("textarea 也算 textbox");
  assert.ok(el);
  assert.equal(el.role, "textbox");
});

test("contenteditable=true 的元素算 textbox（迴歸測試：isContentEditable 在 jsdom 不可靠）", () => {
  const el = byName("contenteditable 也算 textbox");
  assert.ok(el);
  assert.equal(el.role, "textbox");
});

test("checkbox：name 抓外層 <label> 的文字", () => {
  const el = r1.elements.find((e) => e.role === "checkbox");
  assert.ok(el);
  assert.equal(el.name, "我同意");
});

test("兩個 radio 都抓到", () => {
  const radios = r1.elements.filter((e) => e.role === "radio");
  assert.equal(radios.length, 2);
});

test("select：role=combobox", () => {
  assert.ok(r1.elements.find((e) => e.role === "combobox"));
});

test("role=menuitem 抓到，name 來自文字", () => {
  const el = r1.elements.find((e) => e.role === "menuitem");
  assert.ok(el);
  assert.equal(el.name, "選單項目");
});

test("role=tab 抓到", () => {
  const el = r1.elements.find((e) => e.role === "tab");
  assert.ok(el);
  assert.equal(el.name, "分頁 A");
});

test("h2 算 heading", () => {
  const el = byName("這是一個 h2 標題");
  assert.ok(el);
  assert.equal(el.role, "heading");
});

test("role=alert 抓到", () => {
  const el = byName("這是一個 alert 訊息");
  assert.ok(el);
  assert.equal(el.role, "alert");
});

test("純文字 div／span 不是互動角色，不列入", () => {
  assert.equal(byName("純文字 div，沒有互動角色"), undefined);
});

test("uid 格式是 s{snapshot#}-{index}，且真的寫進 DOM 屬性", () => {
  const el = byName("純文字按鈕");
  assert.match(el.uid, /^s1-\d+$/);
  const domEl = window.document.querySelector(`[data-showme-uid="${el.uid}"]`);
  assert.ok(domEl);
  assert.equal(domEl.textContent, "純文字按鈕");
});

test("每個 element 的 testid／name 鍵一定存在且是字串", () => {
  for (const el of r1.elements) {
    assert.equal(typeof el.testid, "string");
    assert.equal(typeof el.name, "string");
  }
});

test("超過 150 個元素時截斷在 150、truncated=true、uid 延續 snapshot#", () => {
  for (let i = 0; i < 200; i++) {
    const b = window.document.createElement("button");
    b.textContent = "extra-" + i;
    window.document.body.appendChild(b);
  }
  const r2 = window.__showme.snapshot(2);
  assert.equal(r2.elements.length, 150);
  assert.equal(r2.truncated, true);
  assert.match(r2.elements[0].uid, /^s2-/);
  assert.equal(r2.elements[149].uid, "s2-150");
});
