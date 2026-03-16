# Cloud Computing - Activity 2: File Storage API

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

## Authors

- Juan Gabriel Carvajal Franco
- María Elena Ventura Roldán
- Aina Muñoz Fernández



