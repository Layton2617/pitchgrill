# Free-demo proxy (optional)

Lets visitors run **one AI analysis without their own Anthropic key**, by holding *your* key in a Cloudflare Worker. The worker — not the caller — builds the prompt, so the key can only ever run a pitchgrill analysis, and it's hard-capped per IP and per day so a public endpoint can't run up your bill.

You don't need this to ship pitchgrill. The site works fully without it (checklist + "grade your numbers" + bring-your-own-key analysis). This only adds the keyless demo run.

## Cost & abuse — read first

- Every demo run calls Claude on **your** key and **costs you money**. With the defaults (`claude-sonnet-4-6`, `max_tokens: 1500`, trimmed KB) a run is roughly **$0.02–0.10**.
- Caps are enforced in the worker: **3 runs / IP / day** and **100 runs / day total** (`PER_IP_PER_DAY`, `GLOBAL_PER_DAY` in `wrangler.toml`). At the global cap, worst case is ~**$10/day**. Lower the caps, or switch `MODEL` to `claude-haiku-4-5`, to cut cost.
- Caps are best-effort (IP-based), not a hard billing limit. Also set a **spend limit on your Anthropic account** as the real backstop.

## Deploy (Cloudflare, free tier)

```bash
npm install -g wrangler
cd serverless
wrangler login                          # opens a browser

# 1. create the rate-limit KV store, paste the printed id into wrangler.toml (id = "...")
wrangler kv namespace create RL

# 2. store your Anthropic key as a secret (not in any file)
wrangler secret put ANTHROPIC_API_KEY   # paste sk-ant-...

# 3. ship it
wrangler deploy
```

`wrangler deploy` prints your worker URL, e.g. `https://pitchgrill-demo.<you>.workers.dev`.

## Turn it on in the page

Edit `docs/index.html`, set the one marked line to your worker URL:

```js
const DEMO_ENDPOINT = "https://pitchgrill-demo.<you>.workers.dev"; /* free-demo worker */
```

Commit and push. The page now shows a **"Run AI analysis — free demo, no key"** button. Leave `DEMO_ENDPOINT = ""` to keep the demo off.

## Notes

- `ALLOWED_ORIGIN` locks CORS to your Pages origin so other sites can't borrow your worker.
- The worker fetches `KB_URL` (your published `kb.json`) and caches it at the edge, so it always reflects the latest KB.
- To disable instantly: set `DEMO_ENDPOINT = ""` and push, or `wrangler delete`.
