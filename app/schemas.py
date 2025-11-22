from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List

# User schemas
class UserCreate(BaseModel):
    username: str = Field(default='user@example.com', min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(default='testtest', min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(default='testtest', min_length=8)

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# Translation schemas
class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    source_lang: str = Field(default="en", max_length=100)
    target_lang: str = Field(default="zh", max_length=100)
    provider: Optional[str] = Field(default="mymemory", max_length=50)

class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    provider: str
    cached: bool
    request_count: Optional[int] = None

class TranslationHistoryResponse(BaseModel):
    id: int
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    provider: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class TranslationHistoryList(BaseModel):
    total: int
    translations: List[TranslationHistoryResponse]

# API Key schemas
class AddAPIKeyRequest(BaseModel):
    provider: str = Field(..., pattern="^(deepl)$")
    api_key: str = Field(..., min_length=10)

class APIKeyResponse(BaseModel):
    id: int
    provider: str
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime]
    
    class Config:
        from_attributes = True

# Stats schemas
class CacheStats(BaseModel):
    cache_hits: int
    cache_misses: int
    hit_rate: str
    total_requests: int
    memory_used: str
    total_keys: int

class UserStats(BaseModel):
    total_translations: int
    translations_today: int
    most_used_language: Optional[str]
    total_characters_translated: int