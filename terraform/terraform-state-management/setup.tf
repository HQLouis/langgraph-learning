
# setup.tf (Run this first to create the S3 bucket and DynamoDB table for Terraform state management)

resource "aws_s3_bucket" "terraform_state_bucket" {
  bucket = "thilio-terraform-state"

  tags = {
    Name = "Thilio Terraform State"
  }
}

resource "aws_dynamodb_table" "terraform_state_lock" {
  name           = "thilio-terraform-state-lock"
  hash_key       = "LockID"
  read_capacity  = 5
  write_capacity = 5

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name = "Thilio Terraform State Lock"
  }
}