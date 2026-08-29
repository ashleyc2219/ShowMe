Feature: 等待使用者
  作為 Qoder Agent
  我想要在 show_step 改為非阻塞時呼叫 wait_for_user
  以便輪詢直到使用者做完或逾時

  Rule: MVP 不提供 wait_for_user，顯示步驟改為畫出 overlay 後阻塞直到完成或逾時
    Example: 不呼叫 wait_for_user
      When 呼叫 start_tutorial
        | url                   | goal             |
        | http://localhost:3000 | create a project |
      Then 可呼叫的工具不含
        | tool          |
        | wait_for_user |

  Rule: 使用者尚未完成時 event 為 pending
    #TODO

  Rule: 使用者完成時回傳與 show_step 相同的 StepResult
    #TODO

  Rule: timeout_s 預設為 25
    #TODO
