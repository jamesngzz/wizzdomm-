# API Configuration Fix

## Problem

The frontend was not properly configured to work with the Django backend. The API client was using absolute URLs pointing directly to Django (`http://127.0.0.1:8000/api`), which bypassed Vite's development proxy entirely.

### Why This Was Wrong

When using Vite's dev server with a proxy:
- The dev server runs on port 8080
- Django backend runs on port 8000
- Vite proxy is configured to forward `/api`, `/media`, and `/ws` requests from :8080 to :8000

However, when you use **absolute URLs** like `http://127.0.0.1:8000/api`, the browser makes **direct requests** to Django, completely bypassing the Vite proxy. This can cause issues with:
- CORS (Cross-Origin Resource Sharing)
- Cookie handling
- Development workflow consistency

## Solution

Changed the frontend to use **relative paths** instead of absolute URLs. This ensures all requests go through the Vite dev server, which properly forwards them to Django via the configured proxy.

## Changes Made

### 1. `/FE/src/lib/api.ts`
- Changed `API_BASE` from `"http://127.0.0.1:8000/api"` to `"/api"`
- Updated `WS_URL` to dynamically construct WebSocket URL based on current location
- Added comments explaining the proxy behavior

**Before:**
```typescript
const API_BASE = (import.meta as any).env?.VITE_API_URL || "http://127.0.0.1:8000/api";
export const WS_URL = (import.meta as any).env?.VITE_WS_URL || "ws://127.0.0.1:8000/ws/notifications/";
```

**After:**
```typescript
const API_BASE = (import.meta as any).env?.VITE_API_URL || "/api";

const getDefaultWsUrl = () => {
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}/ws/notifications/`;
  }
  return "ws://127.0.0.1:8080/ws/notifications/";
};

export const WS_URL = (import.meta as any).env?.VITE_WS_URL || getDefaultWsUrl();
```

### 2. `/FE/src/pages/Grading.tsx`
- Removed unnecessary URL transformation for PDF exports
- Simplified to use relative URLs directly

### 3. `/FE/src/components/ItemAnnotationCanvas.tsx`
- Removed unnecessary URL transformation for image loading
- Simplified to use relative URLs directly

### 4. `/FE/README.md`
- Updated documentation to explain the proxy setup
- Added clear instructions for running both frontend and backend
- Clarified when environment variables should be used

## How It Works Now

### Development Flow

1. **Start Django backend:**
   ```bash
   cd new/backend
   python manage.py runserver 8000
   ```

2. **Start Vite dev server:**
   ```bash
   cd FE
   npm run dev
   ```

3. **Access the app:**
   - Frontend: `http://127.0.0.1:8080`
   - All API calls use relative paths: `/api/exams/`, `/api/submissions/`, etc.
   - Vite proxy intercepts these requests and forwards to Django at `:8000`
   - Media files work the same way: `/media/exams/...` → forwarded to Django
   - WebSockets: `ws://127.0.0.1:8080/ws/...` → forwarded to Django

### Request Flow

```
Browser → Vite Dev Server (:8080) → Vite Proxy → Django Backend (:8000)
```

**Example:**
- Browser makes request: `fetch('/api/exams/')`
- Goes to: `http://127.0.0.1:8080/api/exams/`
- Vite proxy forwards to: `http://127.0.0.1:8000/api/exams/`
- Django responds
- Response flows back through proxy to browser

### Production

In production, you would:
1. Build the frontend: `npm run build`
2. Serve static files from Django or a CDN
3. Set `VITE_API_URL` to your production API URL if needed

## Benefits

✅ **Consistent Development Environment:** All requests go through the same dev server
✅ **No CORS Issues:** Same-origin requests in development
✅ **Proper Cookie Handling:** Credentials work correctly
✅ **Clean URL Structure:** No hardcoded URLs in code
✅ **Production Ready:** Easy to configure for different environments via env vars
✅ **WebSocket Support:** Proper WebSocket proxying

## Environment Variables

You can still override defaults by creating a `.env` file in the `FE/` directory:

```env
# Point to a different backend (e.g., staging server)
VITE_API_URL=https://staging-api.example.com/api

# Custom WebSocket URL
VITE_WS_URL=wss://staging-api.example.com/ws/notifications/
```

**Note:** In normal development, you don't need a `.env` file. The defaults work with the proxy.

## Verification

To verify the fix is working:

1. Start both backend and frontend
2. Open browser DevTools → Network tab
3. Navigate to the app
4. Check API requests:
   - They should show as going to `http://127.0.0.1:8080/api/...`
   - Status should be 200 OK
   - No CORS errors in console

## Summary

The frontend is now properly configured to use Vite's proxy during development, which forwards all API, media, and WebSocket requests to the Django backend. This provides a cleaner development experience and avoids common issues with direct cross-origin requests.

