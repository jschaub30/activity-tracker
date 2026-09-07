terraform {
  backend "s3" {
    bucket  = "schaubj-terraform"
    key     = "activity-tracker/terraform.tfstate"
    region  = "us-west-2"
    encrypt = true
  }
}
