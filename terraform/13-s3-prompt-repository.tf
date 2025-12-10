# ============================================================================
# S3 Bucket for Prompt Repository
# ============================================================================
# This bucket stores all worker prompts for the Lingolino AI system.
# The prompt admin UI uploads prompts directly to this bucket.

resource "aws_s3_bucket" "prompt_repository" {
  bucket = var.s3_prompts_bucket

  tags = {
    Name        = "Lingolino Prompt Repository"
    Description = "Storage for AI worker prompts"
  }
}

# ============================================================================
# CORS Configuration for Direct Browser Uploads
# ============================================================================

resource "aws_s3_bucket_cors_configuration" "prompt_repository" {
  bucket = aws_s3_bucket.prompt_repository.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = [
      "https://prompt-admin.lingolino.io",
      "http://localhost:8000",
      "http://localhost:3000",
      "http://localhost:63342"
    ]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# ============================================================================
# Public Access Configuration
# ============================================================================
# Note: This bucket allows public read AND write access to enable
# the prompt admin UI to upload files directly from the browser.
# Consider using signed URLs or API Gateway for production.

resource "aws_s3_bucket_public_access_block" "prompt_repository" {
  bucket = aws_s3_bucket.prompt_repository.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# ============================================================================
# Bucket Policy - Public Read and Write
# ============================================================================

resource "aws_s3_bucket_policy" "prompt_repository" {
  bucket = aws_s3_bucket.prompt_repository.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.prompt_repository.arn}/*"
      },
      {
        Sid       = "PublicWritePutObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.prompt_repository.arn}/prompts/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.prompt_repository]
}

# ============================================================================
# Versioning for Prompt History
# ============================================================================

resource "aws_s3_bucket_versioning" "prompt_repository" {
  bucket = aws_s3_bucket.prompt_repository.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ============================================================================
# Lifecycle Policy to Manage Old Versions
# ============================================================================

resource "aws_s3_bucket_lifecycle_configuration" "prompt_repository" {
  bucket = aws_s3_bucket.prompt_repository.id

  depends_on = [aws_s3_bucket.prompt_repository]

  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  rule {
    id     = "delete-incomplete-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ============================================================================
# Defining files for the workers' prompts
# ============================================================================

resource "aws_s3_object" "prompt_files" {
  for_each = toset([
    "speech_vocabulary_worker",
    "speech_grammar_worker",
    "speech_interaction_worker",
    "speech_comprehension_worker",
    "boredom_worker",
    "master"
  ])

  bucket       = aws_s3_bucket.prompt_repository.id
  key          = "prompts/${each.value}.txt"
  content      = "" # Empty file
  content_type = "text/plain"

  lifecycle {
    ignore_changes = [
      content,
      etag,
      metadata
    ]
  }
}
