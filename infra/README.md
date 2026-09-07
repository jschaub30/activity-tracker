# AWS infrastructure (Terraform)

Tagged via provider `default_tags`:

- `repo` = `garmin-tracker` (override with `-var repo_name=...`)
- `created-by` = `terraform`

Resources that AWS does not allow tags on (Lambda Function URL permissions, some OAC internals) are untagged.

Lambda Function URLs need `lambda:InvokeFunction` as well as the auto-added `InvokeFunctionUrl` policy, or anonymous URL calls return 403. CloudFront maps those 403s to `index.html` (SPA fallback), which looks like the API is missing.

## First apply (chicken-and-egg image)

Lambda needs an ECR image that does not exist until you push one.

```bash
cd infra
terraform init
terraform apply -target=aws_ecr_repository.api

# from repo root
mise run deploy:image   # builds linux/arm64, pushes :bootstrap (or $GIT_SHA)

cd infra
terraform apply
```

Subsequent deploys: `mise run deploy` from the repo root (SPA sync + image + apply + CloudFront invalidation).

## Optional custom domain

Set `domain_name` and `hosted_zone_id` in `terraform.tfvars`. ACM is issued in **us-east-1**.

## Destroy

```bash
terraform destroy
```

Empty the frontend/data buckets first if destroy fails on non-empty S3.

## Local state

`*.tfstate*` is gitignored. To move state to S3 later, copy `backend.tf.example` → `backend.tf`.
