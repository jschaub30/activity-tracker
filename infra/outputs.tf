output "cloudfront_domain" {
  value = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.main.id
}

output "app_url" {
  value = local.use_custom_domain ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "frontend_bucket" {
  value = aws_s3_bucket.frontend.bucket
}

output "data_bucket" {
  value = aws_s3_bucket.data.bucket
}

output "dynamodb_table" {
  value = aws_dynamodb_table.main.name
}

output "lambda_function_url" {
  value     = aws_lambda_function_url.api.function_url
  sensitive = true
}
