import time
import json
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session
import google.generativeai as genai
from app.core.config import settings
from app.models.style_reference import StyleReference
from app.services.rewriter.migration import get_embedding, seed_style_references
from app.services.rewriter.lexicon import LexiconProcessor
from app.services.rewriter.scorer import AdversarialScorer
from app.services.rewriter.nli_scorer import NLIConsistencyScorer
from app.services.rewriter.cache import embedding_cache
from app.services.rewriter.governor import APIGovernor, FALLBACK_MODELS

# Ensure Gemini is configured
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


class RewriterEngine:
    def __init__(self):
        self.scorer = AdversarialScorer()
        self.nli_scorer = NLIConsistencyScorer()
        self.models = FALLBACK_MODELS

    def _call_gemini_json_sync(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """Call Gemini requesting JSON response format with rate-limiting pacing and instant prioritized fallbacks."""
        if not settings.GEMINI_API_KEY:
            return "[]"
        
        last_error = None
        for model_name in self.models:
            try:
                # Pace request to avoid hitting 15 RPM rate limits
                APIGovernor.pace()
                
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_prompt
                )
                response = model.generate_content(
                    user_prompt,
                    generation_config={
                        "response_mime_type": "application/json",
                        "temperature": temperature
                    }
                )
                return response.text.strip()
            except Exception as e:
                err_msg = str(e)
                print(f"Error calling Gemini JSON with model {model_name}: {err_msg}")
                last_error = e
                # Fallback to the next model instantly
                continue
                        
        raise Exception(f"All Gemini models failed in JSON mode. Last error: {str(last_error)}")

    def _call_gemini_text_sync(self, system_prompt: str, user_prompt: str, temperature: float = 1.0) -> str:
        """Call Gemini requesting raw text response with rate-limiting pacing and instant prioritized fallbacks."""
        if not settings.GEMINI_API_KEY:
            return f"[Dev Mock Rewritten Text] Original: {user_prompt[:50]}"
        
        last_error = None
        for model_name in self.models:
            try:
                # Pace request to avoid hitting 15 RPM rate limits
                APIGovernor.pace()
                
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_prompt
                )
                response = model.generate_content(
                    user_prompt,
                    generation_config={
                        "temperature": temperature,
                        "top_p": 0.95,
                        "top_k": 40
                    }
                )
                return response.text.strip()
            except Exception as e:
                err_msg = str(e)
                print(f"Error calling Gemini Text with model {model_name}: {err_msg}")
                last_error = e
                # Fallback to the next model instantly
                continue
                        
        raise Exception(f"All Gemini models failed in text mode. Last error: {str(last_error)}")

    def _retrieve_style_templates(self, db: Session, query_text: str, domain: str, dialect: str, top_k: int = 2) -> list:
        """Retrieve stylistic references matching domain & dialect, ranked by embedding cosine similarity."""
        # Ensure seed data is populated
        seed_style_references(db)

        # 1. Fetch from Redis Cache first or generate
        query_vector = embedding_cache.get(query_text)
        if not query_vector:
            query_vector = get_embedding(query_text)
            embedding_cache.set(query_text, query_vector)

        # 2. Try native PostgreSQL pgvector cosine similarity search
        has_pgvector = False
        try:
            res = db.execute(text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'style_references' AND column_name = 'embedding';"
            )).fetchone()
            if res and res[0] == 'USER-DEFINED':
                has_pgvector = True
        except Exception:
            pass

        if has_pgvector and query_vector:
            try:
                # Format vector list as SQL string representation e.g. '[0.1, 0.2, ...]'
                vector_str = f"[{','.join(map(str, query_vector))}]"
                sql_query = """
                SELECT content 
                FROM style_references 
                WHERE domain = :domain AND dialect = :dialect 
                ORDER BY embedding <=> CAST(:vector_str AS vector) 
                LIMIT :limit
                """
                results = db.execute(text(sql_query), {
                    "domain": domain, 
                    "dialect": dialect, 
                    "vector_str": vector_str, 
                    "limit": top_k
                }).fetchall()
                
                if results:
                    print("Engine: Executed accelerated pgvector HNSW database query.")
                    return [r[0] for r in results]
            except Exception as e:
                print(f"Engine: pgvector query failed: {str(e)}. Falling back to local numpy similarity.")

        # 3. Fallback numpy Cosine Similarity search if pgvector is unavailable
        references = db.query(StyleReference).filter(
            StyleReference.domain == domain,
            StyleReference.dialect == dialect
        ).all()

        # If no matches, pull by dialect, then by domain, then all
        if not references:
            references = db.query(StyleReference).filter(StyleReference.dialect == dialect).all()
        if not references:
            references = db.query(StyleReference).filter(StyleReference.domain == domain).all()
        if not references:
            references = db.query(StyleReference).all()

        if not references:
            return []

        results = []
        for ref in references:
            if not ref.embedding:
                continue
            
            # Cosine similarity = dot(A, B) / (norm(A) * norm(B))
            v1 = np.array(query_vector)
            v2 = np.array(ref.embedding)
            dot_product = np.dot(v1, v2)
            norm_v1 = np.linalg.norm(v1)
            norm_v2 = np.linalg.norm(v2)
            
            similarity = dot_product / (norm_v1 * norm_v2) if norm_v1 > 0 and norm_v2 > 0 else 0.0
            results.append((ref.content, similarity))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return [content for content, _ in results[:top_k]]

    def _get_feedback_hint(self, attempt_next: int) -> str:
        """Dynamically generate distinct structural feedback hints for subsequent attempts
        to bypass AI detectors without causing structural collapse through extreme temperatures.
        """
        if attempt_next == 2:
            return (
                "The previous output sounded too robotic and was flagged by an AI classifier. "
                "Rewrite with significantly higher variation in sentence length. Use shorter, more punchy sentences. "
                "Remove any word patterns that feel repetitive or structured. Avoid typical corporate transitions. "
                "Inject a highly conversational, personal touch. Start the narrative with a direct, conversational hook "
                "or a rhetorical question (e.g., 'Here is the reality:', 'How do we solve this?', or 'Look, ...')."
            )
        elif attempt_next == 3:
            return (
                "The previous output was still flagged. Invert the chronological or logical order: present the core result "
                "or final action first, followed by the background facts. Write from a direct, first-person active perspective. "
                "Break up any remaining long sentences into extremely short, conversational fragments."
            )
        else:
            return (
                "The previous output failed detection. Rewrite the text using informal, conversational phrasing as if "
                "speaking directly to a close colleague. Drop all formal transitions, vary sentence lengths randomly, and "
                "focus on a punchy, human-first flow."
            )

    def extract_facts(self, text: str) -> dict:
        """Step 1: Abstractor - De-serialize the AI text into raw facts and classify the domain."""
        system_prompt = (
            "You are an advanced factual de-serializer and domain classifier.\n"
            "First, analyze the user's text and classify it into one of the following 4 domains:\n"
            "- 'corporate_email': Formal Indian business/corporate communication.\n"
            "- 'tech_blog': Modern, casual, engineering-focused tech blogs/articles.\n"
            "- 'academic_essay': Formal, complex educational or research-oriented prose.\n"
            "- 'general_content': Web articles, standard blog posts, general write-ups.\n\n"
            "Second, extract all factual assertions, data points, dates, and core arguments, "
            "stripping away all style, adjectives, framing, rhetorical questions, and transitions.\n\n"
            "You MUST output your response in this exact JSON format:\n"
            "{\n"
            "  \"detected_domain\": \"<one_of_the_4_domains>\",\n"
            "  \"extracted_facts\": [\"Fact A\", \"Fact B\", \"Fact C\"]\n"
            "}\n"
            "Do not include any extra markdown formatting or preambles."
        )
        user_prompt = f"Analyze and extract from this text:\n\n{text}"
        
        fallback_res = {
            "detected_domain": "general_content",
            "extracted_facts": [text]
        }
        
        try:
            json_str = self._call_gemini_json_sync(system_prompt, user_prompt, temperature=0.2)
            # Clean up potential markdown formatting block if generated anyway
            if json_str.startswith("```"):
                json_str = json_str.split("\n", 1)[1].rsplit("\n", 1)[0]
                if json_str.startswith("json"):
                    json_str = json_str[4:].strip()
            result = json.loads(json_str)
            if not isinstance(result, dict) or "detected_domain" not in result or "extracted_facts" not in result:
                if isinstance(result, list):
                    return {
                        "detected_domain": "general_content",
                        "extracted_facts": result
                    }
                return fallback_res
            return result
        except Exception as e:
            print(f"Fact extraction failed: {str(e)}. Falling back to default routing.")
            return fallback_res

    def rebuild_text(self, facts: list, exemplars: list, tone: str, dialect: str = "en-US", temperature: float = 0.9, feedback_hint: str = "") -> str:
        """Step 2: Rebuilder - Reconstruct the text enforcing style exemplars, dialect requirements, and burstiness rules."""
        exemplars_formatted = "\n\n".join([f"Exemplar {i+1}:\n{ex}" for i, ex in enumerate(exemplars)])
        facts_formatted = "\n".join([f"- {fact}" for fact in facts])

        # Get dialect-specific prompting instructions
        dialect_instructions = LexiconProcessor.get_dialect_instructions(dialect)

        system_prompt = (
            "You are a master human writer. Your goal is to write a natural, highly human narrative "
            f"in a '{tone}' tone using ONLY the raw facts provided. You MUST base your sentence structure, "
            "cadence, and pacing on the provided human style exemplars.\n\n"
            "Follow these strict formatting directives:\n"
            "1. STRICT BURSTINESS RULE: You must dynamically vary your sentence length. Never allow two consecutive "
            "sentences to have the same word count. Alternate sentence pacing: follow a short, punchy sentence "
            "(under 7 words) with a long, compound/complex sentence (22+ words) containing a conjunction or semi-colon, "
            "followed by a medium sentence (12-16 words).\n"
            "2. PERPLEXITY RULE: Avoid typical AI phrases and cliches. Do not write transitions like 'Moreover', "
            "'Furthermore', 'In conclusion', 'Additionally', 'On one hand...'. Use contractions (don't, it's, let's).\n"
            "3. STYLE SYNTAX: Mirror the informal yet professional sentence structures found in the reference exemplars.\n"
            "4. SOURCE RULES: Do not invent any facts. Stick to the list of facts provided.\n"
        )
        
        if dialect_instructions:
            system_prompt += f"\n5. {dialect_instructions}\n"
        
        if feedback_hint:
            system_prompt += f"\nCRITICAL ADJUSTMENT FOR THIS RUN: {feedback_hint}"

        user_prompt = (
            f"RETRIEVED HUMAN EXEMPLARS:\n{exemplars_formatted}\n\n"
            f"FACTS TO WRITE ABOUT:\n{facts_formatted}\n\n"
            "Write the humanized text now:"
        )

        return self._call_gemini_text_sync(system_prompt, user_prompt, temperature=temperature)

    async def rewrite(self, text: str, tone: str = "human-like", dialect: str = "en-US", max_retries: int = 3) -> dict:
        """Orchestrate the entire Structural & Cadence Transformation Engine.
        Includes abstracting, styling, building, translating, and adversarial looping.
        """
        # Step 1: Extract facts & detect domain (Abstractor)
        print("Extracting raw facts and detecting domain...")
        facts_res = self.extract_facts(text)
        detected_domain = facts_res["detected_domain"]
        extracted_facts = facts_res["extracted_facts"]

        # Setup DB session
        from app.core.database import SessionLocal
        db = SessionLocal()
        
        try:
            # Step 2: Retrieve style references (RAG)
            print(f"Retrieving style templates for domain '{detected_domain}' and dialect '{dialect}'...")
            exemplars = self._retrieve_style_templates(db, text, detected_domain, dialect)
        finally:
            db.close()

        # Fallback if no exemplars were found
        if not exemplars:
            exemplars = [
                "Building a business is hard. You have to learn step by step. Do one thing at a time."
            ]

        # Step 3 & 4: Rebuild, Translate and Adversarial Scoring Loop
        current_temp = 0.9
        feedback_hint = ""
        best_text = ""
        best_score = 1.0
        best_nli_score = 0.0

        for attempt in range(1, max_retries + 1):
            print(f"Attempt {attempt}: Rebuilding text (temp={current_temp:.2f})...")
            rebuilt_text = self.rebuild_text(extracted_facts, exemplars, tone, dialect=dialect, temperature=current_temp, feedback_hint=feedback_hint)
            
            # Step 4: Lexicon translation (Post-processing)
            translated_text = LexiconProcessor.translate(rebuilt_text, dialect)
            
            # Step 5: Adversarial Scorer
            score = await self.scorer.score_text(translated_text, use_api=True)
            print(f"Adversarial Score for attempt {attempt}: {score:.4f} (Target: < 0.35)")
            
            # Step 6: NLI Factual Consistency Scorer
            nli_score = await self.nli_scorer.check_consistency(extracted_facts, translated_text, use_api=True)
            print(f"Factual Alignment for attempt {attempt}: {nli_score:.4f} (Target: >= 0.85)")

            # Update best attempt based on NLI first, then Adversarial score
            is_best = False
            if best_text == "":
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
                best_text = translated_text

            if score <= 0.35 and nli_score >= 0.85:
                print(f"Success! Passed both checks with score {score:.4f} and NLI {nli_score:.4f}")
                self._save_rewrite_pair(text, extracted_facts, translated_text, score, dialect)
                return {
                    "original": text,
                    "rewritten": translated_text,
                    "score": score,
                    "nli_score": nli_score,
                    "attempts": attempt,
                    "status": "success"
                }

            # Tweak parameters for next run
            current_temp = min(current_temp + 0.04, 0.98)  # Safe bounded temperature cap
            feedback_hint = self._get_feedback_hint(attempt + 1)

        print(f"Failed to pass strict checks. Returning best attempt (score={best_score:.4f}, NLI={best_nli_score:.4f})")
        self._save_rewrite_pair(text, extracted_facts, best_text, best_score, dialect)
        return {
            "original": text,
            "rewritten": best_text,
            "score": best_score,
            "nli_score": best_nli_score,
            "attempts": max_retries,
            "status": "partial_success"
        }

    async def rewrite_stream(self, text: str, tone: str = "human-like", dialect: str = "en-US", max_retries: int = 3):
        """Asynchronously stream events for each step of the rewrite process, then stream the final text."""
        import asyncio
        import json
        
        # Step 1: Extract facts & detect domain
        yield {"event": "status", "data": "Extracting raw semantic facts..."}
        loop = asyncio.get_running_loop()
        facts_res = await loop.run_in_executor(None, self.extract_facts, text)
        detected_domain = facts_res["detected_domain"]
        extracted_facts = facts_res["extracted_facts"]
        yield {"event": "status", "data": f"Extracted {len(extracted_facts)} facts. Retrieving style exemplars..."}

        # Step 2: Retrieve style references
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            exemplars = await loop.run_in_executor(None, self._retrieve_style_templates, db, text, detected_domain, dialect)
        finally:
            db.close()

        if not exemplars:
            exemplars = [
                "Building a business is hard. You have to learn step by step. Do one thing at a time."
            ]

        current_temp = 0.9
        feedback_hint = ""
        best_text = ""
        best_score = 1.0
        best_nli_score = 0.0
        final_attempts = max_retries
        final_status = "partial_success"

        for attempt in range(1, max_retries + 1):
            yield {"event": "status", "data": f"Attempt {attempt}: Rebuilding text under '{dialect}' dialect..."}
            
            rebuilt_text = await loop.run_in_executor(
                None, 
                self.rebuild_text, 
                extracted_facts, 
                exemplars, 
                tone, 
                dialect, 
                current_temp, 
                feedback_hint
            )
            
            # Step 4: Lexicon translation
            translated_text = LexiconProcessor.translate(rebuilt_text, dialect)
            
            yield {"event": "status", "data": f"Attempt {attempt}: Running local adversarial scoring..."}
            
            # Step 5: Score
            score = await self.scorer.score_text(translated_text, use_api=True)
            yield {"event": "status", "data": f"Attempt {attempt} completed with AI likelihood score: {score:.2%}"}

            # Step 6: NLI Check
            yield {"event": "status", "data": f"Attempt {attempt}: Verifying factual alignment..."}
            nli_score = await self.nli_scorer.check_consistency(extracted_facts, translated_text, use_api=True)
            yield {"event": "status", "data": f"Attempt {attempt} completed with Factual Alignment: {nli_score:.2%}"}

            # Update best attempt based on NLI first, then Adversarial score
            is_best = False
            if best_text == "":
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
                best_text = translated_text

            if score <= 0.35 and nli_score >= 0.85:
                best_text = translated_text
                best_score = score
                best_nli_score = nli_score
                final_attempts = attempt
                final_status = "success"
                break

            current_temp = min(current_temp + 0.04, 0.98)
            feedback_hint = self._get_feedback_hint(attempt + 1)

        # Log search pair in DB
        await loop.run_in_executor(
            None, 
            self._save_rewrite_pair, 
            text, 
            extracted_facts, 
            best_text, 
            best_score, 
            dialect
        )

        yield {"event": "status", "data": f"Finalizing output (Final Score: {best_score:.2%}). Streaming text..."}
        
        # Stream the winner's text character chunks to simulate a live typing response with low latency
        chunk_size = 15
        for idx in range(0, len(best_text), chunk_size):
            chunk = best_text[idx:idx + chunk_size]
            yield {"event": "text_chunk", "data": chunk}
            await asyncio.sleep(0.015)
            
        yield {
            "event": "result", 
            "data": {
                "original": text,
                "rewritten": best_text,
                "score": best_score,
                "nli_score": best_nli_score,
                "attempts": final_attempts,
                "status": final_status
            }
        }

    def _save_rewrite_pair(self, original: str, facts: list, humanized: str, score: float, dialect: str):
        """Save before-and-after rewrite transitions to the database for future fine-tuning datasets."""
        from app.core.database import SessionLocal
        from app.models.rewrite_pair import RewritePair
        
        db = SessionLocal()
        try:
            pair = RewritePair(
                original_text=original,
                facts=facts,
                humanized_text=humanized,
                score=score,
                is_candidate=(score < 0.15),
                dialect=dialect
            )
            db.add(pair)
            db.commit()
            print(f"Engine: Saved rewrite pair log in DB. Fine-tuning candidate: {score < 0.15}")
        except Exception as e:
            print(f"Engine Warning: Failed to save rewrite pair to DB: {str(e)}")
        finally:
            db.close()


# Global singleton instance
rewriter_engine = RewriterEngine()
