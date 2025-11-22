import httpx
import asyncio
import pytest
pytestmark = pytest.mark.asyncio
from app.translation import translate

@pytest.mark.asyncio
async def test_Helsinki():
    result=await translate(text='hello,world',source_lang="en", target_lang="zh", provider="Helsinki", user_api_key=None)
    expected_translation="你好，世界" #Helsinki返回结果“你好，世界，你好”
    assert result == expected_translation, f"Expected '{expected_translation}', got '{result}'"

@pytest.mark.asyncio
async def test_mymemory():
    result=await translate(text='hello,world',source_lang="en", target_lang="zh", provider="mymemory", user_api_key=None)
    expected_translation="你好，世界"
    assert result == expected_translation, f"Expected '{expected_translation}', got '{result}'"

asyncio.run(test_Helsinki())
asyncio.run(test_mymemory())


