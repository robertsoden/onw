# Ollama Quick Start - 5 Minutes to Local LLM

Run Ontario Nature Watch with **local LLMs** - no API keys needed!

---

## Install & Run (5 minutes)

### Step 1: Install Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download from https://ollama.com/download/windows
```

### Step 2: Download a Model

```bash
# Fast model (2GB, good for testing)
ollama pull llama3.2:3b

# Better quality (8GB, recommended)
ollama pull qwen2.5:14b
```

### Step 3: Install Python Package

```bash
# If using uv (recommended)
uv sync --group dev

# Or with pip
pip install langchain-ollama
```

### Step 4: Configure

```bash
# In .env file
MODEL=llama3.2
SMALL_MODEL=llama3.2
```

### Step 5: Run

```bash
python -m src.main
```

**Done!** 🎉 Your app now runs with local LLMs.

---

## Quick Test

```bash
# Test Ontario statistics
curl -X POST http://localhost:8000/api/ontario/statistics \
  -H "Content-Type: application/json" \
  -d '{
    "area_name": "Algonquin Park",
    "metric": "biodiversity"
  }'
```

---

## Model Recommendations

| Your Hardware | Model | Download Size | Quality |
|---------------|-------|---------------|---------|
| 8GB RAM | llama3.2:3b | 2GB | ⭐⭐⭐ Good |
| 16GB RAM | qwen2.5:14b | 8GB | ⭐⭐⭐⭐ Excellent |
| 64GB RAM | llama3.3:70b | 40GB | ⭐⭐⭐⭐⭐ Best |

---

## Why Use Ollama?

✅ **Free** - No API costs
✅ **Private** - Data stays local
✅ **Fast** - No network latency
✅ **Unlimited** - No rate limits

---

## Troubleshooting

**Model not found?**
```bash
ollama pull llama3.2:3b
```

**Connection refused?**
```bash
ollama serve
```

**Slow performance?**
```bash
# Use smaller model
MODEL=llama3.2 python -m src.main
```

---

## Full Documentation

See `docs/OLLAMA_LOCAL_DEVELOPMENT.md` for:
- Detailed setup guide
- All available models
- Hardware requirements
- Performance tips
- Advanced configuration

---

**Ready to develop!** 🚀
