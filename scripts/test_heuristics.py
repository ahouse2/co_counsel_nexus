from backend.ingestion.categorization import heuristic_categorize, heuristic_tag

def test_heuristics():
    print("Testing Heuristic Categorization...")
    
    samples = [
        (
            "This Settlement Agreement is entered into by and between Plaintiff and Defendant.",
            ["Contract", "Pleading"] # "Plaintiff/Defendant" triggers Pleading, "Settlement Agreement" triggers Contract
        ),
        (
            "INVOICE #12345\nTotal: $500.00\nFrom: Service Corp\nTo: Client Inc",
            ["Financial", "Correspondence"] # "Invoice" -> Financial, "From:/To:" -> Correspondence
        ),
        (
            "CONFIDENTIAL MEMORANDUM\nSubject: Internal Review",
            ["Correspondence"] # "Memorandum", "Subject:" -> Correspondence
        )
    ]
    
    for text, expected in samples:
        cats = heuristic_categorize(text)
        tags = heuristic_tag(text)
        print(f"\nText: {text[:50]}...")
        print(f"Categories: {cats}")
        print(f"Tags: {tags}")
        
        # Basic validation
        if not cats:
            print("❌ No categories found (Expected matches)")
        else:
            print("✅ Categories found")

if __name__ == "__main__":
    test_heuristics()
