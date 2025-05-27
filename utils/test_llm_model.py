"""
Test utility for self-hosted LLM models.
"""
import os
import time
import argparse
import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    print("ERROR: llama-cpp-python not installed.")
    print("Install it with: pip install llama-cpp-python")
    sys.exit(1)

from dotenv import load_dotenv

def test_model(model_path: str, gpu_layers: int, threads: int) -> None:
    """Test GGUF model loading and inference.
    
    Args:
        model_path: Path to GGUF model file
        gpu_layers: Number of GPU layers to offload
        threads: Number of CPU threads to use
    """
    if not os.path.exists(model_path):
        print(f"ERROR: Model not found at {model_path}")
        sys.exit(1)

    # Load model
    start = time.time()
    print(f"Loading model: {model_path}")
    print(f"GPU Layers: {gpu_layers}, Threads: {threads}")
    
    try:
        model = Llama(
            model_path=model_path,
            n_gpu_layers=gpu_layers,
            n_threads=threads,
            n_ctx=2048,
            verbose=False
        )
    except Exception as e:
        print(f"ERROR loading model: {e}")
        sys.exit(1)
        
    end = time.time()
    print(f"Model loaded in {end-start:.2f} seconds")

    # Test inference
    prompt = """<|system|>
You are Alya, a friendly assistant with tsundere personality.
</s>
Human: Hello, who are you?
Assistant:"""

    print("\nRunning inference test...")
    start = time.time()
    try:
        output = model.create_completion(
            prompt=prompt,
            max_tokens=256,
            temperature=0.7,
            top_p=0.95,
            stop=["Human:", "</s>", "\n\n"]
        )
    except Exception as e:
        print(f"ERROR during inference: {e}")
        sys.exit(1)
        
    end = time.time()
    
    print(f"Generated response in {end-start:.2f} seconds:")
    print("-" * 50)
    print(output['choices'][0]['text'])
    print("-" * 50)

    print("\n✅ Test completed successfully!")
    print(f"Model is working properly and ready to use with Alya Bot.")

def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Test GGUF model for Alya Bot")
    parser.add_argument("-m", "--model", help="Model path (default: from .env)")
    parser.add_argument("-g", "--gpu", type=int, default=0, 
                       help="Number of GPU layers to offload")
    parser.add_argument("-t", "--threads", type=int, default=4,
                       help="Number of CPU threads to use")
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    
    # Get model path
    model_path = args.model or os.getenv("LLM_MODEL_PATH")
    if not model_path:
        print("ERROR: Model path not specified. Please provide via argument or .env file.")
        sys.exit(1)
    
    # Get GPU layers and threads
    gpu_layers = args.gpu if args.gpu is not None else int(os.getenv("LLM_N_GPU_LAYERS", "0"))
    threads = args.threads if args.threads is not None else int(os.getenv("LLM_N_THREADS", "4"))
    
    # Run test
    test_model(model_path, gpu_layers, threads)

if __name__ == "__main__":
    main()
