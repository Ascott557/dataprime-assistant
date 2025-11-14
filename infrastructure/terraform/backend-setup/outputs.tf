output "s3_bucket_name" {
  description = "Name of the S3 bucket for Terraform state"
  value       = aws_s3_bucket.terraform_state.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.terraform_state.arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table for state locking"
  value       = aws_dynamodb_table.terraform_locks.id
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.terraform_locks.arn
}

output "backend_config" {
  description = "Backend configuration for main Terraform"
  value = <<-EOT
    Add this to your main.tf:

    terraform {
      backend "s3" {
        bucket         = "${aws_s3_bucket.terraform_state.id}"
        key            = "dataprime-demo/terraform.tfstate"
        region         = "${var.aws_region}"
        dynamodb_table = "${aws_dynamodb_table.terraform_locks.id}"
        encrypt        = true
      }
    }
  EOT
}

output "setup_complete" {
  description = "Confirmation message"
  value = <<-EOT
    ✅ Terraform backend setup complete!
    
    S3 Bucket: ${aws_s3_bucket.terraform_state.id}
    DynamoDB Table: ${aws_dynamodb_table.terraform_locks.id}
    
    Next steps:
    1. Copy the backend config above to infrastructure/terraform/main.tf
    2. Run: cd ../.. && terraform init
    3. Deploy infrastructure: terraform apply
  EOT
}





