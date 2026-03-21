# Voice2Sign Frontend - Clean Architecture

## 📁 Project Structure

```
voice_to_sign/
├── README.md                        # Project documentation
├── index.html                       # Login page (landing)
├── signup.html                      # Signup page
├── dashboard.html                   # Main dashboard
├── css/
│   ├── main.css                     # Core styles, variables, utilities
│   ├── login.css                    # Login page specific styles
│   ├── signup.css                   # Signup page specific styles
│   └── dashboard.css                # Dashboard specific styles
├── js/
│   ├── main.js                      # Theme management, utilities, toast
│   ├── auth.js                      # Authentication (login/signup)
│   └── dashboard.js                 # Dashboard functionality
├── images/
│   ├── README.md                    # Image placement instructions
│   └── voice2sign.png               # Logo (add this)
├── assets/
│   └── README.md                    # Additional assets guide
├── desktop.ini                      # Windows metadata file
└── .                                # Extend with backend or deployment files
```

---

## 🎨 Design System

### Color Palette
- **Light Mode**: Pure white (#FFFFFF) background, black (#000000) text
- **Dark Mode**: Near black (#0A0A0A) background, white (#FFFFFF) text
- **Accent**: Skin tone (#D4A574) - warm, accessible
- **Borders**: Subtle grays (#E5E5E5 light, #262626 dark)

### Typography
- **Font**: Work Sans (Google Fonts)
- **Sizes**: 52px (hero), 32px (title), 15px (body)
- **Weights**: 400 (regular), 500 (medium), 600 (semibold), 700 (bold)

### Spacing
- **Base unit**: 4px grid system
- **Common**: 8px, 12px, 16px, 20px, 24px, 32px, 48px

---

## 🚀 Quick Start

### 1. Setup Files

Place your logo at:
```
images/voice2sign.png (32×32px or larger)
```

If you don't have a logo yet, the pages will work fine - just showing the text "Voice2Sign".

### 2. Open in Browser

Simply open any HTML file:
```bash
# Login page (main entry)
open index.html

# Or signup
open signup.html

# Or dashboard
open dashboard.html
```

### 3. Test Features

**Theme Toggle:**
- Click moon/sun icon in header
- Smooth 0.4s transition between light/dark

**Login:**
- Social login buttons (Google, Facebook)
- Email/password form
- Password visibility toggle
- "Remember me" checkbox

**Dashboard:**
- Pin/unpin conversations
- Delete conversations
- Mode toggle (Hearing/Deaf)
- Theme toggle in sidebar

---

## ✨ Key Features

### Smooth Theme Transitions

**Implemented in `css/main.css`:**
```css
/* Smooth theme transition for all elements */
* {
    transition: background-color 0.4s cubic-bezier(0.4, 0, 0.2, 1),
                border-color 0.4s cubic-bezier(0.4, 0, 0.2, 1),
                color 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
```

**Duration:** 0.4 seconds (configurable via CSS variable)
**Timing:** Smooth cubic-bezier easing
**Elements:** All backgrounds, borders, text colors smoothly animate

### Separated Architecture

**HTML** - Structure only, no inline styles
**CSS** - All styling in separate files
**JavaScript** - All logic in separate files

Benefits:
- ✅ Easy to maintain
- ✅ Easy to update colors/styling
- ✅ Easy to add new features
- ✅ Clean code separation
- ✅ Ready for backend integration

---

## 🔧 File Descriptions

### CSS Files

**main.css** (Core Styles)
- CSS variables for themes
- Base styles and resets
- Common components (buttons, forms, cards)
- Utility classes
- Smooth theme transitions
- Responsive breakpoints

**login.css** (Login Page)
- Hero section styles
- Login card layout
- Features list
- Responsive grid
- Page-specific animations

**dashboard.css** (Dashboard)
- Sidebar navigation
- Chat interface
- Message bubbles
- Input controls
- Welcome screen
- Toast notifications

### JavaScript Files

**main.js** (Core Utilities)
- `ThemeManager` - Theme switching with smooth transitions
- `Toast` - Notification system
- `Utils` - Helper functions (debounce, scroll, etc.)

**auth.js** (Authentication)
- `togglePassword()` - Password visibility
- `checkPasswordStrength()` - Password strength meter
- `handleLogin()` - Login form submission
- `handleSignup()` - Signup form submission
- `loginWithGoogle/Facebook()` - Social auth
- `selectUserType()` - User type selection

**dashboard.js** (Dashboard)
- `switchMode()` - Toggle Hearing/Deaf mode
- `handleInput()` - Microphone/camera controls
- `addUserMessage()` - Display user messages
- `addAssistantMessage()` - Display AI responses
- `togglePin()` - Pin/unpin conversations
- `deleteChat()` - Delete conversations
- `exampleHearing/Deaf()` - Demo interactions

---

## 🎯 Backend Integration (Python)

### Recommended Structure

```
voice2sign_backend/
├── app.py                  # Flask/FastAPI main app
├── api/
│   ├── auth.py            # Authentication endpoints
│   ├── translation.py     # Translation endpoints
│   └── user.py            # User management endpoints
├── models/
│   ├── user.py            # User model
│   └── conversation.py    # Conversation model
├── services/
│   ├── speech_to_text.py  # Whisper API integration
│   ├── sign_recognition.py # MediaPipe/TensorFlow
│   └── text_to_sign.py    # Sign generation
├── utils/
│   └── helpers.py
└── requirements.txt
```

### API Endpoints to Create

```python
# Authentication
POST /api/auth/login
POST /api/auth/signup
POST /api/auth/logout
POST /api/auth/social (Google/Facebook OAuth)

# Translation
POST /api/translate/speech-to-sign
POST /api/translate/sign-to-text
GET  /api/translate/history

# User
GET  /api/user/profile
PUT  /api/user/profile
GET  /api/user/conversations
POST /api/user/conversations/:id/pin
DELETE /api/user/conversations/:id
```

### Frontend Integration Points

**In `auth.js`:**
```javascript
// Change this:
setTimeout(() => {
    window.location.href = 'dashboard.html';
}, 1200);

// To this:
fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        localStorage.setItem('token', data.token);
        window.location.href = 'dashboard.html';
    }
});
```

**In `dashboard.js`:**
```javascript
// Add API calls for translation
async function translateSpeechToSign(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob);
    
    const response = await fetch('/api/translate/speech-to-sign', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
    });
    
    return await response.json();
}
```

---

## 🛠️ Configuration

### Theme Transition Speed

Edit in `css/main.css`:
```css
:root {
    --theme-transition-duration: 0.4s;  /* Change to 0.2s for faster, 0.6s for slower */
}
```

### Color Customization

Edit in `css/main.css`:
```css
:root {
    --accent: #D4A574;  /* Change to your accent color */
    --accent-hover: #C89563;
    --accent-light: #F5EDE4;
}
```

### Font Customization

Edit in HTML `<head>`:
```html
<!-- Change Work Sans to another font -->
<link href="https://fonts.googleapis.com/css2?family=Your+Font:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

Then update in `css/main.css`:
```css
body {
    font-family: 'Your Font', sans-serif;
}
```

---

## 📱 Responsive Design

All pages are fully responsive:

- **Desktop** (1024px+): Full split layouts, sidebar visible
- **Tablet** (640-1024px): Stacked layouts, adjusted spacing
- **Mobile** (<640px): Single column, overlay sidebar, larger touch targets

---

## ♿ Accessibility Features

- ✅ Proper semantic HTML
- ✅ ARIA labels on interactive elements
- ✅ Keyboard navigation support
- ✅ Focus indicators
- ✅ Color contrast WCAG AAA compliant
- ✅ Screen reader compatible

---

## 🔍 Browser Support

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

---

## 📝 To-Do List

### Frontend
- [ ] Create `signup.html` (similar to index.html)
- [ ] Create `css/signup.css`
- [ ] Add settings page
- [ ] Add profile page
- [ ] Add password strength indicator styles
- [ ] Add loading states for all async actions

### Backend (Python)
- [ ] Set up Flask/FastAPI server
- [ ] Create authentication endpoints
- [ ] Integrate Whisper API (speech-to-text)
- [ ] Integrate MediaPipe (sign recognition)
- [ ] Create sign language generation API
- [ ] Set up database (PostgreSQL/MongoDB)
- [ ] Add session management
- [ ] Add rate limiting
- [ ] Add CORS headers

### DevOps
- [ ] Set up environment variables
- [ ] Create Docker containers
- [ ] Set up CI/CD pipeline
- [ ] Configure HTTPS/SSL
- [ ] Set up error logging
- [ ] Add analytics

---

## 🎓 Development Tips

### Testing Theme Transitions

1. Open browser DevTools (F12)
2. Open `css/main.css`
3. Change `--theme-transition-duration` value
4. Toggle theme to see effect
5. Experiment with different timing functions

### Adding New Pages

1. Copy `index.html` structure
2. Create new CSS file in `css/`
3. Link CSS in HTML `<head>`
4. Create corresponding JS file if needed
5. Follow existing naming conventions

### Debugging

**Theme Issues:**
- Check `data-theme` attribute on `<html>`
- Verify CSS variables are defined
- Check browser console for errors

**JavaScript Issues:**
- Check browser console (F12 → Console)
- Ensure scripts are loaded in correct order
- Verify function names match HTML `onclick` attributes

---

## 📞 Support

For issues or questions:
1. Check browser console for errors
2. Verify all files are in correct locations
3. Ensure file paths are correct
4. Test in different browsers

---

## 📄 License

This project is part of a capstone project.

---

**Version**: 1.0  
**Last Updated**: March 2026  
**Status**: Ready for Backend Integration
