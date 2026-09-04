# Instagram Connection Setup Guide

This guide walks through setting up Instagram OAuth integration with the Meta Developer Platform.

## Prerequisites

- Instagram Business or Creator account
- Facebook Page linked to your Instagram account
- Meta Developer account
- Internet connection

---

## Part 1: Meta Developer App Setup

### Step 1: Create Meta Developer Account

1. Go to: https://developers.facebook.com/
2. Click "Get Started"
3. Log in with your Facebook account
4. Complete the developer registration

### Step 2: Create a New App

1. Go to: https://developers.facebook.com/apps
2. Click "Create App"
3. Select **"Business"** as app type
4. Click "Next"

### Step 3: Configure App Details

Fill in:

- **App Name**: "Instagram SEO Manager" (or your choice)
- **App Contact Email**: Your email
- **Business Account**: Select or create one

Click "Create App"

### Step 4: Add Instagram Basic Display Product

1. In your app dashboard, scroll to "Add Products"
2. Find **"Instagram Basic Display"**
3. Click "Set Up"

### Step 5: Configure Instagram Basic Display

1. Go to: Settings > Basic Display
2. Scroll to "User Token Generator"
3. Click "Add or Remove Instagram Testers"
4. Add your Instagram account as a tester
5. Accept the invitation in your Instagram app:
   - Open Instagram mobile app
   - Go to Settings > Apps and Websites > Tester Invites
   - Accept the invite

### Step 6: Get App Credentials

1. Go to: Settings > Basic
2. Copy these values:
   - **App ID**
   - **App Secret** (click "Show")

### Step 7: Configure OAuth Redirect URIs

1. Go to: Instagram Basic Display > Settings
2. Under "OAuth Redirect URIs", add:
   ```
   http://localhost:8000/social-accounts/callback
   ```
3. Click "Save Changes"

### Step 8: Configure Deauthorize and Data Deletion URLs

Add these (can be the same URL):

```
http://localhost:8000/webhooks/instagram/deauthorize
http://localhost:8000/webhooks/instagram/data-deletion
```

---

## Part 2: App Configuration

### Step 1: Update Environment Variables

Edit `D:\Instagram SEO\.env`:

```env
# Instagram OAuth
INSTAGRAM_APP_ID=your_app_id_here
INSTAGRAM_APP_SECRET=your_app_secret_here
INSTAGRAM_REDIRECT_URI=http://localhost:8000/social-accounts/callback
```

Replace `your_app_id_here` and `your_app_secret_here` with your actual credentials.

### Step 2: Restart Backend

```cmd
# Stop the backend (Ctrl+C in the terminal)
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Part 3: Connect Instagram Account

### Step 1: Open the Application

1. Go to: http://localhost:5174
2. Log in to the app
3. Navigate to **Settings** page

### Step 2: Connect Instagram

1. Click "Connect Instagram Account"
2. You'll be redirected to Instagram
3. Log in with your Instagram Business/Creator account
4. Grant permissions to the app
5. You'll be redirected back to the app

### Step 3: Verify Connection

In the Settings page, you should see:

- ✅ Connected Instagram account
- Username displayed
- Last sync time

---

## Part 4: Advanced Setup (Instagram Graph API)

For advanced features (posting, comments, analytics), you need the Instagram Graph API.

### Step 1: Switch to Instagram Graph API

1. In Meta Developer dashboard, add product: **"Instagram"** (not Basic Display)
2. This requires:
   - Facebook Page linked to Instagram
   - Business verification
   - App Review for permissions

### Step 2: Request Permissions

Required permissions:

- `instagram_basic`
- `instagram_content_publish`
- `instagram_manage_comments`
- `instagram_manage_insights`

### Step 3: App Review Process

1. Submit app for review with:

   - Use case description
   - Screen recording of your app
   - Privacy Policy URL
   - Terms of Service URL

2. Wait 3-5 business days for approval

3. Once approved, update permissions in Settings page

---

## Part 5: Testing & Verification

### Step 1: Test Authentication

```python
# Run this test script:
# D:\Instagram SEO\backend\test_instagram_connection.py

import requests
import os
from dotenv import load_dotenv

load_dotenv()

app_id = os.getenv("INSTAGRAM_APP_ID")
redirect_uri = os.getenv("INSTAGRAM_REDIRECT_URI")

print(f"App ID: {app_id}")
print(f"Redirect URI: {redirect_uri}")
print(f"\nOAuth URL:")
print(f"https://api.instagram.com/oauth/authorize?client_id={app_id}&redirect_uri={redirect_uri}&scope=user_profile,user_media&response_type=code")
```

### Step 2: Manual Token Test

1. Copy the OAuth URL from above
2. Open in browser
3. Authorize the app
4. Copy the `code` from the redirect URL
5. Test token exchange in the app

---

## Troubleshooting

### Error: "Redirect URI Mismatch"

- Ensure redirect URI in Meta dashboard **exactly** matches `.env` file
- No trailing slashes
- Must be `http://localhost:8000/social-accounts/callback`

### Error: "Invalid Client ID"

- Double-check `INSTAGRAM_APP_ID` in `.env`
- Ensure app is not in Development Mode for production use

### Error: "User Not a Tester"

1. Add yourself as a tester in Meta Developer dashboard
2. Accept invitation in Instagram mobile app
3. Wait 5-10 minutes for propagation

### Error: "This app is not available in your country"

- Ensure your Meta Developer account is verified
- Check app is in Development Mode
- Add your country to allowed locations

### Permissions Denied

- Request only permissions you actually need
- Provide clear use case in app review
- Include privacy policy and terms

---

## Limitations

### Development Mode (Before App Review):

- ✅ Connect your own Instagram account
- ✅ Test all features with your account
- ✅ Up to 5 tester accounts
- ❌ Public users cannot connect
- ❌ Limited API rate limits

### After App Review:

- ✅ Public users can connect
- ✅ Full API rate limits
- ✅ All requested permissions active

---

## Production Deployment Notes

### Required Changes for Production:

1. **Update redirect URI** in both:

   - Meta Developer dashboard
   - `.env` file (use your production domain)

2. **Use HTTPS**:

   ```env
   INSTAGRAM_REDIRECT_URI=https://yourdomain.com/social-accounts/callback
   ```

3. **Configure webhooks** for real-time updates:

   ```env
   INSTAGRAM_WEBHOOK_VERIFY_TOKEN=your_random_verify_token_here
   ```

4. **Submit for App Review** with:
   - Production domain
   - Privacy policy at: https://yourdomain.com/privacy
   - Terms at: https://yourdomain.com/terms
   - Demo video showing all features

---

## Security Best Practices

### 1. Protect Secrets

Never commit credentials to Git:

```gitignore
# Already in .gitignore:
.env
*.key
*.pem
```

### 2. Rotate Secrets Regularly

Generate new `ENCRYPTION_KEY` for production:

```python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Use Environment Variables

For production, use environment variables instead of `.env` file.

### 4. Enable App Secret Proof

Add to `.env`:

```env
INSTAGRAM_USE_APP_SECRET_PROOF=true
```

---

## Rate Limits

Instagram API rate limits:

- **Development Mode**: 200 calls/hour
- **Live Mode**: Varies by endpoint (25-200 calls/hour)
- **User Token**: 4,800 calls/24 hours

The app automatically handles rate limiting with exponential backoff.

---

## Support Resources

- Meta Developer Docs: https://developers.facebook.com/docs/instagram-api
- Instagram Basic Display: https://developers.facebook.com/docs/instagram-basic-display-api
- Instagram Graph API: https://developers.facebook.com/docs/instagram-api
- Community Forum: https://developers.facebook.com/community/

---

## Next Steps

After connecting Instagram:

1. ✅ Test content upload in the app
2. ✅ Generate captions with AI
3. ✅ Schedule posts
4. ✅ Monitor comments
5. ✅ View analytics

Your Instagram is now integrated with the AI SEO & Social Media Manager!
