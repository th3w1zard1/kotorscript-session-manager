#!/bin/bash

# Create proper GitHub Pages structure
echo "Creating GitHub Pages structure..."

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

echo "Repository Owner: $REPO_OWNER"
echo "Repository Name: $REPO_NAME"

# Create GitHub Pages directory
mkdir -p gh-pages

# Copy web interface files (we're already in src/compose2hcl)
cp -r web/* gh-pages/

# Copy built TypeScript files (we're already in src/compose2hcl)
cp -r dist/* gh-pages/

# Create dynamic config.js
cat > gh-pages/config.js << EOF
// Auto-generated configuration
window.REPO_CONFIG = {
  owner: '$REPO_OWNER',
  repo: '$REPO_NAME',
  baseUrl: 'https://$REPO_OWNER.github.io/$REPO_NAME'
};
EOF

# Create .nojekyll file to ensure GitHub Pages works properly
touch gh-pages/.nojekyll

# Create a proper index.html if it doesn't exist
if [ ! -f "gh-pages/index.html" ]; then
  cat > gh-pages/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compose2HCL - Docker Compose to Nomad HCL Converter</title>
    <script src="config.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="header-content">
                <div class="logo">
                    <span class="logo-icon">🐳</span>
                    <h1>Compose2HCL</h1>
                </div>
                <p class="subtitle">Convert Docker Compose files to Nomad HCL with complete feature support</p>
                <div class="repo-info" id="repo-info">
                    <a href="#" id="repo-link" target="_blank" rel="noopener noreferrer">
                        <span id="repo-name">Repository</span>
                    </a>
                </div>
            </div>
            <div class="header-actions">
                <button class="btn btn-secondary" onclick="showExamples()">
                    <span>📚</span> Examples
                </button>
                <button class="btn btn-secondary" onclick="showSettings()">
                    <span>⚙️</span> Settings
                </button>
                <button class="btn btn-secondary" onclick="showInfo()">
                    <span>ℹ️</span> Info
                </button>
            </div>
        </header>

        <!-- Main Content -->
        <main class="main">
            <!-- Input Section -->
            <section class="input-section">
                <div class="section-header">
                    <h2>Docker Compose Input</h2>
                    <div class="section-actions">
                        <button class="btn btn-small" onclick="clearInput()">Clear</button>
                        <button class="btn btn-small" onclick="loadExample()">Load Example</button>
                        <input type="file" id="file-input" accept=".yml,.yaml" style="display: none;" onchange="loadFile(event)">
                        <button class="btn btn-small" onclick="document.getElementById('file-input').click()">Upload File</button>
                    </div>
                </div>
                <div class="editor-container">
                    <textarea id="compose-input" class="editor" placeholder="Paste your docker-compose.yml content here or upload a file..."></textarea>
                    <div class="editor-info">
                        <span id="input-stats">0 lines, 0 characters</span>
                        <span class="editor-format">YAML</span>
                    </div>
                </div>
            </section>

            <!-- Controls -->
            <section class="controls">
                <button class="btn btn-primary btn-large" onclick="convert()" id="convert-btn">
                    <span class="btn-icon">🔄</span>
                    Convert to Nomad HCL
                </button>
                <button class="btn btn-secondary" onclick="validateOnly()">
                    <span>✅</span> Validate Only
                </button>
            </section>

            <!-- Status -->
            <section class="status" id="status-section" style="display: none;">
                <div id="status-content"></div>
            </section>

            <!-- Output Section -->
            <section class="output-section">
                <div class="section-header">
                    <h2>Nomad HCL Output</h2>
                    <div class="section-actions">
                        <button class="btn btn-small" onclick="copyOutput()">Copy</button>
                        <button class="btn btn-small" onclick="downloadOutput()">Download</button>
                        <select id="output-format" class="format-select" onchange="changeOutputFormat()">
                            <option value="hcl">HCL</option>
                            <option value="json">JSON</option>
                        </select>
                    </div>
                </div>
                <div class="editor-container">
                    <textarea id="hcl-output" class="editor" readonly placeholder="Converted Nomad HCL will appear here..."></textarea>
                    <div class="editor-info">
                        <span id="output-stats">0 lines, 0 characters</span>
                        <span class="editor-format">HCL</span>
                    </div>
                </div>
            </section>
        </main>

        <!-- Footer -->
        <footer class="footer">
            <div class="footer-content">
                <p>&copy; 2024 Compose2HCL. Convert Docker Compose to Nomad HCL with ease.</p>
            </div>
        </footer>
    </div>

    <!-- Scripts -->
    <script src="app.js"></script>
</body>
</html>
EOF
fi

echo "GitHub Pages structure created successfully!"
echo "Files in gh-pages/:"
ls -la gh-pages/
