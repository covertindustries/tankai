# WhatsApp Bot — Setup Guide

Two provider options. **Twilio** is easier for development and testing.
**Meta Cloud API** is free for production (1,000 conversations/month free tier).

---

## Option A — Twilio (recommended for dev/test)

### 1. Create Twilio account
Go to https://twilio.com → sign up (free trial credit included).

### 2. Activate WhatsApp Sandbox
Console → Messaging → Try it out → Send a WhatsApp message.

You'll get a sandbox number (usually `+1 415 523 8886`).
Users join by texting `join [your-sandbox-word]` to that number.

### 3. Configure webhook
Console → Messaging → Settings → WhatsApp Sandbox Settings:
- **When a message comes in:** `https://yourdomain.com/webhook/whatsapp/twilio`
- Method: `HTTP POST`

### 4. Add to .env
```
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

### 5. Test
Text your sandbox number: `leather bag marrakech`

---

## Option B — Meta Cloud API (free production tier)

### 1. Create Meta Developer account
https://developers.facebook.com → Create App → Business type.

### 2. Add WhatsApp product
App Dashboard → Add Product → WhatsApp → Set Up.

### 3. Get credentials
WhatsApp → API Setup:
- Copy **Temporary access token** (or create permanent one)
- Copy **Phone Number ID**

### 4. Configure webhook
WhatsApp → Configuration → Webhook:
- **Callback URL:** `https://yourdomain.com/webhook/whatsapp/meta`
- **Verify token:** same string as `META_VERIFY_TOKEN` in your .env
- Subscribe to: `messages`

### 5. Add to .env
```
WHATSAPP_PROVIDER=meta
META_WHATSAPP_TOKEN=your_access_token
META_PHONE_NUMBER_ID=123456789
META_VERIFY_TOKEN=haggle_verify
```

### 6. Go live
Submit for WhatsApp Business API review (takes 1–3 days).
Free tier: 1,000 conversations/month. Paid: ~$0.005–0.07 per conversation.

---

## Exposing localhost for testing

Use ngrok to expose your local server:
```bash
ngrok http 8000
```
Copy the HTTPS URL and use it as your webhook base URL.

---

## Bot commands reference

| User texts | Bot does |
|---|---|
| `leather bag marrakech` | Search prices + fair wage context |
| `negotiate 600 MAD bag marrakech` | Full negotiation script |
| `ABC1234567` | Look up vendor story by code |
| `vendor` | Instructions for creating a vendor page |
| `help` | Show all commands |

---

## Production checklist

- [ ] HTTPS endpoint (required by both Twilio and Meta)
- [ ] `ANTHROPIC_API_KEY` set (for AI responses)
- [ ] Webhook URL registered with provider
- [ ] Signature verification enabled (Twilio: `verify_twilio_signature`)
- [ ] Rate limiting on webhook endpoint (prevent abuse)
- [ ] Error monitoring (Sentry or similar)
