"""Helper module for publishing battle card graphics to Twitter, Discord, and Telegram."""

import json
import mimetypes
import os
import urllib.request
import uuid


def send_to_discord(webhook_url: str, image_path: str, message: str = "") -> bool:
    """Sends the generated battle card to a Discord channel via Webhook.

    Requires no API keys - just a Discord Webhook URL.
    """
    if not webhook_url:
        print("[Discord] Brak podanego webhook_url.")
        return False

    if not os.path.exists(image_path):
        print(f"[Discord] Plik {image_path} nie istnieje.")
        return False

    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()

    # Message payload
    payload = {"content": message}
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="payload_json"\r\n\r\n')
    body.extend(json.dumps(payload).encode("utf-8"))
    body.extend(b"\r\n")

    # Image file
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    filename = os.path.basename(image_path)
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"

    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        f'Content-Disposition: form-data; name="files[0]"; filename="{filename}"\r\n'.encode()
    )
    body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode())
    body.extend(image_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "StreamBattleBot/1.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[Discord] Wysłano pomyślnie! Status: {resp.status}")
            return True
    except Exception as e:
        print(f"[Discord] Błąd wysyłania: {e}")
        return False


def send_to_telegram(
    bot_token: str, chat_id: str, image_path: str, caption: str = ""
) -> bool:
    """Sends the generated battle card to a Telegram chat/channel using Bot API."""
    if not bot_token or not chat_id:
        print("[Telegram] Wymagany bot_token i chat_id.")
        return False

    if not os.path.exists(image_path):
        print(f"[Telegram] Plik {image_path} nie istnieje.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()

    # chat_id
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="chat_id"\r\n\r\n')
    body.extend(str(chat_id).encode("utf-8"))
    body.extend(b"\r\n")

    # caption
    if caption:
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
        body.extend(caption.encode("utf-8"))
        body.extend(b"\r\n")

    # file
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    filename = os.path.basename(image_path)
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        f'Content-Disposition: form-data; name="photo"; filename="{filename}"\r\n'.encode()
    )
    body.extend(b"Content-Type: image/png\r\n\r\n")
    body.extend(image_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[Telegram] Wysłano pomyślnie! Status: {resp.status}")
            return True
    except Exception as e:
        print(f"[Telegram] Błąd wysyłania: {e}")
        return False


def post_to_twitter(
    api_key: str,
    api_secret: str,
    access_token: str,
    access_token_secret: str,
    image_path: str,
    tweet_text: str,
) -> bool:
    """Posts a tweet with the image using Tweepy (if installed and keys provided)."""
    try:
        import tweepy
    except ImportError:
        print("[Twitter] Aby tweetować, zainstaluj tweepy: pip install tweepy")
        return False

    try:
        # OAuth 1.0a required for media upload on Twitter v1.1 endpoint
        auth = tweepy.OAuth1UserHandler(
            api_key, api_secret, access_token, access_token_secret
        )
        api = tweepy.API(auth)
        media = api.media_upload(filename=image_path)

        # Post tweet with Twitter API v2 Client
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )
        response = client.create_tweet(text=tweet_text, media_ids=[media.media_id])
        print(f"[Twitter] Opublikowano tweeta! ID: {response.data['id']}")
        return True
    except Exception as e:
        print(f"[Twitter] Błąd publikacji tweeta: {e}")
        return False
