import re
from bs4 import BeautifulSoup

# Regex to target emojis and other non-standard Unicode graphic symbols
EMOJI_PATTERN = re.compile(
    "["
    "\U00010000-\U0010FFFF"  # Emoji ranges
    "\u2600-\u27BF"          # Miscellaneous Symbols & Dingbats
    "\u2300-\u23FF"          # Miscellaneous Technical
    "]+",
    flags=re.UNICODE
)

# Text snippets typical of cookie notices, advertising, subscription, and copyrights
UNWANTED_PATTERNS = [
    r"(?i)this website uses cookies",
    r"(?i)all rights reserved",
    r"(?i)subscribe to read the full",
    r"(?i)click here to read",
    r"(?i)read more about",
    r"(?i)follow us on twitter",
    r"(?i)sign in to your account",
    r"(?i)copyright \u00a9 \d+",
    r"(?i)terms of service",
    r"(?i)privacy policy"
]


class StyleSanitizer:
    def __init__(self, min_words: int = 80, max_words: int = 250):
        self.min_words = min_words
        self.max_words = max_words

    def strip_html(self, html_content: str) -> str:
        """Remove all HTML tags, script, and style blocks using BeautifulSoup."""
        if not html_content:
            return ""
        
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Decompose scripts, styles, footer, navigation, and header blocks
        for element in soup(["script", "style", "footer", "nav", "header", "aside"]):
            element.decompose()
            
        return soup.get_text()

    def clean_text(self, text: str) -> str:
        """Sanitize text by removing emojis, unwanted boilerplate patterns, and normalizing spacing."""
        if not text:
            return ""

        # Remove emojis
        text = EMOJI_PATTERN.sub("", text)
        
        # Collapse multiple whitespaces/tabs/newlines
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        
        # Strip boilerplate line-by-line
        lines = text.split("\n")
        cleaned_lines = []
        
        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue
                
            # Check for unwanted patterns
            is_boilerplate = False
            for pattern in UNWANTED_PATTERNS:
                if re.search(pattern, trimmed):
                    is_boilerplate = True
                    break
                    
            if not is_boilerplate:
                cleaned_lines.append(trimmed)
                
        return "\n\n".join(cleaned_lines)

    def extract_style_chunks(self, html_content: str) -> list:
        """Convert raw HTML into a list of cleaned, sanitized paragraph chunks matching the target length limit."""
        # 1. Remove HTML wrapping
        raw_text = self.strip_html(html_content)
        
        # 2. Apply text cleaning & filter boilerplate
        clean_prose = self.clean_text(raw_text)
        
        # 3. Split into paragraphs
        paragraphs = [p.strip() for p in clean_prose.split("\n\n") if p.strip()]
        
        valid_chunks = []
        for p in paragraphs:
            # Normalize whitespace within paragraph
            p_clean = re.sub(r"\s+", " ", p)
            word_count = len(p_clean.split())
            
            # Length filter: must be between min_words and max_words
            if self.min_words <= word_count <= self.max_words:
                valid_chunks.append(p_clean)
                
        print(f"Sanitizer: Extracted {len(valid_chunks)} valid paragraphs out of {len(paragraphs)} total blocks.")
        return valid_chunks
