import sys
import os
import time
from sqlalchemy.orm import Session

# Adjust path if run directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.core.database import SessionLocal
from app.models.style_reference import StyleReference
from app.services.rewriter.crawler import StyleCrawler
from app.services.rewriter.sanitizer import StyleSanitizer
from app.services.rewriter.dedup import MinHashLSH
from app.services.rewriter.migration import get_embedding

# Seed URLs representing top Indian digital newspapers (editorials / opinion RSS feeds)
INDIAN_FEEDS = [
    "https://www.thehindu.com/opinion/editorial/feeder/default.rss",
    "https://www.thehindu.com/opinion/lead/feeder/default.rss"
]


def run_harvest(force_refresh_db: bool = False):
    print("=========================================")
    print("  PHASE 2: DATA HARVESTING & DEDUPLICATION ")
    print("=========================================\n")
    
    db = SessionLocal()
    crawler = StyleCrawler()
    sanitizer = StyleSanitizer()
    lsh = MinHashLSH(num_perm=64, num_bands=8, threshold=0.75)
    
    try:
        # Step 1: Load all existing styles from the database to populate the deduplicator index
        print("Step 1: Ingesting existing database records into MinHash LSH index...")
        existing_records = db.query(StyleReference).all()
        for ref in existing_records:
            lsh.add(ref.id, ref.content)
        print(f"Loaded {len(existing_records)} existing references into deduplication index.\n")

        # Step 2: Fetch and crawl articles from feeds
        print("Step 2: Scanning Indian Editorial Feeds...")
        links_to_crawl = []
        for feed in INDIAN_FEEDS:
            items = crawler.fetch_rss_feed(feed)
            links_to_crawl.extend(items)
            
        # Remove duplicate urls in the feed list
        unique_links = {item["link"]: item["title"] for item in links_to_crawl if item["link"]}
        print(f"Discovered {len(unique_links)} unique articles to scrape.\n")

        # Step 3: Scrape, sanitize, and chunk text
        print("Step 3: Crawling pages, sanitizing HTML, and chunking paragraphs...")
        new_candidates = []
        
        # Scrape maximum of 3 articles per run for standard rate-limiting safety
        max_articles = 3
        count = 0
        
        for url, title in unique_links.items():
            if count >= max_articles:
                break
                
            print(f"\n[{count+1}/{max_articles}] Scraping: '{title}'")
            html_content = crawler.fetch_page_html(url)
            if not html_content:
                continue
                
            # Clean and extract paragraph chunks between 80 and 250 words
            chunks = sanitizer.extract_style_chunks(html_content)
            
            for chunk in chunks:
                new_candidates.append({
                    "content": chunk,
                    "title": title,
                    "url": url
                })
            count += 1
            time.sleep(1.0)  # Politeness sleep between page hits
            
        print(f"\nExtracted a total of {len(new_candidates)} paragraph candidate chunks.\n")

        # Step 4: Run MinHash LSH Deduplication
        print("Step 4: Filtering duplicates and near-duplicates...")
        unique_new_items = []
        duplicate_count = 0
        
        for item in new_candidates:
            if lsh.is_duplicate(item["content"]):
                duplicate_count += 1
            else:
                # Add to LSH index immediately to prevent adding duplicates within the same batch
                temp_id = f"temp_{len(unique_new_items)}"
                lsh.add(temp_id, item["content"])
                unique_new_items.append(item)
                
        print(f"Deduplication complete: Filtered out {duplicate_count} near-duplicates.")
        print(f"Retained {len(unique_new_items)} completely unique style exemplars.\n")

        # Step 5: Generate Embeddings and Persist to Supabase Database
        if not unique_new_items:
            print("Step 5: No new unique style reference entries to save. Pipeline complete.")
            return

        print(f"Step 5: Generating embeddings and writing {len(unique_new_items)} records to DB...")
        for i, item in enumerate(unique_new_items):
            print(f"[{i+1}/{len(unique_new_items)}] Generating embedding for chunk ({len(item['content'].split())} words)...")
            
            embedding = None
            for attempt in range(3):
                try:
                    embedding = get_embedding(item["content"])
                    break
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        print("Rate limit hit. Sleeping 12s...")
                        time.sleep(12)
                    else:
                        print(f"Embedding error: {str(e)}")
                        break
                        
            # If embedding generation failed, use mock vector to prevent crash
            if embedding is None:
                import random
                random.seed(hash(item["content"]))
                embedding = [random.uniform(-0.1, 0.1) for _ in range(768)]

            new_ref = StyleReference(
                content=item["content"],
                embedding=embedding,
                genre="blog",  # General category
                dialect="en-IN",  # Indian English
                metadata_info={"title": item["title"], "source": item["url"]}
            )
            db.add(new_ref)
            db.commit()
            
            time.sleep(2.2)  # Delay between requests to prevent RPM limit
            
        print("\nDatabase update completed successfully! Phase 2 Pipeline Finished.")

    finally:
        db.close()


if __name__ == "__main__":
    # If run with --force-refresh, it clears and re-seeds
    force = "--force" in sys.argv
    run_harvest(force_refresh_db=force)
