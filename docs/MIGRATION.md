# Migration from `nimh-dsst/osm` to `nimh-dsst/osm-dashboard`

This document tracks the migration of the OSM dashboard from the `osm` repository to `osm-dashboard`, allowing the original `osm` URL to serve as a redirect to the new `open-science-metrics` meta repository.

## Completed Steps

### 2026-01-22: Initial Setup

- [x] Created `nimh-dsst/open-science-metrics` meta repository with landing page README
- [x] Created `nimh-dsst/osm-dashboard` repository (copy of `osm`)
- [x] Updated `pyproject.toml` GitHub URLs to point to `osm-dashboard`
- [x] Updated `web/deploy/terraform/README.md` documentation links
- [x] Updated `web/deploy/terraform/modules/iam/policies/assume-role.json.tftpl` IAM OIDC trust policy to allow `osm-dashboard`

### 2026-02-12: Secrets, IAM, and www Subdomain

- [x] Copied all repository secrets and variables from `nimh-dsst/osm` to `nimh-dsst/osm-dashboard`
- [x] Updated AWS IAM trust policy to allow `osm-dashboard`
- [x] Added CNAME DNS record for `www.opensciencemetrics.org` → `opensciencemetrics.org` (via Hover)
- [x] Updated Traefik routing rules in `web/deploy/docker-compose.yaml` to match both `opensciencemetrics.org` and `www.opensciencemetrics.org` (commit `67ad360` on `develop`)
- [x] Deployed the updated routing rules to production EC2 manually via SSH (containers recreated, TLS cert auto-provisioned)
- [x] Verified both https://opensciencemetrics.org and https://www.opensciencemetrics.org return 200

### 2026-04-04: Staging Deployment Test

- [x] Updated live AWS IAM trust policy for `github-actions-role-shared` to allow both `osm` and `osm-dashboard` (via AWS CLI; terraform template was already updated but `tofu apply` had not been run)
- [x] Added deployment info footer to Streamlit dashboard (commit `a032e51` on `develop`)
- [x] Triggered `deploy-docker.yml` manually from `develop` branch targeting staging
- [x] All workflow jobs passed: build-and-push (api+dashboard), docker-up ([run 23986105404](https://github.com/nimh-dsst/osm-dashboard/actions/runs/23986105404))
- [x] Verified https://dev.opensciencemetrics.org returns HTTP 200 (dashboard loads)
- [ ] **Known issue**: `MONGODB_URI` secret is missing from `osm-dashboard` repo — API container is unhealthy, `/api/health` falls through to dashboard. Need to set this secret before production deployment.

## Next Steps

### 1. ~~Test GitHub Actions Deployment to Staging~~ (Done)

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
