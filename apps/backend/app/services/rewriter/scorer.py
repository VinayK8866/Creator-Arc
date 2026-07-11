import re
import os
import statistics
import urllib.request
import numpy as np
import google.generativeai as genai
from app.core.config import settings

# Configure Gemini client
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

MODEL_URL = "https://huggingface.co/Xenova/roberta-base-openai-detector/resolve/main/onnx/model_quantized.onnx"
TOKENIZER_NAME = "roberta-base-openai-detector"


class AdversarialScorer:
    """Class to rate the AI-likelihood of text.
    Returns a score between 0.0 (perfectly human) and 1.0 (obviously AI).
    """

    def __init__(self):
        # Traditional AI detector typical words
        self.AI_CLICHES = {
            "delve", "tapestry", "testament", "beacon", "catalyst", "leverage", 
            "optimize", "streamline", "foster", "demystify", "revolutionary", 
            "robust", "landscape", "moreover", "furthermore", "in conclusion", 
            "additionally", "underscores", "pivotal", "nestled", "whispers"
        }
        
        self.tokenizer = None
        self.ort_session = None
        self.model_path = ""
        self.onnx_available = False
        
        self._initialize_onnx()

    def _initialize_onnx(self):
        """Try loading ONNX Runtime and the RoBERTa tokenizer."""
        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer
            from huggingface_hub import hf_hub_download
            import os
            
            print("ONNXScorer: Resolving local detector model from Hugging Face...")
            self.model_path = hf_hub_download(
                repo_id="nicoamoretti/roberta-openai-detector-onnx",
                filename="onnx/model.onnx",
                local_files_only=False
            )
            
            if self.model_path and os.path.exists(self.model_path):
                print(f"ONNXScorer: Loading ONNX session from {self.model_path}...")
                self.ort_session = ort.InferenceSession(self.model_path, providers=["CPUExecutionProvider"])
                self.tokenizer = AutoTokenizer.from_pretrained("nicoamoretti/roberta-openai-detector-onnx", local_files_only=False)
                self.onnx_available = True
                print("ONNXScorer: Successfully initialized local RoBERTa classifier.")
            else:
                print("ONNXScorer: Model file not found in cache. Falling back to API/heuristics.")
        except Exception as e:
            print(f"ONNXScorer Warning: Failed to initialize ONNX classifier: {str(e)}. Using fallback paths.")
            self.onnx_available = False

    def update_model(self, repo_id: str = "nicoamoretti/roberta-openai-detector-onnx", filename: str = "onnx/model.onnx") -> bool:
        """Download and update the ONNX model from Hugging Face."""
        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer
            from huggingface_hub import hf_hub_download
            import os
            
            print(f"ONNXScorer: Updating/downloading detector model from Hugging Face repo '{repo_id}'...")
            new_model_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_files_only=False,
                force_download=True
            )
            
            if new_model_path and os.path.exists(new_model_path):
                print(f"ONNXScorer: Successfully downloaded model. Initializing new ONNX session...")
                new_session = ort.InferenceSession(new_model_path, providers=["CPUExecutionProvider"])
                new_tokenizer = AutoTokenizer.from_pretrained(repo_id, local_files_only=False)
                
                # Atomically update session and tokenizer
                self.model_path = new_model_path
                self.ort_session = new_session
                self.tokenizer = new_tokenizer
                self.onnx_available = True
                print("ONNXScorer: Scorer model updated successfully.")
                return True
            return False
        except Exception as e:
            print(f"ONNXScorer Error during model update: {str(e)}")
            return False

    def _score_local_heuristics(self, text: str) -> float:
        """Calculate a quick AI score offline based on burstiness (sentence variance) and perplexity (clichés)."""
        words = text.split()
        if not words:
            return 1.0

        # Split into sentences using simple regex
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if len(sentences) < 2:
            # Single sentences don't have burstiness, mark with higher AI chance unless very short/long
            return 0.60

        sentence_lengths = [len(s.split()) for s in sentences]
        
        # 1. Burstiness (Sentence length variation)
        std_dev = statistics.stdev(sentence_lengths) if len(sentence_lengths) > 1 else 0
        
        if std_dev >= 8.0:
            burstiness_penalty = 0.0
        elif std_dev >= 5.0:
            burstiness_penalty = 0.1
        elif std_dev >= 3.0:
            burstiness_penalty = 0.3
        else:
            burstiness_penalty = 0.5  # Very uniform/AI-like sentence lengths

        # 2. Perplexity (Forbidden word density)
        found_cliches = [w for w in words if w.lower().strip(",.?!:;()") in self.AI_CLICHES]
        cliche_density = len(found_cliches) / len(words)
        
        cliche_penalty = min(cliche_density * 10, 0.5)

        # 3. Base Score
        base_score = 0.1
        total_score = base_score + burstiness_penalty + cliche_penalty
        return min(max(total_score, 0.0), 1.0)

    def _softmax(self, x):
        """Compute softmax values for logits."""
        e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e_x / np.sum(e_x, axis=-1, keepdims=True)

    def _score_onnx(self, text: str) -> float:
        """Execute local ONNX RoBERTa model inference to score AI-probability."""
        if not self.onnx_available or not self.ort_session or not self.tokenizer:
            raise Exception("ONNX classifier is not initialized.")
            
        # Tokenize inputs
        inputs = self.tokenizer(
            text, 
            return_tensors="np", 
            truncation=True, 
            max_length=512
        )
        
        input_names = [i.name for i in self.ort_session.get_inputs()]
        
        onnx_inputs = {}
        if "input_ids" in input_names:
            onnx_inputs["input_ids"] = inputs["input_ids"].astype(np.int64)
        if "attention_mask" in input_names:
            onnx_inputs["attention_mask"] = inputs["attention_mask"].astype(np.int64)
            
        # Run model inference
        outputs = self.ort_session.run(None, onnx_inputs)
        logits = outputs[0]
        
        # Softmax to get probabilities (Class 0: Human, Class 1: AI)
        probs = self._softmax(logits)
        return float(probs[0][1])

    async def score_text(self, text: str, use_api: bool = True) -> float:
        """Score the text's AI-generated probability.
        Tries local ONNX RoBERTa model first.
        Falls back to Gemini API scorer, then to local heuristics.
        """
        # 1. Try local ONNX model
        if self.onnx_available:
            try:
                score = self._score_onnx(text)
                print(f"ONNXScorer: Executed offline RoBERTa AI detection. Score: {score:.4f}")
                return score
            except Exception as e:
                print(f"ONNXScorer Error: Offline inference failed ({str(e)}). Trying fallback.")

        # 2. Try Gemini API
        if use_api and settings.GEMINI_API_KEY:
            try:
                # Ask Gemini to evaluate the text acting as a neural classifier
                system_prompt = (
                    "You are an advanced AI content detection tool (like GPTZero or Quillbot). "
                    "Analyze the provided text for writing patterns, transitions, vocabulary frequency, "
                    "sentence length uniformity (burstiness), and structural predictability (perplexity).\n\n"
                    "Return your evaluation ONLY in the following JSON format:\n"
                    '{"ai_probability": <float_between_0.0_and_1.0>, "reasons": [<str>]}\n'
                    "Do not include any extra markdown formatting or preambles."
                )
                
                response = None
                last_err = None
                for model_name in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-pro", "gemini-1.5-pro"]:
                    try:
                        model = genai.GenerativeModel(
                            model_name=model_name,
                            system_instruction=system_prompt
                        )
                        response = model.generate_content(
                            f"Analyze this text:\n\n{text}",
                            generation_config={"response_mime_type": "application/json"}
                        )
                        break
                    except Exception as model_err:
                        last_err = model_err
                        if "404" in str(model_err) or "not found" in str(model_err).lower() or "not supported" in str(model_err).lower():
                            continue
                        raise model_err
                
                if response is None:
                    raise last_err
                
                import json
                result = json.loads(response.text.strip())
                score = float(result.get("ai_probability", 0.5))
                return min(max(score, 0.0), 1.0)
            except Exception as e:
                print(f"API scoring failed: {str(e)}. Falling back to local heuristics.")

        # 3. Fallback: Local Heuristics
        return self._score_local_heuristics(text)
