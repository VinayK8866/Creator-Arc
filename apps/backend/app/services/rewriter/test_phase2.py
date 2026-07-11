import sys
import os

# Adjust path if run directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.services.rewriter.sanitizer import StyleSanitizer
from app.services.rewriter.dedup import MinHashLSH
from app.services.rewriter.crawler import StyleCrawler


def test_sanitizer():
    print("\n--- Unit Test: StyleSanitizer ---")
    sanitizer = StyleSanitizer(min_words=10, max_words=50) # Use smaller bounds for easy unit testing
    
    # 1. Test HTML stripping & decomposition of unwanted tags
    html_data = (
        "<html><head><style>body {color: red;}</style></head>"
        "<body><nav>Home | Contact</nav><article><h1>Article Title</h1>"
        "<p>This is a paragraph of clean text for testing the HTML parser. 😂</p></article>"
        "<footer>Copyright 2026</footer></body></html>"
    )
    stripped = sanitizer.strip_html(html_data)
    print(f"Stripped text (safe representation): {stripped.strip().encode('ascii', errors='replace').decode('ascii')}")
    assert "Home" not in stripped, "Failed to decompose <nav> elements"
    assert "body {color" not in stripped, "Failed to decompose <style> elements"
    assert "testing" in stripped, "Parsed text is incorrect"
    
    # 2. Test cleaning (emojis and cookie warnings)
    raw_dirty = (
        "This is an article paragraph text. 🚀 Click here to read more about our cookie policy! "
        "All rights reserved. This website uses cookies to optimize performance."
    )
    cleaned = sanitizer.clean_text(raw_dirty)
    print(f"Cleaned text: {cleaned}")
    assert "🚀" not in cleaned, "Failed to strip emojis"
    assert "uses cookies" not in cleaned, "Failed to filter cookie policy boilerplate line"
    
    # 3. Test paragraph extraction and length filters
    html_corpus = (
        "<p>Short line.</p>"
        "<p>This is a paragraph that has enough words to pass our minimum word limit check during extraction.</p>"
        "<p>This is an extremely long paragraph containing way too many redundant words that will exceed the upper limits of our parser check and should be discarded.</p>"
    )
    chunks = sanitizer.extract_style_chunks(html_corpus)
    print(f"Extracted chunks: {chunks}")
    assert len(chunks) == 1, f"Expected exactly 1 chunk. Got: {len(chunks)}"
    assert "minimum word limit" in chunks[0], "Extracted wrong chunk"
    print("StyleSanitizer unit tests: PASS")


def test_lsh_dedup():
    print("\n--- Unit Test: Native MinHash LSH Deduplication ---")
    # Setup LSH with threshold 0.50
    lsh = MinHashLSH(num_perm=64, num_bands=16, threshold=0.50)
    
    doc1 = (
        "Building a SaaS in India is fundamentally different from scaling in the US. "
        "You cannot just copy-paste playbooks. Do one thing first: talk to your early users daily. "
        "We spent lakhs in marketing during our first year, but zero conversions happened. "
        "Only when we began customising for localized payments did growth start prepopulating."
    )
    
    # doc2 changes minor words, should flag as duplicate (high shingle similarity)
    doc2 = (
        "Building a SaaS in India is extremely different from scaling in the United States. "
        "You should not just copy-paste playbooks. Do one thing first: talk to your initial users daily. "
        "We spent lakhs in marketing during our first year, but no conversions happened. "
        "Only when we started customizing for localized payments did growth start prepopulating."
    )
    
    # doc3 is completely different topic, should NOT flag as duplicate
    doc3 = (
        "The weather in Mumbai during the monsoon season is very humid and rainy. "
        "Huge downpours occur almost daily, causing major traffic blocks across the city. "
        "Locals prefer using local trains to travel to work because they are faster."
    )

    # Add doc1 to LSH index
    lsh.add("doc1", doc1)
    
    # Test doc2 (near duplicate)
    is_doc2_dup = lsh.is_duplicate(doc2)
    near_dups = lsh.find_near_duplicates(doc2)
    print(f"Doc2 duplicate match: {is_doc2_dup} (Candidates: {near_dups})")
    assert is_doc2_dup, "LSH failed to flag near-duplicate text"
    
    # Test doc3 (completely different)
    is_doc3_dup = lsh.is_duplicate(doc3)
    print(f"Doc3 duplicate match: {is_doc3_dup}")
    assert not is_doc3_dup, "LSH flagged non-duplicate text as a duplicate"
    
    # Test filter list utility
    raw_list = [doc1, doc2, doc3]
    lsh_filter = MinHashLSH(num_perm=64, num_bands=16, threshold=0.50)
    filtered = lsh_filter.filter_unique(raw_list)
    print(f"Filtered list size: {len(filtered)} (Expected: 2)")
    assert len(filtered) == 2, f"Expected 2 unique docs, got: {len(filtered)}"
    assert doc3 in filtered, "Lost unique doc"
    print("MinHash LSH unit tests: PASS")


def main():
    try:
        test_sanitizer()
        test_lsh_dedup()
        print("\nAll Phase 2 tests passed successfully!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nAssertion failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error running tests: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
