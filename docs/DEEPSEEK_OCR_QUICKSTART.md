# DeepSeek OCR Quick Start

## Quick Setup (3 Steps)

### 1. Install Dependencies

```bash
cd apps/api
pip install torch transformers pillow pdf2image
```

**For GPU support (recommended):**
```bash
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers pillow pdf2image

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers pillow pdf2image
```

**For PDF support, install Poppler:**
- **Windows**: Download from https://github.com/oschwartz10612/poppler-windows/releases
- **Linux**: `sudo apt-get install poppler-utils`
- **macOS**: `brew install poppler`

### 2. Configure Environment

Add to `apps/api/.env`:

```bash
USE_DEEPSEEK_OCR=true
USE_STUBS=false
DEEPSEEK_OCR_MODEL_NAME=deepseek-ai/deepseek-ocr
# DEEPSEEK_OCR_DEVICE=  # Leave empty for auto-detect
```

### 3. Test

```bash
python -c "from app.ocr.deepseek_ocr import DeepSeekOCRAdapter; print('✓ DeepSeek OCR ready')"
```

## What Was Added

✅ **DeepSeek OCR Adapter** (`apps/api/app/ocr/deepseek_ocr.py`)
- Uses Hugging Face transformers pipeline
- Supports GPU and CPU
- Handles PDFs and images
- Lazy model loading (loads on first use)

✅ **Factory Integration** (`apps/api/app/ocr/factory.py`)
- DeepSeek OCR as primary provider (when enabled)
- Google Cloud Document AI as fallback
- AWS Textract as secondary fallback

✅ **Configuration** (`apps/api/app/config.py`)
- `USE_DEEPSEEK_OCR` - Enable/disable
- `DEEPSEEK_OCR_MODEL_NAME` - Model selection
- `DEEPSEEK_OCR_DEVICE` - GPU/CPU control

✅ **Dependencies** (`apps/api/requirements.txt`)
- torch, transformers, pillow, pdf2image

## Usage

Once configured, DeepSeek OCR will automatically be used when:
- `USE_DEEPSEEK_OCR=true`
- `USE_STUBS=false`

The system will fall back to Google Cloud Document AI or AWS Textract if DeepSeek OCR fails.

## Full Documentation

See `docs/DEEPSEEK_OCR_SETUP.md` for complete setup guide, troubleshooting, and production recommendations.

