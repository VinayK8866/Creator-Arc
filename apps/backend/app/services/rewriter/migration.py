import os
import random
import time
from sqlalchemy import text
from sqlalchemy.orm import Session
import google.generativeai as genai
from app.core.config import settings
from app.core.database import Base
from app.models.style_reference import StyleReference

# Ensure Gemini is configured
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


def get_embedding(text: str) -> list:
    """Generate text embeddings using Gemini or fallback to a dummy vector if dev mode/quota errors."""
    if not settings.GEMINI_API_KEY:
        # Return a mock 768-dimension float vector for local development offline
        random.seed(hash(text))
        return [random.uniform(-0.1, 0.1) for _ in range(768)]
    
    # Try models in order of preference
    for model_name in ["models/text-embedding-004", "models/embedding-001"]:
        try:
            response = genai.embed_content(
                model=model_name,
                content=text,
                task_type="retrieval_document"
            )
            return response["embedding"]
        except Exception as e:
            err_msg = str(e)
            if "404" in err_msg or "not found" in err_msg.lower() or "not supported" in err_msg.lower():
                print(f"Embedding model {model_name} not supported or not found. Trying fallback...")
                continue
            if "429" in err_msg or "quota" in err_msg.lower():
                print(f"Rate limit hit on {model_name}. Retrying shortly...")
                raise e
            print(f"Error calling {model_name}: {err_msg}. Trying fallback...")
            
    print("All embedding models failed. Using fallback mock vector.")
    random.seed(hash(text))
    return [random.uniform(-0.1, 0.1) for _ in range(768)]


# Stylistic reference seed texts based on the 4 Core Domains:
# - corporate_email
# - tech_blog
# - academic_essay
# - general_content
SEED_DATA = [
    {
        "domain": "corporate_email",
        "dialect": "en-IN",
        "content": (
            "Hi team, PFA the draft project report for your review. Kindly check and revert with your "
            "feedback at the earliest. We can prepone our weekly sync to tomorrow morning if you want "
            "to discuss about the feedback in detail. Regards, Rohit"
        ),
        "payload": {
            "text": (
                "Hi team, PFA the draft project report for your review. Kindly check and revert with your "
                "feedback at the earliest. We can prepone our weekly sync to tomorrow morning if you want "
                "to discuss about the feedback in detail. Regards, Rohit"
            ),
            "domain": "corporate_email",
            "tone": "formal",
            "word_count": 42
        }
    },
    {
        "domain": "corporate_email",
        "dialect": "en-IN",
        "content": (
            "Dear Sir, With reference to our discussion yesterday, I have updated the proposal. "
            "Kindly do the needful and revert back with your confirmation. If there are any changes, "
            "do one thing: mark them directly in the shared document so I can address them. "
            "PFA the invoice copy as well. Thanks and regards."
        ),
        "payload": {
            "text": (
                "Dear Sir, With reference to our discussion yesterday, I have updated the proposal. "
                "Kindly do the needful and revert back with your confirmation. If there are any changes, "
                "do one thing: mark them directly in the shared document so I can address them. "
                "PFA the invoice copy as well. Thanks and regards."
            ),
            "domain": "corporate_email",
            "tone": "formal",
            "word_count": 52
        }
    },
    {
        "domain": "tech_blog",
        "dialect": "en-IN",
        "content": (
            "Building a SaaS in India is fundamentally different from scaling in the US. You cannot just "
            "copy-paste playbooks. Do one thing first: talk to your early users daily. We spent lakhs "
            "in marketing during our first year, but zero conversions happened. Only when we began "
            "customising for localized UPI payments and WhatsApp workflows did growth start picking up. "
            "Now, we are targeting a crore in ARR by next quarter. Let's see how it goes."
        ),
        "payload": {
            "text": (
                "Building a SaaS in India is fundamentally different from scaling in the US. You cannot just "
                "copy-paste playbooks. Do one thing first: talk to your early users daily. We spent lakhs "
                "in marketing during our first year, but zero conversions happened. Only when we began "
                "customising for localized UPI payments and WhatsApp workflows did growth start picking up. "
                "Now, we are targeting a crore in ARR by next quarter. Let's see how it goes."
            ),
            "domain": "tech_blog",
            "tone": "casual",
            "word_count": 68
        }
    },
    {
        "domain": "tech_blog",
        "dialect": "en-IN",
        "content": (
            "Many tech graduates today want to jump straight into product startups. But working in a product "
            "firm requires a massive mindset shift from services. Here, you don't just follow instructions; "
            "you own the outcome. You are expected to build features from scratch, debug them in production, "
            "and discuss about user feedback directly. It is challenging, but the learning curve is immense."
        ),
        "payload": {
            "text": (
                "Many tech graduates today want to jump straight into product startups. But working in a product "
                "firm requires a massive mindset shift from services. Here, you don't just follow instructions; "
                "you own the outcome. You are expected to build features from scratch, debug them in production, "
                "and discuss about user feedback directly. It is challenging, but the learning curve is immense."
            ),
            "domain": "tech_blog",
            "tone": "professional",
            "word_count": 59
        }
    },
    {
        "domain": "academic_essay",
        "dialect": "en-IN",
        "content": (
            "We must examine this research hypothesis carefully. In NPTEL lectures on advanced computer architectures, "
            "instructors emphasize that memory hierarchies dictate compute throughput. Kindly do the needful and "
            "discuss about the experimental methodology in your write-up. We should prepone the thesis review "
            "to ensure all corrections are integrated before final submission."
        ),
        "payload": {
            "text": (
                "We must examine this research hypothesis carefully. In NPTEL lectures on advanced computer architectures, "
                "instructors emphasize that memory hierarchies dictate compute throughput. Kindly do the needful and "
                "discuss about the experimental methodology in your write-up. We should prepone the thesis review "
                "to ensure all corrections are integrated before final submission."
            ),
            "domain": "academic_essay",
            "tone": "academic",
            "word_count": 52
        }
    },
    {
        "domain": "general_content",
        "dialect": "en-IN",
        "content": (
            "A lot of people ask me about transition habits when moving from a services company to a product startup. "
            "Here is the reality. It's not about working longer hours. It's about taking ownership. "
            "In my previous role, everything was structured and pre-defined. But in a fast-growing startup, "
            "you have to build from scratch. PFA my list of core learnings from the past year. Kindly share your thoughts. "
            "#StartupLife #GrowthMindset"
        ),
        "payload": {
            "text": (
                "A lot of people ask me about transition habits when moving from a services company to a product startup. "
                "Here is the reality. It's not about working longer hours. It's about taking ownership. "
                "In my previous role, everything was structured and pre-defined. But in a fast-growing startup, "
                "you have to build from scratch. PFA my list of core learnings from the past year. Kindly share your thoughts. "
                "#StartupLife #GrowthMindset"
            ),
            "domain": "general_content",
            "tone": "casual",
            "word_count": 62
        }
    },
    {
        "domain": "general_content",
        "dialect": "en-IN",
        "content": (
            "Excited to share that our team has successfully shipped the new design module! "
            "Special thanks to the engineering team for working day in and day out to make this happen. "
            "We had to prepone the release due to client requirements, but the team delivered flawlessly. "
            "Kindly check out the live demo link in the comments and let me know your thoughts. "
            "Cheers! #ProductLaunch #TechIndia"
        ),
        "payload": {
            "text": (
                "Excited to share that our team has successfully shipped the new design module! "
                "Special thanks to the engineering team for working day in and day out to make this happen. "
                "We had to prepone the release due to client requirements, but the team delivered flawlessly. "
                "Kindly check out the live demo link in the comments and let me know your thoughts. "
                "Cheers! #ProductLaunch #TechIndia"
            ),
            "domain": "general_content",
            "tone": "enthusiastic",
            "word_count": 52
        }
    },
    # Singapore English (en-SG)
    {
        "domain": "corporate_email",
        "dialect": "en-SG",
        "content": (
            "Dear team, PFA the project update report. Kindly check and revert at the earliest. "
            "We had to prepone the meeting to this morning to discuss the changes. Otherwise, we might "
            "miss the deadline, which would make us look kiasu. Please take MC if you are feeling unwell. "
            "Thanks, Tan."
        ),
        "payload": {
            "text": (
                "Dear team, PFA the project update report. Kindly check and revert at the earliest. "
                "We had to prepone the meeting to this morning to discuss the changes. Otherwise, we might "
                "miss the deadline, which would make us look kiasu. Please take MC if you are feeling unwell. "
                "Thanks, Tan."
            ),
            "domain": "corporate_email",
            "tone": "formal",
            "word_count": 48
        }
    },
    {
        "domain": "tech_blog",
        "dialect": "en-SG",
        "content": (
            "Starting a tech business in Singapore requires high agility and a solid local network. "
            "Don't be kiasu about sharing your ideas; early feedback is essential. Our team had to prepone "
            "our launch date by two weeks to align with SG government grant guidelines. PFA our checklist "
            "of registration requirements. Let's chop the agreement soon."
        ),
        "payload": {
            "text": (
                "Starting a tech business in Singapore requires high agility and a solid local network. "
                "Don't be kiasu about sharing your ideas; early feedback is essential. Our team had to prepone "
                "our launch date by two weeks to align with SG government grant guidelines. PFA our checklist "
                "of registration requirements. Let's chop the agreement soon."
            ),
            "domain": "tech_blog",
            "tone": "professional",
            "word_count": 54
        }
    },
    # Australian English (en-AU)
    {
        "domain": "corporate_email",
        "dialect": "en-AU",
        "content": (
            "Hi mate, here is the proposal for the new project. We need to finalize it this arvo "
            "before the weekly sync. No worries if you need a fortnight to check everything, but "
            "the sooner the better. Let me know if you want to catch up at the local uni or over a barbie "
            "to discuss details. Cheers, Dave."
        ),
        "payload": {
            "text": (
                "Hi mate, here is the proposal for the new project. We need to finalize it this arvo "
                "before the weekly sync. No worries if you need a fortnight to check everything, but "
                "the sooner the better. Let me know if you want to catch up at the local uni or over a barbie "
                "to discuss details. Cheers, Dave."
            ),
            "domain": "corporate_email",
            "tone": "friendly",
            "word_count": 54
        }
    },
    {
        "domain": "tech_blog",
        "dialect": "en-AU",
        "content": (
            "Growing a product business in Australia takes a lot of resilience. We started our journey "
            "at the local uni, working out of a small garage. It took us a fortnight of solid coding "
            "to build the prototype. We finally launched it last Friday arvo, and the response has been "
            "amazing. No worries if things are slow initially; focus on the product."
        ),
        "payload": {
            "text": (
                "Growing a product business in Australia takes a lot of resilience. We started our journey "
                "at the local uni, working out of a small garage. It took us a fortnight of solid coding "
                "to build the prototype. We finally launched it last Friday arvo, and the response has been "
                "amazing. No worries if things are slow initially; focus on the product."
            ),
            "domain": "tech_blog",
            "tone": "casual",
            "word_count": 58
        }
    },
    # British English (en-GB)
    {
        "domain": "corporate_email",
        "dialect": "en-GB",
        "content": (
            "Hi team, I've analysed the recent metrics and updated the draft report. We must organise "
            "our holiday schedules so we don't delay the launch. I realise this is short notice, but "
            "defence of our market share is critical. PFA the detailed spreadsheet. Cheers."
        ),
        "payload": {
            "text": (
                "Hi team, I've analysed the recent metrics and updated the draft report. We must organise "
                "our holiday schedules so we don't delay the launch. I realise this is short notice, but "
                "defence of our market share is critical. PFA the detailed spreadsheet. Cheers."
            ),
            "domain": "corporate_email",
            "tone": "formal",
            "word_count": 40
        }
    },
    {
        "domain": "tech_blog",
        "dialect": "en-GB",
        "content": (
            "Establishing a service business in the UK demands that you understand the local culture. "
            "People appreciate order; they don't like when you cut the queue. We realised early on that "
            "our digital marketing strategy needed a complete revamp. After we analysed customer feedback, "
            "we flat-out changed the onboarding programme. The results are phenomenal."
        ),
        "payload": {
            "text": (
                "Establishing a service business in the UK demands that you understand the local culture. "
                "People appreciate order; they don't like when you cut the queue. We realised early on that "
                "our digital marketing strategy needed a complete revamp. After we analysed customer feedback, "
                "we flat-out changed the onboarding programme. The results are phenomenal."
            ),
            "domain": "tech_blog",
            "tone": "professional",
            "word_count": 51
        }
    },
    # Western Standard (en-US)
    {
        "domain": "corporate_email",
        "dialect": "en-US",
        "content": (
            "Hi everyone, here is the draft project report for your review. Please look it over and send your "
            "feedback as soon as possible. We can reschedule our weekly sync to tomorrow morning if you'd like "
            "to go over the feedback in detail. Thanks, John"
        ),
        "payload": {
            "text": (
                "Hi everyone, here is the draft project report for your review. Please look it over and send your "
                "feedback as soon as possible. We can reschedule our weekly sync to tomorrow morning if you'd like "
                "to go over the feedback in detail. Thanks, John"
            ),
            "domain": "corporate_email",
            "tone": "formal",
            "word_count": 44
        }
    },
    # Platform-specific style exemplars for en-IN
    {
        "domain": "medium",
        "dialect": "en-IN",
        "content": (
            "The startup ecosystem in Bangalore is moving at a breakneck speed. PFA my notes on why so many founders fail in their first year. "
            "The reality is simple: they focus too much on fundraising and not enough on product-market fit. Kindly do the needful and talk to "
            "your customers before writing a single line of code. We prepone our product launches only to realize the market isn't ready. "
            "Focus on the core value first, and scaling will follow."
        ),
        "payload": {
            "text": "Bangalore startup ecosystem notes on why founders fail.",
            "domain": "medium",
            "tone": "engaging",
            "word_count": 68
        }
    },
    {
        "domain": "substack",
        "dialect": "en-IN",
        "content": (
            "When analyzing the macroeconomic landscape of India's digital public infrastructure, one cannot ignore the role of UPI. "
            "It's not just a payment protocol; it's a financial revolution. Many analysts discuss about the scale, but they miss the grassroots impact. "
            "PFA the growth charts. If you're building fintech in India, kindly note that offline merchants are your real partners. "
            "We need to prepone financial inclusion to unlock the next phase of GDP growth."
        ),
        "payload": {
            "text": "UPI role in India's digital public infrastructure analysis.",
            "domain": "substack",
            "tone": "professional",
            "word_count": 67
        }
    },
    {
        "domain": "reddit",
        "dialect": "en-IN",
        "content": (
            "Look, here is the honest truth about working in IT services vs a startup in India. I spent 4 years in a service MNC and it was soul-crushing. "
            "Every single email was 'Kindly do the needful' or 'PFA the sheet'. We preponed reviews for no reason. In a startup, you actually build. "
            "You code, deploy, and fix. Yes, it's chaotic, but the growth is insane. Do one thing: if you are young, leave the MNC and join a product firm. "
            "You won't regret it."
        ),
        "payload": {
            "text": "Honest comparison between MNC services and startups in India.",
            "domain": "reddit",
            "tone": "casual",
            "word_count": 76
        }
    },
    {
        "domain": "quora",
        "dialect": "en-IN",
        "content": (
            "How do I crack product management roles in India? Here is my step-by-step answer:\n"
            "1. Understand user needs: Do not just memorize frameworks.\n"
            "2. Build side projects: Show, don't tell.\n"
            "3. Network: PFA the list of top PM communities in India.\n"
            "Kindly do the needful and reach out to mentors. We often discuss about standard templates, but real-world case studies are what get you hired. "
            "Prepone your prep work now."
        ),
        "payload": {
            "text": "How to crack product management roles in India.",
            "domain": "quora",
            "tone": "authoritative",
            "word_count": 72
        }
    },
    {
        "domain": "wordpress",
        "dialect": "en-IN",
        "content": (
            "Scaling a digital marketing agency in Mumbai requires a deep understanding of local consumer behavior. "
            "We have analyzed the top campaigns from last year and found that video content outperforms text by 3x. Kindly check the attached case study for details. "
            "If you want to grow your business, do one thing: invest in hyper-localized content. Let's prepone our strategy call to discuss the execution plan."
        ),
        "payload": {
            "text": "Scaling digital marketing agencies in Mumbai using video content.",
            "domain": "wordpress",
            "tone": "professional",
            "word_count": 59
        }
    },
    {
        "domain": "squarespace",
        "dialect": "en-IN",
        "content": (
            "Designing a modern e-commerce site for the Indian market is all about building trust. With UPI and cod payment options, checkout must be seamless. "
            "PFA our design template that improved conversions by 24%. Kindly review and revert with your feedback. We can prepone the client review if you have "
            "the inputs ready. Let's discuss about the mobile layout today."
        ),
        "payload": {
            "text": "Designing trust-based e-commerce websites for Indian consumers.",
            "domain": "squarespace",
            "tone": "elegant",
            "word_count": 56
        }
    },
    {
        "domain": "wix",
        "dialect": "en-IN",
        "content": (
            "If you are planning to start a food business in Delhi, building a beautiful website is your first step. It showcases your menu and lets customers order directly. "
            "Do one thing first: get high-quality photos of your dishes. PFA our guide on food photography. Kindly check and revert back. "
            "We need to prepone our launch marketing to create buzz."
        ),
        "payload": {
            "text": "Starting a Delhi food business and website creation tips.",
            "domain": "wix",
            "tone": "friendly",
            "word_count": 55
        }
    }
]

from app.models.platform_metadata import PlatformMetadata

PLATFORM_SEEDS = [
    {
        "platform": "medium",
        "display_name": "Medium",
        "storytelling_cadence": "Deep storytelling cadence, highly polished professional prose, engaging narrative arcs.",
        "heading_style": "Balanced H2 and H3 subheadings with clear structural transitions.",
        "layout_constraints": {"format": "markdown", "elements": ["blockquotes", "bold-intro", "h2", "h3"], "cadence": "narrative"},
        "seo_optimizations": {"keywords_density": 0.015, "title_len": 60}
    },
    {
        "platform": "substack",
        "display_name": "Substack",
        "storytelling_cadence": "Deep analytical and narrative prose, editorial perspective, first-person elements.",
        "heading_style": "Clean H2 subheadings with italicized emphasis or callout blocks.",
        "layout_constraints": {"format": "markdown", "elements": ["blockquotes", "bulletpoints", "bold-intro", "h2"], "cadence": "analytical"},
        "seo_optimizations": {"keywords_density": 0.012, "title_len": 55}
    },
    {
        "platform": "reddit",
        "display_name": "Reddit",
        "storytelling_cadence": "High structural burstiness, conversational first-person narrative, direct and engaging tone.",
        "heading_style": "Bold inline headings with horizontal dividers (---).",
        "layout_constraints": {"format": "markdown", "elements": ["horizontal-dividers", "linebreaks", "bold-inline"], "cadence": "first-person"},
        "seo_optimizations": {"keywords_density": 0.005, "title_len": 120}
    },
    {
        "platform": "quora",
        "display_name": "Quora",
        "storytelling_cadence": "Direct question-to-answer authoritative framework, expert insight, narrative elements.",
        "heading_style": "Inline bolding for critical answers, structured step lists, or QA pairings.",
        "layout_constraints": {"format": "markdown", "elements": ["inline-bolding", "numbered-lists", "qa-pair"], "cadence": "authoritative"},
        "seo_optimizations": {"keywords_density": 0.01, "title_len": 80}
    },
    {
        "platform": "wordpress",
        "display_name": "WordPress",
        "storytelling_cadence": "Formal corporate or lifestyle-blog layouts, highly readable block structures, introductory summaries.",
        "heading_style": "SEO-optimized multi-layered headings (H1, H2, H3, H4).",
        "layout_constraints": {"format": "html-blocks", "elements": ["headings", "bulletpoints", "bold-keywords"], "cadence": "structured"},
        "seo_optimizations": {"keywords_density": 0.02, "title_len": 60, "meta_desc": True}
    },
    {
        "platform": "squarespace",
        "display_name": "Squarespace",
        "storytelling_cadence": "Modern, design-centric layout cadence, elegant and concise paragraphs.",
        "heading_style": "SEO-optimized multi-layered headings.",
        "layout_constraints": {"format": "markdown", "elements": ["headings", "callouts", "clean-spacing"], "cadence": "elegant"},
        "seo_optimizations": {"keywords_density": 0.015, "title_len": 60}
    },
    {
        "platform": "wix",
        "display_name": "Wix",
        "storytelling_cadence": "Lifestyle-blog layout, visual storytelling accents, highly approachable phrasing.",
        "heading_style": "SEO-optimized multi-layered headings.",
        "layout_constraints": {"format": "markdown", "elements": ["headings", "bulletpoints", "visual-notes"], "cadence": "friendly"},
        "seo_optimizations": {"keywords_density": 0.018, "title_len": 60}
    }
]

def seed_platform_metadata(db: Session, force_reseed: bool = False):
    """Seed the platform metadata constraints table."""
    if force_reseed:
        db.execute(text("DROP TABLE IF EXISTS platform_metadata CASCADE;"))
        db.commit()
        Base.metadata.create_all(db.bind, tables=[PlatformMetadata.__table__])
        print("Platform metadata table recreated.")

    count = db.query(PlatformMetadata).count()
    if count > 0 and not force_reseed:
        print(f"Platform metadata already has {count} entries. Skipping.")
        return

    print(f"Seeding {len(PLATFORM_SEEDS)} platform metadata profiles...")
    for entry in PLATFORM_SEEDS:
        meta = PlatformMetadata(
            platform=entry["platform"],
            display_name=entry["display_name"],
            storytelling_cadence=entry["storytelling_cadence"],
            heading_style=entry["heading_style"],
            layout_constraints=entry["layout_constraints"],
            seo_optimizations=entry["seo_optimizations"]
        )
        db.add(meta)
    db.commit()
    print("Platform metadata seeded successfully.")


def seed_style_references(db: Session, force_reseed: bool = False):
    """Seed the style references table if empty or if force_reseed is True."""
    # Seed platform metadata alongside style references
    try:
        seed_platform_metadata(db, force_reseed=force_reseed)
    except Exception as pe:
        print(f"Platform seeding error: {str(pe)}")

    # Check if table exists or needs schema refresh
    if force_reseed:
        print("Dropping and recreating style_references table to apply new domain/payload schema...")
        db.execute(text("DROP TABLE IF EXISTS style_references CASCADE;"))
        db.commit()
        # Recreate table using metadata
        Base.metadata.create_all(db.bind, tables=[StyleReference.__table__])
        print("Table recreated successfully.")
    
    count = db.query(StyleReference).count()
    if count > 0 and not force_reseed:
        print(f"Table style_references already has {count} entries. Skipping seed.")
        return

    print(f"Seeding {len(SEED_DATA)} style reference templates with rate-limit buffers...")
    for entry in SEED_DATA:
        embedding = None
        for attempt in range(3):
            try:
                embedding = get_embedding(entry["content"])
                break
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    print(f"Rate limit hit. Sleeping 12s before retry {attempt+1}/3...")
                    time.sleep(12)
                else:
                    print(f"Unexpected error seeding entry: {str(e)}")
                    break
        
        # If we failed to get it, fallback to mock
        if embedding is None:
            random.seed(hash(entry["content"]))
            embedding = [random.uniform(-0.1, 0.1) for _ in range(768)]

        style_ref = StyleReference(
            content=entry["content"],
            embedding=embedding,
            domain=entry["domain"],
            dialect=entry["dialect"],
            payload=entry["payload"]
        )
        db.add(style_ref)
        db.commit()
        time.sleep(1.0)  # Delay between requests to stay safe under 15 RPM
    
    print("Style references seeded successfully.")
