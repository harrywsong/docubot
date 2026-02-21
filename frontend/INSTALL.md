# Frontend Installation Guide

## Prerequisites

- Node.js 18+ and npm (or yarn/pnpm)
- Backend API running on http://127.0.0.1:8000

## Installation Steps

### 1. Install Dependencies

```bash
cd frontend
npm install
```

This will install:
- React 18.2.0
- React DOM 18.2.0
- Vite 5.0.0
- @vitejs/plugin-react 4.2.1

### 2. Start Development Server

```bash
npm run dev
```

The frontend will start on http://localhost:3000

### 3. Access the Application

Open your browser and navigate to:
```
http://localhost:3000
```

## Troubleshooting

### Port Already in Use

If port 3000 is already in use, Vite will automatically try the next available port (3001, 3002, etc.). Check the terminal output for the actual port.

### Backend Connection Issues

If you see connection errors:

1. Verify the backend is running:
   ```bash
   curl http://127.0.0.1:8000/api/health
   ```

2. Check the backend logs for errors

3. Ensure CORS is enabled in the backend (it should be by default)

### WebSocket Connection Fails

If real-time processing updates don't work:

1. Check browser console for WebSocket errors
2. Verify the backend WebSocket endpoint is accessible
3. Some corporate firewalls block WebSocket connections

### Build Errors

If you encounter build errors:

1. Delete node_modules and package-lock.json:
   ```bash
   rm -rf node_modules package-lock.json
   ```

2. Reinstall dependencies:
   ```bash
   npm install
   ```

3. Clear Vite cache:
   ```bash
   rm -rf node_modules/.vite
   ```

## Production Build

To build for production:

```bash
npm run build
```

The optimized files will be in the `dist/` directory.

To preview the production build:

```bash
npm run preview
```

## Development Tips

- Hot Module Replacement (HMR) is enabled - changes will reflect immediately
- React DevTools browser extension is recommended for debugging
- Check browser console for any errors or warnings
- The Vite dev server provides detailed error messages

## File Structure

```
frontend/
├── src/
│   ├── components/       # React components
│   │   ├── ChatInterface.jsx
│   │   ├── ConversationList.jsx
│   │   ├── FolderManagement.jsx
│   │   ├── HealthCheck.jsx
│   │   ├── ProcessingPanel.jsx
│   │   └── Toast.jsx
│   ├── api.js           # API client
│   ├── App.jsx          # Main app component
│   ├── App.css          # Global styles
│   └── main.jsx         # Entry point
├── index.html           # HTML template
├── vite.config.js       # Vite configuration
└── package.json         # Dependencies
```
