aws_region  = "eu-central-1"
environment = "dev"

project_name      = "conversational-ai"
s3_prompts_bucket = "conversational-ai-prompts-bucket"

# Domain configuration
domain_name            = "lingolino.io"
api_subdomain          = "conversational-api"
web_client_subdomain   = "text-chat-client"
prompt_admin_subdomain = "prompt-admin"

# ECS Configuration
ecs_task_cpu      = "256"
ecs_task_memory   = "512"
ecs_desired_count = 1
ecs_min_capacity  = 1
ecs_max_capacity  = 3

