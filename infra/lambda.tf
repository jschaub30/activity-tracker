resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.name_prefix}-api"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${var.name_prefix}-worker"
  retention_in_days = 14
}

locals {
  lambda_env = {
    DYNAMODB_TABLE       = aws_dynamodb_table.main.name
    DATA_BUCKET          = aws_s3_bucket.data.bucket
    SYNC_BACKEND         = "sqs"
    SYNC_QUEUE_URL       = aws_sqs_queue.sync.url
    ORIGIN_SECRET        = aws_ssm_parameter.origin_secret.value
    SECRET_KEY           = aws_ssm_parameter.secret_key.value
    TOKEN_ENCRYPTION_KEY = aws_ssm_parameter.token_encryption_key.value
    CORS_ORIGINS         = "http://localhost:5180,http://127.0.0.1:5180"
  }
  image_uri = "${aws_ecr_repository.api.repository_url}:${var.lambda_image_tag}"
}

resource "aws_lambda_function" "api" {
  function_name = "${var.name_prefix}-api"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = local.image_uri
  architectures = ["arm64"]
  timeout       = 30
  memory_size   = 512

  image_config {
    command = ["garmin_tracker.lambda_handler.handler"]
  }

  environment {
    variables = local.lambda_env
  }

  depends_on = [aws_cloudwatch_log_group.api, aws_iam_role_policy.lambda]
}

resource "aws_lambda_function" "worker" {
  function_name                  = "${var.name_prefix}-worker"
  role                           = aws_iam_role.lambda.arn
  package_type                   = "Image"
  image_uri                      = local.image_uri
  architectures                  = ["arm64"]
  timeout                        = 900
  memory_size                    = 1024
  reserved_concurrent_executions = 2

  image_config {
    command = ["garmin_tracker.jobs.sync_worker.handler"]
  }

  environment {
    variables = local.lambda_env
  }

  depends_on = [aws_cloudwatch_log_group.worker, aws_iam_role_policy.lambda]
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"
}

# Function URL auto-adds InvokeFunctionUrl. Anonymous URL calls also need InvokeFunction.
resource "aws_lambda_permission" "function_invoke" {
  statement_id  = "AllowPublicInvokeFunction"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "*"
}

resource "aws_lambda_event_source_mapping" "sync" {
  event_source_arn = aws_sqs_queue.sync.arn
  function_name    = aws_lambda_function.worker.arn
  batch_size       = 1
}
