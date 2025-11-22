from fastapi import FastAPI, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional, List
import logging

from .config import get_settings
from .database import get_db, engine, Base
from .models import User, TranslationHistory, UserAPIKey
from .schemas import (
    UserCreate, UserLogin, UserResponse, Token,
    TranslateRequest, TranslateResponse,
    TranslationHistoryResponse, TranslationHistoryList,
    AddAPIKeyRequest, APIKeyResponse,
    CacheStats, UserStats
)
from .auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_active_user
)
from .cache import (
    get_cached_translation, set_cached_translation, get_cache_stats
)
from .translation import (
    translate, encrypt_api_key, decrypt_api_key, test_api_key
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-provider translation API with caching and user management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
# Create static directory if not exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "app_name": settings.APP_NAME
    }

# ==================== Authentication Endpoints ====================
from fastapi.openapi.utils import get_openapi
from app.auth import security
# openAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Translation-API",
        version="1.0.0",
        description="API with JWT Bearer Auth",
        routes=app.routes,
    )
    # "HTTPBearer" 
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {  
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi   # cover default

@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    
    # Check if user exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"New user registered: {user.username}")
    return user

@app.post("/api/auth/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login and get access token"""
    
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user

# ==================== Translation Endpoints ====================

def save_translation_to_db(
    db: Session,
    user_id: int,
    source_text: str,
    translated_text: str,
    source_lang: str,
    target_lang: str,
    provider: str
):
    """Background task to save translation history"""
    try:
        translation = TranslationHistory(
            user_id=user_id,
            source_text=source_text,
            translated_text=translated_text,
            source_lang=source_lang,
            target_lang=target_lang,
            provider=provider
        )
        db.add(translation)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save translation: {e}")
        db.rollback()

@app.post("/api/v1/translate", response_model=TranslateResponse)
async def translate_text(
    req: TranslateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Translate text with caching and user API key support
    
    - **text**: Text to translate (max 5000 characters)
    - **source_lang**: Source language code (default: "en")
    - **target_lang**: Target language code ("zh")
    - **provider**: Translation provider ("Helsinki", "mymemory")
    """
    
    # 1. Check cache
    cached_result = await get_cached_translation(
        req.text, req.source_lang, req.target_lang
    )
    
    if cached_result:
        return TranslateResponse(
            original_text=req.text,
            translated_text=cached_result,
            source_lang=req.source_lang,
            target_lang=req.target_lang,
            provider=req.provider,
            cached=True
        )
    
    # 2. Get user's API key if exists
    user_api_key = None
    if req.provider in ["deepl", "google", "openai"]:
        user_key = db.query(UserAPIKey).filter(
            UserAPIKey.user_id == current_user.id,
            UserAPIKey.provider == req.provider,
            UserAPIKey.is_active == True
        ).first()
        
        if user_key:
            user_api_key = decrypt_api_key(user_key.encrypted_api_key)
            user_key.last_used = datetime.utcnow()
            db.commit()
    
    # 3. Translate
    try:
        translated_text = await translate(
            text=req.text,
            source_lang=req.source_lang,
            target_lang=req.target_lang,
            provider=req.provider,
            user_api_key=user_api_key
        )
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # 4. Cache the result
    request_count = await set_cached_translation(
        req.text, req.source_lang, req.target_lang, translated_text
    )
    
    # 5. Save to database (background task)
    background_tasks.add_task(
        save_translation_to_db,
        db=db,
        user_id=current_user.id,
        source_text=req.text,
        translated_text=translated_text,
        source_lang=req.source_lang,
        target_lang=req.target_lang,
        provider=req.provider
    )
    
    return TranslateResponse(
        original_text=req.text,
        translated_text=translated_text,
        source_lang=req.source_lang,
        target_lang=req.target_lang,
        provider=req.provider,
        cached=False,
        request_count=request_count
    )

# ==================== Translation History ====================

@app.get("/api/v1/history", response_model=TranslationHistoryList)
async def get_translation_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    target_lang: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's translation history with pagination"""
    
    query = db.query(TranslationHistory).filter(
        TranslationHistory.user_id == current_user.id
    )
    
    if target_lang:
        query = query.filter(TranslationHistory.target_lang == target_lang)
    
    total = query.count()
    translations = query.order_by(
        TranslationHistory.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return TranslationHistoryList(
        total=total,
        translations=translations
    )

@app.delete("/api/v1/history/{translation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_translation(
    translation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a specific translation from history"""
    
    translation = db.query(TranslationHistory).filter(
        TranslationHistory.id == translation_id,
        TranslationHistory.user_id == current_user.id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    db.delete(translation)
    db.commit()

# ==================== User API Keys ====================

@app.post("/api/v1/user/api-keys", response_model=APIKeyResponse)
async def add_user_api_key(
    req: AddAPIKeyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add user's own API key for premium providers
    
    Supported providers:
    - deepl: DeepL API (get free key at https://www.deepl.com/pro-api)
    - google: Google Translate API
    - openai: OpenAI GPT translation
    """
    
    # Test if API key is valid
    is_valid = await test_api_key(req.provider, req.api_key)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid API key")
    
    # Encrypt the key
    encrypted_key = encrypt_api_key(req.api_key)
    
    # Check if key already exists
    existing = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == current_user.id,
        UserAPIKey.provider == req.provider
    ).first()
    
    if existing:
        existing.encrypted_api_key = encrypted_key
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        logger.info(f"User {current_user.username} updated {req.provider} API key")
        return existing
    else:
        new_key = UserAPIKey(
            user_id=current_user.id,
            provider=req.provider,
            encrypted_api_key=encrypted_key
        )
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        logger.info(f"User {current_user.username} added {req.provider} API key")
        return new_key

@app.get("/api/v1/user/api-keys", response_model=List[APIKeyResponse])
async def get_user_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all API keys for current user (encrypted keys are not returned)"""
    
    keys = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == current_user.id
    ).all()
    
    return keys

@app.delete("/api/v1/user/api-keys/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_api_key(
    provider: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a specific API key"""
    
    key = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == current_user.id,
        UserAPIKey.provider == provider
    ).first()
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    db.delete(key)
    db.commit()
    logger.info(f"User {current_user.username} deleted {provider} API key")

# ==================== Statistics ====================

@app.get("/api/v1/stats/cache", response_model=CacheStats)
async def get_cache_statistics(
    current_user: User = Depends(get_current_active_user)
):
    """Get cache performance statistics"""
    return await get_cache_stats()

@app.get("/api/v1/stats/user", response_model=UserStats)
async def get_user_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's translation statistics"""
    
    # Total translations
    total_translations = db.query(TranslationHistory).filter(
        TranslationHistory.user_id == current_user.id
    ).count()
    
    # Translations today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    translations_today = db.query(TranslationHistory).filter(
        TranslationHistory.user_id == current_user.id,
        TranslationHistory.created_at >= today_start
    ).count()
    
    # Most used target language
    most_used_lang = db.query(
        TranslationHistory.target_lang,
        func.count(TranslationHistory.target_lang).label('count')
    ).filter(
        TranslationHistory.user_id == current_user.id
    ).group_by(TranslationHistory.target_lang).order_by(
        func.count(TranslationHistory.target_lang).desc()
    ).first()
    
    # Total characters translated
    total_chars = db.query(
        func.sum(func.length(TranslationHistory.source_text))
    ).filter(
        TranslationHistory.user_id == current_user.id
    ).scalar() or 0
    
    return UserStats(
        total_translations=total_translations,
        translations_today=translations_today,
        most_used_language=most_used_lang[0] if most_used_lang else None,
        total_characters_translated=total_chars
    )

# ==================== Root ====================

@app.get("/")
async def root():
    return {
        "message": "Translation API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)