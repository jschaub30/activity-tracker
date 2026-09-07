resource "random_password" "secret_key" {
  length  = 48
  special = false
}

resource "random_password" "origin_secret" {
  length  = 32
  special = false
}

resource "random_id" "fernet_seed" {
  byte_length = 32
}

resource "aws_ssm_parameter" "secret_key" {
  name  = "/${var.name_prefix}/secret-key"
  type  = "SecureString"
  value = random_password.secret_key.result
}

resource "aws_ssm_parameter" "token_encryption_key" {
  name = "/${var.name_prefix}/token-encryption-key"
  type = "SecureString"
  # url-safe base64 32 bytes — valid Fernet key
  value = replace(replace(random_id.fernet_seed.b64_std, "+", "-"), "/", "_")
}

resource "aws_ssm_parameter" "origin_secret" {
  name  = "/${var.name_prefix}/origin-secret"
  type  = "SecureString"
  value = random_password.origin_secret.result
}
