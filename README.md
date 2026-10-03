# Subtitle AI Translator

A provider-independent, context-aware English -> Persian SRT translator designed for long files and technical educational subtitles.

## What it does

- Sends several subtitle blocks together so the model sees sentence context.
- Also sends a configurable number of previous and following subtitles as context.
- Preserves SRT numbers and timestamps in Python; the model never generates timestamps.
- Validates the model's JSON before writing anything.
- Writes **each translated subtitle to disk immediately** and calls `fsync()`.
- Maintains an atomic checkpoint after every written subtitle.
- Can recover from a crash and resume without throwing away completed work.
- If a request is too large or the model returns malformed/incomplete output, the batch can be split automatically and retried.
- Uses conservative token estimation and both item/character/context limits.
- Supports OpenAI-compatible APIs, Ollama, and a generic JSON HTTP adapter.
- Supports an optional second-pass AI review.
- Supports an optional SQLite translation memory keyed by source + context + glossary.
- Uses a glossary to keep technical terminology consistent.

## Installation

```bash
python -m venv .venv
```

Windows:

```cmd
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

Copy `config.example.json` to `config.json` and edit the provider/model.

For an API key, use the environment variable configured by `api_key_env`.

PowerShell example:

```powershell
$env:OPENAI_API_KEY="YOUR_KEY"
```

## Basic usage

```bash
python main.py input.srt -o output_fa.srt
```

Resume after an interruption:

```bash
python main.py input.srt -o output_fa.srt --resume
```

Use another provider defined in the config:

```bash
python main.py input.srt -o output_fa.srt --provider ollama
```

Check configuration without translating:

```bash
python main.py input.srt --dry-run
```

## Long subtitle files

The key safety settings are:

- `batch_max_items`: hard ceiling on subtitles per API call.
- `batch_max_chars`: hard ceiling on source characters per call.
- `context_window_tokens`: approximate model context limit.
- `max_output_tokens`: reserved output capacity.
- `chars_per_token_estimate`: conservative token estimate.
- `token_safety_factor`: extra safety margin.

The program does not rely on one of these limits alone. It stops adding subtitles when any safety limit is reached.

For a local 8B model, a conservative starting configuration is:

```json
"batch_max_items": 8,
"batch_max_chars": 6000,
"context_window_tokens": 8192,
"max_output_tokens": 2500
```

For a larger cloud model you can increase them after testing.

## What happens if the model hits the limit?

Suppose a batch contains 20 subtitles and the provider says the request is too large. The program does not throw away the job. It retries, then automatically splits the batch into smaller parts. A malformed JSON response or incomplete subtitle set can also trigger splitting when possible.

## Crash safety

The order is:

1. Ask the model for a batch.
2. Validate the full response.
3. Optionally run the second-pass review.
4. Write the first subtitle of the batch to the output file.
5. Flush + `fsync()` it.
6. Update the checkpoint atomically.
7. Continue to the next subtitle.

So a 5,000-subtitle file does not wait until the end to save the result.

On startup, the program also inspects the existing SRT output and removes an incomplete final block left by a crash, then resumes from the completed subtitle numbers.

## Provider independence

OpenAI-compatible services only require a base URL, API-key environment variable, and model name. This makes the same translator usable with many gateways and compatible APIs without changing the translation engine.

For a completely different JSON HTTP API, use `type: "http_json"` and configure `body_template` and `response_path`.

## Optional AI review pass

Set:

```json
"review": {
  "enabled": true,
  "retry_count": 1
}
```

The first model call translates the batch. The second call reviews the entire translated batch for meaning, Persian quality, terminology and context. The reviewed output is written only if it passes validation.

Because this costs an additional model call, it is disabled by default.

## Translation memory

The optional SQLite memory stores results keyed by:

- source subtitles
- previous/following context
- glossary
- translation style

Therefore the cache is context-aware instead of blindly reusing a translation for the same English sentence in a different place.

## Recommended project structure

```text
subtitle_ai_translator/
├── main.py
├── translator.py
├── prompt.py
├── validator.py
├── srt.py
├── checkpoint.py
├── translation_memory.py
├── glossary.json
├── config.example.json
├── requirements.txt
└── providers/
    ├── __init__.py
    ├── base.py
    ├── openai_compatible.py
    ├── ollama.py
    └── http_json.py
```

## Files created during translation

For `movie.srt` -> `movie_fa.srt` you will typically get:

```text
movie_fa.srt
movie_fa.srt.checkpoint.json
translation_memory.sqlite
```

After checking the final subtitle file, the checkpoint and memory database can be kept for future resumptions/reuse or deleted.

## Gemini API

This project has a dedicated native Gemini provider based on Google's current `google-genai` SDK. Google recommends the `google-genai` package over the legacy `google-generativeai` package, and Gemini supports structured JSON output through `response_mime_type` / `response_schema`. This project uses that structured-output path so the translator receives predictable `number` + `translation` objects. See the official Gemini documentation for the current API/SDK details.

Install:

```bash
pip install -U google-genai
```

Set the API key:

PowerShell:

```powershell
$env:GEMINI_API_KEY="YOUR_KEY"
```

Then configure:

```json
"gemini": {
  "type": "gemini",
  "api_key_env": "GEMINI_API_KEY",
  "model": "YOUR_GEMINI_MODEL",
  "timeout_seconds": 180,
  "structured_output": true
}
```

Run:

```bash
python main.py input.srt -o output_fa.srt --provider gemini
```

The Gemini provider is intentionally separate from the OpenAI-compatible provider. This avoids relying on an interoperability layer and lets the program use Gemini's native structured-output feature.
