"""
Model downloader utility for Alya Bot.
Downloads and sets up GGUF models for self-hosted LLM.
"""
import os
import requests
import sys
from tqdm import tqdm
import argparse

def download_file(url: str, destination: str) -> None:
    """Download file with progress bar.
    
    Args:
        url: URL to download from
        destination: Path to save file
    """
    if os.path.exists(destination):
        print(f"File already exists at {destination}")
        return
        
    # Make sure parent directory exists
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    
    print(f"Downloading {url} to {destination}")
    response = requests.get(url, stream=True)
    
    # Check if download was successful
    if response.status_code != 200:
        print(f"ERROR: Failed to download file, status code: {response.status_code}")
        sys.exit(1)
    
    # Get file size if available
    total_size_in_bytes = int(response.headers.get('content-length', 0))
    block_size = 1024  # 1 Kibibyte
    
    # Create progress bar
    progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
    
    with open(destination, 'wb') as file:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)
    
    progress_bar.close()
    
    if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
        print("ERROR: File download incomplete")
        sys.exit(1)
        
    print(f"Download complete: {destination}")

def main() -> None:
    """Main download script function."""
    parser = argparse.ArgumentParser(description="Download GGUF models for Alya Bot")
    parser.add_argument("-m", "--model", choices=["openchat", "mistral", "llama3"], 
                       default="openchat", help="Model to download")
    parser.add_argument("-q", "--quantization", choices=["Q4_0", "Q4_K", "Q5_K", "Q5_K_M", "Q6_K", "Q8_0"], 
                       default="Q5_K_M", help="Quantization level (Q5_K_M recommended)")
    parser.add_argument("-d", "--destination", default="data/models", 
                       help="Destination directory")
    args = parser.parse_args()
    
    # Fixed URL for OpenChat Q5_K_M (confirmed working)
    openchat_url = "https://huggingface.co/TheBloke/openchat-3.5-0106-GGUF/resolve/main/openchat-3.5-0106.Q5_K_M.gguf?download=true"
    
    # Simplified model downloads - starting with the one confirmed working URL
    if args.model == "openchat" and args.quantization == "Q5_K_M":
        url = openchat_url
        filename = "openchat-3.5-0106.Q5_K_M.gguf"
    else:
        # Let user know we're defaulting to the working model
        print(f"WARNING: Specified model ({args.model}/{args.quantization}) might not be available.")
        print(f"Defaulting to openchat Q5_K_M which we know works.")
        url = openchat_url
        filename = "openchat-3.5-0106.Q5_K_M.gguf"
    
    # Download
    destination = os.path.join(args.destination, filename)
    download_file(url, destination)
    
    # Update .env suggestion
    print("\n==== MODEL INSTALLATION COMPLETED ====")
    print("\nTo use this model, update your .env with:")
    print(f"LLM_PROVIDER=self")
    print(f"LLM_MODEL_PATH={destination}")
    print("")
    print("Install requirements with:")
    print("pip install llama-cpp-python")
    print("")
    print("For GPU acceleration:")
    print('CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall')

if __name__ == "__main__":
    main()
