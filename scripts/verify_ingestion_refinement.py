import unittest
import asyncio
import os
from pathlib import Path
import shutil
from backend.app.services.flagging_service import get_flagging_service
from backend.app.services.document_processing_service import DocumentProcessingService

class TestIngestionRefinement(unittest.TestCase):
    
    def setUp(self):
        self.test_dir = Path("test_ingestion_refinement")
        self.test_dir.mkdir(exist_ok=True)
        self.doc_processor = DocumentProcessingService()
        self.flagging_service = get_flagging_service()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_flagging_service(self):
        print("\nTesting Flagging Service...")
        
        # Test sensitive keywords
        text = "This document contains CONFIDENTIAL information."
        metadata = {"file_extension": ".txt"}
        flags = self.flagging_service.check_flags(text, metadata)
        self.assertIn("SENSITIVE", flags)
        print("  [OK] Detected 'SENSITIVE' flag")
        
        # Test privileged terms
        text = "This is protected by attorney-client privilege."
        flags = self.flagging_service.check_flags(text, metadata)
        self.assertIn("PRIVILEGED", flags)
        print("  [OK] Detected 'PRIVILEGED' flag")
        
        # Test suspicious file type
        metadata = {"file_extension": ".exe"}
        flags = self.flagging_service.check_flags("some text", metadata)
        self.assertIn("SUSPICIOUS_TYPE", flags)
        print("  [OK] Detected 'SUSPICIOUS_TYPE' flag")
        
        # Test large file flag
        metadata = {"file_extension": ".txt", "file_size": 60 * 1024 * 1024}
        flags = self.flagging_service.check_flags("some text", metadata)
        self.assertIn("LARGE_FILE", flags)
        print("  [OK] Detected 'LARGE_FILE' flag")

    def test_text_splitting(self):
        print("\nTesting Text Splitting...")
        
        # Create a "large" text file (simulated by setting max_size_mb small)
        large_file = self.test_dir / "large_doc.txt"
        content = "A" * (1024 * 1024 * 2) # 2MB
        with open(large_file, "w") as f:
            f.write(content)
            
        # Split with max size 1MB
        chunks = asyncio.run(self.doc_processor.split_text_file(large_file, max_size_mb=1))
        
        self.assertEqual(len(chunks), 2)
        self.assertTrue(chunks[0].name.endswith("_part_1_of_2.txt"))
        self.assertTrue(chunks[1].name.endswith("_part_2_of_2.txt"))
        print(f"  [OK] Split 2MB file into {len(chunks)} chunks (limit 1MB)")
        
        # Verify content
        with open(chunks[0], "r") as f:
            self.assertEqual(len(f.read()), 1024 * 1024)
            
    # Note: PDF splitting requires a valid PDF file, which is hard to generate on the fly without reportlab.
    # We will skip PDF generation test here and rely on the logic similarity with text splitting.

if __name__ == '__main__':
    unittest.main()
