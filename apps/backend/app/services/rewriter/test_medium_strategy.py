import sys
import os

# Ensure backend directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.services.medium_strategy_engine import medium_strategy_engine


def test_title_package_generation():
    """Verify title package generator returns valid dual-title metadata and respects SEO character limits."""
    topic = "Medium SEO Optimization Strategies"
    focus_keyword = "Medium SEO"
    
    pkg = medium_strategy_engine.generate_title_package(topic, focus_keyword)
    
    assert "title_variations" in pkg, "Missing title_variations"
    assert len(pkg["title_variations"]) >= 1, "Should have at least 1 title variation"
    assert "feed_title" in pkg, "Missing feed_title"
    assert "seo_title" in pkg, "Missing seo_title"
    assert "url_slug" in pkg, "Missing url_slug"
    assert len(pkg["seo_title"]) <= 60, f"SEO title exceeds 60 chars: {pkg['seo_title']}"
    assert len(pkg["seo_title"].split()) <= 9, f"SEO title exceeds 9 words: {pkg['seo_title']}"
    assert "-" in pkg["url_slug"] or pkg["url_slug"].isalnum(), f"Invalid slug: {pkg['url_slug']}"
    print("[OK] test_title_package_generation passed")


def test_compliance_disclosures_injection():
    """Verify AI disclosures, FTC affiliate notices, and offsite link notices are correctly injected."""
    raw_markdown = "# Test Title\n\nThis is paragraph one.\n\nThis is paragraph two.\n\n[Check out Gumroad](https://gumroad.com)"
    
    updated, flags = medium_strategy_engine.inject_compliance_disclosures(
        markdown=raw_markdown,
        is_ai_assisted=True,
        has_affiliate_links=True,
        has_offsite_forms=True
    )
    
    assert flags["ai_disclosure_injected"] is True, "AI disclosure should be marked injected"
    assert "*This story was written with the assistance of an AI writing program.*" in updated, "AI disclosure text missing"
    assert flags["ftc_affiliate_injected"] is True, "FTC affiliate should be marked injected"
    assert "Disclosure: This post contains affiliate links" in updated, "FTC disclaimer text missing"
    assert flags["offsite_notice_injected"] is True, "Offsite notice should be marked injected"
    assert "lead offsite outside Medium" in updated, "Offsite notice text missing"
    print("[OK] test_compliance_disclosures_injection passed")


def test_anti_pattern_sanitizer():
    """Verify anti-pattern sanitizer removes AI clichés, primitive dividers, and algorithm begging."""
    dirty_markdown = (
        "# Title\n\n"
        "Moreover, in today's digital landscape, we must consider this.\n\n"
        "Please stay on this page for at least 30 seconds so Medium pays me.\n\n"
        "Leave a comment down below in the description below.\n\n"
        "--------------------\n\n"
        "Furthermore, here is Part Two."
    )
    
    clean = medium_strategy_engine.sanitize_markdown(dirty_markdown)
    
    assert "Moreover," not in clean, "Moreover should be stripped"
    assert "Furthermore," not in clean, "Furthermore should be stripped"
    assert "in today's digital landscape" not in clean, "Digital landscape cliché should be stripped"
    assert "stay on this page for at least 30 seconds" not in clean, "Algorithm begging should be stripped"
    assert "in the description below" not in clean, "Cross-post terminology error should be replaced"
    assert "--------------------" not in clean, "Primitive divider should be converted"
    assert "---" in clean, "Clean divider (---) should be present"
    print("[OK] test_anti_pattern_sanitizer passed")


def test_header_and_footer_architecture():
    """Verify official Medium 5-element header and master footer architecture generation."""
    header = medium_strategy_engine.build_5_step_header_block(
        kicker="GUIDE",
        title="Mastering Medium SEO",
        subtitle="A practitioner guide to scaling views",
        reader_promise="I promise in this post I will teach you Medium SEO.",
        lead_magnet_url="https://gumroad.com"
    )
    
    assert "**GUIDE**" in header, "Kicker missing from header"
    assert "# Mastering Medium SEO" in header, "H1 title missing from header"
    assert "### A practitioner guide to scaling views" in header, "Subtitle missing from header"
    assert "I promise in this post I will teach you Medium SEO." in header, "Promise formula missing"
    assert "gumroad.com" in header, "Lead magnet link missing"

    footer = medium_strategy_engine.build_footer_architecture(
        topic="Medium SEO",
        bullet_summary=["Optimize titles for SERPs", "Use micro-paragraphs", "Enforce 55% read ratio"],
        lead_magnet_url="https://gumroad.com",
        newsletter_url="https://substack.com"
    )
    
    assert "## Action Summary & Key Takeaways" in footer, "Action summary header missing"
    assert "Optimize titles for SERPs" in footer, "Summary bullets missing"
    assert "### Over to You" in footer, "Closing prompt missing"
    assert "**P.S.**" in footer, "Postscript missing"
    assert "### Creator Resources & Ecosystem" in footer, "Ecosystem header missing"
    assert "### Recommended Reading Next" in footer, "Recommended reading cascade missing"
    assert "Become a Medium Member" in footer, "Member referral blurb missing"
    print("[OK] test_header_and_footer_architecture passed")


def test_tk_action_markers_and_audit_engine():
    """Verify TK native safety markers and post-generation strategy compliance auditing."""
    sample_markdown = (
        "**GUIDE**\n\n# Mastering Medium SEO\n\n### A practitioner guide\n\n"
        "![Hero Image](https://images.unsplash.com/photo-1499750310107-5fef28a66643)\n*Photo via Unsplash*\n\n"
        "*This story was written with the assistance of an AI writing program.*\n\n"
        "## Part One: Core Concepts\n\nHere is the first core section.\n\n"
        "## Part Two: Deep Dive\n\nHere is the second deep dive section.\n\n"
        "Note: External links lead offsite outside Medium.\n\n"
        "Disclosure: This post contains affiliate links."
    )

    # 1. Test TK Action Marker Injection
    tk_injected = medium_strategy_engine.inject_tk_action_placeholders(sample_markdown, "Medium SEO")
    assert "TK_HERO_IMAGE" in tk_injected, "TK_HERO_IMAGE missing"
    assert "TK_BODY_IMAGE_1" in tk_injected, "TK_BODY_IMAGE_1 missing"
    assert "TK_FRIEND_LINK" in tk_injected, "TK_FRIEND_LINK missing"
    print("[OK] inject_tk_action_placeholders passed")

    # 2. Test Rule Audit Compliance Engine
    meta = {
        "topic": "Medium SEO",
        "seo_title": "Medium SEO 2026 Guide",
        "feed_title": "How I Mastered Medium SEO",
        "url_slug": "medium-seo-guide",
        "kicker": "GUIDE",
        "subtitle": "A practitioner guide"
    }

    audit = medium_strategy_engine.audit_rule_compliance(tk_injected, meta)
    assert audit["score"] >= 80, f"Expected high audit score, got {audit['score']}"
    assert len(audit["passed_rules"]) >= 4, "Passed rules count should be >= 4"
    assert len(audit["action_items"]) >= 1, "Action items should contain TK placeholders"
    assert len(audit["tag_recommendations"]) == 5, "Should recommend exactly 5 topic tags"
    print("[OK] audit_rule_compliance passed")

    # 3. Test Audit Report Markdown Generation
    report_md = medium_strategy_engine.generate_audit_report_markdown(audit)
    assert "# 🛡️ Medium Strategy & Compliance Audit Report" in report_md
    assert "AUTOMATICALLY ENFORCED RULES" in report_md
    assert "PENDING USER ACTION ITEMS" in report_md
    assert "PRE-PUBLISHING METADATA RECOMMENDATIONS" in report_md
    print("[OK] generate_audit_report_markdown passed")


if __name__ == "__main__":
    print("Running Medium Strategy Engine Unit Tests...")
    test_title_package_generation()
    test_compliance_disclosures_injection()
    test_anti_pattern_sanitizer()
    test_header_and_footer_architecture()
    test_tk_action_markers_and_audit_engine()
    print("\nALL TESTS PASSED SUCCESSFULLY!")
