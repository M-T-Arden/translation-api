import httpx
import asyncio
import pytest
from app.translation import translate

@pytest.mark.asyncio
async def test_Helsinki():
    result=await translate(text='hello,world',source_lang="en", target_lang="zh", provider="Helsinki", user_api_key=None)
    assert isinstance(result,str),f"Expected string, got {type(result)}"
    assert len(result) >0, f"Expected unempty result, got {result}"
    print(f"Helsinki translation: {result}")

@pytest.mark.asyncio
async def test_mymemory():
    result=await translate(text='hello,world',source_lang="en", target_lang="zh", provider="mymemory", user_api_key=None)
    assert isinstance(result,str),f"Expected string, got {type(result)}"
    assert len(result) >0, f"Expected unempty result, got {result}"
    print(f"Mymemory translation: {result}")




