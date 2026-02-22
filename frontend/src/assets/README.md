# Assets Folder

## Logo Setup Instructions

1. **Place your logo image in this folder** with the name `logo.png`
   - Supported formats: `.png`, `.jpg`, `.jpeg`, `.svg`, `.webp`
   - Recommended size: 512x512px or larger
   - Square format works best for consistent display

2. **If using a different filename or format**, update the import in:
   - `frontend/src/App.jsx` (line ~17)
   - `frontend/src/components/ChatInterface.jsx` (line ~4)
   
   Example for different formats:
   ```javascript
   // For SVG
   import logo from './assets/logo.svg';
   
   // For JPG
   import logo from './assets/logo.jpg';
   
   // For WebP
   import logo from './assets/logo.webp';
   ```

3. **Where the logo appears**:
   - Sidebar header (top left corner)
   - Chat interface (assistant message avatars)

## Current Setup

The app is configured to use `logo.png` from this folder. Until you add your logo file, you may see a broken image icon or error in the browser console.

## Quick Fix (Temporary)

If you don't have a logo ready yet, you can:
1. Download any square image from the internet
2. Rename it to `logo.png`
3. Place it in this folder
4. Refresh your browser

The app will automatically use it!
