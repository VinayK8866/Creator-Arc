import json
import time
import asyncio
from typing import AsyncGenerator, Dict, List
from sqlalchemy.orm import Session
import google.generativeai as genai

from app.core.config import settings
from app.models.platform_metadata import PlatformMetadata
from app.models.blog_post import BlogPost
from app.services.rewriter.engine import rewriter_engine
from app.services.rewriter.lexicon import LexiconProcessor
from app.services.medium_strategy_engine import medium_strategy_engine
from app.services.performance_engine import performance_engine


class BlogService:
    def __init__(self):
        pass

    def generate_factual_base(self, db: Session, topic: str, platform: str) -> dict:
        """Module 1: Factual Expansion Layer
        Runs a reliable LLM at a cold temperature (T=0.3) to output a structured factual JSON dictionary.
        """
        # Retrieve platform layout constraints from DB if available
        meta = db.query(PlatformMetadata).filter(PlatformMetadata.platform == platform).first()
        platform_name = meta.display_name if meta else platform.capitalize()
        storytelling = meta.storytelling_cadence if meta else ""
        headings = meta.heading_style if meta else ""

        system_prompt = (
            "You are an expert natural language processing factual structure planner.\n"
            "Your objective is to generate an un-compromised factual base layer for a blog post based on the user's topic.\n"
            "You must output a highly structured JSON dictionary containing exactly the following keys:\n"
            "1. 'target_platform': string\n"
            "2. 'suggested_title': string\n"
            "3. 'seo_keywords': list of strings (4-6 relevant keywords)\n"
            "4. 'content_chunks': A list of objects (between 3 to 5 chunks), where each object contains:\n"
            "   - 'heading': A string heading for this section.\n"
            "   - 'raw_factual_bullet_points': A list of strings representing the core factual arguments/ideas of the section.\n\n"
            f"Target Platform Profile: {platform_name}\n"
            f"Storytelling style: {storytelling}\n"
            f"Heading style: {headings}\n\n"
        )

        if platform == "medium":
            system_prompt += (
                "MEDIUM PLATFORM STRUCTURAL DIRECTIVES (Resource 1-36 Blueprint):\n"
                "- Enforce 5-Step Macro Structure: (1) Intro + Explicit Reader Promise Formula, (2) Part One (Peak Value), "
                "(3) Mid-Article Promotional Sandwich Slot, (4) Part Two (Secondary Value), (5) Actionable Bullet Summary.\n"
                "- 5-Point Keyword Synchronicity: Embed primary topic keyword naturally across title, intro, and headings.\n"
                "- Include a rhetorical question triad and a recognized cognitive framework in Part One.\n"
                "- Ensure headings are phrased as conversational questions or pivot statements.\n\n"
            )

        learned_insights_prompt = performance_engine.get_active_insights_prompt(db)
        if learned_insights_prompt:
            system_prompt += f"\n{learned_insights_prompt}\n"

        system_prompt += (
            "Rules:\n"
            "- Set temperature context to T=0.3 internally. Stick strictly to facts, dates, and evidence-backed statements. Avoid all generic filler, narrative fluff, or adjectives.\n"
            "- You must return valid JSON only. Do not wrap in markdown code blocks."
        )

        user_prompt = f"Generate the factual base structure for the topic: '{topic}'"

        try:
            # Call Gemini JSON mode
            json_str = rewriter_engine._call_gemini_json_sync(system_prompt, user_prompt, temperature=0.3)
            
            # Clean potential markdown formatting
            if json_str.startswith("```"):
                json_str = json_str.split("\n", 1)[1].rsplit("\n", 1)[0]
                if json_str.startswith("json"):
                    json_str = json_str[4:].strip()

            result = json.loads(json_str)
            if not isinstance(result, dict) or "content_chunks" not in result:
                raise ValueError("Parsed JSON is not a structured factual outline dictionary.")
        except Exception as e:
            # Fallback structure on parsing error
            print(f"Failed to parse Gemini JSON or API rate limited: {str(e)}.")
            result = {
                "target_platform": platform,
                "suggested_title": f"Understanding {topic}",
                "seo_keywords": [topic, "industry trends", "insights"],
                "content_chunks": [
                    {
                        "heading": "What You Need to Know",
                        "raw_factual_bullet_points": [f"Overview and current status of {topic}."]
                    },
                    {
                        "heading": "Part One: Core Insights and Analysis",
                        "raw_factual_bullet_points": [f"Key data points and core arguments regarding {topic}."]
                    },
                    {
                        "heading": "Part Two: Deep Dive Framework",
                        "raw_factual_bullet_points": [f"Technical analysis and practitioner advice on {topic}."]
                    },
                    {
                        "heading": "Action Summary and Practical Steps",
                        "raw_factual_bullet_points": [f"Summary and immediate action items on {topic}."]
                    }
                ]
            }

        return result

    def _rebuild_chunk_text(
        self,
        facts: list,
        exemplars: list,
        tone: str,
        platform_meta: PlatformMetadata,
        temperature: float = 0.9,
        feedback_hint: str = "",
        db: Session = None
    ) -> str:
        """Call Gemini to rewrite the factual bullets for a single chunk while strictly enforcing the
        dynamic burstiness sentence length cycle constraint and platform-specific rules.
        """
        exemplars_formatted = "\n\n".join([f"Exemplar {i+1}:\n{ex}" for i, ex in enumerate(exemplars)])
        facts_formatted = "\n".join([f"- {fact}" for fact in facts])

        platform_layout = f"Platform Layout style: {platform_meta.storytelling_cadence}. Headings: {platform_meta.heading_style}."

        system_prompt = (
            "You are a master human content creator. Your goal is to rewrite the raw factual points into a cohesive, "
            f"deeply humanized content block in a '{tone}' tone. \n\n"
            "Follow these strict formatting and style constraints:\n"
            "1. STRICT BURSTINESS RULE (Sentence Pacing Cycle):\n"
            "   You must alternate your sentence pacing periodically across each paragraph. Follow this exact length sequence:\n"
            "   - Sentence 1: A very short, punchy sentence (under 7 words) (e.g. 'This changes everything.', 'But here is the catch.').\n"
            "   - Sentence 2: A long, compound or complex sentence (22+ words) containing at least one conjunction (and, but, although, because) AND a semicolon (;) to split the thoughts naturally.\n"
            "   - Sentence 3: A medium sentence (12-16 words) to balance the rhythm.\n"
            "   Repeat this cyclical pacing (short -> complex/semicolon -> medium) to ensure high structural burstiness that bypasses AI classifiers.\n"
            "2. STYLE TEMPLATE REF:\n"
            f"   You MUST mirror the vocabulary, cadence, and sentence phrasing structures from these reference style exemplars:\n{exemplars_formatted}\n"
            "3. PLATFORM STYLE INSTRUCTION:\n"
            f"   {platform_layout}\n"
        )

        if platform_meta and platform_meta.platform == "medium":
            system_prompt += (
                "4. MEDIUM BLUEPRINT FORMATTING RULES (Resource 1-36 Guidelines):\n"
                "   - MICRO-PARAGRAPH FORMATTING (SR-01): Keep paragraphs short (strictly 1-3 sentences, 2-4 max) with generous whitespace.\n"
                "   - CONVERSATIONAL SUBHEADINGS (SR-02): Subheadings MUST be phrased as conversational questions or pivot statements.\n"
                "   - SINGLE-LINE RHYTHMIC HOOK BEATS (SR-05): Use standalone single-sentence lines (e.g. 'It was horrible.', 'What happened?') for vertical momentum.\n"
                "   - SUPERSCRIPT CITATIONS (SR-70): Format all citations and statistics with native superscript markers (e.g. '[1]', '¹').\n"
                "   - PULL QUOTE CALLOUTS (SR-18): Wrap key takeaways in blockquotes (`> *Takeaway*`).\n"
                "   - MAX WORD BOUNDARY (SR-35): Ensure section block does not exceed 300 words without subheadings.\n"
                "5. STRICT ANTI-AI CLICHES FILTER:\n"
                "   Do NOT use: 'Moreover', 'Furthermore', 'In conclusion', 'Additionally', 'On one hand...', 'In today's digital landscape'. Use contractions (don't, it's, we've).\n"
                "6. SOURCE FIDELITY: Rely strictly on the facts provided. Do not hallucinate or invent outside statements."
            )
        else:
            system_prompt += (
                "4. AVOID AI CLICHES:\n"
                "   Do not use: 'Moreover', 'Furthermore', 'In conclusion', 'Additionally', 'On one hand...'. Use contractions (don't, it's, we've).\n"
                "5. SOURCE FIDELITY: Rely strictly on the facts provided. Do not hallucinate or invent outside statements."
            )

        if db:
            learned_insights_prompt = performance_engine.get_active_insights_prompt(db)
            if learned_insights_prompt:
                system_prompt += f"\n\n{learned_insights_prompt}"

        if feedback_hint:
            system_prompt += f"\n\nCRITICAL DIRECTIVE FOR RETRY: {feedback_hint}"

        user_prompt = (
            f"RAW SEMANTIC FACTS TO REWRITE:\n{facts_formatted}\n\n"
            "Write the humanized section text now:"
        )

        try:
            return rewriter_engine._call_gemini_text_sync(system_prompt, user_prompt, temperature=temperature)
        except Exception as e:
            print(f"Gemini text rewrite failed: {str(e)}. Using local mock rewrite fallback.")
            paragraphs = []
            for fact in facts:
                cleaned_fact = fact.strip()
                if cleaned_fact:
                    paragraphs.append(f"Regarding the facts, we know that {cleaned_fact.lower().rstrip('.')}.")
            return " ".join(paragraphs) + " This serves as a critical milestone for digital integration."

    async def generate_blog_stream(
        self,
        db: Session,
        topic: str,
        platform: str,
        tone: str
    ) -> AsyncGenerator[str, None]:
        """Module 2 & SSE Bridge: Orchestrate the chunk-by-chunk expansion and humanization,
        streaming progress states in real-time.
        """
        loop = asyncio.get_running_loop()

        def make_sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        yield make_sse("status", {"message": "Layer 1: Structuring Core Arguments Safely...", "progress": 10})
        await asyncio.sleep(0.5)

        # 1. Fetch Platform metadata
        platform_meta = db.query(PlatformMetadata).filter(PlatformMetadata.platform == platform).first()
        if not platform_meta:
            yield make_sse("error", {"detail": f"Platform '{platform}' is not supported."})
            return

        # 2. Generate factual base (T=0.3)
        try:
            factual_base = await loop.run_in_executor(None, self.generate_factual_base, db, topic, platform)
            yield make_sse("status", {"message": "Layer 1 Completed: Factual outline generated.", "progress": 25})
            yield make_sse("factual_base", {
                "suggested_title": factual_base["suggested_title"],
                "seo_keywords": factual_base["seo_keywords"],
                "chunks_count": len(factual_base["content_chunks"])
            })
            await asyncio.sleep(0.5)
        except Exception as fe_err:
            yield make_sse("error", {"detail": f"Failed to generate factual base: {str(fe_err)}"})
            return

        # Create Blog Post model instance in DB
        focus_keyword = factual_base["seo_keywords"][0] if factual_base.get("seo_keywords") else topic

        title_pkg = {}
        if platform == "medium":
            title_pkg = await loop.run_in_executor(
                None,
                medium_strategy_engine.generate_title_package,
                topic,
                focus_keyword
            )

        blog_post = BlogPost(
            topic=topic,
            platform=platform,
            suggested_title=title_pkg.get("feed_title", factual_base["suggested_title"]),
            seo_title=title_pkg.get("seo_title", factual_base["suggested_title"]),
            feed_title=title_pkg.get("feed_title", factual_base["suggested_title"]),
            title_variations=title_pkg.get("title_variations", []),
            url_slug=title_pkg.get("url_slug", focus_keyword.lower().replace(" ", "-")),
            kicker=title_pkg.get("kicker", "GUIDE"),
            subtitle=title_pkg.get("subtitle", f"A practitioner guide to {topic}"),
            seo_keywords=factual_base["seo_keywords"],
            original_factual_base=factual_base,
            status="processing"
        )
        db.add(blog_post)
        db.commit()
        db.refresh(blog_post)

        # 3. Loop through content chunks chunk-by-chunk
        chunks = factual_base["content_chunks"]
        completed_chunks = []
        assembled_content_blocks = []

        total_chunks = len(chunks)
        for idx, chunk in enumerate(chunks):
            heading = chunk["heading"]
            facts = chunk["raw_factual_bullet_points"]
            facts_text = " ".join(facts)

            yield make_sse("status", {
                "message": f"Layer 2: Retrieving style exemplars for Section {idx + 1}/{total_chunks}: '{heading}'...",
                "progress": int(25 + (idx / total_chunks) * 60)
            })

            # Vector semantic search for domain/platform exemplars (en-IN dialect)
            exemplars = await loop.run_in_executor(
                None,
                rewriter_engine._retrieve_style_templates,
                db,
                facts_text,
                platform,  # matches domain column in database
                "en-IN",   # en-IN Humanizer dialect
                2          # retrieve 2 exemplars
            )
            if not exemplars:
                # fallback standard domain styles if platform vector is missing
                exemplars = await loop.run_in_executor(
                    None,
                    rewriter_engine._retrieve_style_templates,
                    db,
                    facts_text,
                    "general_content",
                    "en-IN",
                    2
                )

            # Adversarial optimization loop
            current_temp = 0.9
            feedback_hint = ""
            best_chunk_text = ""
            best_score = 1.0
            best_nli_score = 0.0
            max_retries = 3
            passed = False

            yield make_sse("status", {
                "message": f"Layer 2: Rebuilding & checking Section {idx + 1}/{total_chunks} via Adversarial checks...",
                "progress": int(30 + (idx / total_chunks) * 60)
            })

            for attempt in range(1, max_retries + 1):
                yield make_sse("status", {
                    "message": f"Section {idx + 1}: Attempt {attempt}/{max_retries} - Reconstructing text...",
                    "progress": int(32 + (idx / total_chunks) * 60)
                })

                # Reconstruct chunk text enforcing burstiness pacing
                candidate_text = await loop.run_in_executor(
                    None,
                    self._rebuild_chunk_text,
                    facts,
                    exemplars,
                    tone,
                    platform_meta,
                    current_temp,
                    feedback_hint,
                    db
                )

                # Translate Indian English lexicon
                translated_text = LexiconProcessor.translate(candidate_text, "en-IN")

                # Adversarial Scorer (Target <= 0.35)
                score = await rewriter_engine.scorer.score_text(translated_text, use_api=True)
                
                # NLI Factual alignment (Target >= 0.85)
                nli_score = await rewriter_engine.nli_scorer.check_consistency(facts, translated_text, use_api=True)

                yield make_sse("status", {
                    "message": f"Section {idx + 1}: Scored AI likelihood: {score:.2%}, Fact Alignment: {nli_score:.2%}",
                    "progress": int(35 + (idx / total_chunks) * 60)
                })

                # Log best attempt
                is_best = False
                if best_chunk_text == "":
                    is_best = True
                else:
                    if nli_score >= 0.85 and best_nli_score < 0.85:
                        is_best = True
                    elif nli_score >= 0.85 and best_nli_score >= 0.85:
                        if score < best_score:
                            is_best = True
                    elif nli_score < 0.85 and best_nli_score < 0.85:
                        if nli_score > best_nli_score:
                            is_best = True

                if is_best:
                    best_score = score
                    best_nli_score = nli_score
                    best_chunk_text = translated_text

                if score <= 0.35 and nli_score >= 0.85:
                    passed = True
                    yield make_sse("status", {
                        "message": f"Section {idx + 1} passed adversarial loop checks on attempt {attempt}.",
                        "progress": int(38 + (idx / total_chunks) * 60)
                    })
                    break

                # Adjust variables for next retry
                current_temp = min(current_temp + 0.05, 0.99)
                feedback_hint = rewriter_engine._get_feedback_hint(attempt + 1)
                feedback_hint += (
                    " Ensure you alternate short sentences (<=6 words) with long compound sentences (22+ words) "
                    "containing a semicolon, followed by a medium sentence."
                )

            # Store completed chunk
            final_text = best_chunk_text
            completed_chunks.append({
                "heading": heading,
                "raw_factual_bullet_points": facts,
                "humanized_text": final_text,
                "score": best_score,
                "nli_score": best_nli_score,
                "passed_checks": passed
            })

            # Assemble blog markdown block
            assembled_block = f"## {heading}\n\n{final_text}\n\n"
            if platform in ["medium", "substack"] and idx == 0:
                quotes_hint = f"> *Key takeaway: {topic.capitalize()} requires a deep understanding of core facts.*"
                assembled_block += quotes_hint + "\n\n"
            elif platform == "reddit":
                assembled_block += "---\n\n"

            # Mid-Article Promotional Sandwich Insertion for Medium (SR-23)
            if platform == "medium" and idx == 1:
                assembled_block += (
                    "👉 *[Download the free prompt & execution checklist before reading Part Two](https://gumroad.com)* "
                    "*(Note: Clicking this link takes you offsite outside Medium)*\n\n"
                )

            assembled_content_blocks.append(assembled_block)

            # Yield chunk completion payload
            yield make_sse("chunk_completed", {
                "chunk_index": idx,
                "heading": heading,
                "humanized_text": final_text,
                "score": best_score,
                "nli_score": best_nli_score
            })

        # Assemble full content
        if platform == "medium":
            header_block = medium_strategy_engine.build_5_step_header_block(
                kicker=blog_post.kicker or "GUIDE",
                title=blog_post.feed_title or factual_base['suggested_title'],
                subtitle=blog_post.subtitle or f"A practitioner guide to {topic}",
                reader_promise=f"I promise in this post I will break down {topic} into actionable, real-world steps.",
                lead_magnet_url="https://gumroad.com"
            )
            body_content = "".join(assembled_content_blocks)
            footer_block = medium_strategy_engine.build_footer_architecture(
                topic=topic,
                bullet_summary=[c["heading"] for c in completed_chunks]
            )
            raw_markdown = header_block + body_content + footer_block

            # Inject TK Native Safety Markers (Resource Rule AD-25)
            tk_markdown = medium_strategy_engine.inject_tk_action_placeholders(raw_markdown, topic)

            # Inject compliance disclosures (AI disclosure, FTC, Offsite link notices)
            disclosed_markdown, compliance_flags = medium_strategy_engine.inject_compliance_disclosures(
                markdown=tk_markdown,
                is_ai_assisted=True,
                has_affiliate_links=False,
                has_offsite_forms=True
            )

            # Run anti-pattern sanitizer
            full_assembled_markdown = medium_strategy_engine.sanitize_markdown(disclosed_markdown)
            
            # Run Rule Compliance Audit Engine
            audit_metadata = {
                "topic": topic,
                "seo_title": blog_post.seo_title,
                "feed_title": blog_post.feed_title,
                "url_slug": blog_post.url_slug,
                "kicker": blog_post.kicker,
                "subtitle": blog_post.subtitle
            }
            strategy_audit = medium_strategy_engine.audit_rule_compliance(full_assembled_markdown, audit_metadata)
            audit_report_md = medium_strategy_engine.generate_audit_report_markdown(strategy_audit)

            blog_post.compliance_flags = compliance_flags
            blog_post.strategy_audit = strategy_audit
            blog_post.tag_recommendations = strategy_audit.get("tag_recommendations", [])
        elif platform == "quora":
            full_assembled_markdown = f"**Question:** What are the key facts and trends surrounding {topic}?\n\n**Answer:**\n\n" + "".join(assembled_content_blocks)
            strategy_audit = {}
            audit_report_md = ""
        else:
            full_assembled_markdown = f"# {factual_base['suggested_title']}\n\n" + "".join(assembled_content_blocks)
            strategy_audit = {}
            audit_report_md = ""

        # Update BlogPost in Database
        blog_post.humanized_content = full_assembled_markdown
        blog_post.content_chunks = completed_chunks
        blog_post.status = "completed"
        db.commit()

        yield make_sse("status", {"message": "Layer 3: Formatting & compiling final post...", "progress": 95})
        await asyncio.sleep(0.5)

        # Save rewrite log pairs for further fine tuning datasets
        for c in completed_chunks:
            rewriter_engine._save_rewrite_pair(
                original="; ".join(c["raw_factual_bullet_points"]),
                facts=c["raw_factual_bullet_points"],
                humanized=c["humanized_text"],
                score=c["score"],
                dialect="en-IN"
            )

        yield make_sse("completed", {
            "post_id": blog_post.id,
            "title": blog_post.suggested_title,
            "seo_title": blog_post.seo_title,
            "feed_title": blog_post.feed_title,
            "url_slug": blog_post.url_slug,
            "seo_keywords": blog_post.seo_keywords,
            "full_content": full_assembled_markdown,
            "chunks": completed_chunks,
            "strategy_audit": strategy_audit,
            "audit_report_markdown": audit_report_md
        })


blog_service = BlogService()
