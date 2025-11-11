# DeepSeek OCR Setup Guide

**Date:** 2025-01-27  
**Purpose:** Complete setup guide for DeepSeek OCR integration

## Overview

DeepSeek OCR is an open-source OCR solution that runs locally using Hugging Face transformers. It's a cost-effective alternative to Google Cloud Document AI, especially for high-volume processing.

## Prerequisites

1. **Python 3.8+** (required for transformers library)
2. **CUDA-capable GPU** (optional but recommended for faster processing)
3. **System Dependencies** (for PDF processing):
   - **Windows**: Install Poppler from https://github.com/oschwartz10612/poppler-windows/releases
   - **Linux**: `sudo apt-get install poppler-utils` (Ubuntu/Debian) or `sudo yum install poppler-utils` (RHEL/CentOS)
   - **macOS**: `brew install poppler`

## Installation Steps

### Step 1: Install Python Dependencies

```bash
cd apps/api
pip install torch transformers pillow pdf2image
```

**Note:** If you have a CUDA-capable GPU, install PyTorch with CUDA support:

```bash
# For CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Then install other dependencies
pip install transformers pillow pdf2image
```

### Step 2: Configure Environment Variables

Add these to your `apps/api/.env` file:

```bash
# Enable DeepSeek OCR
USE_DEEPSEEK_OCR=true

# Optional: Customize model (default: deepseek-ai/deepseek-ocr)
DEEPSEEK_OCR_MODEL_NAME=deepseek-ai/deepseek-ocr

# Optional: Force device (auto-detect if not set)
# Options: 'cuda' (GPU), 'cpu' (CPU), or leave empty for auto-detect
DEEPSEEK_OCR_DEVICE=

# Disable stub mode (required for production)
USE_STUBS=false
```

### Step 3: Verify Installation

Test the setup:

```bash
cd apps/api
python -c "from app.ocr.deepseek_ocr import DeepSeekOCRAdapter; print('DeepSeek OCR import successful')"
```

### Step 4: Test OCR Processing

Create a simple test script (`test_deepseek_ocr.py`):

```python
import asyncio
from uuid import uuid4
from app.ocr.deepseek_ocr import DeepSeekOCRAdapter

async def test_ocr():
    adapter = DeepSeekOCRAdapter()
    
    # Test health check
    is_healthy = await adapter.health_check()
    print(f"DeepSeek OCR healthy: {is_healthy}")
    
    # Note: Full test requires S3 bucket and document
    # This will be tested during actual document processing

if __name__ == "__main__":
    asyncio.run(test_ocr())
```

Run the test:

```bash
python test_deepseek_ocr.py
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_DEEPSEEK_OCR` | `false` | Enable DeepSeek OCR as primary provider |
| `DEEPSEEK_OCR_MODEL_NAME` | `deepseek-ai/deepseek-ocr` | Hugging Face model identifier |
| `DEEPSEEK_OCR_DEVICE` | `None` (auto) | Device to use: `cuda`, `cpu`, or leave empty for auto-detect |

### Model Selection

DeepSeek OCR models are available on Hugging Face. You can use different models:

- `deepseek-ai/deepseek-ocr` (default) - General purpose OCR
- Other DeepSeek OCR variants as they become available

To use a different model:

```bash
DEEPSEEK_OCR_MODEL_NAME=your-model-name/your-model-id
```

## How It Works

1. **Model Loading**: The model is loaded lazily on first use (not at startup)
2. **PDF Processing**: PDFs are converted to images using `pdf2image`
3. **Image Processing**: Each page/image is processed through the DeepSeek OCR model
4. **Text Extraction**: Extracted text is combined and returned as `OCRResult`

## Performance Considerations

### GPU vs CPU

- **GPU (CUDA)**: Significantly faster (10-50x), recommended for production
- **CPU**: Slower but works on any machine, suitable for development/low volume

### Memory Requirements

- **Model Size**: ~2-4 GB RAM for the model
- **Processing**: Additional 1-2 GB per concurrent document
- **Recommendation**: Minimum 8 GB RAM, 16 GB+ recommended

### Processing Speed

- **GPU**: ~1-5 seconds per page
- **CPU**: ~10-60 seconds per page (depends on CPU)

## Troubleshooting

### Import Errors

**Error:** `ImportError: DeepSeek OCR dependencies not installed`

**Solution:**
```bash
pip install torch transformers pillow pdf2image
```

### PDF Conversion Errors

**Error:** `pdf2image.exceptions.PDFInfoNotInstalledError`

**Solution:** Install Poppler (see Prerequisites section)

**Windows:**
1. Download Poppler from https://github.com/oschwartz10612/poppler-windows/releases
2. Extract to a folder (e.g., `C:\poppler`)
3. Add `C:\poppler\Library\bin` to your PATH environment variable

**Linux:**
```bash
sudo apt-get install poppler-utils  # Ubuntu/Debian
sudo yum install poppler-utils      # RHEL/CentOS
```

**macOS:**
```bash
brew install poppler
```

### CUDA/GPU Issues

**Error:** `CUDA out of memory`

**Solution:**
- Reduce batch size (if processing multiple documents)
- Use CPU instead: `DEEPSEEK_OCR_DEVICE=cpu`
- Process documents sequentially instead of in parallel

**Error:** `CUDA not available`

**Solution:**
- Verify CUDA installation: `python -c "import torch; print(torch.cuda.is_available())"`
- Install CUDA-enabled PyTorch (see Step 1)
- Fall back to CPU: `DEEPSEEK_OCR_DEVICE=cpu`

### Model Download Issues

**Error:** `Failed to load DeepSeek OCR model`

**Solution:**
- Check internet connection (first download requires Hugging Face access)
- Verify model name is correct
- Check Hugging Face token if using private models:
  ```bash
  export HF_TOKEN=your-huggingface-token
  ```

## Comparison: DeepSeek OCR vs Google Cloud Document AI

| Feature | DeepSeek OCR | Google Cloud Document AI |
|---------|--------------|--------------------------|
| **Cost** | Free (self-hosted) | Pay-per-use |
| **Setup** | Requires model download | Requires GCP account |
| **Speed** | Fast (with GPU) | Very fast |
| **Accuracy** | High | Very high |
| **Privacy** | Fully local | Cloud-based |
| **Scalability** | Limited by hardware | Unlimited |
| **Maintenance** | Model updates needed | Managed service |

## Production Recommendations

1. **Use GPU**: Significantly improves processing speed
2. **Monitor Memory**: Watch for memory leaks during high-volume processing
3. **Fallback Strategy**: Keep Google Cloud Document AI as fallback:
   ```bash
   USE_DEEPSEEK_OCR=true
   GOOGLE_CLOUD_PROJECT=your-project-id  # Keep configured as fallback
   GOOGLE_DOCUMENTAI_PROCESSOR_ID=your-processor-id
   ```
4. **Caching**: Consider caching OCR results to avoid reprocessing
5. **Error Handling**: Implement retry logic for transient failures

## Next Steps

After setup:

1. **Test with Real Documents**: Upload a test document through your application
2. **Monitor Performance**: Check processing times and accuracy
3. **Tune Configuration**: Adjust device settings based on your hardware
4. **Set Up Fallback**: Configure Google Cloud Document AI as backup

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review application logs: `apps/api/logs/`
3. Test model loading: `python -c "from transformers import AutoModelForVision2Seq; print('OK')"`
4. Verify dependencies: `pip list | grep -E "torch|transformers|pillow|pdf2image"`

