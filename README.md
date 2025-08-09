# Cafe24 Automation Hub v2.0

안전하고 확장 가능한 Cafe24 쇼핑몰 자동화 시스템

## 🚀 Quick Start

### 1. 환경 설정

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (Linux/Mac)
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 실제 값을 입력:

```bash
cp .env.example .env
```

⚠️ **중요**: `.env` 파일은 절대 Git에 커밋하지 마세요!

### 3. 암호화 키 생성

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

생성된 키를 `.env` 파일의 `ENCRYPTION_KEY`에 입력

### 4. 애플리케이션 실행

```bash
# 개발 서버 실행 (Windows)
run_dev.bat

# 개발 서버 실행 (Linux/Mac)  
./run_dev.sh

# 또는 직접 실행
python -m uvicorn web.app:app --reload --port 3000
```

## 📁 프로젝트 구조

```
cafe24-automation-hub/
├── .env                    # 환경 변수 (Git 제외)
├── .env.example           # 환경 변수 예시
├── .gitignore            # Git 제외 파일
├── requirements.txt      # Python 의존성
├── README.md            # 프로젝트 문서
│
├── src/                 # 소스 코드
│   ├── config/         # 설정 관리
│   │   └── settings.py
│   ├── core/          # 핵심 모듈
│   │   ├── auth_manager.py
│   │   ├── token_manager.py
│   │   └── exceptions.py
│   ├── api/           # API 클라이언트
│   │   ├── client.py
│   │   ├── products.py
│   │   └── orders.py
│   ├── services/      # 비즈니스 로직
│   │   ├── product_sync.py
│   │   └── price_update.py
│   └── utils/         # 유틸리티
│
├── web/               # 웹 애플리케이션
│   ├── app.py        # FastAPI 앱
│   ├── routes/       # API 라우트
│   └── templates/    # HTML 템플릿
│
└── tests/            # 테스트 코드
    ├── unit/        # 단위 테스트
    └── integration/ # 통합 테스트
```

## 🔐 보안 기능

- ✅ 환경 변수를 통한 민감 정보 관리
- ✅ 토큰 암호화 저장
- ✅ OAuth 2.0 인증
- ✅ Rate Limiting 처리
- ✅ 에러 로깅 및 모니터링

## 🛠️ 주요 기능

### 1. 상품 관리
- 상품 목록 조회
- 상품 정보 수정
- 가격 일괄 업데이트
- 재고 관리

### 2. 주문 관리
- 주문 목록 조회
- 주문 상태 변경
- 배송 정보 관리

### 3. 고객 관리
- 고객 정보 조회
- 고객 등급 관리

## 📊 API 엔드포인트

### 인증
- `GET /auth/login` - OAuth 로그인
- `GET /auth/callback` - OAuth 콜백
- `POST /auth/refresh` - 토큰 갱신

### 상품
- `GET /api/products` - 상품 목록
- `GET /api/products/{id}` - 상품 상세
- `PUT /api/products/{id}` - 상품 수정
- `POST /api/products/sync` - 상품 동기화

### 주문
- `GET /api/orders` - 주문 목록
- `GET /api/orders/{id}` - 주문 상세
- `PUT /api/orders/{id}/status` - 주문 상태 변경

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest

# 커버리지 포함
pytest --cov=src

# 특정 테스트만 실행
pytest tests/unit/test_auth.py
```

## 📝 환경 변수 설명

| 변수명 | 설명 | 필수 |
|--------|------|------|
| CAFE24_MALL_ID | Cafe24 몰 ID | ✅ |
| CAFE24_CLIENT_ID | API Client ID | ✅ |
| CAFE24_CLIENT_SECRET | API Client Secret | ✅ |
| ENCRYPTION_KEY | 토큰 암호화 키 | ✅ |
| JWT_SECRET | JWT 서명 키 | ✅ |
| DATABASE_URL | 데이터베이스 연결 URL | ✅ |
| REDIS_URL | Redis 연결 URL | ❌ |
| SENTRY_DSN | Sentry 모니터링 DSN | ❌ |

## 🚀 배포

### Render 배포

1. GitHub 리포지토리 연결
2. 환경 변수 설정 (Render Dashboard)
3. 빌드 명령어: `pip install -r requirements.txt`
4. 시작 명령어: `python -m uvicorn web.app:app --host 0.0.0.0 --port $PORT`

### Docker 배포

```bash
# 이미지 빌드
docker build -t cafe24-hub .

# 컨테이너 실행
docker run -p 8000:8000 --env-file .env cafe24-hub
```

## 📚 문서

자세한 문서는 [Wiki](https://github.com/yourusername/cafe24-automation-hub/wiki)를 참조하세요.

## 🤝 기여

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

MIT License

## 🆘 지원

문제가 있으시면 [Issues](https://github.com/yourusername/cafe24-automation-hub/issues)에 등록해주세요.