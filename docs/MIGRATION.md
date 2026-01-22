# Migration from `nimh-dsst/osm` to `nimh-dsst/osm-dashboard`

This document tracks the migration of the OSM dashboard from the `osm` repository to `osm-dashboard`, allowing the original `osm` URL to serve as a redirect to the new `open-science-metrics` meta repository.

## Completed Steps

### 2026-01-22: Initial Setup

- [x] Created `nimh-dsst/open-science-metrics` meta repository with landing page README
- [x] Created `nimh-dsst/osm-dashboard` repository (copy of `osm`)
- [x] Updated `pyproject.toml` GitHub URLs to point to `osm-dashboard`
- [x] Updated `web/deploy/terraform/README.md` documentation links
- [x] Updated `web/deploy/terraform/modules/iam/policies/assume-role.json.tftpl` IAM OIDC trust policy to allow `osm-dashboard`

## Next Steps

### 1. Copy Repository Secrets and Variables

Copy all secrets and variables from `nimh-dsst/osm` to `nimh-dsst/osm-dashboard`. See [Copying Secrets](#copying-secrets-from-osm-to-osm-dashboard) below.

### 2. Update AWS IAM Trust Policy

The IAM role in AWS currently only trusts `nimh-dsst/osm`. You need to update it to also trust `nimh-dsst/osm-dashboard`:

**Option A: Trust both repos during transition**

Temporarily modify `assume-role.json.tftpl` in the *original* `osm` repo to trust both:

```json
"token.actions.githubusercontent.com:sub": [
    "repo:nimh-dsst/osm:*",
    "repo:nimh-dsst/osm-dashboard:*"
]
```

Then redeploy shared resources from `osm`:

```bash
cd web/deploy/terraform/shared
tofu apply
```

**Option B: Direct cutover**

If you're ready to fully switch, just deploy from `osm-dashboard` after updating secrets.

### 3. Test Deployment to Staging

Manually trigger the Docker deployment workflow from `osm-dashboard`:

```bash
gh workflow run deploy-docker.yml --repo nimh-dsst/osm-dashboard -f development-environment=staging
```

Or use the GitHub Actions UI at:
https://github.com/nimh-dsst/osm-dashboard/actions/workflows/deploy-docker.yml

### 4. Verify Staging

Confirm https://dev.opensciencemetrics.org is working correctly.

### 5. Test Deployment to Production

Once staging is verified:

```bash
gh workflow run deploy-docker.yml --repo nimh-dsst/osm-dashboard -f development-environment=production
```

### 6. Verify Production

Confirm https://opensciencemetrics.org is working correctly.

### 7. Convert Original `osm` Repo to Redirect

Once `osm-dashboard` is confirmed working:

1. Archive or delete the deployment infrastructure in `osm`
2. Replace the README with a redirect notice:

```markdown
# OSM has moved

This repository has been reorganized. Please visit:

**[github.com/nimh-dsst/open-science-metrics](https://github.com/nimh-dsst/open-science-metrics)**

For the dashboard specifically, see [osm-dashboard](https://github.com/nimh-dsst/osm-dashboard).
```

### 8. Update Meta Repository

Update `nimh-dsst/open-science-metrics` README to point to the correct dashboard URL once migration is complete.

---

## Copying Secrets from `osm` to `osm-dashboard`

GitHub does not allow viewing secret values once they are set. You must either:
- Have the original values saved locally
- Retrieve them from their original sources (AWS console, SSH key files, etc.)

### List Existing Secrets and Variables

First, see what secrets and variables exist in the source repo:

```bash
# List secrets in osm
gh secret list --repo nimh-dsst/osm

# List variables in osm
gh variable list --repo nimh-dsst/osm
```

### Required Secrets

Set each secret in `osm-dashboard` using the original values:

```bash
# AWS credentials
gh secret set AWS_ACCOUNT_ID --repo nimh-dsst/osm-dashboard
gh secret set AWS_REGION --repo nimh-dsst/osm-dashboard

# Database
gh secret set MONGODB_URI --repo nimh-dsst/osm-dashboard

# SSH keys (use file input for multiline values)
gh secret set SSH_PRIVATE_KEY --repo nimh-dsst/osm-dashboard < /path/to/private/key
gh secret set SSH_PUBLIC_KEY --repo nimh-dsst/osm-dashboard < /path/to/public/key

# Host IPs
gh secret set SSH_PROD_HOST --repo nimh-dsst/osm-dashboard
gh secret set SSH_STAGE_HOST --repo nimh-dsst/osm-dashboard

# Other
gh secret set LETSENCRYPT_ADMIN_EMAIL --repo nimh-dsst/osm-dashboard
gh secret set DEPLOYMENT_USERNAME --repo nimh-dsst/osm-dashboard
```

When run without a value, `gh secret set` will prompt you to enter the value interactively (hidden input).

### Required Variables

```bash
gh variable set PRODUCTION_DEPLOYMENT_URI --repo nimh-dsst/osm-dashboard --body "'opensciencemetrics.org'"
gh variable set STAGING_DEPLOYMENT_URI --repo nimh-dsst/osm-dashboard --body "'dev.opensciencemetrics.org'"
```

### Batch Copy Script

If you have the secret values in environment variables or a secure file, you can script this:

```bash
#!/bin/bash
# copy-secrets.sh
# Run this with your secret values exported as environment variables

DEST_REPO="nimh-dsst/osm-dashboard"

echo "$AWS_ACCOUNT_ID" | gh secret set AWS_ACCOUNT_ID --repo $DEST_REPO
echo "$AWS_REGION" | gh secret set AWS_REGION --repo $DEST_REPO
echo "$MONGODB_URI" | gh secret set MONGODB_URI --repo $DEST_REPO
cat "$SSH_PRIVATE_KEY_PATH" | gh secret set SSH_PRIVATE_KEY --repo $DEST_REPO
cat "$SSH_PUBLIC_KEY_PATH" | gh secret set SSH_PUBLIC_KEY --repo $DEST_REPO
echo "$SSH_PROD_HOST" | gh secret set SSH_PROD_HOST --repo $DEST_REPO
echo "$SSH_STAGE_HOST" | gh secret set SSH_STAGE_HOST --repo $DEST_REPO
echo "$LETSENCRYPT_ADMIN_EMAIL" | gh secret set LETSENCRYPT_ADMIN_EMAIL --repo $DEST_REPO
echo "$DEPLOYMENT_USERNAME" | gh secret set DEPLOYMENT_USERNAME --repo $DEST_REPO

gh variable set PRODUCTION_DEPLOYMENT_URI --repo $DEST_REPO --body "'opensciencemetrics.org'"
gh variable set STAGING_DEPLOYMENT_URI --repo $DEST_REPO --body "'dev.opensciencemetrics.org'"
```

### Verify Secrets Were Set

```bash
gh secret list --repo nimh-dsst/osm-dashboard
gh variable list --repo nimh-dsst/osm-dashboard
```

This will show the secret names (not values) and confirm they exist.
