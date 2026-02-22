# IconsAI Scraping - Next.js Frontend
# Multi-stage build for optimized production image

# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app

# Copy package file
COPY package.json ./

# Install dependencies
RUN npm install

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build arguments
ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown
ARG NEXT_PUBLIC_API_URL

# Set environment variables for build
ENV NEXT_TELEMETRY_DISABLED=1
ENV GIT_SHA=${GIT_SHA}
ENV BUILD_DATE=${BUILD_DATE}
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Build the application
RUN npm run build

# Stage 3: Production
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Set ownership
RUN chown -R nextjs:nodejs /app

USER nextjs

# Expose port
EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
