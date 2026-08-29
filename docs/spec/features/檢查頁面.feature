Feature: 檢查頁面
  作為 Qoder Agent
  我想要呼叫 inspect_page
  以便在不畫任何東西的情況下取得新鮮的濃縮 snapshot

  Rule: 成功時回傳新鮮的濃縮 page
    #TODO

  Rule: session 狀態不是 READY 時操作失敗
    #TODO

  Rule: 成功時回傳的 page 其 uid snapshot# 比上一份加一
    Example: 開始教學之後第一次檢查頁面
      Given session 的 session_id 為
        | session_id |
        | s_8f2a     |
      And 最新 page.elements 含
        | uid  | role   | name        |
        | s1-4 | button | New Project |
      When 呼叫 inspect_page
        | session_id |
        | s_8f2a     |
      Then 回傳的 page.elements 含
        | uid  |
        | s2-4 |

  Rule: session 不存在時操作失敗且錯誤為 session_not_found
    Example: 尚未開始教學就檢查頁面
      When 呼叫 inspect_page
        | session_id |
        | s_missing  |
      Then 操作失敗
      And 錯誤為
        | error              |
        | session_not_found  |

  Rule: 呼叫後不畫任何 overlay 步驟
    #TODO

  Rule: page.truncated 為 true 時仍回傳濃縮 page 供再看
    #TODO
