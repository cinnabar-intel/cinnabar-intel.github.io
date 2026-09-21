"""Stage 1 of the scan: judge every candidate article before Claude reads any.

Today the weekly scan hands ~40 articles to Claude, which reads all of them and
decides Strong / Weak / Noise in prose. That judgment is high-volume, repetitive,
and drifts between runs. Here it becomes four typed questions per article, asked
in one parallel request, with the framework's hard rules applied afterwards in
code where they belong.

Hype is scored HERE, on every candidate, not after the noise filter. The
framework's Peak-hype exclusion is meant to bite at this point; applied to
already-surviving signals it had nothing left to exclude (every signal logged
since April is Grounded).

This module decides what is worth reading. It does not write anything.
"""

from typesafe_sdk import Choice, Noul

# Category 07 is deliberately absent - it is not in the knowledge taxonomy.
CATEGORIES = {
    "01 GenAI Capabilities": "Model capability, benchmarks, frontier research results, open-weight releases.",
    "02 Enterprise AI & Org Transformation": "How organizations adopt AI: operating models, restructuring, enterprise deployment.",
    "03 Workforce & Human-AI Collaboration": "Effects on roles, skills, headcount, and how people and models divide work.",
    "04 AI Governance & Ethics": "Policy, regulation, safety commitments, incidents, accountability, evaluation integrity.",
    "05 AI Infrastructure Trajectory": "Compute, silicon, data centres, energy, serving economics, cost curves.",
    "06 Weak Signal Watch": "Genuinely spans several categories and cannot be placed in one.",
    "08 AI Productivity Tools": "Tools practitioners use day to day, and evidence about their real effect.",
    "09 Transformation Methods - AI Era": "How change, delivery, and consulting method itself adapts to AI.",
    "10 Local AI Engineering": "Running and adapting models locally: quantization, fine-tuning, on-device.",
    "11 Agent Frameworks & Dev Tools": "Agents, tool use, protocols, orchestration, and the developer surface around them.",
}

HYPE_CRITERIA = {
    "Grounded": "Claims match evidence. Deployments confirm the narrative, independent benchmarks exist, and discourse is about tradeoffs rather than potential.",
    "Ahead of itself": "Real progress, but claims outpace deployment. Impressive demos, 'coming soon' outnumbering 'we deployed'.",
    "Peak hype": "Massive attention with minimal production evidence. Everyone talking, few building, vendor announcements recycled as news, no independent benchmarks.",
    "Post-hype": "Attention has dropped but real builders are still shipping. Fewer headlines, more commits; honest assessment has replaced breathless coverage.",
}


def triage_questions() -> dict:
    """Four independent judgments over one article. Asked in a single request."""
    return {
        "structural": Noul(
            instructions={
                "task": "Does this article report a structural development in AI, rather than routine news?",
                "yes_looks_like": "A capability that did not exist, a deployment at real scale, a governance or safety shift, an infrastructure or cost-curve change, or a documented incident that reveals how these systems actually behave.",
                "no_looks_like": "Product launches and feature updates, funding rounds, executive moves, opinion and commentary that adds no new evidence, conference coverage, or an announcement already reported elsewhere and merely restated.",
            }
        ),
        "corroborated": Noul(
            instructions={
                "task": "Is the article's central claim supported by evidence independent of whoever benefits from it being true?",
                "note": "A company's own blog post about its own product is not independent. A third-party benchmark, a reproduction, a regulator's filing, or reporting that cites named sources with direct knowledge is.",
            }
        ),
        "hype": Choice(
            instructions={
                "task": "Judge whether the attention this is receiving is proportional to its substance.",
                "note": "This measures the gap between claims and evidence, not the quality of the underlying technology and not its lifecycle stage.",
            },
            criteria=HYPE_CRITERIA,
        ),
        "category": Choice(
            instructions={
                "task": "Place this article in the single most relevant knowledge category.",
                "note": "Choose 06 only when the article genuinely spans several categories, not merely when the choice is difficult.",
            },
            criteria=CATEGORIES,
        ),
    }


def article_state(article: dict) -> dict:
    """Shape one candidate article into state.

    Give the model the article text, not a summary of it. The evidence-strength
    benchmark scored systematically low when fed three-line summaries, because
    evidence it cannot see is evidence it cannot credit.
    """
    return {
        "title": article.get("title", ""),
        "publication": article.get("source", ""),
        "published": article.get("published", ""),
        "url": article.get("url", ""),
        "text": article.get("text", ""),
    }
