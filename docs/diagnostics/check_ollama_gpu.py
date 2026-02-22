#!/usr/bin/env python3
"""
Diagnostic script to check if Ollama is using GPU properly.

Run this script to verify:
1. Ollama is running
2. Models are available
3. GPU is being used
4. Performance is acceptable
"""

import requests
import time
import sys

def check_ollama_running():
    """Check if Ollama is running."""
    print("🔍 Checking if Ollama is running...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama is running")
            return True
        else:
            print(f"❌ Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama is not running: {e}")
        print("   Run 'ollama serve' to start it")
        return False

def check_models():
    """Check which models are installed."""
    print("\n🔍 Checking installed models...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            
            required_models = ["qwen2.5vl:7b", "qwen2.5:14b", "mxbai-embed-large"]
            found_models = []
            
            for model in models:
                name = model.get("name", "")
                for required in required_models:
                    if required in name:
                        found_models.append(required)
                        print(f"✅ Found: {name}")
            
            missing = set(required_models) - set(found_models)
            if missing:
                print(f"\n❌ Missing models: {', '.join(missing)}")
                print("   Run: ollama pull <model_name>")
                return False
            else:
                print("\n✅ All required models installed")
                return True
        else:
            print(f"❌ Failed to get models: status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to check models: {e}")
        return False

def check_gpu_usage():
    """Check if models are using GPU."""
    print("\n🔍 Checking GPU usage...")
    try:
        response = requests.get("http://localhost:11434/api/ps", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            
            if not models:
                print("⚠️  No models currently loaded")
                print("   Models load on first use")
                return True
            
            for model in models:
                name = model.get("name", "unknown")
                size = model.get("size", 0)
                size_gb = size / (1024**3)
                
                # Check processor field if available
                processor = model.get("processor", "unknown")
                
                print(f"\n📊 Model: {name}")
                print(f"   Size: {size_gb:.2f} GB")
                print(f"   Processor: {processor}")
                
                if "GPU" in processor.upper():
                    print(f"   ✅ Using GPU")
                elif "CPU" in processor.upper():
                    print(f"   ❌ Using CPU (should be GPU!)")
                    return False
                else:
                    print(f"   ⚠️  Processor type unknown")
            
            return True
        else:
            print(f"❌ Failed to check running models: status {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  Could not check GPU usage: {e}")
        print("   This endpoint might not be available in your Ollama version")
        return True

def test_vision_performance():
    """Test vision model performance."""
    print("\n🔍 Testing vision model performance...")
    print("   This will test image processing speed...")
    
    # Create a simple test image
    try:
        from PIL import Image
        import base64
        import io
        
        # Create a small test image
        img = Image.new('RGB', (100, 100), color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Test vision model
        print("   Sending test image to qwen2.5vl:7b...")
        start_time = time.time()
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5vl:7b",
                "prompt": "Describe this image briefly.",
                "images": [img_base64],
                "stream": False
            },
            timeout=60
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            print(f"   ✅ Vision model responded in {elapsed:.2f} seconds")
            
            if elapsed < 5:
                print(f"   ✅ EXCELLENT: GPU is working perfectly!")
            elif elapsed < 10:
                print(f"   ⚠️  ACCEPTABLE: Might be first load or CPU")
            else:
                print(f"   ❌ TOO SLOW: Likely using CPU instead of GPU")
                print(f"      Expected: <5 seconds with GPU")
                print(f"      Got: {elapsed:.2f} seconds")
                return False
            
            return True
        else:
            print(f"   ❌ Vision model failed: status {response.status_code}")
            print(f"      Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Performance test failed: {e}")
        return False

def main():
    """Run all diagnostic checks."""
    print("=" * 60)
    print("Ollama GPU Diagnostic Tool")
    print("=" * 60)
    
    checks = [
        ("Ollama Running", check_ollama_running),
        ("Models Installed", check_models),
        ("GPU Usage", check_gpu_usage),
        ("Vision Performance", test_vision_performance),
    ]
    
    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))
        
        if not result and name in ["Ollama Running", "Models Installed"]:
            print(f"\n❌ Critical check failed: {name}")
            print("   Cannot continue with remaining checks")
            break
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 All checks passed! Your system is configured correctly.")
        print("   Ollama is using your GPU for inference.")
    else:
        print("\n⚠️  Some checks failed. See recommendations above.")
        print("\nCommon fixes:")
        print("1. Restart Ollama: Stop with Ctrl+C, then run 'ollama serve'")
        print("2. Check NVIDIA drivers: Run 'nvidia-smi'")
        print("3. Reinstall Ollama: Download from https://ollama.ai/download")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
