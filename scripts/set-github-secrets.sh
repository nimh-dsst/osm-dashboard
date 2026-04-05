#!/bin/bash
#
# Set GitHub secrets and variables for nimh-dsst/osm-dashboard
#
# Usage: ./scripts/set-github-secrets.sh
#
# Prerequisites:
#   - gh CLI authenticated (gh auth login)
#   - .secrets.env file configured in repo root
#
set -euo pipefail

REPO="nimh-dsst/osm-dashboard"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.secrets.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}!${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Check prerequisites
if ! command -v gh &> /dev/null; then
    log_error "gh CLI not found. Install from https://cli.github.com/"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    log_error "Not authenticated with GitHub. Run 'gh auth login' first."
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Config file not found: $ENV_FILE"
    exit 1
fi

# Source the config file
source "$ENV_FILE"

echo "Setting secrets and variables for ${REPO}..."
echo ""

# ============================================
# Set Secrets
# ============================================

echo "Setting secrets..."

# AWS
echo "$AWS_ACCOUNT_ID" | gh secret set AWS_ACCOUNT_ID --repo "$REPO"
log_success "AWS_ACCOUNT_ID"

echo "$AWS_REGION" | gh secret set AWS_REGION --repo "$REPO"
log_success "AWS_REGION"

# EC2 Hosts
echo "$SSH_PROD_HOST" | gh secret set SSH_PROD_HOST --repo "$REPO"
log_success "SSH_PROD_HOST"

echo "$SSH_STAGE_HOST" | gh secret set SSH_STAGE_HOST --repo "$REPO"
log_success "SSH_STAGE_HOST"

# SSH Keys (expand ~ to full path)
SSH_PRIVATE_KEY_FULL="${SSH_PRIVATE_KEY_PATH/#\~/$HOME}"
SSH_PUBLIC_KEY_FULL="${SSH_PUBLIC_KEY_PATH/#\~/$HOME}"

if [[ -f "$SSH_PRIVATE_KEY_FULL" ]]; then
    gh secret set SSH_PRIVATE_KEY --repo "$REPO" < "$SSH_PRIVATE_KEY_FULL"
    log_success "SSH_PRIVATE_KEY"
else
    log_error "SSH_PRIVATE_KEY - file not found: $SSH_PRIVATE_KEY_FULL"
fi

if [[ -f "$SSH_PUBLIC_KEY_FULL" ]]; then
    gh secret set SSH_PUBLIC_KEY --repo "$REPO" < "$SSH_PUBLIC_KEY_FULL"
    log_success "SSH_PUBLIC_KEY"
else
    log_error "SSH_PUBLIC_KEY - file not found: $SSH_PUBLIC_KEY_FULL"
fi

# Deployment
echo "$DEPLOYMENT_USERNAME" | gh secret set DEPLOYMENT_USERNAME --repo "$REPO"
log_success "DEPLOYMENT_USERNAME"

echo "$LETSENCRYPT_ADMIN_EMAIL" | gh secret set LETSENCRYPT_ADMIN_EMAIL --repo "$REPO"
log_success "LETSENCRYPT_ADMIN_EMAIL"

# MongoDB (optional)
if [[ -n "${MONGODB_URI:-}" ]]; then
    echo "$MONGODB_URI" | gh secret set MONGODB_URI --repo "$REPO"
    log_success "MONGODB_URI"
else
    log_warning "MONGODB_URI - skipped (not set in config)"
fi

echo ""

# ============================================
# Set Variables
# ============================================

echo "Setting variables..."

gh variable set PRODUCTION_DEPLOYMENT_URI --repo "$REPO" --body "$PRODUCTION_DEPLOYMENT_URI"
log_success "PRODUCTION_DEPLOYMENT_URI"

gh variable set STAGING_DEPLOYMENT_URI --repo "$REPO" --body "$STAGING_DEPLOYMENT_URI"
log_success "STAGING_DEPLOYMENT_URI"

echo ""

# ============================================
# Verify
# ============================================

echo "Verifying..."
echo ""
echo "Secrets:"
gh secret list --repo "$REPO"
echo ""
echo "Variables:"
gh variable list --repo "$REPO"
echo ""
log_success "Done! Secrets and variables have been set for ${REPO}"
