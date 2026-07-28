import asyncio
import google.generativeai as genai
from app.core.config import settings

# Configure Gemini client if key is present
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


class GeminiService:
    def __init__(self):
        # Multimodal and generative models ranked in order of preference
        self.FALLBACK_MODELS = [
            "gemini-2.5-flash",
            "gemini-2.5-pro"
        ]

    def _call_gemini_sync(self, system_prompt: str, user_prompt: str, generation_config: dict = None) -> str:
        # Check if API key is configured
        if not settings.GEMINI_API_KEY:
            return f"[Gemini Dev Mode Mock] Prompt: '{user_prompt[:50]}...'\nGenerated content matches request."

        last_error = None
        for model_name in self.FALLBACK_MODELS:
            try:
                # Initialize model with system instruction
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_prompt
                )
                response = model.generate_content(user_prompt, generation_config=generation_config)
                return response.text.strip()
            except Exception as e:
                print(f"Gemini error with model {model_name}: {str(e)}. Trying fallback...")
                last_error = e
                
        raise Exception(f"All Gemini models failed. Last error: {str(last_error)}")

    async def _call_gemini(self, system_prompt: str, user_prompt: str, generation_config: dict = None) -> str:
        # Offload CPU/network block to thread pool to prevent event loop lag
        return await asyncio.to_thread(self._call_gemini_sync, system_prompt, user_prompt, generation_config)

    def summarize_audio_sync(self, file_path: str, system_prompt: str, user_prompt: str) -> str:
        if not settings.GEMINI_API_KEY:
            return f"[Gemini Dev Mode Audio Mock] Summarized audio from {os.path.basename(file_path)} successfully."

        # Upload the audio file to Gemini Files API
        print(f"Uploading audio file '{file_path}' to Gemini...")
        audio_file = genai.upload_file(path=file_path)
        print(f"Audio file uploaded successfully. Name: {audio_file.name}")

        last_error = None
        for model_name in self.FALLBACK_MODELS:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_prompt
                )
                
                # Pass both the uploaded file handle and text prompt to Gemini
                response = model.generate_content([audio_file, user_prompt])
                
                # Clean up the file immediately on Google's servers
                try:
                    audio_file.delete()
                    print(f"Cleaned up remote Gemini file: {audio_file.name}")
                except Exception as del_err:
                    print(f"Failed to delete Gemini remote file: {str(del_err)}")

                return response.text.strip()
            except Exception as e:
                print(f"Gemini audio processing failed with model {model_name}: {str(e)}. Trying fallback...")
                last_error = e
                
        # Clean up file on total execution failure
        try:
            audio_file.delete()
        except:
            pass
            
        raise Exception(f"All Gemini models failed to process audio file. Last error: {str(last_error)}")

    async def summarize_audio(self, file_path: str, system_prompt: str, user_prompt: str) -> str:
        return await asyncio.to_thread(self.summarize_audio_sync, file_path, system_prompt, user_prompt)

    async def rewrite_text(self, text: str, tone: str) -> str:
        system_prompt = (
            f"You are a master human writer and rewriter. Your goal is to rewrite the user's text so it is "
            f"100% indistinguishable from text written by a human. It must bypass all AI detectors by having high "
            f"perplexity (unpredictable word choices) and high burstiness (varying sentence lengths and structures).\n\n"
            f"Follow these strict rules:\n"
            f"1. Tone: Write in a natural, engaging, and {tone} tone.\n"
            f"2. Sentence Structure (Burstiness): Mix sentence lengths drastically. Follow a 25-word sentence with a 4-word sentence. Use occasional sentence fragments. Never write consecutive sentences of similar length or rhythm.\n"
            f"3. Vocabulary (Perplexity): Avoid typical AI/corporate fluff and predictable word choices. Do NOT use these forbidden words: delve, tapestry, testament, beacon, catalyst, leverage, optimize, streamline, foster, crucial, vibrant, demystify, revolutionary, robust, landscape.\n"
            f"4. Transitions: Do NOT use academic transition words like 'Moreover', 'Furthermore', 'In conclusion', 'Additionally', 'On one hand...'. Use informal or natural human transitions (e.g., 'But here's the thing', 'So', 'Plus', 'Actually', 'Though').\n"
            f"5. Conversational Style: Use contractions (e.g., don't, it's, we'll, there's) and active voice instead of passive. Include occasional rhetorical questions or conversational asides if they fit the tone.\n"
            f"6. Meaning preservation: Keep the core message intact, but restructure the phrasing and paragraphs completely. Do not do a simple word-for-word replacement."
        )
        generation_config = {
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 40
        }
        return await self._call_gemini(system_prompt, f"Text to rewrite:\n{text}", generation_config)

    async def generate_tweets(self, topic: str, context: str = None, tone: str = "engaging") -> list:
        system_prompt = (
            f"You are an expert social media manager. Generate a list of 3 distinct, high-impact tweets (within 280 characters each) "
            f"about the user's topic in a {tone} tone. Return the tweets separated by a triple dash '---'. "
            f"Do not write markdown numbers, descriptions, or emojis at the start of tweets."
        )
        user_prompt = f"Topic: {topic}\nContext: {context or 'None'}"
        raw_output = await self._call_gemini(system_prompt, user_prompt)
        tweets = [t.strip() for t in raw_output.split("---") if t.strip()]
        return tweets[:3]

    async def generate_linkedin(self, topic: str, context: str = None, tone: str = "engaging") -> str:
        system_prompt = (
            f"You are a thought leader on LinkedIn. Write a compelling, readable post "
            f"about the user's topic in a {tone} tone. Use natural spacing, clear paragraphs, "
            f"and 2-3 targeted hashtags. Keep it professional and engaging."
        )
        user_prompt = f"Topic: {topic}\nContext: {context or 'None'}"
        return await self._call_gemini(system_prompt, user_prompt)


gemini_service = GeminiService()
