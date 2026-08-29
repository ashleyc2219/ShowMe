// tests/fixtures/fake_overlay.js
//
// A 側測試替身（test double）—— 不是產品 overlay。
//
// 這個檔案只模仿 docs/handoff.md 鎖死的介面，讓 A 能在 B 的 overlay 寫好之前
// 驗證 showme/browser.py 的四個 evaluate 包裝。它刻意做得很笨：
//   - 掃 [data-role]（測試 HTML 自己標的），不做 a11y 角色推導
//   - 不用 Driver.js，只在 body 上加一個屬性當「有沒有在 show」的證據
//   - 沒有完成觀察 listener，也不會自己發出完成事件
//     （測試要模擬「人做完了」時，自己用 page.evaluate 手動打一發 emit）
//
// 產品 overlay 在 overlay/overlay.js，由 B 負責。

(function () {
  var MAX_ELEMENTS = 150;
  var calls = [];

  function collect(n) {
    var nodes = document.querySelectorAll("[data-role]");
    var elements = [];
    for (var i = 0; i < nodes.length && i < MAX_ELEMENTS; i += 1) {
      var node = nodes[i];
      var uid = "s" + n + "-" + (i + 1);
      node.setAttribute("data-showme-uid", uid);
      elements.push({
        uid: uid,
        role: node.getAttribute("data-role") || "",
        name: (node.textContent || "").trim(),
        testid: node.getAttribute("data-testid") || "",
      });
    }
    return { elements: elements, truncated: nodes.length > MAX_ELEMENTS };
  }

  window.__showme = {
    _calls: calls,

    snapshot: function (n) {
      calls.push(["snapshot", n]);
      return collect(n);
    },

    show: function (opts) {
      calls.push(["show", opts]);
      document.body.setAttribute("data-showme-showing", opts.uid);
    },

    clear: function () {
      calls.push(["clear"]);
      document.body.removeAttribute("data-showme-showing");
    },

    done: function (text) {
      calls.push(["done", text]);
      var banner = document.getElementById("showme-banner");
      if (!banner) {
        banner = document.createElement("div");
        banner.id = "showme-banner";
        document.body.appendChild(banner);
      }
      banner.textContent = text;
    },
  };
})();
