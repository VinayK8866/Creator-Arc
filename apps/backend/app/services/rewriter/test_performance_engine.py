import unittest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.blog_post import BlogPost
from app.models.performance_snapshot import PerformanceSnapshot
from app.models.learned_insight import LearnedInsight
from app.services.performance_engine import performance_engine


class TestPerformanceEngine(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_extract_metrics_mock(self):
        metrics = performance_engine.extract_metrics_from_screenshot(b"fake_image_bytes")
        self.assertIn("views", metrics)
        self.assertIn("reads", metrics)
        self.assertIn("read_ratio", metrics)
        self.assertIn("confidence", metrics)

    def test_generate_learned_insights(self):
        # Create sample published post with audit data
        post = BlogPost(
            topic="UPI Digital Infrastructure",
            platform="medium",
            suggested_title="How UPI Changed India",
            publication_status="published",
            published_url="https://medium.com/@test/upi-digital",
            published_at=datetime.datetime.utcnow(),
            strategy_audit={
                "passed_rules": [{"id": "SR-01"}, {"id": "SR-02"}, {"id": "AD-25"}]
            }
        )
        self.db.add(post)
        self.db.commit()

        # Create high-performing snapshot
        snap = PerformanceSnapshot(
            blog_post_id=post.id,
            snapshot_week=1,
            extracted_metrics={
                "views": 2500,
                "reads": 1500,
                "read_ratio": 0.60,
                "claps": 450,
                "fans": 80
            }
        )
        self.db.add(snap)
        self.db.commit()

        # Run insights generator
        insights = performance_engine.generate_learned_insights(self.db)
        self.assertGreaterEqual(len(insights), 1)
        self.assertTrue(any(i.rule_id == "SR-01" for i in insights))

        # Verify prompt string builder
        prompt = performance_engine.get_active_insights_prompt(self.db)
        self.assertIn("LEARNED FROM PAST PERFORMANCE DATA", prompt)
        self.assertIn("SR-01", prompt)


if __name__ == "__main__":
    unittest.main()
