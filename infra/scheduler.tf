resource "aws_scheduler_schedule" "daily_sync" {
  count = var.enable_scheduled_sync ? 1 : 0
  name  = "${var.name_prefix}-daily-sync"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "cron(0 13 * * ? *)" # 13:00 UTC ~ 6am Denver (MST) / 7am MDT-ish

  target {
    arn      = aws_sqs_queue.sync.arn
    role_arn = aws_iam_role.scheduler[0].arn
    input    = jsonencode({ action = "sync_all" })
  }
}
