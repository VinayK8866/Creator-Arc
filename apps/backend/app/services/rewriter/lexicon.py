import re

# Phrase mappings for Indian English post-processing
INDIAN_ENGLISH_LEXICON = {
    # 1. ASAP / Prompt Reply -> Kindly revert at the earliest
    r"\b(please reply|reply|let me know|respond) as soon as possible\b": "kindly revert at the earliest",
    r"\bplease reply asap\b": "kindly revert at the earliest",
    
    # 2. Rescheduling to an earlier date -> Prepone
    r"\breschedule the meeting to an earlier (date|time)\b": "prepone the meeting",
    r"\brescheduled to an earlier (date|time)\b": "preponed",
    r"\bmove the meeting to an earlier (date|time)\b": "prepone the meeting",
    r"\breschedule to an earlier date\b": "prepone",
    
    # 3. Please find attached / attached file -> PFA
    r"\bplease find the attached file\b": "PFA the document",
    r"\bplease find attached\b": "PFA",
    r"\battached is the document\b": "PFA the document",
    
    # 4. Revert Back
    r"\breply back\b": "revert back",
    r"\bget back to me\b": "revert back to me",
    
    # 5. Do this one thing -> Do one thing
    r"\bdo this one thing\b": "do one thing",
    r"\bfirst, do one thing\b": "do one thing first",
    
    # 6. Discussing about
    r"\bdiscuss the ([a-zA-Z0-9_\- ]+)\b": r"discuss about the \1",
}

# Phrase mappings for Singapore English (Singlish / Professional SG)
SINGAPORE_ENGLISH_LEXICON = {
    r"\b(please reply|reply|let me know|respond) as soon as possible\b": "kindly revert at the earliest",
    r"\bplease reply asap\b": "kindly revert at the earliest",
    r"\bplease find the attached file\b": "PFA the document",
    r"\bplease find attached\b": "PFA",
    r"\breply back\b": "revert back",
    r"\btake sick leave\b": "take MC",
    r"\bsubmit a sick note\b": "submit MC",
    r"\bput a stamp\b": "chop",
    r"\bafraid of missing out\b": "kiasu",
    r"\breschedule the meeting to an earlier (date|time)\b": "prepone the meeting",
}

# Phrase mappings for Australian English
AUSTRALIAN_ENGLISH_LEXICON = {
    r"\bthis afternoon\b": "this arvo",
    r"\bafternoon\b": "arvo",
    r"\btwo weeks\b": "a fortnight",
    r"\bno problem\b": "no worries",
    r"\byou're welcome\b": "no worries",
    r"\bhow are you\b": "how ya going",
    r"\buniversity\b": "uni",
    r"\bbarbecue\b": "barbie",
}

# Phrase mappings for British English
BRITISH_ENGLISH_LEXICON = {
    r"\bcolor\b": "colour",
    r"\bcolors\b": "colours",
    r"\bflavor\b": "flavour",
    r"\bflavors\b": "flavours",
    r"\banalyze\b": "analyse",
    r"\banalyzed\b": "analysed",
    r"\banalyzes\b": "analyses",
    r"\banalyzing\b": "analysing",
    r"\borganization\b": "organisation",
    r"\borganizations\b": "organisations",
    r"\brealize\b": "realise",
    r"\brealized\b": "realised",
    r"\brealizes\b": "realises",
    r"\brealizing\b": "realising",
    r"\bdefense\b": "defence",
    r"\boffense\b": "offence",
    r"\bapartment\b": "flat",
    r"\bapartments\b": "flats",
    r"\belevator\b": "lift",
    r"\belevators\b": "lifts",
    r"\bvacation\b": "holiday",
    r"\bvacations\b": "holidays",
    r"\bqueue\b": "line",
}


class LexiconProcessor:
    @staticmethod
    def get_dialect_instructions(dialect: str) -> str:
        """Get system prompt instructions for the target dialect, guiding the LLM
        to natively use appropriate local phrases, spelling, and vocabulary.
        """
        dialect_lower = dialect.lower()
        if dialect_lower == "en-in":
            return (
                "DIALECT DIRECTIVE: You MUST write in professional Indian English (en-IN). "
                "Incorporate the following regional corporate idioms and patterns naturally where appropriate:\n"
                "- Use 'prepone' (or 'preponed') when moving a meeting or event to an earlier date/time.\n"
                "- Use 'kindly revert' or 'revert at the earliest' when asking for a reply or response.\n"
                "- Use 'revert back' when returning to a topic or replying.\n"
                "- Use 'PFA' (Please Find Attached) when referencing attachments (e.g., 'PFA the document').\n"
                "- Use 'do one thing' instead of 'do this one thing' (e.g., 'do one thing: check the doc').\n"
                "- Use 'discuss about' followed by the topic (e.g., 'discuss about the feedback').\n"
                "- Ensure the tone is polite and professional, reflecting typical Indian corporate communication styles."
            )
        elif dialect_lower == "en-sg":
            return (
                "DIALECT DIRECTIVE: You MUST write in Singapore English / professional Singlish (en-SG). "
                "Incorporate the following regional idioms naturally where appropriate:\n"
                "- Use 'prepone the meeting' when moving a meeting to an earlier date/time.\n"
                "- Use 'kindly revert at the earliest' when requesting a response.\n"
                "- Use 'revert back' when replying or getting back to someone.\n"
                "- Use 'PFA' or 'PFA the document' to refer to attachments.\n"
                "- Use 'take MC' or 'submit MC' when referencing sick leave or sick notes.\n"
                "- Use 'chop' when referring to putting a stamp or signing off/sealing an agreement.\n"
                "- Use 'kiasu' naturally when describing an anxious attitude of avoiding missing out on an opportunity."
            )
        elif dialect_lower == "en-au":
            return (
                "DIALECT DIRECTIVE: You MUST write in Australian English (en-AU). "
                "Incorporate the following Australian terms and spelling conventions naturally where appropriate:\n"
                "- Use 'this arvo' or 'arvo' instead of 'this afternoon' or 'afternoon'.\n"
                "- Use 'a fortnight' instead of 'two weeks'.\n"
                "- Use 'no worries' instead of 'no problem' or 'you're welcome'.\n"
                "- Use 'how ya going' instead of 'how are you'.\n"
                "- Use 'uni' instead of 'university'.\n"
                "- Use 'barbie' instead of 'barbecue'.\n"
                "- Employ spelling conventions common in Australia (e.g., colour, analyse, organisation)."
            )
        elif dialect_lower == "en-gb":
            return (
                "DIALECT DIRECTIVE: You MUST write in British English (en-GB). "
                "Follow these British English spelling and vocabulary conventions:\n"
                "- Spelling: Use British spellings: '-our' instead of '-or' (colour, flavour), "
                "'-ise'/'-ising'/'-ised' instead of '-ize'/'-izing'/'-ized' (analyse, organisation, realise), "
                "and '-ce' instead of '-se' for nouns (defence, offence).\n"
                "- Vocabulary: Use 'flat' instead of 'apartment', 'lift' instead of 'elevator', "
                "'holiday' instead of 'vacation', and 'queue' instead of 'line'.\n"
                "- Keep the phrasing natural and idiomatic to British business/writing styles."
            )
        return ""

    @staticmethod
    def translate(text: str, dialect: str = "en-US") -> str:
        """Post-process the rewritten text. With dialect shifting moved directly into 
        the LLM prompt, this method only performs minor casing and capitalization cleanup.
        """
        dialect_lower = dialect.lower()
        processed_text = text
        
        # Capitalize specific acronyms if they appear in text
        if dialect_lower in ("en-in", "en-sg"):
            # Ensure PFA is capitalized if written in lowercase by the LLM
            processed_text = re.sub(r"\bpfa\b", "PFA", processed_text, flags=re.IGNORECASE)
            
        return processed_text
