Feature: 開始教學
  作為 Qoder Agent
  我想要呼叫 start_tutorial
  以便開啟目標 app 並取得第一份頁面結構

  Rule: 成功開始後回傳的 goal 等於傳入的 goal
    Example: 開始 create a project
      When 呼叫 start_tutorial
        | url                        | goal              |
        | http://localhost:3000      | create a project  |
      Then 回傳的 goal 為
        | goal             |
        | create a project |

  Rule: 成功開始後回傳第一份濃縮 page，uid 的 snapshot# 為 1
    Example: Dashboard 的第一份 snapshot
      When 呼叫 start_tutorial
        | url                        | goal              |
        | http://localhost:3000      | create a project  |
      Then 回傳的 page.url 為
        | url                     |
        | http://localhost:3000/  |
      And 回傳的 page.title 為
        | title     |
        | Dashboard |
      And 回傳的 page.truncated 為
        | truncated |
        | false     |
      And 回傳的 page.elements 為
        | uid  | role   | name        | testid      |
        | s1-4 | button | New Project | new-project |
        | s1-7 | link   | Settings    |             |

  Rule: 成功開始後 session 狀態為 READY
    Example: start_tutorial 之後狀態
      When 呼叫 start_tutorial
        | url                        | goal              |
        | http://localhost:3000      | create a project  |
      Then session 的 state 為
        | state |
        | READY |

  Rule: 同一時間只允許一個教學場次，再次開始教學時場次識別不變並覆蓋目標與網址
    Example: 進行中再開始另一個目標
      Given session 的 session_id 為
        | session_id |
        | s_8f2a     |
      And session 的 goal 為
        | goal             |
        | create a project |
      When 呼叫 start_tutorial
        | url                   | goal             |
        | http://localhost:3000 | invite a member  |
      Then 回傳的 session_id 為
        | session_id |
        | s_8f2a     |
      And 回傳的 goal 為
        | goal            |
        | invite a member |
      And session 的 state 為
        | state |
        | READY |
      And session 的 steps_shown 為
        | steps_shown |
        | 0           |

  Rule: goal 為空字串時仍成功開始
    Example: 空目標照常開頁
      When 呼叫 start_tutorial
        | url                        | goal |
        | http://localhost:3000      |      |
      Then 回傳的 goal 為
        | goal |
        |      |
      And session 的 state 為
        | state |
        | READY |

  Rule: 開始教學不因 url 不是 localhost 而操作失敗
    #TODO

  Rule: 目標 url 無法開啟時操作失敗且錯誤為 navigation_failed
    Example: 打不開的網址
      When 呼叫 start_tutorial
        | url                    | goal             |
        | http://localhost:1     | create a project |
      Then 操作失敗
      And 錯誤為
        | error              |
        | navigation_failed  |

  Rule: 回傳的 page.elements 只含互動角色與 heading 與 alert
    #TODO

  Rule: page.elements 硬上限 150，依 DOM 走訪順序取前 150，不分 viewport
    Example: 不多於 150 個時 truncated 為 false
      When 呼叫 start_tutorial
        | url                        | goal              |
        | http://localhost:3000      | create a project  |
      Then 回傳的 page.truncated 為
        | truncated |
        | false     |

    Example: 超過 150 個時只留前 150 且 truncated 為 true
      Given 符合條件的互動角色與 heading 與 alert 共 151 個
      When 呼叫 start_tutorial
        | url                        | goal              |
        | http://localhost:3000      | create a project  |
      Then 回傳的 page.truncated 為
        | truncated |
        | true      |
      And 回傳的 page.elements 數量為
        | count |
        | 150   |

  Rule: page.elements 的 testid 鍵永遠存在，沒有 data-testid 時為空字串
    Example: Settings 沒有 testid
      When 呼叫 start_tutorial
        | url                        | goal              |
        | http://localhost:3000      | create a project  |
      Then 回傳的 page.elements 含
        | uid  | role | name     | testid |
        | s1-7 | link | Settings |        |

  Rule: 沒有 a11y name 的互動元素仍列出且 name 為空字串
    #TODO

  Rule: 啟動或重用 Chrome 並開啟傳入的 url
    #TODO

  Rule: 注入 overlay.js
    #TODO
