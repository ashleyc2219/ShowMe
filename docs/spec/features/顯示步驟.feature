Feature: 顯示步驟
  作為 Qoder Agent
  我想要呼叫 show_step
  以便驗證 uid、畫出下一步、阻塞等待使用者做完、再拿到新的 page

  Rule: 畫出 overlay 後阻塞直到使用者做完或逾時
    Example: 使用者完成後才回傳
      Given 最新 page.elements 含
        | uid  | role   | name        |
        | s1-4 | button | New Project |
      When 呼叫 show_step
        | uid  | instruction       | kind  | step_index | step_total |
        | s1-4 | Click New Project | click | 1          | 4          |
      And 完成訊號為
        | signal      |
        | url_changed |
      Then 回傳的 event 為
        | event     |
        | step_done |

  Rule: 操作失敗時寫在回傳的 error，不丟例外
    Example: 已畫滿 12 步
      Given session 的 steps_shown 為
        | steps_shown |
        | 12          |
      When 呼叫 show_step
        | uid  | instruction       | kind  | step_index | step_total |
        | s1-4 | Click New Project | click | 1          | 4          |
      Then 操作失敗
      And 錯誤為
        | error              |
        | max_steps_exceeded |

  Rule: 僅在 session 狀態為 READY 時可成功畫出步驟
    #TODO

  Rule: steps_shown 大於等於 12 時操作失敗且錯誤為 max_steps_exceeded
    Example: 已畫滿 12 步
      Given session 的 steps_shown 為
        | steps_shown |
        | 12          |
      When 呼叫 show_step
        | uid  | instruction        | kind  | step_index | step_total |
        | s1-4 | Click New Project  | click | 1          | 4          |
      Then 操作失敗
      And 錯誤為
        | error               |
        | max_steps_exceeded  |

  Rule: uid 不在最新 snapshot 時操作失敗且錯誤為 uid_not_in_snapshot
    #TODO

  Rule: uid 不在最新 snapshot 時回傳新鮮 page 且 uid snapshot# 加一
    #TODO

  Rule: session 不存在時操作失敗且錯誤為 session_not_found
    #TODO

  Rule: uid 通過驗證後畫出高亮與 popover（說明、Step k / N、Next、I'm stuck）
    #TODO

  Rule: uid 通過驗證並畫出後 steps_shown 加 1，含 I'm stuck 後對同一 uid 再畫
    Example: 卡住後同一 uid 再畫仍加 1
      Given session 的 steps_shown 為
        | steps_shown |
        | 3           |
      And 最新 page.elements 含
        | uid  | role   | name        |
        | s1-4 | button | New Project |
      When 呼叫 show_step
        | uid  | instruction                  | kind  | step_index | step_total |
        | s1-4 | Click the New Project button | click | 1          | 4          |
      Then session 的 steps_shown 為
        | steps_shown |
        | 4           |

  Rule: 畫出後 session 狀態為 SHOWING 直到事件
    #TODO

  Rule: 收到事件後 session 狀態為 READY 並回傳新 page
    Example: 點擊 New Project 後 URL 變更
      Given 最新 page.elements 含
        | uid  | role   | name        |
        | s1-4 | button | New Project |
      When 呼叫 show_step
        | uid  | instruction        | kind  | step_index | step_total |
        | s1-4 | Click New Project  | click | 1          | 4          |
      And 完成訊號為
        | signal      |
        | url_changed |
      Then 回傳的 event 為
        | event     |
        | step_done |
      And 回傳的 elapsed_s 為
        | elapsed_s |
        | 4.2       |
      And 回傳的 page.url 為
        | url                                  |
        | http://localhost:3000/projects/new   |
      And 回傳的 page.title 為
        | title       |
        | New Project |
      And session 的 state 為
        | state |
        | READY |

  Rule: kind 為 click 時目標元素被移除或隱藏即完成
    #TODO

  Rule: kind 為 click 時 URL 變更即完成
    Example: 點擊後進入 New Project 頁
      Given 最新 page.elements 含
        | uid  | role   | name        |
        | s1-4 | button | New Project |
      When 呼叫 show_step
        | uid  | instruction        | kind  | step_index | step_total |
        | s1-4 | Click New Project  | click | 1          | 4          |
      And 完成訊號為
        | signal      |
        | url_changed |
      Then 回傳的 event 為
        | event     |
        | step_done |
      And 回傳的 page.url 為
        | url                                  |
        | http://localhost:3000/projects/new   |

  Rule: kind 為 click 時不以 DOM mutation 次數作為完成條件
    Example: 僅 DOM 變動且目標仍在、網址未變、未按 Next
      Given 最新 page.elements 含
        | uid  | role   | name        |
        | s1-4 | button | New Project |
      When 呼叫 show_step
        | uid  | instruction       | kind  | step_index | step_total |
        | s1-4 | Click New Project | click | 1          | 4          |
      And 發生 DOM mutation
      And 目標元素仍可見
      And page.url 未變更
      And 使用者未按 Next
      Then 尚未回傳

  Rule: kind 為 click 時不等待 HTTP response 作為完成條件
    #TODO

  Rule: kind 為 input 時目標 value 長度大於 0 且觸發 blur 或 change 即完成
    Example: 填入後完成
      When 呼叫 show_step
        | uid  | instruction           | kind  | step_index | step_total |
        | s2-9 | Type a project name   | input | 2          | 4          |
      And 目標 value 長度大於 0 且觸發 blur 或 change
      Then 回傳的 event 為
        | event     |
        | step_done |

  Rule: kind 為 input 時使用者按 Next 即完成
    #TODO

  Rule: kind 為 select 時目標觸發 change 即完成
    #TODO

  Rule: kind 不屬於 click、input、select、observe 時視為 observe
    Example: 傳入 tap 且 expect_text 為空
      Given 最新 page.elements 含
        | uid   | role    | name        |
        | s2-h1 | heading | New Project |
      When 呼叫 show_step
        | uid   | instruction          | kind | step_index | step_total | expect_text |
        | s2-h1 | Wait for the heading | tap  | 1          | 4          |             |
      Then 操作失敗
      And 錯誤為
        | error                |
        | expect_text_required |

  Rule: kind 為 observe 且 expect_text 為空時操作失敗且錯誤為 expect_text_required
    Example: 等文字出現但沒帶文字
      Given 最新 page.elements 含
        | uid  | role    | name        |
        | s2-h1 | heading | New Project |
      When 呼叫 show_step
        | uid   | instruction          | kind    | step_index | step_total | expect_text |
        | s2-h1 | Wait for the heading | observe | 1          | 4          |             |
      Then 操作失敗
      And 錯誤為
        | error                 |
        | expect_text_required  |

  Rule: kind 為 observe 時出現 expect_text 即完成
    #TODO

  Rule: kind 為 observe 時使用者按 Next 即完成
    #TODO

  Rule: 任何 kind 使用者按 Next 時 event 為 step_done
    #TODO

  Rule: 任何 kind 使用者按 I'm stuck 時 event 為 stuck
    #TODO

  Rule: 完成判定只看 event，signal 可為空且不列入驗收
    Example: 完成時不檢查 signal
      Given 最新 page.elements 含
        | uid  | role   | name        |
        | s1-4 | button | New Project |
      When 呼叫 show_step
        | uid  | instruction       | kind  | step_index | step_total |
        | s1-4 | Click New Project | click | 1          | 4          |
      And 完成訊號為
        | signal      |
        | url_changed |
      Then 回傳的 event 為
        | event     |
        | step_done |

  Rule: timeout_s 未傳或為 0 或負值時視為 120
    Example: 傳入 0
      Given 最新 page.elements 含
        | uid  | role   | name        |
        | s1-4 | button | New Project |
      When 呼叫 show_step
        | uid  | instruction       | kind  | step_index | step_total | timeout_s |
        | s1-4 | Click New Project | click | 1          | 4          | 0         |
      Then 此步的 timeout_s 為
        | timeout_s |
        | 120       |

  Rule: elapsed_s 大於等於 timeout_s 時 event 為 timeout 且狀態為 READY
    Example: 剛好等於 timeout_s
      Given 最新 page.elements 含
        | uid  | role   | name        |
        | s1-4 | button | New Project |
      When 呼叫 show_step
        | uid  | instruction       | kind  | step_index | step_total | timeout_s |
        | s1-4 | Click New Project | click | 1          | 4          | 120       |
      And 經過秒數為
        | elapsed_s |
        | 120       |
      Then 回傳的 event 為
        | event   |
        | timeout |
      And session 的 state 為
        | state |
        | READY |

    Example: 完成訊號與截止同一瞬間仍為 timeout
      Given 最新 page.elements 含
        | uid  | role   | name        |
        | s1-4 | button | New Project |
      When 呼叫 show_step
        | uid  | instruction       | kind  | step_index | step_total | timeout_s |
        | s1-4 | Click New Project | click | 1          | 4          | 120       |
      And 經過秒數為
        | elapsed_s |
        | 120       |
      And 使用者按 Next
      Then 回傳的 event 為
        | event   |
        | timeout |

  Rule: 每步恰好回傳一次事件；同一 session 同一 ts 後至的事件丟棄
    Example: 同 ts 第二筆不取代第一筆
      Given 該步已收到第一筆事件
        | session_id | ts         | kind      |
        | s_8f2a     | 1756400000 | step_done |
      When 同一 session 同一 ts 再收到一筆
        | session_id | ts         | kind  |
        | s_8f2a     | 1756400000 | stuck |
      Then 回傳的 event 為
        | event     |
        | step_done |

  Rule: 同一 session 並發的 show_step 被拒絕且錯誤為 show_step_in_progress
    Example: 正在等使用者時又畫下一步
      Given session 的 state 為
        | state   |
        | SHOWING |
      When 呼叫 show_step
        | uid  | instruction       | kind  | step_index | step_total |
        | s1-4 | Click New Project | click | 1          | 4          |
      Then 操作失敗
      And 錯誤為
        | error                  |
        | show_step_in_progress  |

  Rule: event 為 off_script 時回傳新 page（stretch）
    #TODO
