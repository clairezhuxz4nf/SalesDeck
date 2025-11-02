# OAuth Authentication Debugging Guide

## What I Fixed:
1. ✅ Changed redirect URL from `/dashboard` to `/` (root)
2. ✅ Improved session_id detection using `window.location.hash`
3. ✅ Added detailed console logging
4. ✅ Added backend logging for session creation
5. ✅ Fixed Authorization header support

## How to Test:

### Step 1: Click "Get Started with Google"
- You should be redirected to: `https://auth.emergentagent.com/?redirect=https://salesdeck-creator.preview.emergentagent.com/`

### Step 2: After Google Authentication
- You should be redirected back to: `https://salesdeck-creator.preview.emergentagent.com/#session_id=XXXXXXXXX`
- **IMPORTANT**: The URL must have `#session_id=...` in it

### Step 3: Check Browser Console
Open Developer Tools (F12) and check Console tab for:
```
Session ID detected, processing... XXXX...
Session created successfully: {success: true, session_token: "..."}
Successfully logged in!
```

### Step 4: Check if you're redirected to Dashboard
- If successful, you'll be redirected to `/dashboard`
- You should see your name in the top right corner

## Troubleshooting:

### Issue: No `#session_id` in URL after OAuth
**Possible causes:**
- Emergent Auth service issue
- Incorrect redirect URL format

**Solution:**
Check the actual URL you're redirected to. It MUST contain `#session_id=`

### Issue: Session ID detected but authentication fails
**Check backend logs:**
```bash
tail -f /var/log/supervisor/backend.err.log | grep -i session
```

You should see:
```
Creating session for session_id: XXXX...
User data retrieved: your@email.com
Session created successfully for user: your@email.com
Cookie set successfully
```

### Issue: Cookie not being set
**Possible causes:**
- Browser blocking third-party cookies
- SameSite=None not working

**Solution:**
1. Check browser dev tools > Application > Cookies
2. Look for `session_token` cookie on `salesdeck-creator.preview.emergentagent.com`
3. If missing, try logging in again

### Manual Test:
You can manually test the session endpoint:
```bash
curl -X POST "https://salesdeck-creator.preview.emergentagent.com/api/auth/session" \
  -F "session_id=YOUR_SESSION_ID_HERE" \
  -v
```

Look for `Set-Cookie: session_token=...` in the response headers.
