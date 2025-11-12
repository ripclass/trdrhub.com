# Google Cloud Document AI Setup Guide

## Step 1: Find Your Project ID

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Look at the top bar - you'll see a project dropdown
3. Click on it - your **Project ID** is shown there (e.g., `my-project-123456`)
   - **Note**: Project ID is different from Project Name
   - It's usually lowercase with hyphens/numbers

**OR** if you don't have a project yet:
1. Click "Select a project" → "New Project"
2. Enter a project name
3. Click "Create"
4. Copy the Project ID shown

---

## Step 2: Enable Document AI API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Make sure your project is selected (top bar)
3. Go to: **APIs & Services** → **Library** (or search "API Library")
4. Search for: **"Document AI API"**
5. Click on it → Click **"Enable"**
6. Wait for it to enable (takes ~30 seconds)

---

## Step 3: Create a Document AI Processor

1. Go to [Document AI Console](https://console.cloud.google.com/ai/document-ai/processors)
2. Make sure your project is selected
3. Click **"+ Create Processor"**
4. Choose processor type:
   - **"Form Parser"** - for general documents (recommended)
   - **"OCR Processor"** - for text extraction only
   - **"Invoice Parser"** - for invoices
   - **"Document OCR"** - for general OCR
5. Fill in:
   - **Processor name**: e.g., "LC Document Processor"
   - **Region**: Choose **"us"** (or your preferred region)
6. Click **"Create"**
7. **Copy the Processor ID** - it's shown on the processor details page
   - Format: `1234567890abcdef` (long alphanumeric string)

---

## Step 4: Create Service Account & Download Credentials

### Option A: Create New Service Account (Recommended)

1. Go to [IAM & Admin](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Make sure your project is selected
3. Click **"+ Create Service Account"**
4. Fill in:
   - **Service account name**: `document-ai-service`
   - **Service account ID**: (auto-filled, keep it)
   - **Description**: "Service account for Document AI OCR"
5. Click **"Create and Continue"**
6. **Grant roles**:
   - Click **"+ Add Another Role"**
   - Search for: **"Document AI API User"**
   - Select it
   - Click **"Continue"**
7. Click **"Done"**

### Download JSON Key:

1. Click on the service account you just created
2. Go to **"Keys"** tab
3. Click **"Add Key"** → **"Create new key"**
4. Choose **"JSON"**
5. Click **"Create"**
6. **JSON file downloads automatically** - save it securely!
   - ⚠️ **Keep this file secret** - it has full access to your GCP project
   - Don't commit it to Git!

---

## Step 5: Set Environment Variables in Render

Go to your Render dashboard → Environment Variables and add:

```
GOOGLE_CLOUD_PROJECT=your-project-id-here
GOOGLE_DOCUMENTAI_PROCESSOR_ID=your-processor-id-here
GOOGLE_DOCUMENTAI_LOCATION=us
GOOGLE_APPLICATION_CREDENTIALS=/opt/render/project/src/apps/api/gcp-credentials.json
```

### For GOOGLE_APPLICATION_CREDENTIALS:

**Option 1: Upload JSON file content as environment variable** (Easier)
1. Open the downloaded JSON file
2. Copy the entire JSON content
3. In Render, create environment variable:
   - **Key**: `GOOGLE_APPLICATION_CREDENTIALS_JSON`
   - **Value**: Paste the entire JSON content
4. Then update your code to read from this env var instead

**Option 2: Store JSON file in repo** (Less secure, but simpler)
1. Save the JSON file as `apps/api/gcp-credentials.json`
2. Add to `.gitignore` to prevent committing secrets
3. Upload manually to Render file system (if supported)

**Option 3: Use Render's secret file feature** (Best practice)
- Some Render plans support secret file storage
- Check Render docs for your plan

---

## Quick Checklist

- [ ] Project ID found: `_________________`
- [ ] Document AI API enabled
- [ ] Processor created: `_________________`
- [ ] Service account created with "Document AI API User" role
- [ ] JSON key downloaded
- [ ] Environment variables set in Render

---

## Troubleshooting

### "Permission denied" errors:
- Make sure service account has "Document AI API User" role
- Check that Document AI API is enabled

### "Processor not found":
- Verify Processor ID is correct
- Check that location matches (us, eu, etc.)

### "Credentials not found":
- Verify JSON file path is correct
- Check that JSON content is valid
- Try using environment variable instead of file path

---

## Security Notes

⚠️ **IMPORTANT**:
- Never commit the JSON credentials file to Git
- Add `gcp-credentials.json` to `.gitignore`
- Rotate keys if accidentally exposed
- Use least-privilege roles (Document AI API User only)

