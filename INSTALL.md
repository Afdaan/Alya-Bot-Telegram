# Panduan Instalasi Model GGUF untuk Alya-Bot

## 1. Setup Folder Structure

Pertama, buat folder untuk model:

```bash
mkdir -p data/models
```

## 2. Download Model GGUF

Ada dua cara untuk download model GGUF:

### Cara Manual (Recommended):

1. Kunjungi [TheBloke/openchat-3.5-0106-GGUF](https://huggingface.co/TheBloke/openchat-3.5-0106-GGUF/tree/main)
2. Download model Q5_K variant (sekitar 4.5GB):
   ```
   wget https://huggingface.co/TheBloke/openchat-3.5-0106-GGUF/resolve/main/openchat-3.5-0106.Q5_K.gguf -O data/models/openchat-3.5-0106-Q5_K.gguf
   ```

### Cara dengan Script Python:

Buat file script berikut:

```python
# model_downloader.py
import os
import requests
import sys
from tqdm import tqdm
import argparse

def download_file(url, destination):
    """Download file with progress bar."""
    if os.path.exists(destination):
        print(f"File already exists at {destination}")
        return
        
    # Make sure parent directory exists
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    
    print(f"Downloading {url} to {destination}")
    response = requests.get(url, stream=True)
    
    # Get file size if available
    total_size_in_bytes = int(response.headers.get('content-length', 0))
    block_size = 1024 # 1 Kibibyte
    
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download GGUF models")
    parser.add_argument("-m", "--model", choices=["openchat", "mistral", "llama3"], 
                       default="openchat", help="Model to download")
    parser.add_argument("-q", "--quantization", choices=["Q4_0", "Q4_K", "Q5_K", "Q6_K", "Q8_0"], 
                       default="Q5_K", help="Quantization level")
    args = parser.parse_args()
    
    # Model URLs
    model_urls = {
        "openchat": {
            "Q5_K": "https://huggingface.co/TheBloke/openchat-3.5-0106-GGUF/resolve/main/openchat-3.5-0106.Q5_K.gguf",
            "Q4_K": "https://huggingface.co/TheBloke/openchat-3.5-0106-GGUF/resolve/main/openchat-3.5-0106.Q4_K.gguf"
        },
        "mistral": {
            "Q5_K": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q5_K.gguf",
            "Q4_K": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K.gguf"
        }
    }
    
    # Get URL
    try:
        url = model_urls[args.model][args.quantization]
    except KeyError:
        print(f"Model {args.model} with {args.quantization} quantization not available")
        sys.exit(1)
    
    # Download
    destination = f"data/models/{args.model}-{args.quantization}.gguf"
    download_file(url, destination)
    
    # Update .env
    print("\nTo use this model, update your .env with:")
    print(f"LLM_MODEL_PATH=data/models/{args.model}-{args.quantization}.gguf")
    print("LLM_PROVIDER=self")
```

Jalankan dengan:

