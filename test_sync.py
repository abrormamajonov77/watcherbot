from google import genai
import sys

API_KEY = "AIzaSyDb0_Xh-PlHDANyS02xqw5DLbukWEsbbFA"
client = genai.Client(api_key=API_KEY)

def test_model(model_name):
    print(f"Testing sync {model_name}...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say hi"
        )
        print(f"SUCCESS: {model_name} -> {response.text}")
    except Exception as e:
        print(f"FAILED: {model_name} -> {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_model('gemini-1.5-flash')
    test_model('gemini-2.0-flash')
    test_model('gemini-2.5-flash')
