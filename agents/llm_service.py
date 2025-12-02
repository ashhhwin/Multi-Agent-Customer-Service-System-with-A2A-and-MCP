import requests
import json
import re
import time
import os

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_ID = "meta-llama/Llama-3.2-3B-Instruct"
HF_TOKEN = "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"  # Hardcoded token
os.environ['HF_TOKEN'] = "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"

def clean_json_text(text: str) -> str:
    """Extract JSON from text."""
    match = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    if match: return match.group(1).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match: return match.group(0).strip()
    return text.strip()

def query_llm(system_prompt: str, user_text: str, json_mode: bool = False):
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    final_system_prompt = system_prompt
    if json_mode:
        final_system_prompt += "\n\nIMPORTANT: Output ONLY valid JSON."

    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": final_system_prompt},
            {"role": "user", "content": user_text}
        ],
        "max_tokens": 500,
        "temperature": 0.1 if json_mode else 0.7,
        "stream": False
    }

    for attempt in range(2):  # Retry once if model is loading
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 503:
                print("[LLM-WAIT] Model loading... retrying in 10s")
                time.sleep(10)
                continue
            if response.status_code != 200:
                print(f"[LLM-FAIL] {response.status_code}: {response.text}")
                return None

            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
            else:
                print(f"[LLM-FAIL] Unexpected format: {result}")
                return None

            if json_mode:
                cleaned = clean_json_text(content)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    print(f"[LLM-PARSE-ERROR] Failed to parse JSON: {cleaned}")
                    return None

            return content.strip()

        except requests.exceptions.RequestException as e:
            print(f"[LLM-EXCEPTION] {e}")
            time.sleep(5)

    return None

# -------------------------
# Example usage
# -------------------------
# to test if api is working
if __name__ == "__main__":
    system_prompt = "You are a helpful assistant."
    user_text = "Generate a JSON with keys 'name' and 'age' for a fictional person."

    result = query_llm(system_prompt, user_text, json_mode=True)
    print(result)
