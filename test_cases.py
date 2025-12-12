import requests
import json
import zipfile
import io

BASE_URL = "http://localhost:8001/api"

def test_case_management():
    print("Testing Case Management...")
    
    # 1. Create Case
    print("1. Creating Case...")
    response = requests.post(f"{BASE_URL}/cases", json={"name": "Test Case", "description": "A test case"})
    if response.status_code != 200:
        print(f"Failed to create case: {response.text}")
        return
    case = response.json()
    case_id = case["id"]
    print(f"   Created case: {case_id}")
    
    # 2. List Cases
    print("2. Listing Cases...")
    response = requests.get(f"{BASE_URL}/cases")
    cases = response.json()
    found = any(c["id"] == case_id for c in cases)
    print(f"   Case found in list: {found}")
    
    # 3. Export Case
    print("3. Exporting Case...")
    response = requests.get(f"{BASE_URL}/cases/{case_id}/export")
    if response.status_code != 200:
        print(f"Failed to export case: {response.text}")
        return
    
    zip_content = response.content
    with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
        print(f"   Exported zip contains: {z.namelist()}")
        
    # 4. Import Case
    print("4. Importing Case...")
    # Modify the case name in the export to verify update
    with zipfile.ZipFile(io.BytesIO(zip_content), "r") as z_in:
        case_meta = json.loads(z_in.read("case_metadata.json"))
        case_meta["name"] = "Test Case Imported"
        
        out_buffer = io.BytesIO()
        with zipfile.ZipFile(out_buffer, "w") as z_out:
            z_out.writestr("case_metadata.json", json.dumps(case_meta))
            z_out.writestr("documents_metadata.json", z_in.read("documents_metadata.json"))
            
        out_buffer.seek(0)
        files = {"file": ("import.zip", out_buffer, "application/zip")}
        response = requests.post(f"{BASE_URL}/cases/import", files=files)
        
        if response.status_code != 200:
            print(f"Failed to import case: {response.text}")
            return
            
        imported_case = response.json()
        print(f"   Imported case name: {imported_case['name']}")
        assert imported_case["name"] == "Test Case Imported"
        
    print("Case Management Test Passed!")

if __name__ == "__main__":
    try:
        test_case_management()
    except Exception as e:
        print(f"Test failed with error: {e}")
