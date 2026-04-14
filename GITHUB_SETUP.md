# GitHub Setup Guide

## Step 1: Initialize Git Repository

```bash
cd atoma_backend
git init
```

## Step 2: Add All Files

```bash
git add .
```

## Step 3: Commit

```bash
git commit -m "Initial commit: Atoma beautician booking platform"
```

## Step 4: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `atoma-backend` (or your preferred name)
3. Make it Public or Private
4. **Don't** initialize with README (you already have one)
5. Click "Create repository"

## Step 5: Connect and Push

Replace `YOUR_USERNAME` with your GitHub username:

```bash
git remote add origin https://github.com/YOUR_USERNAME/atoma-backend.git
git branch -M main
git push -u origin main
```

## Alternative: Using GitHub CLI

If you have `gh` installed:

```bash
gh repo create atoma-backend --public --source=. --remote=origin --push
```

## Done!

Your code is now on GitHub. You can view it at:
`https://github.com/YOUR_USERNAME/atoma-backend`
