#!/bin/bash

# Get repository owner and name from GitHub environment or git remote
if [ -n "$GITHUB_REPOSITORY_OWNER" ] && [ -n "$GITHUB_REPOSITORY" ]; then
  # Running in GitHub Actions
  REPO_OWNER="$GITHUB_REPOSITORY_OWNER"
  REPO_NAME="${GITHUB_REPOSITORY#*/}"
else
  # Running locally - get from git remote
  GIT_REMOTE=$(git config --get remote.origin.url)
  if [ -n "$GIT_REMOTE" ]; then
    REPO_OWNER=$(echo "$GIT_REMOTE" | sed -n 's|.*github\.com[:/]\([^/]*\)/\([^/]*\)$|\1|p')
    REPO_NAME=$(echo "$GIT_REMOTE" | sed -n 's|.*github\.com[:/]\([^/]*\)/\([^/]*\)$|\2|p')
  else
    echo "Error: No git remote found. Please ensure you're in a git repository with a GitHub remote."
    exit 1
  fi
fi

if [ -z "$REPO_OWNER" ]; then
    echo "Error: Could not determine repository owner"
    exit 1
fi

echo "Repository Owner: $REPO_OWNER"
echo "Repository Name: $REPO_NAME"

# Create dynamic configuration files
cat > src/compose2hcl/web/config.js << EOF
// Auto-generated configuration
window.REPO_CONFIG = {
  owner: '$REPO_OWNER',
  repo: '$REPO_NAME',
  baseUrl: 'https://$REPO_OWNER.github.io/$REPO_NAME'
};
EOF

# Update package.json homepage if it exists
if [ -f "src/compose2hcl/package.json" ]; then
    # Use sed to update homepage field
    sed -i "s|\"homepage\": \".*\"|\"homepage\": \"https://$REPO_OWNER.github.io/$REPO_NAME\"|" src/compose2hcl/package.json
fi

echo "Created config.js with repository information:"
echo "  Owner: $REPO_OWNER"
echo "  Repo: $REPO_NAME"
echo "  URL: https://$REPO_OWNER.github.io/$REPO_NAME"

echo "GitHub Pages configuration updated for: https://$REPO_OWNER.github.io/$REPO_NAME"
