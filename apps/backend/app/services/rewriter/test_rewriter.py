import asyncio
import sys
from app.core.database import SessionLocal
from app.services.rewriter.lexicon import LexiconProcessor
from app.services.rewriter.scorer import AdversarialScorer
from app.services.rewriter.engine import rewriter_engine
from app.services.rewriter.migration import seed_style_references
from app.models.style_reference import StyleReference


def test_lexicon():
    print("\n--- Testing Lexicon Instruction Generation ---")
    # Verify en-IN instruction content
    in_instructions = LexiconProcessor.get_dialect_instructions("en-IN")
    assert "prepone" in in_instructions
    assert "kindly revert" in in_instructions
    assert "PFA" in in_instructions
    print("en-IN instructions test: PASS")

    # Verify en-US instructions are empty
    us_instructions = LexiconProcessor.get_dialect_instructions("en-US")
    assert us_instructions == "", f"Expected empty instructions for en-US. Got: {us_instructions}"
    print("en-US instructions test: PASS")

    # Test basic translate casing formatting
    pfa_test = "Please check the pfa for details."
    translated_pfa = LexiconProcessor.translate(pfa_test, dialect="en-IN")
    assert "PFA" in translated_pfa, f"Expected PFA to be capitalized. Got: {translated_pfa}"
    print("Translate capitalization test: PASS")


def test_local_scorer():
    print("\n--- Testing Local Scorer Heuristics ---")
    scorer = AdversarialScorer()

    # Robotic, uniform sentence length with clichés
    robotic_text = (
        "Delving into this crucial topic fosters a tapestry of robust workflows. "
        "Additionally, we must optimize and leverage our catalyst to streamline operations. "
        "In conclusion, this testament is pivotal to navigate the changing landscape."
    )
    # Bursty, varied text with no clichés
    human_text = (
        "Let's get this straight. We failed. Our ads didn't convert, and we lost thousands. "
        "But instead of giving up, we started talking directly to our customers. "
        "It turned everything around."
    )

    robotic_score = scorer._score_local_heuristics(robotic_text)
    human_score = scorer._score_local_heuristics(human_text)
    
    print(f"Robotic heuristic score: {robotic_score:.4f}")
    print(f"Human heuristic score: {human_score:.4f}")
    
    assert robotic_score > human_score, f"Robotic text should score higher than human text. {robotic_score} <= {human_score}"
    print("Heuristic scoring test: PASS")


async def test_end_to_end():
    print("\n--- Testing Database Seeding & End-to-End RAG Rewrite ---")
    db = SessionLocal()
    try:
        # Step 1: Force seed the style templates database
        print("Seeding database...")
        seed_style_references(db, force_reseed=True)
        
        # Verify db counts
        ref_count = db.query(StyleReference).count()
        print(f"Total seeded references in DB: {ref_count}")
        assert ref_count > 0, "No references seeded"

        # Step 2: Run End-to-End rewrite for Indian English
        ai_input = (
            "Please reply as soon as possible. We need to reschedule the meeting to an earlier date "
            "because our key client is travelling. Please find the attached file containing the updated proposal. "
            "It is highly crucial that we optimize this layout to streamline the pipeline and delve deeper."
        )
        
        print("\nExecuting rewrite pipeline...")
        result = await rewriter_engine.rewrite(
            text=ai_input,
            tone="professional",
            dialect="en-IN",
            max_retries=2
        )
        
        print("\n=== REWRITE RESULT ===")
        print(f"Original Text:\n{result['original']}\n")
        print(f"Rewritten Text:\n{result['rewritten']}\n")
        print(f"Adversarial Score: {result['score']:.4f}")
        print(f"Attempts: {result['attempts']}")
        print(f"Status: {result['status']}")
        
        assert result["score"] >= 0.0, "Score is invalid"
        assert "nli_score" in result, "NLI score is missing in result"
        assert result["nli_score"] >= 0.0, "NLI score is invalid"

        # Verify that Indian English terms are produced natively by the LLM
        rewritten_lower = result["rewritten"].lower()
        has_indian_phrasing = any(
            phrase in rewritten_lower for phrase in ["prepone", "revert", "pfa", "discuss about", "do one thing"]
        )
        assert has_indian_phrasing, f"Expected Indian English terms in rewritten text. Got: {result['rewritten']}"
        print("End-to-End Rewrite Test: PASS")

    finally:
        db.close()


async def main():
    try:
        test_lexicon()
        test_local_scorer()
        await test_end_to_end()
        print("\nAll tests passed successfully!")
        sys.exit(0)
    except AssertionError as ae:
        print(f"\nAssertion error occurred: {str(ae)}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during execution: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
