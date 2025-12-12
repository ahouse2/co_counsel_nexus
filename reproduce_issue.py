import requests
import zipfile
import io
import os

def create_zip_content():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('test_folder/test_file.txt', 'This is a test file content.')
    buffer.seek(0)
    return buffer.read()

def test_upload_directory():
    url = "http://localhost:8001/api/documents/upload_directory"
    params = {"case_id": "test_case"}
    
    zip_content = create_zip_content()
    
    files = {
        'file': ('test.zip', zip_content, 'application/zip')
    }
    data = {
        'document_id': 'test_doc_id_123'
    }
    
    try:
        print(f"Uploading to {url}...")
        response = requests.post(url, params=params, files=files, data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_upload_directory()
