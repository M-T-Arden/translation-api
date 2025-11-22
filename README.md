# 🌍 Translation API Template

A production-ready REST API template for multi-provider translation services with intelligent caching, user authentication, and Docker deployment.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

> **📝 Read the full technical deep-dive**: Blog is in Progress

## 🚀 Quick Start (5 minutes)

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/M-T-Arden/translation-api.git
cd translation-api

# 2. Create environment file from template
cp .env.example .env

# 3. Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy the output and paste it into .env as ENCRYPTION_KEY

# 4. Generate secret key (or use any random 32+ character string)
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy the output and paste it into .env as SECRET_KEY

# 5. Start all services
docker-compose up --build

```

### Verify Installation

Open your browser and visit:

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📖 Test Example

You can test the function through curl in terminal or swagger UI http://localhost:8000/docs.

1.docs dashboard

![](https://github.com/M-T-Arden/translation-api/blob/main/statics/Swagger%20UI%20dashboard.png)

2. Login test example:

![login](https://github.com/M-T-Arden/translation-api/blob/main/statics/Login.png)

3. Translation test example (mymemory) cache:False

![](https://github.com/M-T-Arden/translation-api/blob/main/statics/Trans%20mymemory.png)

4. Translation example (Helsinki) cache=True

![](https://github.com/M-T-Arden/translation-api/blob/main/statics/Trans%20cache.png)

5. Translation example (Helsinki) cache=False

![](https://github.com/M-T-Arden/translation-api/blob/main/statics/Trans%20Helsinki%20.png)

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│     FastAPI Application         │
│  ┌───────────────────────────┐  │
│  │  JWT Authentication       │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │  Translation Endpoints    │  │
│  └───────────────────────────┘  │
└────────┬────────────────┬───────┘
         │                │
    ┌────▼────┐      ┌────▼─────┐
    │  Redis  │      │PostgreSQL│
    │ (Cache) │      │   (DB)   │
    └─────────┘      └──────────┘
         │
    ┌────▼──────────────────┐
    │ Translation Providers │
    │ (Helsinki, etc) │
    └───────────────────────┘
```

## 🔧 Configuration

All configuration is managed through environment variables in `.env.example`:

| Variable         | Description                  | Required | Default |
| ---------------- | ---------------------------- | -------- | ------- |
| `DATABASE_URL`   | PostgreSQL connection string | Yes      | -       |
| `REDIS_URL`      | Redis connection string      | Yes      | -       |
| `SECRET_KEY`     | JWT signing key (32+ chars)  | Yes      | -       |
| `ENCRYPTION_KEY` | Fernet encryption key        | Yes      | -       |
| `DEEPL_API_KEY`  | DeepL API key (**optional**) | **No**   | -       |

See [.env.example](.env.example) for full configuration options.

## ✨ Feature

- 🔌 **Multi-provider Support Built-in**: MyMemory, Helsinki, DeepL

| Provider     | Free?     | Limits / Requirements                                | Supported Languages                                          |
| ------------ | --------- | ---------------------------------------------------- | ------------------------------------------------------------ |
| **MyMemory** | **Yes**   | **1000 words/day (anonymous)**                       | **Most major languages**                                     |
| Helsinki-NLP | Yes       | Requires Hugging Face token                          | Currently only en ↔ zh, but you can select similar model on hugging face that supports other language |
| DeepL        | Free tier | Requires DeepL API key (free tier: 500k chars/month) | 30+ languages, high quality                                  |

- ⚡ **Smart Caching**: Redis with popularity-based TTL (70%+ hit rate)
- 🔐 **JWT Authentication**: Secure user management with bcrypt
- 🔑 **Custom API Keys**: Users can integrate their own provider keys
- 🐳 **Docker Ready**: One-command deployment with Docker Compose
- 📚 **Auto Documentation**: Interactive Swagger UI out of the box
- 🧪 **90% Test Coverage**: Comprehensive pytest suite

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or report a Issue.

## 📝 License

This project is licensed under the MIT License.

---

⭐ If this project helped you, please consider giving it a star!
