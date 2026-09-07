resource "aws_sqs_queue" "sync_dlq" {
  name                      = "${var.name_prefix}-sync-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "sync" {
  name                       = "${var.name_prefix}-sync"
  visibility_timeout_seconds = 900
  receive_wait_time_seconds  = 10
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.sync_dlq.arn
    maxReceiveCount     = 3
  })
}
