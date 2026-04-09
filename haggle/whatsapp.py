"""WhatsApp bot for Haggle.

Supports two providers:
  - Twilio WhatsApp Sandbox / Business (WHATSAPP_PROVIDER=twilio)
  - Meta Cloud API / WhatsApp Business Platform (WHATSAPP_PROVIDER=meta)

Commands users can send:
  leather bag marrakech           → price search
  negotiate 600 MAD bag marrakech → negotiation script
  vendor                          → how to create a vendor story
  ABC1234567                      → look up a vendor story by code
  help                            → show commands
"""

import os
import re
import hmac
import hashlib
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

PROVIDER = os.getenv("WHATSAPP_PROVIDER", "twilio").lower()

# Twilio config
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# Meta Cloud API config
META_ACCESS_TOKEN    = os.getenv("META_WHATSAPP_TOKEN", "")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")
META_VERIFY_TOKEN    = os.getenv("META_VERIFY_TOKEN", "haggle_verify")

# ── City / country lookup ──────────────────────────────────────────────────────

CITY_COUNTRY = {
    "bangkok": "Thailand",    "chiang mai": "Thailand",   "phuket": "Thailand",
    "marrakech": "Morocco",   "fez": "Morocco",           "casablanca": "Morocco",
    "istanbul": "Turkey",     "ankara": "Turkey",         "cappadocia": "Turkey",
    "delhi": "India",         "mumbai": "India",          "jaipur": "India",
    "bali": "Indonesia",      "jakarta": "Indonesia",     "yogyakarta": "Indonesia",
    "cairo": "Egypt",         "luxor": "Egypt",           "aswan": "Egypt",
    "mexico city": "Mexico",  "oaxaca": "Mexico",         "guadalajara": "Mexico",
    "hanoi": "Vietnam",       "ho chi minh city": "Vietnam", "hoi an": "Vietnam",
    "nairobi": "Kenya",       "cape town": "South Africa",
    "cusco": "Peru",          "lima": "Peru",
    "havana": "Cuba",         "singapore": "Singapore",
    "dubai": "UAE",           "abu dhabi": "UAE",
    "kathmandu": "Nepal",     "colombo": "Sri Lanka",
}

# ── Intent parsing ─────────────────────────────────────────────────────────────

NEGOTIATE_RE = re.compile(
    r'^negotiate\s+'
    r'(?P<price>\d+(?:\.\d+)?)\s*'
    r'(?P<currency>[A-Za-z]{2,4})\s+'
    r'(?P<item>.+?)\s+'
    r'(?P<city>[A-Za-z ]+?)$',
    re.IGNORECASE,
)

VENDOR_CODE_RE = re.compile(r'^[A-Z0-9]{10}$')


def parse_message(text: str) -> dict:
    """Parse incoming WhatsApp message into structured intent."""
    text = text.strip()
    lower = text.lower()

    # Help
    if lower in ("help", "hi", "hello", "start", "menu", "hola"):
        return {"intent": "help"}

    # Vendor signup
    if lower in ("vendor", "seller", "artisan", "i am a vendor", "vendedor"):
        return {"intent": "vendor_info"}

    # Negotiate: "negotiate 600 MAD leather bag marrakech"
    m = NEGOTIATE_RE.match(text)
    if m:
        city = m.group("city").strip().lower()
        return {
            "intent": "negotiate",
            "price": float(m.group("price")),
            "currency": m.group("currency").upper(),
            "item": m.group("item").strip().lower(),
            "city": city,
            "country": CITY_COUNTRY.get(city),
        }

    # Vendor code lookup: "ABC1234567"
    if VENDOR_CODE_RE.match(text.upper()):
        return {"intent": "vendor_lookup", "code": text.upper()}

    # Price search: "leather bag marrakech" or "silk scarf in bangkok"
    clean = re.sub(r'\b(in|at|for|the|a|an)\b', ' ', lower).strip()
    words = clean.split()
    if len(words) >= 2:
        # Try to match last 1-2 words as city
        for n_city_words in (2, 1):
            city_candidate = " ".join(words[-n_city_words:])
            if city_candidate in CITY_COUNTRY or _is_known_city(city_candidate):
                item_candidate = " ".join(words[:-n_city_words]).strip(" -,.")
                if item_candidate:
                    return {
                        "intent": "prices",
                        "item": item_candidate,
                        "city": city_candidate,
                        "country": CITY_COUNTRY.get(city_candidate),
                    }

    return {"intent": "unknown", "raw": text}


def _is_known_city(s: str) -> bool:
    """Loose check — if string looks like it might be a city."""
    # For simplicity, trust known cities only; fallback gracefully
    return s in CITY_COUNTRY


# ── Response builders ──────────────────────────────────────────────────────────

HELP_MSG = """🤝 *Haggle Bot* — Know what to pay at any market

*Commands:*
• `leather bag marrakech` — what others paid
• `negotiate 600 MAD bag marrakech` — get your script
• `[VENDOR_CODE]` — look up a vendor's craft story
• `vendor` — list your craft (for artisans)

⚖️ We show fair prices that protect vendors too.
Full app: haggle.app"""

VENDOR_INFO_MSG = """🎨 *Are you a market artisan?*

Create a free, anonymous craft page that customers can view before buying. No name. No address. Just your story.

To get started, visit:
👉 haggle.app/vendor

Your page shows:
• Your craft & how long it takes
• Materials you use
• Photos of your work
• A fair price context

Share your code with customers so they understand the value of what you make.

Free forever. Fully anonymous."""

UNKNOWN_MSG = """Not sure what you're looking for 🤔

Try:
• `leather bag marrakech`
• `negotiate 500 THB scarf bangkok`
• `help` for all commands

haggle.app"""


def build_price_reply(item: str, city: str, stats: dict, fair: dict, ai_text: str) -> str:
    """Format price search reply for WhatsApp."""
    if not stats:
        return (
            f"No data yet for *{item}* in *{city}* 📭\n\n"
            f"Be the first to submit a price at haggle.app\n\n"
            f"Or try a different item/city."
        )

    lines = [
        f"🤝 *{item.title()} · {city.title()}*\n",
        f"💰 What others paid (USD):",
        f"  Low: ${stats['low']:.0f}  |  Typical: ${stats['median']:.0f}  |  High: ${stats['high']:.0f}",
        f"  Based on {stats['count']} report{'s' if stats['count'] != 1 else ''}",
    ]

    if fair:
        lines += [
            f"\n⚖️ *Fair price: ~${fair['fair_price_usd']:.0f}+*",
            f"  {fair['country']} min wage: ~${fair['daily_wage_usd']:.0f}/day",
            f"  This item takes ~{fair['craft_hours']:.0f}h to make",
        ]

    lines += [f"\n{ai_text}"]
    lines += [f"\nhaggle.app 🌍"]

    return "\n".join(lines)


def build_negotiate_reply(
    item: str, city: str, price: float, currency: str, ai_text: str
) -> str:
    return f"💬 *Haggle Script — {item.title()} in {city.title()}*\n\nVendor asks: {price:.0f} {currency}\n\n{ai_text}\n\nhaggle.app 🤝"


def build_vendor_lookup_reply(story: dict) -> str:
    if not story:
        return "Vendor code not found. Check the code and try again.\n\nhaggle.app"

    photos = f"\n📸 {len(story.get('photo_paths', []))} photos" if story.get('photo_paths') else ""
    gen = f"\n👨‍👩‍👧 {story['generation']}" if story.get('generation') else ""
    time_made = f"\n⏱️ {story['time_to_make']}" if story.get('time_to_make') else ""
    materials = f"\n🧵 {story['materials']}" if story.get('materials') else ""

    return (
        f"🎨 *Vendor Story*\n"
        f"Craft: {story['craft'].title()}\n"
        f"City: {story['city'].title()}{gen}{time_made}{materials}{photos}\n\n"
        f"📖 {story.get('story', 'No story shared yet.')}\n\n"
        f"Views: {story.get('views', 0)} · haggle.app/vendor/{story['vendor_code']}"
    )


# ── Sending messages ──────────────────────────────────────────────────────────

async def send_message(to: str, body: str):
    """Send WhatsApp message via configured provider."""
    if PROVIDER == "meta":
        await _send_meta(to, body)
    else:
        await _send_twilio(to, body)


async def _send_twilio(to: str, body: str):
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print(f"[WhatsApp/Twilio] No credentials — would send to {to}:\n{body}")
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    async with httpx.AsyncClient() as client:
        await client.post(
            url,
            data={"From": TWILIO_FROM_NUMBER, "To": to, "Body": body},
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
        )


async def _send_meta(to: str, body: str):
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        print(f"[WhatsApp/Meta] No credentials — would send to {to}:\n{body}")
        return
    url = f"https://graph.facebook.com/v18.0/{META_PHONE_NUMBER_ID}/messages"
    async with httpx.AsyncClient() as client:
        await client.post(
            url,
            headers={"Authorization": f"Bearer {META_ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to.replace("whatsapp:", ""),
                "type": "text",
                "text": {"body": body},
            },
        )


# ── Signature verification ────────────────────────────────────────────────────

def verify_twilio_signature(auth_token: str, signature: str, url: str, params: dict) -> bool:
    """Verify Twilio webhook signature to prevent spoofing."""
    s = url + "".join(f"{k}{v}" for k, v in sorted(params.items()))
    expected = hmac.new(auth_token.encode(), s.encode(), hashlib.sha1).digest()
    import base64
    return hmac.compare_digest(
        base64.b64encode(expected).decode(),
        signature,
    )
