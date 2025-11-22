import httpx
from typing import Optional
from fastapi import HTTPException
from cryptography.fernet import Fernet
from .config import get_settings
import os

settings = get_settings()

# Encryption for user API keys
cipher = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_api_key(plain_key: str) -> str:
    return cipher.encrypt(plain_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    return cipher.decrypt(encrypted_key.encode()).decode()

async def translate_with_Helsinki(
    text: str,
    source_lang: str,
    target_lang: str
) -> str:
    """Translate using huggingface Helsinki"""
    try:
        HF_TOKEN = os.getenv("HF_TOKEN")
        if not HF_TOKEN:
            raise ValueError("HF_TOKEN environment variable is required for Hugging Face API.")
        if source_lang != "en" or target_lang != "zh":
            raise ValueError(f"Model supports only en -> zh. Provided: {source_lang} -> {target_lang}")
        model_id = "Helsinki-NLP/opus-mt-en-zh"
        url = f"https://router.huggingface.co/hf-inference/models/{model_id}"

        # print(f"HF token is {HF_TOKEN}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                json={"inputs": text}
            )
            
            # print(f"[DEBUG] Response status: {response.status_code}")
            # print(f"[DEBUG] Response text preview: {response.text[:200]}")
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Hugging Face Inference error: {response.text}"
                )
            
            result = response.json()
            if not isinstance(result, list) or len(result) == 0 or "translation_text" not in result[0]:
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid response format: {result}"
                )
            
            return result[0]["translation_text"]
    except httpx.ConnectError as ce:
        msg = str(ce) or repr(ce) or "Connection failed"
        raise HTTPException(status_code=500, detail=f"HF connection failed: {msg}")
    except httpx.TimeoutException as te:
        msg = str(te) or "Request timed out"
        raise HTTPException(status_code=504, detail=f"HF timeout: {msg}")
    except httpx.HTTPStatusError as he:
        msg = f"{he.response.status_code}: {he.response.text or 'No details'}"
        raise HTTPException(status_code=500, detail=f"HF HTTP error: {msg}")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"HF config error: {str(ve)}")
    except Exception as e:
        msg = str(e) or repr(e) or "Unknown HF exception"
        raise HTTPException(status_code=500, detail=f"HF unexpected error: {msg}")

async def translate_with_mymemory(
    text: str,
    source_lang: str,
    target_lang: str
) -> str:
    """Translate using MyMemory (free, 1000 requests/day)"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            lang_pair = f"{source_lang if source_lang != 'auto' else 'en'}|{target_lang}"
            response = await client.get(
                "https://api.mymemory.translated.net/get",
                params={
                    "q": text,
                    "langpair": lang_pair
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="MyMemory error")
            
            result = response.json()
            return result["responseData"]["translatedText"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")

async def translate_with_deepl(
    text: str,
    target_lang: str,
    api_key: str
) -> str:
    """Translate using DeepL API"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api-free.deepl.com/v2/translate",
                data={
                    "auth_key": api_key,
                    "text": text,
                    "target_lang": target_lang.upper()
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="DeepL API error")
            
            result = response.json()
            return result["translations"][0]["text"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DeepL error: {str(e)}")

async def test_api_key(provider: str, api_key: str) -> bool:
    """Test if API key is valid"""
    try:
        if provider == "deepl":
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    "https://api-free.deepl.com/v2/translate",
                    data={
                        "auth_key": api_key,
                        "text": "test",
                        "target_lang": "ZH"
                    }
                )
                return response.status_code == 200
        # Add more providers as needed
        return False
    except:
        return False

async def translate(
    text: str,
    source_lang: str,
    target_lang: str,
    provider: str,
    user_api_key: Optional[str] = None
) -> str:
    """
    Main translation function - routes to appropriate provider
    """
    if user_api_key and provider == "deepl":
        return await translate_with_deepl(text, target_lang, user_api_key)
    elif provider == "mymemory":
        return await translate_with_mymemory(text, source_lang, target_lang)
    elif provider == "Helsinki":
        # Default to Helsinki
        return await translate_with_Helsinki(text, source_lang, target_lang)