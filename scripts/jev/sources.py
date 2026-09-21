"""Tier-2 scan sources and their feeds.

Mirrors the 16 sources named in scripts/weekly-scan-prompt.md. Four have no
discoverable feed and are listed as blind spots rather than quietly omitted —
the shadow comparison must not count a signal these would have carried as a
triage miss.

Verified 2026-09-21: every FEEDS entry returned items; every BLIND_SPOTS URL
returned zero across several candidate paths.
"""

FEEDS = {
    "Import AI": "https://importai.substack.com/feed",
    "One Useful Thing": "https://www.oneusefulthing.org/feed",
    "Don't Worry About the Vase": "https://thezvi.substack.com/feed",
    "Stratechery": "https://stratechery.com/feed/",
    "SemiAnalysis": "https://newsletter.semianalysis.com/feed",
    "Simon Willison": "https://simonwillison.net/atom/everything/",
    "Latent Space": "https://www.latent.space/feed",
    "Interconnects": "https://www.interconnects.ai/feed",
    "Road to AI We Can Trust": "https://garymarcus.substack.com/feed",
    "The Pragmatic Engineer": "https://newsletter.pragmaticengineer.com/feed",
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
    "OpenAI": "https://openai.com/blog/rss.xml",
}

# No feed found. The live scan reaches these with WebSearch/WebFetch; the
# shadow run cannot, so they are excluded from any accuracy claim.
BLIND_SPOTS = {
    "The Batch": "https://www.deeplearning.ai/the-batch/",
    "Every / Chain of Thought": "https://every.to/chain-of-thought",
    "Anthropic News": "https://www.anthropic.com/news",
    "Analytics India Magazine": "https://analyticsindiamag.com/",
}

# Publishers writing about their own products: the framework caps evidence
# strength for these unless independently corroborated.
FIRST_PARTY = {"OpenAI", "Hugging Face", "Anthropic News"}
