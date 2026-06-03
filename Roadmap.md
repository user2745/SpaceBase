# SpaceBase Roadmap

> Last updated: 2026-06-02

## Architecture

| Priority | Item | Status | Description |
|----------|------|--------|-------------|
| 🔴 P0 | Producer-Consumer Decoupling | `PLANNED` | Refactor `launch()` to decouple LLM generation from the PostScheduler. Currently the scheduler is blocked until `generate_batch()` completes, which hangs when Ollama is slow. Move to an assembly-line model: a background Producer thread generates tweets one-at-a-time and pushes to a shared queue; the Scheduler thread pulls from the queue on its own timer. Neither blocks the other. |
| 🟡 P1 | RAG Pipeline | `PLANNED` | Add a Retrieval-Augmented Generation layer using ChromaDB + Ollama embeddings. Ingest NASA docs, SpaceX engineering specs, and Apollo mission transcripts. The AutoReplyEngine queries the vector DB before generating replies so responses are grounded in real technical data instead of hallucinated trivia. |
| 🟢 P2 | Graceful LLM Timeout | `PLANNED` | Add a hard timeout (e.g., 30s) to every Ollama HTTP call in `LLMPipeline.query()`. If the LLM hangs, return `None` and move on instead of blocking the thread indefinitely. |

## Content Quality

| Priority | Item | Status | Description |
|----------|------|--------|-------------|
| 🔴 P0 | Long-Form Educational Threads | `PLANNED` | Benchmark accounts like @AstronomyVibes pull 10K+ impressions with long-form, sourced, educational posts + images. Update the `Deep_Dive` archetype prompt to generate multi-paragraph, citation-backed content instead of one-liners. |
| 🟡 P1 | Image Quality Pipeline | `PLANNED` | Current `Visual_Hype` pulls random NASA images. Improve by scoring image relevance to the tweet topic, preferring high-resolution results, and caching previously used images to avoid repeats. |
| 🟡 P1 | LLM Prompt Library | `PLANNED` | Extract all hardcoded prompt strings into a separate `prompts.py` module. Makes A/B testing different tones trivial without touching engine logic. |

## Growth Mechanics

| Priority | Item | Status | Description |
|----------|------|--------|-------------|
| 🟡 P1 | DQN Reward Shaping | `PLANNED` | Current reward function uses raw X algorithm weights. Add a secondary reward signal for follower conversion rate (impressions → follows) to teach the DQN which content *converts*, not just which content gets engagement. |
| 🟢 P2 | Engagement Time Optimization | `PLANNED` | Track which posting hours yield the highest engagement and let the DQN learn optimal posting windows instead of using fixed intervals. |
| 🟢 P2 | Multi-Platform Syndication | `IDEA` | Port the engine to Bluesky (free API) and/or Threads. DQN tracks per-platform states independently. |

## Reliability

| Priority | Item | Status | Description |
|----------|------|--------|-------------|
| 🔴 P0 | Ghost Tweet Cleanup | `PLANNED` | Purge tweet IDs from the SQLite DB that received 403 errors and never actually posted. These pollute the MetricsCollector with false data and waste API calls on lookups that will always return `None`. |
| 🟡 P1 | Health Check Endpoint | `IDEA` | Expose a simple HTTP endpoint inside the container (e.g., Flask on port 8080) that returns queue depth, last post time, thread status, and DQN epsilon. Enables remote monitoring without SSH + docker logs. |
| 🟢 P2 | Auto-Restart on Hang | `IDEA` | Add a Docker healthcheck that pings the health endpoint. If no response for 5 minutes, Docker auto-restarts the container. |

---

## Completed

| Item | Date | Notes |
|------|------|-------|
| SQLite Migration | 2026-06-02 | Replaced CSV with `tweet_records.db` |
| 4-Hour Feedback Loop | 2026-06-02 | Shortened from 24h to 4h |
| X Algorithm Alignment | 2026-06-02 | Reward weights: RT 20x, BM 17x, RP 13.5x, LK 0.5x |
| NASA Image API | 2026-06-02 | `Visual_Hype` archetype fetches from NASA Image Library |
| Spaceflight News API | 2026-06-02 | `News_Break` archetype injects live headlines |
| Proactive Hunting | 2026-06-02 | `AutoReplyEngine.hunt_and_reply()` with `search_recent_tweets` |
| Spam Filter | 2026-06-02 | `-has:links lang:en` query filter |
| LLM Short-Term Memory | 2026-06-02 | `_get_recent_history()` prevents fact repetition |
| Throttle Limiter | 2026-06-02 | Max 1 reply per loop in both check and hunt |
| LLM Pre-Filter | 2026-06-02 | `_score_tweet()` gates quote-tweets with 1-10 scoring |
| Null Check Fix | 2026-06-02 | `get_tweet_metrics` handles missing tweet data |
