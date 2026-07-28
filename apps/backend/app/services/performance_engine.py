import json
import re
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import google.generativeai as genai

from app.core.config import settings
from app.models.blog_post import BlogPost
from app.models.performance_snapshot import PerformanceSnapshot
from app.models.learned_insight import LearnedInsight
from app.services.rewriter.governor import APIGovernor, FALLBACK_MODELS

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


class PerformanceEngine:
    def __init__(self):
        self.models = FALLBACK_MODELS

    def extract_metrics_from_screenshot(self, image_bytes: bytes, mime_type: str = "image/png") -> dict:
        """Uses Gemini Vision (multimodal) to OCR and parse key analytics metrics from a Medium/Platform stats screenshot."""
        if not settings.GEMINI_API_KEY:
            return {
                "views": 1500,
                "reads": 900,
                "read_ratio": 0.60,
                "claps": 320,
                "fans": 45,
                "highlights": 12,
                "responses": 8,
                "external_views": 400,
                "internal_views": 1100,
                "new_followers": 15,
                "raw_text": "Mock OCR extraction payload",
                "confidence": 0.95
            }

        prompt = (
            "You are an expert analytics OCR parser specializing in Medium & blogging platform stats dashboards.\n"
            "Analyze the provided image of a story/article statistics page carefully.\n"
            "Extract the numerical performance metrics and return a single valid JSON object containing exactly these fields:\n"
            "- \"views\": integer (total views)\n"
            "- \"reads\": integer (total reads)\n"
            "- \"read_ratio\": float between 0.0 and 1.0 (e.g. 0.58 for 58% read ratio)\n"
            "- \"claps\": integer (total claps/applause)\n"
            "- \"fans\": integer (unique readers who clapped)\n"
            "- \"highlights\": integer (number of highlights)\n"
            "- \"responses\": integer (comments/responses)\n"
            "- \"external_views\": integer (views from search engines, twitter, etc., if shown, else 0)\n"
            "- \"internal_views\": integer (views from Medium platform/feed, if shown, else 0)\n"
            "- \"new_followers\": integer (followers gained from this story, if shown, else 0)\n"
            "- \"confidence\": float between 0.0 and 1.0 indicating your confidence in data accuracy\n"
            "- \"raw_text\": string summarizing what you read from the screenshot\n\n"
            "Respond ONLY with valid JSON. Do not include markdown code block formatting."
        )

        last_err = None
        for model_name in self.models:
            try:
                APIGovernor.pace()
                model = genai.GenerativeModel(model_name=model_name)
                response = model.generate_content([
                    prompt,
                    {"mime_type": mime_type, "data": image_bytes}
                ])

                text_resp = response.text.strip()
                if text_resp.startswith("```"):
                    text_resp = text_resp.split("\n", 1)[1].rsplit("\n", 1)[0]
                    if text_resp.startswith("json"):
                        text_resp = text_resp[4:].strip()

                data = json.loads(text_resp)
                # Ensure read_ratio is normalized float
                if "read_ratio" in data and isinstance(data["read_ratio"], (int, float)):
                    if data["read_ratio"] > 1.0:
                        data["read_ratio"] = round(data["read_ratio"] / 100.0, 4)
                return data
            except Exception as e:
                last_err = e
                print(f"Gemini Vision extraction failed on model {model_name}: {str(e)}")
                continue

        # Fallback dictionary if OCR fails
        return {
            "views": 0,
            "reads": 0,
            "read_ratio": 0.0,
            "claps": 0,
            "fans": 0,
            "highlights": 0,
            "responses": 0,
            "external_views": 0,
            "internal_views": 0,
            "new_followers": 0,
            "raw_text": f"Failed extraction: {str(last_err)}",
            "confidence": 0.0
        }

    def generate_learned_insights(self, db: Session) -> List[LearnedInsight]:
        """Analyzes all published posts and their performance snapshots to discover rule correlations
        and upsert actionable learned insights for prompt injection.
        """
        published_posts = db.query(BlogPost).filter(BlogPost.publication_status == "published").all()
        if not published_posts:
            return []

        insights_to_upsert = []

        # Analyze read ratio vs rule compliance
        rule_performance_map: Dict[str, List[float]] = {}
        rule_views_map: Dict[str, List[int]] = {}

        for post in published_posts:
            latest_snap = (
                db.query(PerformanceSnapshot)
                .filter(PerformanceSnapshot.blog_post_id == post.id)
                .order_by(PerformanceSnapshot.snapshot_week.desc())
                .first()
            )
            if not latest_snap or not latest_snap.extracted_metrics:
                continue

            metrics = latest_snap.extracted_metrics
            read_ratio = metrics.get("read_ratio", 0.0)
            views = metrics.get("views", 0)
            audit = post.strategy_audit or {}
            passed_rules = audit.get("passed_rules", [])

            for r in passed_rules:
                r_id = r.get("id") if isinstance(r, dict) else str(r)
                if r_id:
                    rule_performance_map.setdefault(r_id, []).append(read_ratio)
                    rule_views_map.setdefault(r_id, []).append(views)

        # Evaluate rules that consistently yield > 55% read ratio or high views
        for rule_id, ratios in rule_performance_map.items():
            if len(ratios) >= 1:  # min sample size
                avg_rr = float(sum(ratios) / len(ratios))
                avg_v = float(sum(rule_views_map[rule_id]) / len(rule_views_map[rule_id]))

                if avg_rr >= 0.50:
                    insight_str = (
                        f"Rule {rule_id} compliance correlated with a high average read ratio of {avg_rr:.1%}. "
                        f"Strictly maintain this pattern in post structure."
                    )
                    confidence = min(0.5 + (len(ratios) * 0.1), 0.95)

                    # Check if already exists
                    existing = (
                        db.query(LearnedInsight)
                        .filter(LearnedInsight.rule_id == rule_id, LearnedInsight.source == "auto")
                        .first()
                    )
                    if existing:
                        existing.insight_text = insight_str
                        existing.confidence_score = confidence
                        existing.sample_size = len(ratios)
                        existing.avg_read_ratio = avg_rr
                        existing.avg_views = avg_v
                        insights_to_upsert.append(existing)
                    else:
                        new_insight = LearnedInsight(
                            insight_type="structural",
                            rule_id=rule_id,
                            insight_text=insight_str,
                            confidence_score=confidence,
                            sample_size=len(ratios),
                            avg_read_ratio=avg_rr,
                            avg_views=avg_v,
                            is_active=True,
                            source="auto"
                        )
                        db.add(new_insight)
                        insights_to_upsert.append(new_insight)

        db.commit()
        return insights_to_upsert

    def get_active_insights_prompt(self, db: Session) -> str:
        """Retrieves active learned insights and formats them as a prompt injection block."""
        active = (
            db.query(LearnedInsight)
            .filter(LearnedInsight.is_active == True)
            .order_by(LearnedInsight.confidence_score.desc())
            .limit(5)
            .all()
        )

        if not active:
            return ""

        lines = ["\nLEARNED FROM PAST PERFORMANCE DATA (Self-Learning Feedback Loop):"]
        for ins in active:
            lines.append(f"- [{ins.insight_type.upper()}] {ins.insight_text} (Confidence: {ins.confidence_score:.0%})")
        lines.append("Enforce these proven performance principles in this generation.\n")
        return "\n".join(lines)


performance_engine = PerformanceEngine()
