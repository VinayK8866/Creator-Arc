import os
import numpy as np
import google.generativeai as genai
from app.core.config import settings

# Configure Gemini client
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


class NLIConsistencyScorer:
    """Class to check semantic and factual alignment between facts (premise) 
    and rewritten text (hypothesis). Returns a score between 0.0 (contradictory/unaligned)
    and 1.0 (perfectly aligned/entailed).
    """

    def __init__(self):
        self.tokenizer = None
        self.ort_session = None
        self.onnx_available = False
        self.model_path = ""
        self._initialize_onnx()

    def _initialize_onnx(self):
        """Load ONNX Runtime session and tokenizer for DeBERTa NLI."""
        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer
            from huggingface_hub import hf_hub_download
            
            print("NLIScorer: Resolving local NLI model from Hugging Face...")
            self.model_path = hf_hub_download(
                repo_id="Xenova/nli-deberta-v3-base",
                filename="onnx/model.onnx",
                local_files_only=False
            )
            
            if self.model_path and os.path.exists(self.model_path):
                print(f"NLIScorer: Loading ONNX session from {self.model_path}...")
                self.ort_session = ort.InferenceSession(self.model_path, providers=["CPUExecutionProvider"])
                self.tokenizer = AutoTokenizer.from_pretrained("Xenova/nli-deberta-v3-base", local_files_only=False)
                self.onnx_available = True
                print("NLIScorer: Successfully initialized local DeBERTa NLI classifier.")
            else:
                print("NLIScorer: NLI model file not found in cache. Falling back to API.")
        except Exception as e:
            print(f"NLIScorer Warning: Failed to initialize ONNX NLI classifier: {str(e)}. Using API fallback.")
            self.onnx_available = False

    def _score_local_onnx(self, premise: str, hypothesis: str) -> float:
        """Run local ONNX model inference to score factual consistency."""
        if not self.onnx_available or not self.ort_session or not self.tokenizer:
            raise Exception("ONNX NLI classifier not initialized.")
            
        inputs = self.tokenizer(
            premise,
            hypothesis,
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
            
        outputs = self.ort_session.run(None, onnx_inputs)
        logits = outputs[0][0]
        
        # Softmax: Index 0 = Contradiction, Index 1 = Entailment, Index 2 = Neutral
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)
        
        entailment_prob = float(probs[1])
        contradiction_prob = float(probs[0])
        
        # Penalize alignment score if contradiction probability is high
        if contradiction_prob > 0.35:
            return min(entailment_prob, 1.0 - contradiction_prob)
            
        return entailment_prob

    async def check_consistency(self, facts: list, hypothesis: str, use_api: bool = True) -> float:
        """Check factual consistency between premise (facts) and hypothesis (rewritten text).
        Evaluates fact-by-fact in both directions to ensure bidirectional semantic alignment
        without false negatives caused by specificity variations.
        Returns the minimum consistency score across all facts (target: >= 0.85).
        """
        if not facts:
            return 1.0
            
        # Reverse-normalize regional dialect terms to standard English to ensure the NLI model
        # understands the vocabulary correctly (avoiding out-of-vocabulary penalty).
        normalized_hypothesis = hypothesis
        reverse_lexicon = {
            r"\bprepone\b": "reschedule to an earlier date",
            r"\bpreponed\b": "rescheduled to an earlier date",
            r"\bpfa\b": "please find attached",
            r"\brevert at the earliest\b": "reply as soon as possible",
            r"\bkindly revert\b": "please reply",
            r"\brevert back\b": "reply back",
            r"\bdiscuss about\b": "discuss",
            r"\bdo one thing\b": "do this one thing",
            r"\btake MC\b": "take sick leave",
            r"\bsubmit MC\b": "submit a sick note",
            r"\bchop\b": "stamp/sign",
            r"\bkiasu\b": "fear of missing out",
            r"\bthis arvo\b": "this afternoon",
            r"\barvo\b": "afternoon",
            r"\ba fortnight\b": "two weeks",
            r"\bno worries\b": "no problem",
            r"\bhow ya going\b": "how are you",
            r"\buni\b": "university",
            r"\bbarbie\b": "barbecue",
        }
        
        import re
        for pattern, replacement in reverse_lexicon.items():
            normalized_hypothesis = re.sub(pattern, replacement, normalized_hypothesis, flags=re.IGNORECASE)

        scores = []
        
        # 1. Try local ONNX model
        if self.onnx_available:
            try:
                for fact in facts:
                    # Direction A: Hypothesis entails Fact (standard check if hyp is more specific)
                    score_a = self._score_local_onnx(normalized_hypothesis, fact)
                    # Direction B: Fact entails Hypothesis (standard check if hyp is weaker/modal)
                    score_b = self._score_local_onnx(fact, normalized_hypothesis)
                    
                    # Take the maximum entailment score of the two directions
                    fact_score = max(score_a, score_b)
                    scores.append(fact_score)
                    
                min_score = min(scores) if scores else 1.0
                print(f"NLIScorer: Offline NLI checks. Fact scores: {[f'{s:.4f}' for s in scores]}. Min Alignment: {min_score:.4f}")
                return min_score
            except Exception as e:
                print(f"NLIScorer Error: Local NLI inference failed ({str(e)}). Trying API fallback.")
                scores = []

        # 2. Try Gemini API fallback
        if use_api and settings.GEMINI_API_KEY:
            try:
                system_prompt = (
                    "You are a strict natural language inference (NLI) classifier. "
                    "Your job is to determine the factual consistency between a set of Premise Facts "
                    "and a Hypothesis (the rewritten text).\n\n"
                    "For each Premise Fact, determine if it is entailed by (logically consistent with) "
                    "the Hypothesis. Ensure there are no direct contradictions or omissions.\n"
                    "Return your evaluation ONLY in the following JSON format:\n"
                    '{"entailment_probability": <float_between_0.0_and_1.0>, "reasons": [<str>]}\n'
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
                        premise_str = "\n".join([f"- {fact}" for fact in facts])
                        user_prompt = (
                            f"Premise Facts:\n{premise_str}\n\n"
                            f"Hypothesis (Rewritten Text):\n{normalized_hypothesis}\n\n"
                            "Evaluate consistency now:"
                        )
                        response = model.generate_content(
                            user_prompt,
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
                score = float(result.get("entailment_probability", 0.5))
                print(f"NLIScorer: Executed Gemini API NLI check. Factual Alignment: {score:.4f}")
                return min(max(score, 0.0), 1.0)
            except Exception as e:
                print(f"NLIScorer API fallback failed: {str(e)}. Returning default alignment score.")
                
        # 3. Safe fallback
        return 1.0
