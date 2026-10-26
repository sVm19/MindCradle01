FROM node:22.23.2-alpine3.24 AS build

WORKDIR /workspace/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./

ARG VITE_API_URL
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_APP_ID
ARG VITE_FIREBASE_MESSAGING_SENDER_ID
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_VAPID_KEY
ARG VITE_MIXPANEL_TOKEN
ARG VITE_TRUSTPILOT_TOKEN
ARG VITE_COGNITO_DOMAIN
ARG VITE_COGNITO_CLIENT_ID
ARG VITE_COGNITO_REDIRECT_URI

RUN ./node_modules/.bin/vite build

FROM python:3.11.17-slim AS prerender

WORKDIR /workspace
COPY prerender.py ./prerender.py
COPY backend/app/data/blog_data.py ./backend/app/data/blog_data.py
COPY backend/app/data/docs_data.py ./backend/app/data/docs_data.py
COPY frontend/src/ ./frontend/src/
COPY --from=build /workspace/frontend/dist ./frontend/dist

RUN python prerender.py

FROM nginxinc/nginx-unprivileged:1.30.6-alpine3.24-slim AS runtime

ENV BACKEND_ORIGIN=http://backend:8080 \
    NGINX_ENVSUBST_FILTER=^BACKEND_ORIGIN$

COPY frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=prerender /workspace/frontend/dist /usr/share/nginx/html

EXPOSE 8080
