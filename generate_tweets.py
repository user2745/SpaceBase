import csv
import random
import subprocess
import json
from datetime import datetime

# ------------------------------
# Configuration
# ------------------------------
MODEL_NAME = "llama3.1"          # Change to "mistral", "phi3", etc.
NUM_TWEETS = 100               # Total tweets to generate
OUTPUT_FILE = "space_tweets.csv"
TEMPERATURE = 0.9

# ------------------------------
# Archetype Templates
# Each template expects {topic} (and possibly {astronaut_name}, {event} etc.)
# We'll fill them based on topic context.
# ------------------------------
ARCHETYPES = {
    "JawDrop_Fact": {
        "template": (
            "Write a single, mind-blowing fact about {topic} that would stop a scroller dead. "
            "No thread. No hashtags unless they are naturally part of the fact. "
            "Tone: pure awe. Max 280 characters. Output only the tweet text, nothing else."
        ),
        "is_thread": False
    },
    "Explain_Thread": {
        "template": (
            "Write a 4-tweet thread that explains {topic} to a smart, non-engineer audience. "
            "Start with a provocative question as tweet 1. Use vivid analogies. "
            "End with a forward-looking statement about Artemis 2. "
            "Output exactly 4 tweets, each separated by '---TWEET---'."
        ),
        "is_thread": True
    },
    "Astro_Spotlight": {
        "template": (
            "Write a 2-sentence personal story about {topic} (an Artemis 2 astronaut), "
            "using a real quote or fact from recent training news. "
            "Make it intimate and inspiring. Include a call-to-action like "
            "'What would you say to your family before leaving Earth?' "
            "Output only the tweet text."
        ),
        "is_thread": False
    },
    "Myth_Buster": {
        "template": (
            "State a common misconception about {topic}. Then correct it with one powerful, "
            "undeniable data point. Keep the tone confident, not arrogant. End with a single relevant emoji. "
            "Output only the tweet text."
        ),
        "is_thread": False
    },
    "Hype_Countdown": {
        "template": (
            "Write a hype-building countdown post about {topic} (an upcoming Artemis milestone). "
            "Use the exact timeframe from today's date (approx May 2026) if possible. "
            "Use short, staccato sentences. Make the reader feel the historic weight of the mission. "
            "Output only the tweet text."
        ),
        "is_thread": False
    },
    "Hot_Take": {
        "template": (
            "Write an 'unpopular opinion' tweet about {topic} that is grounded in real facts. "
            "It should challenge a widely held belief but remain respectful. "
            "Invite replies with 'Change my mind.' Output only the tweet text."
        ),
        "is_thread": False
    },
    "Visual_Invitation": {
        "template": (
            "Describe a scene about {topic} in rich visual detail that doesn't exist as a photograph yet. "
            "Make it so compelling that artists reading will want to create it. "
            "End with 'Someone, please.' and a palette emoji. Output only the tweet text."
        ),
        "is_thread": False
    },
    "Nostalgia_Hook": {
        "template": (
            "Draw a direct parallel between an Apollo moment and an upcoming Artemis moment related to {topic}. "
            "Use a 'In {year}, … In {year}, …' structure. "
            "End with a unifying, emotional statement about human exploration. "
            "Output only the tweet text."
        ),
        "is_thread": False
    },
    "Poll": {
        "template": (
            "Create a Twitter poll with two options about {topic} that are both compelling. "
            "The question must highlight the historic significance of each. "
            "Add a remark like '(This is harder than it looks.)' to provoke debate. "
            "Output only the poll text (question and two options), no extra commentary."
        ),
        "is_thread": False
    },
    "Community_CTA": {
        "template": (
            "Ask a deeply personal but universal question about the reader's connection to space exploration, "
            "inspired by {topic}. Share your own brief answer first to break the ice. "
            "Encourage replies and promise to highlight the best ones. "
            "Output only the tweet text."
        ),
        "is_thread": False
    }
}

# ------------------------------
# Topic Pools (with context for certain archetypes)
# ------------------------------
TOPICS = [
    "Orion heat shield and re-entry",
    "SLS core stage stacking",
    "Artemis 2 crew: Reid Wiseman, Victor Glover, Christina Koch, Jeremy Hansen",
    "Artemis 2 launch timeline (late 2026)",
    "Lunar flyby trajectory – 4,600 miles beyond the Moon",
    "Space Launch System vs Saturn V",
    "Orion life support system",
    "Deep space communication with Earth",
    "Artemis 2 vs Apollo 8",
    "Moon suits and cockpit design",
    "NASA’s mission control for Artemis",
    "Space radiation protection on Orion",
    "Artemis 2 recovery operations (splashdown)",
    "European Service Module (ESM) contribution",
    "Training in the Orion simulator",
    "Why we haven’t been back to the Moon since 1972",
    "Gateway station and Artemis 2’s role",
    "Artemis 3 landing site selection",
    "International partnerships on Artemis",
    "The ‘Earthfall’ moment – Earth seen from beyond the Moon"
]

# Extra detailed astronaut names for Astro_Spotlight
ASTRONAUT_TOPICS = [
    "Reid Wiseman’s perspective as Artemis 2 commander",
    "Victor Glover’s journey from pilot to deep space astronaut",
    "Christina Koch’s record-setting career and Artemis 2 role",
    "Jeremy Hansen representing Canada on the Moon return",
    "The diversity of Artemis 2 crew and what it means"
]

# ------------------------------
# Helper function to call Ollama
# ------------------------------
def query_ollama(prompt, temperature=0.9):
    """Send a prompt to the local Ollama model and return the generated text."""
    # Use subprocess to call ollama run with JSON output (version >=0.1.14)
    # Alternative: use ollama Python library, but subprocess is zero-dependency.
    cmd = [
        "ollama", "run", MODEL_NAME,
        "--format", "json",
        prompt
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=60
        )
        # Ollama --format json returns a JSON line with "response" field
        response_json = json.loads(result.stdout.strip())
        return response_json.get("message", "").strip()
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Error calling Ollama: {e}")
        return None

# ------------------------------
# Generate tweet combinations
# ------------------------------
def generate_prompts():
    """Create a list of (archetype_name, filled_template, is_thread) tuples."""
    combos = []
    # Cycle through archetypes and topics, ensuring each archetype gets airtime
    archetype_names = list(ARCHETYPES.keys())
    random.shuffle(archetype_names)  # randomness for first pass

    for i in range(NUM_TWEETS):
        arch = archetype_names[i % len(archetype_names)]  # cycle through
        arch_def = ARCHETYPES[arch]
        template = arch_def["template"]
        is_thread = arch_def["is_thread"]

        # Pick a topic appropriate for the archetype
        if arch == "Astro_Spotlight":
            topic = random.choice(ASTRONAUT_TOPICS)
        elif arch in ["Hype_Countdown", "Poll", "Visual_Invitation"]:
            topic = random.choice(TOPICS[:15])  # more specific
        else:
            topic = random.choice(TOPICS)

        # Fill template
        filled_prompt = template.replace("{topic}", topic)
        # For Hype_Countdown, we might need a date placeholder – topic already includes event.
        combos.append((arch, filled_prompt, is_thread, topic))
    return combos

# ------------------------------
# Process and save tweets
# ------------------------------
def main():
    combos = generate_prompts()
    tweets_data = []

    print(f"🚀 Generating {NUM_TWEETS} tweets with model '{MODEL_NAME}'...")

    for idx, (arch, prompt, is_thread, topic) in enumerate(combos, start=1):
        print(f"[{idx}/{NUM_TWEETS}] {arch}: {topic}")
        raw_output = query_ollama(prompt, TEMPERATURE)

        if raw_output is None:
            print("  ↳ Skipping due to error.")
            continue

        # Handle thread output (split by separator) or single tweet
        if is_thread and "---TWEET---" in raw_output:
            parts = [p.strip() for p in raw_output.split("---TWEET---") if p.strip()]
            for part_num, part in enumerate(parts, start=1):
                tweets_data.append({
                    "archetype": arch,
                    "topic": topic,
                    "tweet_number": part_num,
                    "total_parts": len(parts),
                    "tweet_text": part
                })
        else:
            tweets_data.append({
                "archetype": arch,
                "topic": topic,
                "tweet_number": 1,
                "total_parts": 1,
                "tweet_text": raw_output
            })

        # Save incrementally to avoid losing progress
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "archetype", "topic", "tweet_number", "total_parts", "tweet_text"
            ])
            writer.writeheader()
            writer.writerows(tweets_data)

    print(f"\n✅ Done! Saved {len(tweets_data)} tweet parts to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()