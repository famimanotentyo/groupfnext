import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupf.settings')
django.setup()

from django.conf import settings
import google.generativeai as genai

print(f"API Key configured: {'Yes' if settings.GEMINI_API_KEY else 'No'}")

if not settings.GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY is missing in settings.")
    # Try to read .env manually just in case load_dotenv didn't work in settings for some reason
    # (Though settings.py already calls load_dotenv)
    exit(1)

genai.configure(api_key=settings.GEMINI_API_KEY)

target_model = 'gemini-2.5-flash'
print(f"Testing model: {target_model}")

try:
    model = genai.GenerativeModel(target_model)
    response = model.generate_content("Hello, reply with 'OK'")
    print(f"Success! Response: {response.text}")
except Exception as e:
    print(f"Failed with {target_model}: {e}")
    print("\nListing available models:")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e2:
        print(f"Failed to list models: {e2}")
