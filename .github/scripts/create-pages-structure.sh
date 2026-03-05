#!/bin/bash

# Create GitHub Pages structure for the KOTORScript Session Manager
echo "Creating GitHub Pages structure..."

# Create GitHub Pages directory
mkdir -p gh-pages

# Copy static HTML files
cp index.html gh-pages/
cp waiting.html gh-pages/
cp README.md gh-pages/

# Create .nojekyll file to ensure GitHub Pages works properly
touch gh-pages/.nojekyll

echo "GitHub Pages structure created successfully!"
echo "Files in gh-pages/:"
ls -la gh-pages/
