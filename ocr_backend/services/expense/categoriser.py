import re
from typing import Dict, Any

class ExpenseCategoriser:
    def __init__(self):
        # Deterministic rule-based keyword mapping
        # Maps category and confidence score base
        self.rules = {
            "Food": ["restaurant", "cafe", "bistro", "pizza", "burger", "coffee", "grocery", "supermarket", "diner"],
            "Travel": ["uber", "lyft", "taxi", "hotel", "motel", "airlines", "flight", "train", "transit"],
            "Shopping": ["apparel", "clothing", "shoes", "electronics", "mall", "store", "boutique", "amazon"],
            "Utilities": ["electric", "water", "gas", "internet", "phone", "telecom", "utility"]
        }
        self.default_category = "Others"

    def categorise(self, text: str, merchant: str) -> str:
        combined_text = f"{text} {merchant}".lower()
        
        category_scores = {category: 0 for category in self.rules.keys()}
        
        for category, keywords in self.rules.items():
            for keyword in keywords:
                # Count occurrences of the keyword
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', combined_text))
                category_scores[category] += count
                
        # Find category with max score
        best_category = self.default_category
        max_score = 0
        
        for cat, score in category_scores.items():
            if score > max_score:
                max_score = score
                best_category = cat
                
        # Optionally, one could integrate Groq LLM refinement here if needed, 
        # but the determinism is mandatory as primary requirement.
        
        return best_category
