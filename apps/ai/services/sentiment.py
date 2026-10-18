"""Feedback sentiment and topics (English + Hinglish word lists)."""
import re

POS = {'good', 'great', 'tasty', 'delicious', 'yummy', 'fresh', 'clean', 'nice', 'excellent', 'best', 'love', 'hot', 'perfect', 'achha', 'accha', 'badhiya', 'mast', 'swadisht', 'zabardast', 'shandar'}


NEG = {'bad', 'cold', 'stale', 'raw', 'dirty', 'late', 'slow', 'worst', 'bland', 'oily', 'salty', 'spicy', 'less', 'hair', 'insect', 'smell', 'kharab', 'bekar', 'thanda', 'ganda', 'kam', 'nahi', 'baasi', 'bakwas', 'tel', 'namak'}


TOPICS = {'taste': {'taste', 'tasty', 'bland', 'salty', 'spicy', 'oily', 'swad', 'swadisht', 'namak', 'tel', 'mirchi'},
          'quantity': {'quantity', 'less', 'little', 'portion', 'kam', 'enough'},
          'hygiene': {'dirty', 'clean', 'hair', 'insect', 'smell', 'ganda', 'hygiene', 'cockroach'},
          'delay': {'late', 'slow', 'wait', 'delay', 'der'},
          'temperature': {'cold', 'hot', 'thanda', 'garam'},
          'freshness': {'stale', 'fresh', 'baasi', 'raw', 'kharab'},
          'variety': {'variety', 'same', 'repeat', 'boring'}}


def sentiment(text, rating=None):
    words = re.findall(r"[a-zA-Z]+", text.lower())
    score = sum(w in POS for w in words) - sum(w in NEG for w in words)
    if rating:
        score += (rating - 3)
    label = 'positive' if score > 0 else 'negative' if score < 0 else 'neutral'
    topics = [t for t, ks in TOPICS.items() if any(w in ks for w in words)]
    return label, topics
