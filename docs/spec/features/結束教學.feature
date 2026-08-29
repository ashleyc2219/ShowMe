Feature: 結束教學
  作為 Qoder Agent
  我想要呼叫 end_tutorial
  以便清掉 overlay、顯示完成 banner、並釋放 session

  Rule: 成功結束後回傳 ok 為 true
    Example: 結束一場教學
      When 呼叫 end_tutorial
        | session_id |
        | s_8f2a     |
      Then 回傳的 ok 為
        | ok   |
        | true |

  Rule: session 不存在時操作失敗且錯誤為 session_not_found
    Example: 用假的場次識別結束教學
      When 呼叫 end_tutorial
        | session_id |
        | s_missing  |
      Then 操作失敗
      And 錯誤為
        | error              |
        | session_not_found  |

  Rule: 成功結束後刪除 Session
    Example: 結束後再結束
      Given session 的 session_id 為
        | session_id |
        | s_8f2a     |
      When 呼叫 end_tutorial
        | session_id |
        | s_8f2a     |
      Then 回傳的 ok 為
        | ok   |
        | true |
      When 呼叫 end_tutorial
        | session_id |
        | s_8f2a     |
      Then 操作失敗
      And 錯誤為
        | error              |
        | session_not_found  |

  Rule: session 狀態不是 READY 時操作失敗
    #TODO

  Rule: 成功結束後清掉 overlay
    #TODO

  Rule: 成功結束後顯示完成 banner，文案固定且忽略 summary
    Example: 傳入不同 summary 文案仍相同
      When 呼叫 end_tutorial
        | session_id | summary         |
        | s_8f2a     | invite a member |
      Then 完成 banner 文案為
        | text                            |
        | ✅ Done — you created a project |
