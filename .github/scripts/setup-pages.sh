#!/bin/bash

# Setup script for GitHub Pages deployment
# Creates the pages directory structure for the KOTORScript Session Manager

if [ -n "$GITHUB_REPOSITORY_OWNER" ] && [ -n "$GITHUB_REPOSITORY" ]; then
  REPO_OWNER="$GITHUB_REPOSITORY_OWNER"
  REPO_NAME="${GITHUB_REPOSITORY#*/}"
else
  GIT_REMOTE=$(git config --get remote.origin.url)
  if [ -n "$GIT_REMOTE" ]; then
    REPO_OWNER=$(echo "$GIT_REMOTE" | sed -n 's|.*github\.com[:/]\([^/]*\)/\([^/]*\)$|\1|p')
    REPO_NAME=$(echo "$GIT_REMOTE" | sed -n 's|.*github\.com[:/]\([^/]*\)/\([^/]*\)$|\2|p')
  else
    echo "Error: No git remote found."
    exit 1
  fi
fi

echo "Repository: $REPO_OWNER/$REPO_NAME"
echo "Pages URL: https://$REPO_OWNER.github.io/$REPO_NAME"
