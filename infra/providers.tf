provider "aws" {
  region = var.region

  default_tags {
    tags = {
      repo       = var.repo_name
      created-by = "terraform"
    }
  }
}

# ACM certificates for CloudFront must live in us-east-1.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      repo       = var.repo_name
      created-by = "terraform"
    }
  }
}
