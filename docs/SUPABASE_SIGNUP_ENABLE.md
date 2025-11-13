# Enable User Signup in Supabase

## Problem

If you're seeing a `422` error with `signup_disabled` when users try to register, it means email/password signup is disabled in your Supabase project.

## Solution

### Step 1: Open Supabase Dashboard

1. Go to [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. Select your project: `nnmmhgnriisfsncphipd`

### Step 2: Enable Email Signup

1. Navigate to **Authentication** → **Providers** in the left sidebar
2. Find **Email** provider (should be at the top)
3. Click on **Email** to open settings
4. Ensure **Enable Email provider** is toggled **ON**
5. Under **Email Auth**, ensure **Enable email confirmations** is set according to your preference:
   - **OFF** = Users can sign in immediately after registration
   - **ON** = Users must verify their email before signing in

### Step 3: Verify Settings

1. Scroll down to **Email Templates** section
2. Ensure email templates are configured (or use defaults)
3. Click **Save** if you made any changes

### Step 4: Test Registration

1. Go to your registration page: `https://trdrhub.com/register`
2. Try registering a new user
3. If email confirmation is enabled, check the user's email inbox
4. If email confirmation is disabled, user should be logged in immediately

## Alternative: Enable Signup via API

If you prefer to enable signup programmatically, you can use the Supabase Management API:

```bash
curl -X PATCH 'https://api.supabase.com/v1/projects/nnmmhgnriisfsncphipd/auth/config' \
  -H 'Authorization: Bearer YOUR_SUPABASE_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "EXTERNAL_EMAIL_ENABLED": true,
    "MAILER_AUTOCONFIRM": true
  }'
```

## Troubleshooting

### Still Getting 422 Error?

1. **Check Project Settings**: Go to **Settings** → **API** and verify your project is active
2. **Check Rate Limits**: Ensure you haven't hit Supabase rate limits
3. **Check Email Domain**: If using custom email domains, ensure they're verified
4. **Check Auth Settings**: Verify **Authentication** → **Settings** → **Auth Providers** shows Email as enabled

### Email Confirmation Not Working?

1. Check **Authentication** → **Email Templates** for correct SMTP settings
2. Verify SMTP credentials in **Settings** → **Auth** → **SMTP Settings**
3. Check spam folder for confirmation emails
4. Review Supabase logs: **Logs** → **Auth Logs**

## Related Documentation

- [Supabase Auth Configuration](https://supabase.com/docs/guides/auth)
- [Email Provider Setup](https://supabase.com/docs/guides/auth/auth-email)
- [SMTP Configuration](https://supabase.com/docs/guides/auth/auth-smtp)

