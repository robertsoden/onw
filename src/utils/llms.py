import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.utils.config import APISettings

load_dotenv()

# Check if Ollama is available for local development
OLLAMA_AVAILABLE = False
try:
    from langchain_ollama import ChatOllama
    OLLAMA_AVAILABLE = True
except ImportError:
    # Ollama not installed, skip
    pass

# Anthropic
SONNET = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0,
    max_tokens=64_000,  # Sonnet has a limit of max 64000 tokens
)
HAIKU = ChatAnthropic(
    model="claude-3-5-haiku-latest",
    temperature=0,
    max_tokens=8_192,  # Haiku has a limit of max 8192 tokens
)

# Google
GEMINI = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.0,
    max_tokens=None,  # max_tokens=None means no limit
    include_thoughts=False,
    max_retries=2,
    thinking_budget=512,
)
GEMINI_FLASH = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.0,
    max_tokens=None,  # max_tokens=None means no limit
    include_thoughts=False,
    max_retries=2,
    thinking_budget=0,
)

# OpenAI
GPT = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=None,  # max_tokens=None means no limit
)

# Ollama (Local Development)
# Only initialize if Ollama is available
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

if OLLAMA_AVAILABLE:
    # Llama 3.3 - 70B parameter model, excellent quality
    LLAMA_3_3_70B = ChatOllama(
        model="llama3.3:70b",
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    # Llama 3.2 - Smaller, faster variants
    LLAMA_3_2_3B = ChatOllama(
        model="llama3.2:3b",
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    # Qwen 2.5 - Strong coding model
    QWEN_2_5_32B = ChatOllama(
        model="qwen2.5:32b",
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    QWEN_2_5_14B = ChatOllama(
        model="qwen2.5:14b",
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    # Phi-4 - Microsoft's compact model
    PHI_4 = ChatOllama(
        model="phi4:14b",
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    # Mistral - Fast and capable
    MISTRAL_LARGE = ChatOllama(
        model="mistral-large",
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    # DeepSeek - Excellent for coding
    DEEPSEEK_R1_7B = ChatOllama(
        model="deepseek-r1:7b",
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

# Model Registry for dynamic selection
MODEL_REGISTRY = {
    "sonnet": SONNET,
    "haiku": HAIKU,
    "gemini": GEMINI,
    "gemini-flash": GEMINI_FLASH,
    "gpt": GPT,
}

# Add Ollama models if available
if OLLAMA_AVAILABLE:
    MODEL_REGISTRY.update({
        "llama3.3": LLAMA_3_3_70B,
        "llama3.2": LLAMA_3_2_3B,
        "qwen2.5": QWEN_2_5_32B,
        "qwen2.5-14b": QWEN_2_5_14B,
        "phi4": PHI_4,
        "mistral": MISTRAL_LARGE,
        "deepseek": DEEPSEEK_R1_7B,
    })

# Available models list for frontend
AVAILABLE_MODELS = list(MODEL_REGISTRY.keys())


def get_model():
    """Get the configured model from environment or default to sonnet."""
    model_name = APISettings.model.lower()
    if model_name not in MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model: {model_name}. Available models: {AVAILABLE_MODELS}"
        )
    return MODEL_REGISTRY[model_name]


def get_small_model():
    """Get the configured small model from environment or default to haiku."""
    model_name = APISettings.small_model.lower()
    if model_name not in MODEL_REGISTRY:
        raise ValueError(
            f"Unknown small model: {model_name}. Available models: {AVAILABLE_MODELS}"
        )
    return MODEL_REGISTRY[model_name]


# Base Model - dynamically selected from environment
MODEL = get_model()

# Small Model - dynamically selected from environment
SMALL_MODEL = get_small_model()
