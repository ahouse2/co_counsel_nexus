from app.services.document_generation import get_document_generation_service
import os

def test_document_generation():
    service = get_document_generation_service()
    
    # Test Draft
    draft_path = "test_draft.docx"
    service.draft_legal_document(
        filepath=draft_path,
        motion_type="Summary Judgment",
        data={
            "case_id": "123",
            "date": "2023-10-27",
            "introduction": "Intro text",
            "facts": ["Fact 1", "Fact 2"],
            "argument": "Legal argument",
            "conclusion": "Conclusion text"
        }
    )
    if os.path.exists(draft_path):
        print(f"Draft generated at {draft_path}")
        os.remove(draft_path)
    else:
        print("Draft generation failed")

    # Test Binder
    binder_path = "test_binder.docx"
    service.prepare_binder(
        filepath=binder_path,
        evidence_list=[
            {"id": "1", "name": "Ev 1", "type": "doc", "url": "http://example.com", "annotation": "Note 1"}
        ],
        case_name="Test Case"
    )
    if os.path.exists(binder_path):
        print(f"Binder generated at {binder_path}")
        os.remove(binder_path)
    else:
        print("Binder generation failed")

if __name__ == "__main__":
    test_document_generation()
