import asyncio
import sys
import os

# Adjust path if run directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.core.database import SessionLocal
from app.models.rewrite_pair import RewritePair
from app.services.rewriter.scorer import AdversarialScorer
from app.services.rewriter.engine import rewriter_engine


def test_onnx_download_and_scoring():
    print("\n--- Unit Test: Local ONNX Classifier Inference ---")
    scorer = AdversarialScorer()
    
    if not scorer.onnx_available:
        print("ONNXScorer Warning: Hugging Face model download or initialization failed (offline environment).")
        print("Verifying fallback scoring path...")
        # Verify fallback scoring runs without crashing
        test_text = "This is a quick sentence to test the fallback scorer."
        score = scorer._score_local_heuristics(test_text)
        assert 0.0 <= score <= 1.0, "Fallback score out of range"
        print("Fallback path checks: PASS")
        return
        
    # Verify model is available (will trigger download on first run)
    assert os.path.exists(scorer.model_path), "Model download failed or missing"
    assert scorer.onnx_available, "ONNX session failed to initialize"
    print("ONNX model download and initialization: PASS")
    
    # Run scoring on some test texts
    text_robotic = (
        "Delving into this crucial topic fosters a tapestry of robust workflows. "
        "Additionally, we must optimize and leverage our catalyst to streamline operations."
    )
    text_human = (
        "Honestly, we just built a prototype. It's rough around the edges, "
        "but it works really well when you hook it up to standard databases."
    )
    
    score_robotic = scorer._score_onnx(text_robotic)
    score_human = scorer._score_onnx(text_human)
    
    print(f"ONNX Robotic Score: {score_robotic:.4f}")
    print(f"ONNX Human Score: {score_human:.4f}")
    
    assert 0.0 <= score_robotic <= 1.0, "Score out of range"
    assert 0.0 <= score_human <= 1.0, "Score out of range"
    print("ONNX scoring inference: PASS")


async def test_rewrite_pair_logging():
    print("\n--- Unit Test: Rewrite Pair Ingestion ---")
    db = SessionLocal()
    try:
        # Clear existing logs for fresh test
        db.query(RewritePair).delete()
        db.commit()
        
        # Verify db insert
        pair = RewritePair(
            original_text="This is the robot text",
            facts=["This is the robot text"],
            humanized_text="This is the human counterpart",
            score=0.12,  # Should mark as candidate (score < 0.15)
            dialect="en-IN"
        )
        db.add(pair)
        db.commit()
        
        # Query it back
        db_pair = db.query(RewritePair).filter(RewritePair.original_text == "This is the robot text").first()
        assert db_pair is not None, "Failed to retrieve saved pair"
        assert db_pair.is_candidate is True, "Candidate flag failed to compute"
        assert db_pair.humanized_text == "This is the human counterpart", "Data mismatch"
        print("RewritePair DB logging check: PASS")
    finally:
        db.close()


async def test_end_to_end_pipeline():
    print("\n--- Integration Test: End-to-End Rewrite Logging Loop ---")
    db = SessionLocal()
    try:
        # Clear logs
        db.query(RewritePair).delete()
        db.commit()
        
        ai_input = "We need to reschedule the meeting. Please reply as soon as possible because we optimize layout."
        
        print("Executing rewrite...")
        result = await rewriter_engine.rewrite(
            text=ai_input,
            tone="professional",
            dialect="en-IN",
            max_retries=1
        )
        
        # Verify a record was automatically written to the database rewrite_pairs table
        log_count = db.query(RewritePair).count()
        print(f"Total rewrite pairs logged in DB: {log_count}")
        assert log_count > 0, "No rewrite pair was logged in the database during the pipeline execution!"
        
        logged_item = db.query(RewritePair).first()
        print(f"Logged Original: {logged_item.original_text}")
        print(f"Logged Humanized: {logged_item.humanized_text}")
        print(f"Logged Score: {logged_item.score:.4f}")
        print(f"Logged Candidate: {logged_item.is_candidate}")
        
        assert logged_item.original_text == ai_input, "Logged original text mismatch"
        print("End-to-End Pipeline Logging: PASS")
        
    finally:
        db.close()


async def main():
    try:
        test_onnx_download_and_scoring()
        await test_rewrite_pair_logging()
        await test_end_to_end_pipeline()
        print("\nAll Phase 4 tests passed successfully!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nAssertion failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error running tests: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
