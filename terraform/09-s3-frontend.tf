# ============================================================================
# S3 Buckets for Frontend Hosting
# ============================================================================

# Web Client Bucket
resource "aws_s3_bucket" "web_client" {
  bucket = "text-chat-client.lingolino.io"

  tags = {
    Name = "Lingolino Web Client"
  }
}

resource "aws_s3_bucket_website_configuration" "web_client" {
  bucket = aws_s3_bucket.web_client.id

  index_document {
    suffix = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "web_client" {
  bucket = aws_s3_bucket.web_client.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "web_client" {
  bucket = aws_s3_bucket.web_client.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "CloudFrontAccess"
        Effect    = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.web_client.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.web_client.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.web_client]
}

# ============================================================================
# Prompt Admin UI Bucket
# ============================================================================

resource "aws_s3_bucket" "prompt_admin" {
  bucket = "prompt-admin.lingolino.io"

  tags = {
    Name = "Lingolino Prompt Admin UI"
  }
}

resource "aws_s3_bucket_website_configuration" "prompt_admin" {
  bucket = aws_s3_bucket.prompt_admin.id

  index_document {
    suffix = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "prompt_admin" {
  bucket = aws_s3_bucket.prompt_admin.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "prompt_admin" {
  bucket = aws_s3_bucket.prompt_admin.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "CloudFrontAccess"
        Effect    = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.prompt_admin.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.prompt_admin.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.prompt_admin]
}

