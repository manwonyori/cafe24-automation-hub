# 🚨 즉시 실행 계획 - Cafe24 보안 패치

## Step 1: 보안 긴급 조치 (30분 소요)

### 1.1 환경 변수 파일 생성
```bash
# .env 파일 (절대 Git에 올리지 말 것!)
CAFE24_MALL_ID=manwonyori
CAFE24_CLIENT_ID=your_client_id_here
CAFE24_CLIENT_SECRET=your_client_secret_here
CAFE24_SERVICE_KEY=your_service_key_here
ENCRYPTION_KEY=generate_new_key_here
DATABASE_URL=sqlite:///cafe24.db
REDIS_URL=redis://localhost:6379
SENTRY_DSN=your_sentry_dsn_here
```

### 1.2 .gitignore 업데이트
```gitignore
# 보안 파일
.env
*.env
.env.*
!.env.example

# 토큰 및 인증 정보
*token*.json
*credentials*.json
*secret*
*password*

# 캐시 및 로그
*.log
*.cache
__pycache__/
*.pyc

# 데이터베이스
*.db
*.sqlite
```

### 1.3 GitHub 기존 히스토리 정리
```bash
# 민감 정보가 포함된 파일 히스토리에서 제거
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch config/cafe24_api_config.json" \
  --prune-empty --tag-name-filter cat -- --all

# 강제 푸시 (주의!)
git push origin --force --all
```

## Step 2: Render 환경 변수 설정 (10분)

1. Render Dashboard 접속
2. Environment > Environment Variables
3. 다음 변수 추가:
   - CAFE24_CLIENT_ID
   - CAFE24_CLIENT_SECRET
   - CAFE24_MALL_ID
   - ENCRYPTION_KEY
   - PYTHON_VERSION=3.11

## Step 3: 핵심 보안 모듈 생성 (1시간)

### 3.1 설정 관리자
```python
# src/config/settings.py
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # Cafe24 API
    cafe24_mall_id: str = Field(..., env='CAFE24_MALL_ID')
    cafe24_client_id: str = Field(..., env='CAFE24_CLIENT_ID')
    cafe24_client_secret: str = Field(..., env='CAFE24_CLIENT_SECRET')
    cafe24_service_key: Optional[str] = Field(None, env='CAFE24_SERVICE_KEY')
    
    # Security
    encryption_key: str = Field(..., env='ENCRYPTION_KEY')
    jwt_secret: str = Field(default='your-jwt-secret', env='JWT_SECRET')
    
    # API Settings
    api_version: str = "2024-06-01"
    api_timeout: int = 30
    max_retries: int = 3
    
    # URLs
    @property
    def cafe24_base_url(self) -> str:
        return f"https://{self.cafe24_mall_id}.cafe24api.com/api/v2"
    
    @property
    def redirect_uri(self) -> str:
        if os.getenv('RENDER'):
            return "https://cafe24-automation.onrender.com/callback"
        return "http://localhost:8000/callback"
    
    class Config:
        env_file = '.env'
        case_sensitive = False

# 싱글톤 인스턴스
settings = Settings()
```

### 3.2 토큰 관리자
```python
# src/core/token_manager.py
import json
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Optional, Dict
import redis
import os

class TokenManager:
    """보안 토큰 관리"""
    
    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key.encode() if len(encryption_key) == 32 else Fernet.generate_key())
        self.redis_client = self._init_redis()
        self.token_file = Path('.tokens.encrypted')
    
    def _init_redis(self) -> Optional[redis.Redis]:
        """Redis 연결 (있으면 사용, 없으면 파일 사용)"""
        try:
            client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
            client.ping()
            return client
        except:
            return None
    
    def save_token(self, token_type: str, token: str, expires_in: int = 7200):
        """토큰 암호화 저장"""
        encrypted = self.cipher.encrypt(token.encode())
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        data = {
            'token': encrypted.decode(),
            'expires_at': expires_at.isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        if self.redis_client:
            # Redis에 저장
            self.redis_client.setex(
                f"cafe24:token:{token_type}",
                expires_in,
                json.dumps(data)
            )
        else:
            # 파일에 암호화 저장
            tokens = self._load_file_tokens()
            tokens[token_type] = data
            self._save_file_tokens(tokens)
    
    def get_token(self, token_type: str) -> Optional[str]:
        """토큰 복호화 및 반환"""
        if self.redis_client:
            data = self.redis_client.get(f"cafe24:token:{token_type}")
            if data:
                token_data = json.loads(data)
        else:
            tokens = self._load_file_tokens()
            token_data = tokens.get(token_type)
        
        if not token_data:
            return None
        
        # 만료 확인
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            return None
        
        # 복호화
        encrypted = token_data['token'].encode()
        return self.cipher.decrypt(encrypted).decode()
    
    def _load_file_tokens(self) -> Dict:
        """파일에서 토큰 로드"""
        if not self.token_file.exists():
            return {}
        
        try:
            with open(self.token_file, 'rb') as f:
                encrypted_data = f.read()
                decrypted = self.cipher.decrypt(encrypted_data)
                return json.loads(decrypted)
        except:
            return {}
    
    def _save_file_tokens(self, tokens: Dict):
        """파일에 토큰 저장"""
        data = json.dumps(tokens).encode()
        encrypted = self.cipher.encrypt(data)
        
        with open(self.token_file, 'wb') as f:
            f.write(encrypted)
```

## Step 4: 안전한 API 클라이언트 (2시간)

### 4.1 인증 관리자
```python
# src/core/auth_manager.py
import base64
import httpx
from typing import Optional, Dict
from datetime import datetime

from ..config.settings import settings
from .token_manager import TokenManager

class AuthManager:
    """Cafe24 OAuth 인증 관리"""
    
    def __init__(self):
        self.token_manager = TokenManager(settings.encryption_key)
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_access_token(self, auth_code: Optional[str] = None) -> str:
        """Access Token 획득"""
        # 저장된 토큰 확인
        token = self.token_manager.get_token('access')
        if token and not auth_code:
            return token
        
        # 새 토큰 요청
        if auth_code:
            token_data = await self._request_token_with_code(auth_code)
        else:
            # Refresh token으로 갱신
            refresh_token = self.token_manager.get_token('refresh')
            if refresh_token:
                token_data = await self._refresh_token(refresh_token)
            else:
                raise Exception("인증 필요: Authorization Code를 제공하세요")
        
        # 토큰 저장
        self.token_manager.save_token(
            'access',
            token_data['access_token'],
            token_data.get('expires_in', 7200)
        )
        
        if 'refresh_token' in token_data:
            self.token_manager.save_token(
                'refresh',
                token_data['refresh_token'],
                2592000  # 30일
            )
        
        return token_data['access_token']
    
    async def _request_token_with_code(self, auth_code: str) -> Dict:
        """Authorization Code로 토큰 요청"""
        auth_string = f"{settings.cafe24_client_id}:{settings.cafe24_client_secret}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        
        response = await self.client.post(
            f"{settings.cafe24_base_url}/oauth/token",
            headers={
                "Authorization": f"Basic {auth_bytes}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": settings.redirect_uri
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def _refresh_token(self, refresh_token: str) -> Dict:
        """Refresh Token으로 Access Token 갱신"""
        auth_string = f"{settings.cafe24_client_id}:{settings.cafe24_client_secret}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        
        response = await self.client.post(
            f"{settings.cafe24_base_url}/oauth/token",
            headers={
                "Authorization": f"Basic {auth_bytes}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_auth_url(self) -> str:
        """OAuth 인증 URL 생성"""
        params = {
            "response_type": "code",
            "client_id": settings.cafe24_client_id,
            "redirect_uri": settings.redirect_uri,
            "scope": "mall.read_product,mall.write_product,mall.read_order"
        }
        
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{settings.cafe24_base_url}/oauth/authorize?{query}"
```

## 실행 순서

### 오늘 (Day 0)
1. ✅ 이 파일들을 생성
2. ✅ .env 파일 작성 (실제 값 입력)
3. ✅ GitHub에서 기존 민감 정보 제거
4. ✅ Render 환경 변수 설정

### 내일 (Day 1)
1. ⏳ 새 구조로 기존 기능 이전
2. ⏳ 테스트 실행
3. ⏳ Render 배포

### 이번 주 (Week 1)
1. ⏳ 전체 리팩토링 완료
2. ⏳ 모니터링 시스템 구축
3. ⏳ 문서화

## 테스트 명령어

```bash
# 환경 설정 테스트
python -c "from src.config.settings import settings; print(settings.cafe24_mall_id)"

# 토큰 암호화 테스트
python -c "from src.core.token_manager import TokenManager; tm = TokenManager('test-key'); tm.save_token('test', 'my-token')"

# API 연결 테스트
python -m pytest tests/test_auth.py -v
```

---

**🔥 지금 당장 실행하세요!**

보안 문제는 하루도 방치하면 안 됩니다.