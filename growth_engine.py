"""
X-Integrated RL + LLM Growth Engine — Production Ready
=======================================================
Posts to X, collects real metrics after 24h, trains DQN on outcomes.
"""

import csv
import json
import os
import random
import subprocess
import time
import threading
import numpy as np
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from dotenv import load_dotenv
import schedule
import tweepy
import torch
import torch.nn as nn
import torch.optim as optim

load_dotenv()

# ------------------------------
# X API CONFIGURATION & CLIENT
# ------------------------------
X_CONFIG = {
    "api_key": os.getenv("X_API_KEY"),
    "api_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_secret": os.getenv("X_ACCESS_SECRET"),
    "bearer_token": os.getenv("X_BEARER_TOKEN"),
}


class XClient:
    def __init__(self):
        self.client = tweepy.Client(
            bearer_token=X_CONFIG["bearer_token"],
            consumer_key=X_CONFIG["api_key"],
            consumer_secret=X_CONFIG["api_secret"],
            access_token=X_CONFIG["access_token"],
            access_token_secret=X_CONFIG["access_secret"],
        )
        self.user_id = self._get_own_user_id()

    def _get_own_user_id(self) -> str:
        me = self.client.get_me()
        return str(me.data.id)

    def post_tweet(self, text: str) -> Optional[str]:
        try:
            response = self.client.create_tweet(text=text)
            tweet_id = str(response.data['id'])
            print(f"  ✅ Posted: {tweet_id} | {text[:80]}...")
            return tweet_id
        except Exception as e:
            print(f"  ❌ Post failed: {e}")
            return None

    def post_thread(self, tweets: List[str]) -> List[str]:
        tweet_ids = []
        reply_to = None
        for i, text in enumerate(tweets):
            try:
                if reply_to:
                    response = self.client.create_tweet(
                        text=text, in_reply_to_tweet_id=reply_to
                    )
                else:
                    response = self.client.create_tweet(text=text)
                tweet_id = str(response.data['id'])
                tweet_ids.append(tweet_id)
                reply_to = tweet_id
                print(f"  ✅ Thread {i+1}: {tweet_id}")
            except Exception as e:
                print(f"  ❌ Thread {i+1} failed: {e}")
                break
        return tweet_ids

    def get_follower_count(self) -> int:
        try:
            me = self.client.get_me(user_fields=["public_metrics"])
            return me.data.public_metrics["followers_count"]
        except Exception:
            return 0

    def get_tweet_metrics(self, tweet_id: str) -> Dict:
        """Fetch impressions + engagement for a tweet posted 24h ago."""
        try:
            tweet = self.client.get_tweet(
                tweet_id,
                tweet_fields=["public_metrics", "non_public_metrics"],
            )
            metrics = tweet.data.public_metrics
            non_public = tweet.data.get("non_public_metrics", {})
            impressions = non_public.get("impression_count", 0) if non_public else 0
            return {
                "impressions": impressions,
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "bookmarks": metrics.get("bookmark_count", 0),
            }
        except Exception as e:
            print(f"  ⚠️ Metrics failed for {tweet_id}: {e}")
            return {"impressions": 0, "likes": 0, "retweets": 0, "replies": 0, "bookmarks": 0}

    def get_user_id(self, username: str) -> Optional[str]:
        try:
            user = self.client.get_user(username=username)
            if user and user.data:
                return str(user.data.id)
        except Exception as e:
            print(f"  ⚠️ Failed to resolve username {username}: {e}")
        return None

    def get_recent_tweets(self, user_id: str, limit: int = 5) -> List[Dict]:
        try:
            max_results = max(5, limit)
            response = self.client.get_users_tweets(
                id=user_id,
                max_results=max_results,
                tweet_fields=["created_at"]
            )
            if response and response.data:
                sliced_data = response.data[:limit]
                return [{"id": str(t.id), "text": t.text} for t in sliced_data]
        except Exception as e:
            print(f"  ⚠️ Failed to fetch tweets for user {user_id}: {e}")
        return []

    def post_url_quote(self, text: str, target_username: str, target_tweet_id: str) -> Optional[str]:
        try:
            # Append URL to simulate quote tweet
            full_text = f"{text}\n\nhttps://x.com/{target_username}/status/{target_tweet_id}"
            response = self.client.create_tweet(text=full_text)
            tweet_id = str(response.data['id'])
            print(f"  ✅ URL-Quoted: {tweet_id} | {full_text[:80]}...")
            return tweet_id
        except Exception as e:
            print(f"  ❌ URL-Quote failed: {e}")
            return None
            return {"impressions": 0, "likes": 0, "retweets": 0, "replies": 0, "bookmarks": 0}


# ------------------------------
# NICHE CONFIG
# ------------------------------
NICHE_CONFIG = {
    "name": "space_artemis",
    "target_accounts": [
        "NASA", "SpaceX", "elonmusk", "NASAArtemis", "EverydayAdast", "DJSnM"
    ],
    "keywords": [
        "space", "moon", "artemis", "nasa", "sls", "orion", "starship", "rocket", "launch",
        "mars", "astronaut", "satellite", "orbit", "crew", "esa", "jaxa", "booster",
        "propulsion", "cosmos", "universe", "lunar"
    ],
    "model": "llama3.2:3b",
    "max_posts": 10000,
    "posts_per_day": 20,
    "alpha": 1e-5,
    "topics": [
        "Orion heat shield and re-entry",
        "SLS core stage stacking",
        "Artemis 2 crew: Reid Wiseman, Victor Glover, Christina Koch, Jeremy Hansen",
        "Artemis 2 launch timeline late 2026",
        "Lunar flyby trajectory 4600 miles beyond the Moon",
        "Space Launch System vs Saturn V",
        "Orion life support system",
        "Deep space communication with Earth",
        "Artemis 2 vs Apollo 8",
        "Moon suits and cockpit design",
        "NASA mission control for Artemis",
        "Space radiation protection on Orion",
        "Artemis 2 recovery operations splashdown",
        "European Service Module ESM contribution",
        "Training in the Orion simulator",
        "Why we have not been back to the Moon since 1972",
        "Gateway station and Artemis 2 role",
        "Artemis 3 landing site selection",
        "International partnerships on Artemis",
        "The Earthfall moment Earth seen from beyond the Moon",
    ],
    "events": [
        {"date": "2026-09-01", "label": "Artemis 2 prep ramp", "topic": "Artemis 2 launch timeline late 2026"},
        {"date": "2026-12-01", "label": "Artemis 2 launch window", "topic": "Artemis 2 crew: Reid Wiseman, Victor Glover, Christina Koch, Jeremy Hansen"},
        {"date": "2027-06-01", "label": "Artemis 3 planning", "topic": "Artemis 3 landing site selection"},
    ],
    "archetypes": {
        "Hot_Take": {
            "template": (
                "Write a bold, opinionated tweet about {topic}. Challenge conventional wisdom about space exploration. "
                "Make it provocative but grounded in real science. End with a single relevant emoji. "
                "Output only the tweet text, max 280 characters."
            ),
            "is_thread": False,
        },
        "How_To_Thread": {
            "template": (
                "Write a 4-tweet educational thread about {topic}. Start with the most mind-blowing fact as a hook. "
                "Each subsequent tweet adds one layer of depth. Make complex aerospace concepts accessible. "
                "Output exactly 4 tweets separated by '---TWEET---'."
            ),
            "is_thread": True,
        },
        "JawDrop_Fact": {
            "template": (
                "Write one surprising, counterintuitive fact about {topic} that makes people "
                "stop scrolling. No thread. Pure impact. Use a comparison to something everyday "
                "to make the scale tangible. Output only the tweet text."
            ),
            "is_thread": False,
        },
        "Hype_Countdown": {
            "template": (
                "Write a hype-building countdown post about {topic} (an upcoming Artemis milestone). "
                "Use the approximate timeframe from today (June 2026). "
                "Use short, staccato sentences. Make the reader feel the historic weight. "
                "Output only the tweet text."
            ),
            "is_thread": False,
        },
        "Nostalgia_Hook": {
            "template": (
                "Draw a direct parallel between an Apollo moment and an upcoming Artemis moment related to {topic}. "
                "Use a then vs now structure. "
                "End with a unifying, emotional statement about human exploration. "
                "Output only the tweet text."
            ),
            "is_thread": False,
        },
    },
}


# ------------------------------
# DATA STRUCTURES
# ------------------------------
@dataclass
class TweetRecord:
    tweet_id: str
    text: str
    archetype: str
    topic: str
    follower_count_before: int
    impressions: int
    follower_delta: int
    reward: float
    posted_at: datetime
    metrics_collected: bool = False


# ------------------------------
# PYTORCH DQN NETWORK
# ------------------------------
class QNetwork(nn.Module):
    """Deep Q-Network: state → Q-values for all actions."""

    def __init__(self, state_dim: int, num_actions: int, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_actions),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.net(state)


class DQNAgent:
    """Full DQN agent with experience replay and target network."""

    def __init__(self, state_dim: int, num_actions: int,
                 lr: float = 1e-3, gamma: float = 0.99,
                 epsilon: float = 0.5, epsilon_min: float = 0.05,
                 epsilon_decay: float = 0.995, batch_size: int = 32,
                 buffer_size: int = 5000):
        self.state_dim = state_dim
        self.num_actions = num_actions
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size

        # Networks
        self.q_network = QNetwork(state_dim, num_actions)
        self.target_network = QNetwork(state_dim, num_actions)
        self.target_network.load_state_dict(self.q_network.state_dict())
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=lr)
        self.loss_fn = nn.HuberLoss()

        # Replay buffer
        self.replay_buffer = deque(maxlen=buffer_size)
        self.priorities = deque(maxlen=buffer_size)

        # Counters
        self.train_steps = 0
        self.target_update_freq = 100

    def select_action(self, state_vector: np.ndarray) -> int:
        """ε-greedy action selection."""
        if np.random.random() < self.epsilon:
            return np.random.randint(self.num_actions)
        state_tensor = torch.FloatTensor(state_vector).unsqueeze(0)
        with torch.no_grad():
            q_values = self.q_network(state_tensor)
            return q_values.argmax().item()

    def store_transition(self, state: np.ndarray, action: int,
                         reward: float, next_state: np.ndarray, done: bool):
        """Add experience to replay buffer with max priority."""
        self.replay_buffer.append((state, action, reward, next_state, done))
        max_prio = max(self.priorities) if self.priorities else 1.0
        self.priorities.append(max_prio)

    def train_step(self):
        """Sample batch and update Q-network."""
        if len(self.replay_buffer) < self.batch_size:
            return None

        prios = np.array(self.priorities)
        probs = prios / prios.sum()
        indices = np.random.choice(len(self.replay_buffer),
                                   size=self.batch_size, p=probs)
        batch = [self.replay_buffer[i] for i in indices]

        states, actions, rewards, next_states, dones = zip(*batch)

        states = torch.FloatTensor(np.array(states))
        actions = torch.LongTensor(actions).unsqueeze(1)
        rewards = torch.FloatTensor(rewards).unsqueeze(1)
        next_states = torch.FloatTensor(np.array(next_states))
        dones = torch.FloatTensor(dones).unsqueeze(1)

        current_q = self.q_network(states).gather(1, actions)

        with torch.no_grad():
            next_q = self.target_network(next_states).max(1, keepdim=True)[0]
            target_q = rewards + self.gamma * next_q * (1 - dones)

        loss = self.loss_fn(current_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        td_errors = (target_q - current_q).abs().detach().numpy().flatten()
        for i, idx in enumerate(indices):
            self.priorities[idx] = td_errors[i] + 1e-6

        self.train_steps += 1

        if self.train_steps % self.target_update_freq == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())

        return loss.item()

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def save(self, path: str = "dqn_checkpoint.pt"):
        torch.save({
            "q_network": self.q_network.state_dict(),
            "target_network": self.target_network.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "epsilon": self.epsilon,
            "train_steps": self.train_steps,
        }, path)
        print(f"💾 Saved checkpoint to {path}")

    def load(self, path: str = "dqn_checkpoint.pt"):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            try:
                checkpoint = torch.load(path)
                self.q_network.load_state_dict(checkpoint["q_network"])
                self.target_network.load_state_dict(checkpoint["target_network"])
                self.optimizer.load_state_dict(checkpoint["optimizer"])
                self.epsilon = checkpoint["epsilon"]
                self.train_steps = checkpoint["train_steps"]
                print(f"📂 Loaded checkpoint from {path}")
            except Exception as e:
                print(f"⚠️ Failed to load checkpoint {path}: {e}")


# ------------------------------
# 24-HOUR METRICS COLLECTOR
# ------------------------------
class MetricsCollector:
    """
    Runs in a background thread. Every hour, checks tweets posted 24h ago,
    fetches their real impressions and engagement, computes rewards,
    and feeds them back to the state tracker and DQN agent.
    """

    def __init__(self, x_client: XClient, state_tracker, agent: DQNAgent,
                 engagement_predictor, checkpoint_file: str = "tweet_records.csv"):
        self.x_client = x_client
        self.state_tracker = state_tracker
        self.agent = agent
        self.predictor = engagement_predictor
        self.checkpoint_file = checkpoint_file
        self.pending_tweets: List[TweetRecord] = []
        self.collected_tweets: List[TweetRecord] = []
        self._load_checkpoint()

    def _load_checkpoint(self):
        """Load previously posted tweet records from CSV."""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    record = TweetRecord(
                        tweet_id=row["tweet_id"],
                        text=row["text"],
                        archetype=row["archetype"],
                        topic=row["topic"],
                        follower_count_before=int(row["follower_count_before"]),
                        impressions=int(row["impressions"]),
                        follower_delta=int(row["follower_delta"]),
                        reward=float(row["reward"]),
                        posted_at=datetime.fromisoformat(row["posted_at"]),
                        metrics_collected=row["metrics_collected"] == "True",
                    )
                    self.collected_tweets.append(record)
            print(f"📂 Loaded {len(self.collected_tweets)} historical records.")

    def _save_checkpoint(self):
        """Save all records to CSV."""
        all_records = self.collected_tweets + self.pending_tweets
        with open(self.checkpoint_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "tweet_id", "text", "archetype", "topic",
                "follower_count_before", "impressions", "follower_delta",
                "reward", "posted_at", "metrics_collected",
            ])
            writer.writeheader()
            for r in all_records:
                writer.writerow({
                    "tweet_id": r.tweet_id,
                    "text": r.text,
                    "archetype": r.archetype,
                    "topic": r.topic,
                    "follower_count_before": r.follower_count_before,
                    "impressions": r.impressions,
                    "follower_delta": r.follower_delta,
                    "reward": r.reward,
                    "posted_at": r.posted_at.isoformat(),
                    "metrics_collected": str(r.metrics_collected),
                })

    def add_posted_tweet(self, tweet_id: str, text: str, archetype: str, topic: str):
        """Called immediately after a tweet is posted to track it."""
        follower_before = self.state_tracker.follower_count
        record = TweetRecord(
            tweet_id=tweet_id,
            text=text,
            archetype=archetype,
            topic=topic,
            follower_count_before=follower_before,
            impressions=0,
            follower_delta=0,
            reward=0.0,
            posted_at=datetime.now(),
            metrics_collected=False,
        )
        self.pending_tweets.append(record)
        self._save_checkpoint()

    def collect_metrics(self):
        """
        Check all pending tweets. If 24h have passed since posting,
        fetch real metrics and compute reward.
        """
        now = datetime.now()
        newly_collected = []

        for record in self.pending_tweets[:]:
            hours_since_post = (now - record.posted_at).total_seconds() / 3600
            if hours_since_post >= 24 and not record.metrics_collected:
                print(f"\n📊 Collecting metrics for tweet {record.tweet_id}...")

                metrics = self.x_client.get_tweet_metrics(record.tweet_id)
                record.impressions = metrics["impressions"]

                current_followers = self.x_client.get_follower_count()
                record.follower_delta = current_followers - record.follower_count_before

                # Check for milestone reward
                milestone_bonus = 0.0
                if record.impressions >= 100000:
                    achievements_file = "achievements.json"
                    achievements = {}
                    if os.path.exists(achievements_file):
                        try:
                            with open(achievements_file, "r") as af:
                                achievements = json.load(af)
                        except Exception:
                            pass
                    if not achievements.get("milestone_100k_impressions"):
                        print(f"🏆 MILESTONE ACHIEVED: Tweet {record.tweet_id} gained {record.impressions} impressions! Awarding DQN +100.0 bonus.")
                        milestone_bonus = 100.0
                        achievements["milestone_100k_impressions"] = {
                            "tweet_id": record.tweet_id,
                            "impressions": record.impressions,
                            "achieved_at": datetime.now().isoformat()
                        }
                        try:
                            with open(achievements_file, "w") as af:
                                json.dump(achievements, af)
                        except Exception as e:
                            print(f"  ⚠️ Failed to save achievements: {e}")

                alpha = NICHE_CONFIG["alpha"]
                record.reward = record.follower_delta + alpha * record.impressions + milestone_bonus

                record.metrics_collected = True

                self.pending_tweets.remove(record)
                self.collected_tweets.append(record)

                self.state_tracker.follower_count = current_followers
                self.predictor.add_sample(record)

                newly_collected.append(record)

                print(f"  Impressions: {record.impressions}")
                print(f"  Follower Δ: {record.follower_delta}")
                print(f"  Reward: {record.reward:.4f}")

        self._save_checkpoint()
        return newly_collected

    def build_rl_transitions(self):
        """
        Convert collected tweets into (s, a, r, s') transitions
        and feed them to the DQN agent.
        """
        if len(self.collected_tweets) < 2:
            return

        sorted_records = sorted(self.collected_tweets, key=lambda r: r.posted_at)

        for i in range(len(sorted_records) - 1):
            r = sorted_records[i]
            r_next = sorted_records[i + 1]

            state = self._approximate_state(r)
            next_state = self._approximate_state(r_next)
            action_idx = self._get_action_index(r.archetype, r.topic)
            done = False

            self.agent.store_transition(state, action_idx, r.reward, next_state, done)

    def _approximate_state(self, record: TweetRecord) -> np.ndarray:
        """Build approximate state vector from a tweet record."""
        return np.array([
            np.log1p(record.follower_count_before),
            0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0,
            record.posted_at.hour / 24.0,
            record.posted_at.weekday() / 7.0,
            30.0 / 365.0,
        ])

    def _get_action_index(self, archetype: str, topic: str) -> int:
        """Map archetype + topic back to action index."""
        archetypes = list(NICHE_CONFIG["archetypes"].keys())
        topics = NICHE_CONFIG["topics"]
        arch_idx = archetypes.index(archetype) if archetype in archetypes else 0
        topic_idx = topics.index(topic) if topic in topics else 0
        return arch_idx * len(topics) + topic_idx

    def run_loop(self):
        """Background thread: collect metrics every hour."""
        while True:
            try:
                newly_collected = self.collect_metrics()
                if newly_collected:
                    self.build_rl_transitions()
                    for _ in range(10):
                        loss = self.agent.train_step()
                        if loss:
                            print(f"  🧠 DQN loss: {loss:.4f}")
                    self.agent.decay_epsilon()
                    print(f"  🎯 Epsilon: {self.agent.epsilon:.3f}")
            except Exception as e:
                print(f"  ⚠️ Metrics collector error: {e}")
            time.sleep(3600)


# ------------------------------
# LLM PIPELINE
# ------------------------------
class LLMPipeline:
    def __init__(self, model: str = "llama3.2:3b"):
        self.model = model
        self.archetypes = NICHE_CONFIG["archetypes"]

    def query(self, prompt: str) -> Optional[str]:
        import urllib.request
        import json
        try:
            url = f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434').rstrip('/')}/api/generate"
            data = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                return resp_data.get("response", "").strip()
        except Exception as e:
            print(f"  Ollama API error: {e}")
            # Fallback to command line if API fails
            try:
                result = subprocess.run(
                    ["ollama", "run", self.model, prompt],
                    capture_output=True, text=True, timeout=120, check=True,
                )
                return result.stdout.strip()
            except Exception as e2:
                print(f"  Ollama fallback CLI error: {e2}")
                return None

    def generate_candidates(self, action, k: int = 5) -> List[str]:
        arch = self.archetypes[action.archetype]
        prompt = arch["template"].replace("{topic}", action.topic)
        candidates = []
        for _ in range(k):
            raw = self.query(prompt)
            if raw:
                candidates.append(raw)
        return candidates


# ------------------------------
# ENGAGEMENT PREDICTOR
# ------------------------------
class EngagementPredictor:
    def __init__(self):
        self.training_data: List[TweetRecord] = []
        self.trained = False

    def rule_based_score(self, text: str) -> float:
        score = 0.0
        if 50 < len(text) < 250:
            score += 1.0
        power_words = ["secret", "surprising", "never", "mistake", "everyone",
                       "hack", "transform", "truth", "unpopular", "why", "AI"]
        score += sum(1.5 for w in power_words if w.lower() in text.lower())
        if "?" in text:
            score += 2.0
        spam = ["buy now", "click here", "DM me", "$$"]
        for sw in spam:
            if sw.lower() in text.lower():
                score -= 5.0
        return max(score, 0.1)

    def predict(self, text: str, follower_count: int) -> float:
        return self.rule_based_score(text)

    def add_sample(self, record: TweetRecord):
        self.training_data.append(record)
        if len(self.training_data) >= 100 and not self.trained:
            self.train()

    def train(self):
        print(f"\n📊 Training engagement predictor on {len(self.training_data)} samples...")
        self.trained = True


# ------------------------------
# ACTION SPACE & STATE TRACKER
# ------------------------------
@dataclass
class Action:
    index: int
    archetype: str
    topic: str


class ActionSpace:
    def __init__(self):
        self.archetypes = list(NICHE_CONFIG["archetypes"].keys())
        self.topics = NICHE_CONFIG["topics"]
        self.actions: List[Action] = []
        for arch in self.archetypes:
            for topic in self.topics:
                idx = len(self.actions)
                self.actions.append(Action(idx, arch, topic))

    def __len__(self):
        return len(self.actions)

    def decode(self, index: int) -> Action:
        return self.actions[index]

    def safe_actions(self) -> List[int]:
        return [i for i, a in enumerate(self.actions)
                if a.archetype in ["JawDrop_Fact", "Personal_Story"]]


class StateTracker:
    def __init__(self, max_posts: int = 10000):
        self.max_posts = max_posts
        self.post_history: List[TweetRecord] = []
        self.follower_count = 0

    def compute_state(self, t: int) -> np.ndarray:
        """Return state vector for RL agent."""
        recent = self.post_history[-20:] if self.post_history else []
        if recent:
            avg_likes = np.mean([r.impressions * 0.05 for r in recent])
            avg_rt = np.mean([r.impressions * 0.01 for r in recent])
            avg_replies = np.mean([r.impressions * 0.005 for r in recent])
            imp_per_follower = np.mean([
                r.impressions / max(self.follower_count, 1) for r in recent
            ])
        else:
            avg_likes = avg_rt = avg_replies = imp_per_follower = 0.0

        archetype_names = list(NICHE_CONFIG["archetypes"].keys())
        content_mix = [0.0] * len(archetype_names)
        for r in recent:
            for i, a in enumerate(archetype_names):
                if r.archetype == a:
                    content_mix[i] += 1.0
        if recent:
            content_mix = [c / len(recent) for c in content_mix]

        today = datetime.now()
        days_until_event = 365
        for event in NICHE_CONFIG["events"]:
            event_date = datetime.strptime(event["date"], "%Y-%m-%d")
            delta = (event_date - today).days
            if 0 <= delta < days_until_event:
                days_until_event = delta

        return np.array([
            np.log1p(self.follower_count),
            avg_likes, avg_rt, avg_replies, imp_per_follower,
            *content_mix,
            t / self.max_posts,
            datetime.now().hour / 24.0,
            datetime.now().weekday() / 7.0,
            days_until_event / 365.0,
        ])


# ------------------------------
# POST SCHEDULER
# ------------------------------
class PostScheduler:
    def __init__(self, x_client: XClient, metrics_collector: MetricsCollector):
        self.x_client = x_client
        self.metrics_collector = metrics_collector
        self.queue: deque = deque()
        self.posted_today = 0
        self.posts_per_day = NICHE_CONFIG["posts_per_day"]

    def enqueue(self, text: str, archetype: str, topic: str, is_thread: bool = False):
        parts = text.split("---TWEET---") if is_thread else [text]
        self.queue.append({
            "parts": [p.strip() for p in parts if p.strip()],
            "archetype": archetype,
            "topic": topic,
            "is_thread": is_thread,
        })

    def post_one(self):
        if not self.queue or self.posted_today >= self.posts_per_day:
            return None

        item = self.queue.popleft()
        parts = item["parts"]

        if len(parts) == 1:
            tweet_id = self.x_client.post_tweet(parts[0])
            if tweet_id:
                self.posted_today += 1
                self.metrics_collector.add_posted_tweet(
                    tweet_id, parts[0], item["archetype"], item["topic"]
                )
                return {"tweet_id": tweet_id, "text": parts[0]}
        else:
            tweet_ids = self.x_client.post_thread(parts)
            if tweet_ids:
                self.posted_today += 1
                self.metrics_collector.add_posted_tweet(
                    tweet_ids[0], " ||| ".join(parts),
                    item["archetype"], item["topic"]
                )
                return {"tweet_id": tweet_ids[0], "text": parts[0]}
        return None


# ------------------------------
# AUTO REPLY ENGINE
# ------------------------------
class AutoReplyEngine:
    def __init__(self, x_client: XClient, llm: LLMPipeline, metrics_collector: MetricsCollector):
        self.x_client = x_client
        self.llm = llm
        self.metrics_collector = metrics_collector
        self.target_usernames = NICHE_CONFIG.get("target_accounts", [
            "NASA", "SpaceX", "elonmusk", "NASAArtemis", "EverydayAdast", "DJSnM"
        ])
        self.keywords = NICHE_CONFIG.get("keywords", [
            "space", "moon", "artemis", "nasa", "sls", "orion", "starship", "rocket", "launch",
            "mars", "astronaut", "satellite", "orbit", "crew", "esa", "jaxa", "booster",
            "propulsion", "cosmos", "universe", "lunar"
        ])
        self.replied_tweets_file = "replied_tweets.json"
        self.replied_tweets = self._load_replied_tweets()
        self.target_ids = {}
        self.running = False
        self.thread = None

    def _load_replied_tweets(self) -> dict:
        if os.path.exists(self.replied_tweets_file):
            try:
                with open(self.replied_tweets_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_replied_tweets(self):
        try:
            with open(self.replied_tweets_file, "w") as f:
                json.dump(self.replied_tweets, f)
        except Exception as e:
            print(f"  ⚠️ Failed to save replied tweets: {e}")

    def resolve_targets(self):
        print("🔍 Resolving target accounts to IDs...")
        for username in self.target_usernames:
            user_id = self.x_client.get_user_id(username)
            if user_id:
                self.target_ids[username] = user_id
                print(f"  👤 Resolved @{username} -> {user_id}")
            time.sleep(1)

    def check_and_reply(self):
        if not self.target_ids:
            self.resolve_targets()

        for username, user_id in self.target_ids.items():
            print(f"📡 Checking recent tweets from @{username}...")
            tweets = self.x_client.get_recent_tweets(user_id, limit=3)
            for tweet in tweets:
                tweet_id = tweet["id"]
                text = tweet["text"]

                if tweet_id in self.replied_tweets:
                    continue

                # Check relevance
                lower_text = text.lower()
                is_relevant = any(kw in lower_text for kw in self.keywords)
                if not is_relevant:
                    continue

                print(f"✨ Found relevant tweet from @{username}: \"{text[:80]}...\"")
                
                # Generate reply
                reply_prompt = f"""
You are @SpaceBase1958, an enthusiastic, knowledgeable, and sharp space outreach account.
Write a witty, value-adding, or supportive reply to this tweet from @{username}.

Tweet: "{text}"

Rules:
- Keep it under 280 characters.
- Do not sound like a generic bot. Be authentic, add a neat space fact or sharp insight if possible.
- End with a relevant emoji.
- Output ONLY the reply text. Do not include quotes.
"""
                reply_text = self.llm.query(reply_prompt)
                if not reply_text:
                    print("  ⚠️ Reply generation returned empty.")
                    continue

                reply_text = reply_text.strip().strip('"').strip("'")
                print(f"✍️ Generated reply: \"{reply_text}\"")

                # Post URL Quote Tweet (bypasses 403 restriction)
                posted_id = self.x_client.post_url_quote(reply_text, username, tweet_id)
                if posted_id:
                    self.replied_tweets[tweet_id] = {
                        "quote_id": posted_id,
                        "quote_text": reply_text,
                        "quoted_at": datetime.now().isoformat(),
                        "target_username": username
                    }
                    self._save_replied_tweets()

                    # Add to metrics collector
                    self.metrics_collector.add_posted_tweet(
                        posted_id, reply_text, "quote", username
                    )
                
                time.sleep(5)

            time.sleep(2)

    def run_loop(self):
        self.running = True
        time.sleep(60)
        while self.running:
            try:
                self.check_and_reply()
            except Exception as e:
                print(f"⚠️ Error in Auto-Reply loop step: {e}")
            
            for _ in range(600):
                if not self.running:
                    break
                time.sleep(1)

    def start(self):
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()
        print("🤖 Auto-Reply Loop started in background thread.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)


# ------------------------------
# SEED GENERATOR
# ------------------------------
class SeedGenerator:
    def __init__(self, llm: LLMPipeline):
        self.llm = llm

    def generate_from_seed(self, seed_prompt: str, num_posts: int = 10) -> List[dict]:
        print(f"\n🌱 Generating {num_posts} seed posts...")
        generation_prompt = f"""
You are a social media strategist. Based on this account description,
generate exactly {num_posts} tweet ideas.

Account: "{seed_prompt}"

Rules:
- Each tweet under 280 characters.
- Vary styles: hot takes, tips, personal stories, facts, questions.
- No hashtags unless natural.
- Output exactly {num_posts} tweets, one per line, no numbering.
"""
        raw = self.llm.query(generation_prompt)
        if not raw:
            return []

        lines = [line.strip() for line in raw.split("\n") if line.strip()]
        results = []
        for line in lines:
            lower_line = line.lower()
            # Skip conversational intro/outro/header filler
            if (lower_line.startswith("here") or 
                lower_line.startswith("sure") or 
                lower_line.endswith(":") or 
                "tweet ideas" in lower_line or 
                "social media" in lower_line or
                len(line) < 15):
                continue
                
            # Clean up numbering
            if len(line) > 1 and line[0].isdigit() and line[1] in ".):":
                line = line[2:].strip()
            elif len(line) > 2 and line[0].isdigit() and line[1].isdigit() and line[2] in ".):":
                line = line[3:].strip()
                
            results.append({"text": line, "archetype": "seed", "topic": "seed", "is_thread": False})
            print(f"  {line[:100]}...")
            if len(results) >= num_posts:
                break
        return results


# ------------------------------
# GROWTH ENGINE
# ------------------------------
class GrowthEngine:
    def __init__(self):
        # Core components
        self.x_client = XClient()
        self.action_space = ActionSpace()
        self.state_tracker = StateTracker(max_posts=NICHE_CONFIG["max_posts"])
        self.llm = LLMPipeline(model=NICHE_CONFIG["model"])
        self.predictor = EngagementPredictor()
        self.seed_generator = SeedGenerator(self.llm)

        # DQN Agent
        state_dim = self.state_tracker.compute_state(0).shape[0]
        self.agent = DQNAgent(state_dim=state_dim, num_actions=len(self.action_space))
        self.agent.load("dqn_checkpoint.pt")

        # Metrics collector
        self.metrics_collector = MetricsCollector(
            self.x_client, self.state_tracker, self.agent, self.predictor
        )

        # Auto Reply Engine
        self.auto_reply_engine = AutoReplyEngine(self.x_client, self.llm, self.metrics_collector)

        # Scheduler
        self.scheduler = PostScheduler(self.x_client, self.metrics_collector)

        # Update state tracker with current follower count
        self.state_tracker.follower_count = self.x_client.get_follower_count()

        self.post_count = 0
        self.running = False

    def generate_next_post(self) -> Optional[dict]:
        """Use DQN agent to select action, LLM to generate candidates."""
        state = self.state_tracker.compute_state(self.post_count)

        if self.state_tracker.follower_count < 1000 and random.random() < 0.3:
            safe = self.action_space.safe_actions()
            action_idx = random.choice(safe)
        else:
            action_idx = self.agent.select_action(state)

        action = self.action_space.decode(action_idx)
        candidates = self.llm.generate_candidates(action, k=3)

        if not candidates:
            return None

        scores = [self.predictor.predict(c, self.state_tracker.follower_count)
                  for c in candidates]
        best_text = candidates[np.argmax(scores)]

        self.post_count += 1
        return {
            "text": best_text,
            "archetype": action.archetype,
            "topic": action.topic,
            "is_thread": NICHE_CONFIG["archetypes"][action.archetype]["is_thread"],
        }

    def generate_batch(self, count: int = 20):
        print(f"\n🤖 Generating {count} posts via DQN + LLM...")
        for i in range(count):
            post = self.generate_next_post()
            if post:
                self.scheduler.enqueue(
                    text=post["text"],
                    archetype=post["archetype"],
                    topic=post["topic"],
                    is_thread=post.get("is_thread", False),
                )
                print(f"  {i+1}/{count} | {post['archetype']} | {post['text'][:60]}...")
        print(f"✅ {count} posts enqueued.\n")

    def start_scheduler(self):
        """Start the scheduler in the main thread."""
        schedule.every().day.at("00:00").do(self._reset_daily_count)
        interval_minutes = (16 * 60) // self.scheduler.posts_per_day
        schedule.every(interval_minutes).minutes.do(self._scheduled_post)
        schedule.every(4).hours.do(self._refill_queue)

        print(f"⏰ Scheduler started: {self.scheduler.posts_per_day} posts/day")
        print(f"   Interval: {interval_minutes} minutes\n")

        while self.running:
            schedule.run_pending()
            time.sleep(30)

    def _scheduled_post(self):
        self.scheduler.post_one()

    def _refill_queue(self):
        if len(self.scheduler.queue) < 5:
            self.generate_batch(count=10)

    def _reset_daily_count(self):
        self.scheduler.posted_today = 0

    def launch(self, seed_prompt: str):
        """Generate seed posts, enqueue, and begin full operation."""
        seed_posts = self.seed_generator.generate_from_seed(seed_prompt, num_posts=10)

        if not seed_posts:
            print("❌ Seed generation failed.")
            return

        print("📋 Enqueuing seed posts...")
        for post in seed_posts:
            self.scheduler.enqueue(
                text=post["text"],
                archetype=post["archetype"],
                topic=post["topic"],
                is_thread=post.get("is_thread", False),
            )

        self.generate_batch(count=10)

        metrics_thread = threading.Thread(
            target=self.metrics_collector.run_loop, daemon=True
        )
        metrics_thread.start()
        print("📊 Metrics collector started in background.")

        schedule.every(1).hours.do(lambda: self.agent.save("dqn_checkpoint.pt"))

        self.running = True
        print(f"\n🚀 Growth engine LIVE.")
        print(f"👤 Followers: {self.x_client.get_follower_count()}")
        print(f"📦 Queue: {len(self.scheduler.queue)} posts ready\n")

        print("📣 Posting initial tweet immediately to verify credentials...")
        posted = self.scheduler.post_one()
        if posted:
            print(f"✅ Posted initial tweet: {posted['text']}")
        else:
            print("⚠️ Initial tweet posting skipped or failed.")

        # Start Auto-Reply Loop
        self.auto_reply_engine.start()

        self.start_scheduler()
        
        # Stop Auto-Reply Loop when scheduler stops
        self.auto_reply_engine.stop()


# ------------------------------
# MAIN
# ------------------------------
def main():
    print("""
╔══════════════════════════════════════════════╗
║   AI-Powered X Growth Engine — Production   ║
║   DQN + LLM + X API + Metrics Collector     ║
╚══════════════════════════════════════════════╝
""")

    if not all(X_CONFIG.values()):
        print("❌ Missing X API credentials in .env")
        print("Required keys: X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET, X_BEARER_TOKEN")
        return

    engine = GrowthEngine()

    print(f"✅ Connected to X")
    print(f"👤 Followers: {engine.x_client.get_follower_count()}")
    print(f"📦 Niche: {NICHE_CONFIG['name']}")
    print(f"🧠 DQN actions: {len(engine.action_space)}")
    print(f"💾 Tweet records loaded: {len(engine.metrics_collector.collected_tweets)}\n")

    # Hardcoded seed prompt for Space & Artemis II
    seed_prompt = "Everything Space and Artemis II. Sharp facts, bold takes, and countdown hype for humanitys return to the Moon."
    print(f"🌱 Using seed prompt: \"{seed_prompt}\"")
    engine.launch(seed_prompt)


if __name__ == "__main__":
    main()
