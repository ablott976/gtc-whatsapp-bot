# Stage 1: Build admin dashboard (React SPA)
FROM node:20-alpine AS admin-build
WORKDIR /app/admin
COPY admin/package.json admin/package-lock.json* ./
RUN npm install
COPY admin/ ./
RUN npm run build

# Stage 2: Python app
FROM python:3.12-slim
WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code + SQL schema
COPY app/ ./app/
COPY sql/ ./sql/

# Copy built admin dashboard
COPY --from=admin-build /app/admin/dist ./admin/dist

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
