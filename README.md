# Cloud Computing - Activity 3: File Storage API

This project implements a complete HTTP API for a file storage system with user authentication. Built with FastAPI and containerized with Docker

### --Authentication API--
- `POST /auth/register` - Register new users (passwords hashed with SHA-256)
- `POST /auth/login` - Authenticate and receive session token (UUID v4)
- `POST /auth/logout` - Invalidate session token
- `GET /auth/introspect` - Validate token and get user info

### --Files API--
- `GET /files` - List all files owned by the authenticated user
- `POST /files` - Create file metadata (without content)
- `GET /files/{id}` - Get file details and content (if exists)
- `POST /files/{id}` - Upload file content (base64 encoded)
- `DELETE /files/{id}` - Delete a file
- `POST /files/merge` - Merge two PDF files into one (real PDF merging with pypdf)

# Build and run with Docker Compose
docker-compose up carlemany-backend

# Access the API
Swagger UI: http://localhost:8000/docs

# Requirements

fastapi==0.100.1
pypdf==6.8.0
python-multipart==0.0.9
aiohttp==3.11.13
requests==2.32.3
pydantic_settings==2.0.0
aerich==0.6.3
tortoise-orm==0.19.3
asyncpg==0.28.0

## Authors

- Juan Gabriel Carvajal Franco
- María Elena Ventura Roldán
- Aina Muñoz Fernández



