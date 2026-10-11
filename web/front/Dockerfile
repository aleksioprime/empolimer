FROM node:22-alpine AS builder

WORKDIR /usr/src/app

ARG VITE_LOGGING=0
ENV VITE_LOGGING=$VITE_LOGGING

COPY app/package.json app/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY app ./

FROM builder AS dev
CMD ["npm", "run", "dev", "--", "--host"]

FROM builder AS prod-builder
RUN npm run build

FROM nginx:1.27-alpine AS prod

COPY --from=prod-builder /usr/src/app/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
