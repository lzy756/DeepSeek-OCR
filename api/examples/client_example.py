"""Example Python Client for DeepSeek-OCR API"""
import requests
import base64
import json
import time
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = "YOUR_API_KEY_HERE"  # Replace with your actual API key

# Headers with authentication
HEADERS = {
    "X-API-Key": API_KEY
}


def check_health():
    """Check API health"""
    response = requests.get(f"{API_BASE_URL}/health")
    print("Health Check:", response.json())
    return response.status_code == 200


def get_model_info():
    """Get model information"""
    response = requests.get(f"{API_BASE_URL}/api/v1/info", headers=HEADERS)
    if response.status_code == 200:
        print("Model Info:", json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.status_code} - {response.text}")


def ocr_image_file(image_path: str, mode: str = "document_markdown", output_path: str = "result.zip"):
    """
    Perform OCR on an image file.
    
    Args:
        image_path: Path to image file
        mode: OCR mode (document_markdown, free_ocr, etc.)
        output_path: Where to save the result ZIP
    """
    print(f"\n🖼️  Processing image: {image_path}")
    print(f"   Mode: {mode}")
    
    with open(image_path, 'rb') as f:
        files = {'file': (Path(image_path).name, f, 'image/jpeg')}
        data = {'mode': mode, 'resolution_preset': 'Gundam'}
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/ocr/image",
            headers=HEADERS,
            files=files,
            data=data
        )
    
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ Success! Result saved to: {output_path}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")


def ocr_image_base64(image_path: str, mode: str = "document_markdown", output_path: str = "result.zip"):
    """
    Perform OCR on an image using base64 encoding.
    """
    print(f"\n🖼️  Processing image (base64): {image_path}")
    
    with open(image_path, 'rb') as f:
        image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    data = {
        'image_base64': image_base64,
        'mode': mode,
        'resolution_preset': 'Base'
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/ocr/image",
        headers=HEADERS,
        data=data
    )
    
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ Success! Result saved to: {output_path}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")


def ocr_pdf_sync(pdf_path: str, mode: str = "document_markdown", output_path: str = "result.zip"):
    """
    Perform OCR on a PDF file synchronously.
    """
    print(f"\n📄 Processing PDF (sync): {pdf_path}")
    print(f"   Mode: {mode}")
    
    with open(pdf_path, 'rb') as f:
        files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
        data = {'mode': mode, 'resolution_preset': 'Gundam'}
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/ocr/pdf",
            headers=HEADERS,
            files=files,
            data=data
        )
    
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ Success! Result saved to: {output_path}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")


def ocr_pdf_async(pdf_path: str, mode: str = "document_markdown"):
    """
    Perform OCR on a PDF file asynchronously.
    """
    print(f"\n📄 Processing PDF (async): {pdf_path}")
    print(f"   Mode: {mode}")
    
    # Submit task
    with open(pdf_path, 'rb') as f:
        files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
        data = {'mode': mode, 'resolution_preset': 'Gundam'}
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/ocr/pdf/async",
            headers=HEADERS,
            files=files,
            data=data
        )
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return
    
    task_info = response.json()
    task_id = task_info['task_id']
    print(f"✅ Task submitted! Task ID: {task_id}")
    print(f"   Status: {task_info['status']}")
    
    # Poll for completion
    print("\n⏳ Waiting for completion...")
    while True:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/ocr/task/{task_id}",
            headers=HEADERS
        )
        
        if response.status_code != 200:
            print(f"❌ Error checking status: {response.status_code}")
            return
        
        status = response.json()
        print(f"   Status: {status['status']} (progress: {status.get('progress', 0):.0%})")
        
        if status['status'] == 'completed':
            print("✅ Task completed!")
            
            # Download result
            response = requests.get(
                f"{API_BASE_URL}/api/v1/ocr/task/{task_id}/download",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                output_path = f"result_{task_id}.zip"
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Result downloaded to: {output_path}")
            else:
                print(f"❌ Error downloading result: {response.status_code}")
            break
        
        elif status['status'] == 'failed':
            print(f"❌ Task failed: {status.get('error', {})}")
            break
        
        time.sleep(2)


if __name__ == "__main__":
    print("=" * 60)
    print("DeepSeek-OCR API Client Example")
    print("=" * 60)
    
    # Check health
    if not check_health():
        print("❌ API is not healthy. Please check the service.")
        exit(1)
    
    print("\n" + "=" * 60)
    
    # Get model info
    get_model_info()
    
    print("\n" + "=" * 60)
    print("Example API Calls")
    print("=" * 60)
    
    # Example 1: OCR image file
    # Uncomment and provide your image path
    # ocr_image_file("path/to/your/image.jpg", mode="document_markdown")
    
    # Example 2: OCR image with base64
    # ocr_image_base64("path/to/your/image.jpg", mode="free_ocr")
    
    # Example 3: OCR PDF synchronously
    # ocr_pdf_sync("path/to/your/document.pdf", mode="document_markdown")
    
    # Example 4: OCR PDF asynchronously
    # ocr_pdf_async("path/to/your/large_document.pdf", mode="document_markdown")
    
    print("\n" + "=" * 60)
    print("Note: Uncomment examples above and provide file paths to test")
    print("=" * 60)
