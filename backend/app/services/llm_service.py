import json
from typing import Iterator

from app.core.config import settings


def _groq_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }


def _groq_generate(prompt: str) -> str:
    # Using Groq's OpenAI-compatible endpoint
    # POST /chat/completions
    import urllib.request

    url = f"{settings.GROQ_BASE_URL}/chat/completions"
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "stream": False,
    }

    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=_groq_headers(),
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        print("Groq generate HTTPError", {
            "status": e.code,
            "url": url,
            "model": settings.GROQ_MODEL,
            "response": err_body,
        })
        raise


    data = json.loads(body)

    # OpenAI format: choices[0].message.content
    return data["choices"][0]["message"]["content"]


def _groq_stream(prompt: str) -> Iterator[str]:
    # Stream via chunked response (SSE-ish). We'll parse lines that contain data.
    import urllib.request

    url = f"{settings.GROQ_BASE_URL}/chat/completions"
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "stream": True,
    }

    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=_groq_headers(),
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            # Read line-by-line to handle streaming.
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                # Expected: data: {...}
                if line.startswith("data:"):
                    data_str = line[len("data:") :].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        data = json.loads(data_str)
                    except Exception:
                        continue

                    delta = (
                        data.get("choices", [{}])[0]
                        .get("delta", {})
                    )
                    content = delta.get("content")
                    if content:
                        yield content

    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        print("Groq stream HTTPError", {
            "status": e.code,
            "url": url,
            "model": settings.GROQ_MODEL,
            "response": err_body,
        })
        raise





def _gemini_headers(api_key: str) -> dict:
    # API key is passed as query param in this implementation.
    return {"Content-Type": "application/json"}


def _gemini_generate(prompt: str) -> str:
    """Generate using Google Gemini.

    Uses Generative Language API:
    POST /models/{model}:generateContent?key={api_key}

    Note: We use a non-stream request here; stream fallback handled in stream_answer.

    Model fallback:
    If the current model (settings.GEMINI_MODEL) fails, retry with other allowed Gemini model options.
    """
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    import urllib.parse
    import urllib.request

    allowed_models = [
        # prefer current model first
        settings.GEMINI_MODEL,
        "gemini-2.0-flash",
        "gemini-2.0-flash-001",
        "gemini-2.0-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ]

    # de-dup while preserving order
    models: list[str] = []
    seen = set()
    for m in allowed_models:
        if m and m not in seen:
            models.append(m)
            seen.add(m)

    last_exc: Exception | None = None

    for model in models:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            f"?key={urllib.parse.quote(settings.GEMINI_API_KEY)}"
        )

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            # keep consistent with groq-ish temperature
            "generationConfig": {"temperature": 0.2},
        }

        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=_gemini_headers(settings.GEMINI_API_KEY),
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")

            data = json.loads(body)

            # Expected structure:
            # candidates[0].content.parts[0].text
            candidates = data.get("candidates") or []
            if not candidates:
                raise RuntimeError("Gemini response missing candidates")

            content = candidates[0].get("content") or {}
            parts = content.get("parts") or []
            text_parts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
            text = "".join(text_parts).strip()

            if not text:
                # some responses use a different shape; fall back to raw
                raise RuntimeError("Gemini response missing text parts")

            return text

        except Exception as e:
            last_exc = e
            # Keep existing logging behavior style, but update model.
            if isinstance(e, urllib.error.HTTPError):
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                print(
                    "Gemini generate HTTPError",
                    {
                        "status": e.code,
                        "url": url,
                        "model": model,
                        "response": err_body,
                    },
                )
            else:
                # non-HTTPError exceptions also get surfaced after trying all models
                pass

    # If we get here, all model attempts failed.
    if last_exc:
        raise last_exc
    raise RuntimeError("Gemini request failed with no specific exception")



def _gemini_stream(prompt: str) -> Iterator[str]:
    """Stream using Gemini if possible.

    The Gemini API streaming format can be more complex; to keep the backend robust,
    we fallback to non-stream generation while still yielding a single chunk.
    """
    text = _gemini_generate(prompt)
    if text:
        yield text


def generate_answer(prompt: str) -> str:
    """Try Groq first; if it fails, fall back to Gemini."""
    groq_key_present = bool(settings.GROQ_API_KEY)

    if groq_key_present:
        try:
            return _groq_generate(prompt)
        except Exception:
            # fall through to Gemini
            pass

    # Gemini fallback
    return _gemini_generate(prompt)


def stream_answer(prompt: str):
    """Try Groq streaming first; if it fails, fall back to Gemini.

    If both fail, yield a short fallback so the websocket stays alive.
    """
    if settings.GROQ_API_KEY:
        try:
            for token in _groq_stream(prompt):
                yield token
            return
        except Exception:
            # fall through to Gemini
            pass

    if settings.GEMINI_API_KEY:
        try:
            for chunk in _gemini_stream(prompt):
                # Gemini streaming fallback may yield once with whole text
                yield chunk
            return
        except Exception:
            pass

    # last resort
    yield "Sorry—both Groq and Gemini requests failed." 




