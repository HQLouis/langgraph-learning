#!/bin/bash

# Infrastructure Deployment Helper Script
# Automates common Terraform operations for Lingolino deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Change to terraform directory
cd "$(dirname "$0")/terraform"

echo -e "${BLUE}🏗️  Lingolino Infrastructure Deployment${NC}"
echo "========================================="
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo "🔍 Checking prerequisites..."

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        echo -e "${RED}❌ Terraform not found. Install with: brew install terraform${NC}"
        exit 1
    fi

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}❌ AWS CLI not found. Install with: brew install awscli${NC}"
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}❌ AWS credentials not configured. Run: aws configure${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ All prerequisites met${NC}"
    echo ""
}

# Function to initialize Terraform
init_terraform() {
    echo "🔧 Initializing Terraform..."
    terraform init
    echo -e "${GREEN}✅ Terraform initialized${NC}"
    echo ""
}

# Function to validate Terraform
validate_terraform() {
    echo "🔍 Validating Terraform configuration..."
    terraform validate
    echo -e "${GREEN}✅ Configuration is valid${NC}"
    echo ""
}

# Function to plan deployment
plan_deployment() {
    echo "📋 Planning infrastructure changes..."
    terraform plan -out=tfplan
    echo ""
    echo -e "${YELLOW}📊 Review the plan above${NC}"
    echo ""
}

# Function to apply deployment
apply_deployment() {
    echo "🚀 Deploying infrastructure..."
    terraform apply tfplan
    rm -f tfplan
    echo ""
    echo -e "${GREEN}✅ Infrastructure deployed successfully!${NC}"
    echo ""
}

# Function to show outputs
show_outputs() {
    echo "📤 Infrastructure Outputs:"
    echo "=========================="
    terraform output
    echo ""
}

# Function to create secrets
create_secrets() {
    echo ""
    echo -e "${YELLOW}📝 Next Step: Create Secrets${NC}"
    echo "=============================="
    echo ""
    echo "Run this command to create your Google API key secret:"
    echo ""
    echo -e "${BLUE}aws secretsmanager create-secret \\${NC}"
    echo -e "${BLUE}  --name lingolino/google-api-key \\${NC}"
    echo -e "${BLUE}  --secret-string \"YOUR_GOOGLE_API_KEY\" \\${NC}"
    echo -e "${BLUE}  --region eu-central-1${NC}"
    echo ""
}

# Function to show GitHub setup
show_github_setup() {
    echo -e "${YELLOW}📝 GitHub Actions Setup${NC}"
    echo "========================"
    echo ""
    echo "1. Go to GitHub → Your Repo → Settings → Secrets → Actions"
    echo "2. Add these secrets:"
    echo ""
    echo "   AWS_ACCESS_KEY_ID: <your-access-key-id>"
    echo "   AWS_SECRET_ACCESS_KEY: <your-secret-access-key>"
    echo ""
}

# Function to push initial image
show_image_push() {
    echo -e "${YELLOW}📝 Push Initial Docker Image${NC}"
    echo "============================"
    echo ""
    ECR_URL=$(terraform output -raw ecr_repository_url 2>/dev/null || echo "")

    if [ -n "$ECR_URL" ]; then
        echo "Run these commands from project root:"
        echo ""
        echo -e "${BLUE}# Login to ECR${NC}"
        echo "aws ecr get-login-password --region eu-central-1 | \\"
        echo "  docker login --username AWS --password-stdin $ECR_URL"
        echo ""
        echo -e "${BLUE}# Build image${NC}"
        echo "docker build -t lingolino-api ."
        echo ""
        echo -e "${BLUE}# Tag and push${NC}"
        echo "docker tag lingolino-api:latest $ECR_URL:latest"
        echo "docker push $ECR_URL:latest"
    else
        echo "Deploy infrastructure first to get ECR URL"
    fi
    echo ""
}

# Function to show next steps
show_next_steps() {
    echo ""
    echo -e "${GREEN}🎉 Infrastructure Deployed!${NC}"
    echo "=========================="
    echo ""
    echo "📋 Next Steps:"
    echo ""
    echo "1. ✅ Create AWS Secrets (see above)"
    echo "2. ✅ Configure GitHub Secrets (see above)"
    echo "3. ✅ Push initial Docker image (see above)"
    echo "4. ✅ Push to GitHub to trigger deployment"
    echo ""
    echo "📖 For detailed instructions, see:"
    echo "   - DEPLOYMENT.md"
    echo "   - QUICK_DEPLOY.md"
    echo ""
}

# Function to destroy infrastructure
destroy_infrastructure() {
    echo -e "${RED}⚠️  WARNING: This will destroy ALL infrastructure!${NC}"
    echo ""
    read -p "Are you sure? Type 'yes' to confirm: " confirm

    if [ "$confirm" = "yes" ]; then
        echo ""
        echo "🗑️  Destroying infrastructure..."
        terraform destroy
        echo ""
        echo -e "${GREEN}✅ Infrastructure destroyed${NC}"
    else
        echo "Cancelled."
        exit 0
    fi
}

# Main script
case "${1:-}" in
    init)
        check_prerequisites
        init_terraform
        ;;
    plan)
        check_prerequisites
        validate_terraform
        plan_deployment
        ;;
    deploy)
        check_prerequisites
        init_terraform
        validate_terraform
        plan_deployment
        echo ""
        read -p "Apply this plan? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            apply_deployment
            show_outputs
            create_secrets
            show_github_setup
            show_image_push
            show_next_steps
        else
            echo "Deployment cancelled."
            rm -f tfplan
        fi
        ;;
    apply)
        check_prerequisites
        apply_deployment
        show_outputs
        ;;
    output)
        show_outputs
        ;;
    secrets)
        create_secrets
        ;;
    github)
        show_github_setup
        ;;
    image)
        show_image_push
        ;;
    destroy)
        check_prerequisites
        destroy_infrastructure
        ;;
    validate)
        check_prerequisites
        validate_terraform
        ;;
    *)
        echo "Usage: $0 {init|plan|deploy|apply|output|secrets|github|image|destroy|validate}"
        echo ""
        echo "Commands:"
        echo "  init     - Initialize Terraform"
        echo "  plan     - Show what will be created"
        echo "  deploy   - Full deployment (init + plan + apply)"
        echo "  apply    - Apply changes"
        echo "  output   - Show infrastructure outputs"
        echo "  secrets  - Show secret creation command"
        echo "  github   - Show GitHub setup instructions"
        echo "  image    - Show Docker image push commands"
        echo "  destroy  - Destroy all infrastructure"
        echo "  validate - Validate Terraform configuration"
        echo ""
        echo "Example: ./deploy.sh deploy"
        exit 1
        ;;
esac

