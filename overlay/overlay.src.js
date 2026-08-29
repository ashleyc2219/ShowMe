/*
 * ShowMe overlay — 人員 B 負責。
 *
 * 這份檔案不是直接注入的檔案：build.sh 會把它跟 vendor/driver.iife.js、
 * vendor/driver.css 串成 overlay/dist/overlay.bundle.js，人員 A 用
 * `context.add_init_script(path="overlay/dist/overlay.bundle.js")` 注入一個檔案。
 *
 * 對外只暴露 window.__showme = { snapshot, show, clear, done }，
 * 以及會呼叫 window.__showme_emit({ kind, url, ts, signal })（由人員 A 的
 * page.expose_function 提供，此檔不負責定義它）。
 *
 * 目前進度（S3）：snapshot() 已實作、可獨立測試。
 * show / observe / clear / done 是 S4 待做，先留 stub 不讓呼叫直接炸掉。
 * 對應規格：docs/design/showme.md §10（snapshot/uid）、§11（完成判定）、§12（介面）。
 */
(function () {
  "use strict";

  // 已經注入過就不要重複安裝（例如同一頁被重複 add_init_script 兩次）。
  if (window.__showme) {
    return;
  }

  // ---------------------------------------------------------------------
  // 角色白名單（docs/design/showme.md §10）：
  // button、link、textbox、checkbox、radio、combobox、menuitem、tab、
  // heading、alert。
  //
  // 每個角色一組 CSS selector；全部合併成一個 selector 字串後只呼叫一次
  // querySelectorAll —— DOM 規範保證回傳結果依 tree order 排列，且同一個
  // 元素就算同時符合多個子 selector 也只會出現一次，天然去重、天然照 DOM 序。
  // ---------------------------------------------------------------------
  var ROLE_SELECTORS = {
    button:
      'button, input[type="button"], input[type="submit"], input[type="reset"], [role="button"]',
    link: 'a[href], [role="link"]',
    textbox:
      'input:not([type]), input[type="text"], input[type="search"], ' +
      'input[type="email"], input[type="url"], input[type="tel"], ' +
      'input[type="password"], input[type="number"], textarea, ' +
      '[role="textbox"], [contenteditable="true"], [contenteditable=""]',
    checkbox: 'input[type="checkbox"], [role="checkbox"]',
    radio: 'input[type="radio"], [role="radio"]',
    combobox: 'select, [role="combobox"]',
    menuitem: '[role="menuitem"]',
    tab: '[role="tab"]',
    heading: 'h1, h2, h3, h4, h5, h6, [role="heading"]',
    alert: '[role="alert"]',
  };

  // 顯性 role="..." 覆蓋原生標籤語意時的優先序（ARIA 精神：作者指定的 role 優先）。
  var EXPLICIT_ROLE_WHITELIST = Object.keys(ROLE_SELECTORS);

  var ALL_SELECTOR = Object.keys(ROLE_SELECTORS)
    .map(function (k) {
      return ROLE_SELECTORS[k];
    })
    .join(", ");

  var MAX_ELEMENTS = 150;

  // 原生標籤 → 角色 的 fallback 表（沒有顯性 role 屬性時用這個判斷）。
  function nativeRoleOf(el) {
    var tag = el.tagName.toLowerCase();
    if (tag === "button") return "button";
    if (tag === "a" && el.hasAttribute("href")) return "link";
    if (tag === "select") return "combobox";
    if (tag === "textarea") return "textbox";
    if (/^h[1-6]$/.test(tag)) return "heading";
    if (tag === "input") {
      var type = (el.getAttribute("type") || "text").toLowerCase();
      if (type === "button" || type === "submit" || type === "reset") return "button";
      if (type === "checkbox") return "checkbox";
      if (type === "radio") return "radio";
      // text/search/email/url/tel/password/number/沒填 type 都算 textbox
      return "textbox";
    }
    if (el.hasAttribute("contenteditable")) {
      var ce = el.getAttribute("contenteditable").toLowerCase();
      if (ce === "true" || ce === "") return "textbox";
    }
    return null;
  }

  function roleOf(el) {
    var explicit = (el.getAttribute("role") || "").toLowerCase();
    if (explicit && EXPLICIT_ROLE_WHITELIST.indexOf(explicit) !== -1) {
      return explicit;
    }
    return nativeRoleOf(el) || explicit || "";
  }

  // ---------------------------------------------------------------------
  // 簡化版 accessible name：不是完整 W3C accname 演算法，但涵蓋一般表單/
  // 按鈕會用到的來源，順序大致照官方演算法的優先序。沒有就回傳 ""
  // （spec 明講：沒有 a11y name，name 為空字串，元素仍要列出）。
  // ---------------------------------------------------------------------
  function collapse(s) {
    return (s || "").replace(/\s+/g, " ").trim();
  }

  function labelFor(el) {
    if (el.id) {
      var byFor = document.querySelector('label[for="' + cssEscape(el.id) + '"]');
      if (byFor) return collapse(byFor.textContent);
    }
    var wrapping = el.closest ? el.closest("label") : null;
    if (wrapping) return collapse(wrapping.textContent);
    return "";
  }

  function cssEscape(s) {
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return String(s).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
  }

  function accessibleName(el) {
    var ariaLabel = collapse(el.getAttribute("aria-label"));
    if (ariaLabel) return ariaLabel;

    var labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
      var text = labelledBy
        .split(/\s+/)
        .map(function (id) {
          var ref = document.getElementById(id);
          return ref ? collapse(ref.textContent) : "";
        })
        .filter(Boolean)
        .join(" ");
      if (text) return collapse(text);
    }

    var label = labelFor(el);
    if (label) return label;

    var tag = el.tagName.toLowerCase();
    if (tag === "input") {
      var type = (el.getAttribute("type") || "text").toLowerCase();
      if (type === "button" || type === "submit" || type === "reset") {
        var v = collapse(el.getAttribute("value"));
        if (v) return v;
      }
    }
    if (tag === "input" || tag === "textarea") {
      var placeholder = collapse(el.getAttribute("placeholder"));
      if (placeholder) return placeholder;
    }

    var text = collapse(el.textContent);
    if (text) return text;

    var img = el.querySelector ? el.querySelector("img[alt]") : null;
    if (img) {
      var alt = collapse(img.getAttribute("alt"));
      if (alt) return alt;
    }

    var title = collapse(el.getAttribute("title"));
    if (title) return title;

    return "";
  }

  // ---------------------------------------------------------------------
  // snapshot(n) → { elements, truncated }
  // ---------------------------------------------------------------------
  function snapshot(snapshotNumber) {
    var all = document.querySelectorAll(ALL_SELECTOR);
    var truncated = all.length > MAX_ELEMENTS;
    var limited = Array.prototype.slice.call(all, 0, MAX_ELEMENTS);

    var elements = limited.map(function (el, i) {
      var uid = "s" + snapshotNumber + "-" + (i + 1);
      el.setAttribute("data-showme-uid", uid);
      return {
        uid: uid,
        role: roleOf(el),
        name: accessibleName(el),
        testid: el.getAttribute("data-testid") || "",
      };
    });

    return { elements: elements, truncated: truncated };
  }

  // ---------------------------------------------------------------------
  // emit：唯一跟 Python 講話的管道。__showme_emit 由人員 A 的
  // page.expose_function 提供，這份檔案不負責定義它。
  // ---------------------------------------------------------------------
  function emit(kind, extra) {
    var payload = Object.assign(
      { kind: kind, url: location.href, ts: Date.now() },
      extra || {}
    );
    if (typeof window.__showme_emit === "function") {
      window.__showme_emit(payload);
    } else {
      console.warn("[showme] __showme_emit 不存在（在 Playwright 外測試？）", payload);
    }
  }

  // ---------------------------------------------------------------------
  // history.pushState / replaceState 只包一次；popstate、hashchange 一起轉成
  // 同一個自訂事件，observe(kind="click") 用它判斷 URL 變了沒（§11）。
  // ---------------------------------------------------------------------
  var historyPatched = false;
  function patchHistoryOnce() {
    if (historyPatched) return;
    historyPatched = true;

    function fireLocationChange() {
      window.dispatchEvent(new Event("showme:locationchange"));
    }

    var rawPush = history.pushState;
    var rawReplace = history.replaceState;
    history.pushState = function () {
      var ret = rawPush.apply(this, arguments);
      fireLocationChange();
      return ret;
    };
    history.replaceState = function () {
      var ret = rawReplace.apply(this, arguments);
      fireLocationChange();
      return ret;
    };
    window.addEventListener("popstate", fireLocationChange);
    window.addEventListener("hashchange", fireLocationChange);
  }

  // driver.css 由 build.sh 內嵌成 __SHOWME_DRIVER_CSS__（沒 vendor 進來時這個
  // 識別字根本不存在——用 typeof 判斷才不會直接 ReferenceError）。
  var driverCssInjected = false;
  function injectDriverCssOnce() {
    if (driverCssInjected) return;
    driverCssInjected = true;
    if (typeof __SHOWME_DRIVER_CSS__ === "undefined") {
      console.error(
        "[showme] driver.css 沒有內嵌進來：確認 overlay/vendor/driver.css 存在，且是跑 " +
          "./build.sh 產生的 overlay.js，不是直接載入 overlay.src.js。"
      );
      return;
    }
    var style = document.createElement("style");
    style.setAttribute("data-showme", "driver-css");
    style.textContent = __SHOWME_DRIVER_CSS__;
    (document.head || document.documentElement).appendChild(style);
  }

  // 「隱藏」的最小集合定義（§11 design，非像素級）：
  // 不在 document 裡、display:none、visibility:hidden、aria-hidden=true。
  function isGone(el) {
    if (!el.isConnected) return true;
    var style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return true;
    if (el.getAttribute("aria-hidden") === "true") return true;
    return false;
  }

  // rAF 內合併同一畫面內的多次 mutation callback，避免對每個 mutation 都重算一次
  // getComputedStyle／innerText——這只是節流，不是「數 mutation 次數」判完成。
  function rafDebounce(fn) {
    var scheduled = false;
    return function () {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(function () {
        scheduled = false;
        fn();
      });
    };
  }

  // ---------------------------------------------------------------------
  // 進行中那一步的狀態。同一時間最多一份；每份只准 emit 一次（finish 的 guard）。
  // ---------------------------------------------------------------------
  var current = null;

  function teardown() {
    if (!current) return;
    var c = current;
    current = null;
    c.cleanupFns.forEach(function (fn) {
      try {
        fn();
      } catch (e) {
        console.error("[showme] teardown 清理失敗", e);
      }
    });
    if (c.driverInstance) {
      try {
        c.driverInstance.destroy();
      } catch (e) {
        console.error("[showme] driver destroy 失敗", e);
      }
    }
  }

  function finish(kind, signal) {
    if (!current || current.emitted) return;
    current.emitted = true;
    var uid = current.uid;
    teardown();
    emit(kind, { signal: signal, uid: uid });
  }

  // ---------------------------------------------------------------------
  // observe(kind, el, expectText)：依 kind 掛完成條件的 listener，全部塞進
  // current.cleanupFns，讓 teardown() 統一拆。任何 kind 共同的 Next／I'm stuck
  // 不在這裡處理，是 show() 掛在 Driver.js popover 按鈕上。
  // ---------------------------------------------------------------------
  function observe(kind, el, expectText) {
    if (kind === "click") {
      var startUrl = location.href;

      var checkGone = rafDebounce(function () {
        if (isGone(el)) finish("step_done", "removed_or_hidden");
      });
      var mo = new MutationObserver(checkGone);
      mo.observe(document.documentElement, {
        subtree: true,
        childList: true,
        attributes: true,
        attributeFilter: ["style", "class", "aria-hidden", "hidden"],
      });
      current.cleanupFns.push(function () {
        mo.disconnect();
      });

      function onLocationChange() {
        if (location.href !== startUrl) finish("step_done", "url_changed");
      }
      window.addEventListener("showme:locationchange", onLocationChange);
      current.cleanupFns.push(function () {
        window.removeEventListener("showme:locationchange", onLocationChange);
      });
      return;
    }

    if (kind === "input") {
      function onInputSignal(e) {
        if ((el.value || "").length > 0) finish("step_done", e.type);
      }
      el.addEventListener("blur", onInputSignal);
      el.addEventListener("change", onInputSignal);
      current.cleanupFns.push(function () {
        el.removeEventListener("blur", onInputSignal);
        el.removeEventListener("change", onInputSignal);
      });
      return;
    }

    if (kind === "select") {
      function onChange() {
        finish("step_done", "change");
      }
      el.addEventListener("change", onChange);
      current.cleanupFns.push(function () {
        el.removeEventListener("change", onChange);
      });
      return;
    }

    // observe，以及不合法 kind 一律落到這裡（T 層已轉成 observe，這裡只管完成條件）。
    if (!expectText) {
      // Python 應該已經擋掉空 expect_text 才會呼叫 show；防禦性處理，不掛 observer。
      return;
    }
    var checkText = rafDebounce(function () {
      var body = document.body ? document.body.innerText : "";
      if (body.indexOf(expectText) !== -1) finish("step_done", "expect_text");
    });
    var textMo = new MutationObserver(checkText);
    textMo.observe(document.body, { childList: true, subtree: true, characterData: true });
    current.cleanupFns.push(function () {
      textMo.disconnect();
    });
    // 立即檢查一次：expect_text 有可能在開始觀察的當下就已經在畫面上。
    var body0 = document.body ? document.body.innerText : "";
    if (body0.indexOf(expectText) !== -1) finish("step_done", "expect_text");
  }

  // ---------------------------------------------------------------------
  // show({uid, instruction, kind, index, total, expect})
  // ---------------------------------------------------------------------
  var VALID_KINDS = ["click", "input", "select", "observe"];

  function show(opts) {
    teardown(); // 上一步如果還沒收尾（理論上 A 會先等 finish 才叫下一次 show），先清乾淨、不 emit

    var uid = opts.uid;
    var kind = VALID_KINDS.indexOf(opts.kind) !== -1 ? opts.kind : "observe";
    var expect = opts.expect || "";

    var el = document.querySelector('[data-showme-uid="' + cssEscape(uid) + '"]');
    if (!el) {
      console.error("[showme] show(): 找不到 uid 對應的元素", uid);
      return;
    }

    injectDriverCssOnce();
    patchHistoryOnce();

    if (typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ block: "center", behavior: "instant" });
    }

    current = { uid: uid, emitted: false, cleanupFns: [], driverInstance: null };

    var driverFactory =
      window.driver && window.driver.js && window.driver.js.driver;
    if (typeof driverFactory !== "function") {
      console.error(
        "[showme] Driver.js 沒有載入：確認 overlay/vendor/driver.iife.js 存在，且是跑 " +
          "./build.sh 產生的 overlay.js。沒有高亮還是繼續判斷完成條件，不然會整個卡死。"
      );
      observe(kind, el, expect);
      return;
    }

    var driverObj = driverFactory({
      animate: true,
      allowClose: false,
      overlayOpacity: 0.5,
      stagePadding: 6,
      popoverClass: "showme-popover",
    });
    current.driverInstance = driverObj;

    driverObj.highlight({
      element: el,
      popover: {
        title: "Step " + opts.index + " / " + opts.total,
        description: opts.instruction || "",
        showButtons: ["next"],
        nextBtnText: "Next",
        onNextClick: function () {
          finish("step_done", "next_button");
        },
        onPopoverRender: function (popover) {
          var stuckBtn = document.createElement("button");
          stuckBtn.type = "button";
          stuckBtn.textContent = "I'm stuck";
          stuckBtn.className = "driver-popover-footer-btn showme-stuck-btn";
          stuckBtn.style.marginLeft = "8px";
          stuckBtn.addEventListener("click", function () {
            finish("stuck", "stuck_button");
          });
          popover.footerButtons.appendChild(stuckBtn);
        },
      },
    });

    observe(kind, el, expect);
  }

  // ---------------------------------------------------------------------
  // clear() / done(text)
  // ---------------------------------------------------------------------
  var BANNER_ID = "__showme-banner";

  function removeBanner() {
    var el = document.getElementById(BANNER_ID);
    if (el) el.remove();
  }

  function showBanner(text) {
    removeBanner();
    var el = document.createElement("div");
    el.id = BANNER_ID;
    el.textContent = text;
    el.style.cssText = [
      "position:fixed",
      "top:16px",
      "left:50%",
      "transform:translateX(-50%)",
      "z-index:2147483647",
      "background:#16a34a",
      "color:#fff",
      "font:600 15px/1.4 system-ui,sans-serif",
      "padding:10px 20px",
      "border-radius:8px",
      "box-shadow:0 4px 16px rgba(0,0,0,.25)",
    ].join(";");
    document.body.appendChild(el);
  }

  function clear() {
    teardown();
    removeBanner();
  }

  function done(text) {
    teardown();
    showBanner(text);
  }

  window.__showme = {
    snapshot: snapshot,
    show: show,
    clear: clear,
    done: done,
  };
})();
