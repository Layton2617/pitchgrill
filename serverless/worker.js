// pitchgrill free-demo proxy (Cloudflare Worker).
//
// Holds YOUR Anthropic key server-side so visitors can run one AI analysis
// without their own key. Hard-capped per IP and globally per day so a public
// endpoint can't run up your bill. The worker — not the caller — builds the
// prompt, so the key can only ever be used for a pitchgrill analysis.
//
// Secrets / vars (see wrangler.toml + README):
//   ANTHROPIC_API_KEY  (secret)   your key
//   RL                 (KV)       rate-limit counters
//   ALLOWED_ORIGIN     (var)      e.g. https://layton2617.github.io
//   KB_URL             (var)      e.g. https://layton2617.github.io/pitchgrill/kb.json
//   MODEL              (var)      default claude-sonnet-4-6
//   PER_IP_PER_DAY     (var)      default 3
//   GLOBAL_PER_DAY     (var)      default 100

const SYSTEM =
  "You are a notoriously skeptical early-stage investor doing pre-investment diligence. " +
  "Below is a founder's pitch deck and a structured knowledge base (red flags with thresholds, " +
  "stage-specific grilling questions, a data-room checklist). Your job is NOT to score the company " +
  "or predict odds of success. Surface the losing moves: check the deck strictly against the " +
  "specific red flags and thresholds in the knowledge base.\n\n" +
  "Output three markdown sections:\n" +
  "1. Red flags hit — for each, name the exact line/number in the deck that triggers which red flag, " +
  "cite the threshold, mark severity. Do not invent hits.\n" +
  "2. You will be asked — the questions most lethal for this deck, and the weak answer the founder will give.\n" +
  "3. Data-room gaps — documents this deck doesn't show that diligence will demand.\n\n" +
  "Use only the knowledge base and the deck.";

const CAPS = { red_flags: 15, grilling: 10, data_room: 20 };
const MAX_DECK_CHARS = 60000;
const MAX_PDF_BYTES = 8 * 1024 * 1024;

let KB_CACHE = null;

const stageMatch = (it, s) => !it.stage || !it.stage.length || it.stage.includes(s);
const wedgeMatch = (it, w) => { const iw = it.wedge || "general"; return iw === "general" || iw === w; };
const sectorMatch = (it, sec) => { const s = it.sector; if (!s) return true; if (!sec) return false; return s === sec; };

function pick(kb, bucket, { stage, wedge, sector }) {
  return (kb[bucket] || [])
    .filter(it => stageMatch(it, stage) && wedgeMatch(it, wedge) && sectorMatch(it, sector))
    .slice(0, CAPS[bucket])
    .map(it => {
      const o = { ...it };
      delete o.detect; delete o.sources; delete o.id; // trim tokens
      return o;
    });
}

function corsHeaders(origin, allowed) {
  return {
    "Access-Control-Allow-Origin": origin === allowed ? origin : allowed,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
    "Vary": "Origin",
  };
}

const reply = (obj, status, headers) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json", ...headers } });

export default {
  async fetch(req, env) {
    const allowed = env.ALLOWED_ORIGIN || "*";
    const cors = corsHeaders(req.headers.get("Origin") || "", allowed);

    if (req.method === "OPTIONS") return new Response(null, { headers: cors });
    if (req.method !== "POST") return reply({ error: "POST only" }, 405, cors);

    // --- rate limit ---
    const perIp = parseInt(env.PER_IP_PER_DAY || "3", 10);
    const global = parseInt(env.GLOBAL_PER_DAY || "100", 10);
    const ip = req.headers.get("CF-Connecting-IP") || "anon";
    const day = new Date().toISOString().slice(0, 10);
    const gk = `g:${day}`, ik = `i:${ip}:${day}`;
    if (env.RL) {
      const [gc, ic] = await Promise.all([env.RL.get(gk), env.RL.get(ik)]);
      if (+ic >= perIp) return reply({ error: "You've used today's free demo runs on this network. Add your own Anthropic key above for unlimited runs." }, 429, cors);
      if (+gc >= global) return reply({ error: "Today's shared free-demo budget is used up. Add your own Anthropic key above to run now." }, 429, cors);
      await Promise.all([
        env.RL.put(gk, String(+gc + 1), { expirationTtl: 172800 }),
        env.RL.put(ik, String(+ic + 1), { expirationTtl: 172800 }),
      ]);
    }

    // --- input ---
    let body;
    try { body = await req.json(); } catch { return reply({ error: "bad json" }, 400, cors); }
    const { stage = "seed", sector = "", wedge = "general", deck = "", pdfBase64 = "" } = body;
    if (!deck && !pdfBase64) return reply({ error: "Add your deck (text or a PDF) first." }, 400, cors);
    if (deck.length > MAX_DECK_CHARS) return reply({ error: "Deck text too long for the free demo. Trim it or add your own key." }, 413, cors);
    if (pdfBase64 && pdfBase64.length > MAX_PDF_BYTES * 1.37) return reply({ error: "PDF too large for the free demo. Use a smaller file or your own key." }, 413, cors);

    // --- KB ---
    try {
      if (!KB_CACHE) {
        const r = await fetch(env.KB_URL, { cf: { cacheTtl: 600, cacheEverything: true } });
        KB_CACHE = await r.json();
      }
    } catch { return reply({ error: "knowledge base unavailable" }, 502, cors); }

    const subset = {
      red_flags: pick(KB_CACHE, "red_flags", { stage, wedge, sector }),
      grilling: pick(KB_CACHE, "grilling", { stage, wedge, sector }),
      data_room: pick(KB_CACHE, "data_room", { stage, wedge, sector }),
    };
    const kbText = "## Knowledge base (your checklist)\n```json\n" + JSON.stringify(subset) + "\n```";
    const content = pdfBase64
      ? [
          { type: "document", source: { type: "base64", media_type: "application/pdf", data: pdfBase64 } },
          { type: "text", text: kbText + "\n\nThe deck is the attached PDF. Analyze it against the knowledge base." },
        ]
      : kbText + "\n\n## Deck\n" + deck;

    // --- model call ---
    const ar = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-api-key": env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: env.MODEL || "claude-sonnet-4-6",
        max_tokens: 1500,
        system: SYSTEM,
        messages: [{ role: "user", content }],
      }),
    });
    const data = await ar.json();
    if (!ar.ok) return reply({ error: (data.error && data.error.message) || "model error" }, 502, cors);
    const text = (data.content || []).filter(b => b.type === "text").map(b => b.text).join("");
    return reply({ analysis: text }, 200, cors);
  },
};
