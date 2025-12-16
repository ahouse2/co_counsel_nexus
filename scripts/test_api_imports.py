import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

print("Testing API imports...")

try:
    from backend.app.api import autonomous_courtlistener
    print("Successfully imported autonomous_courtlistener")
except Exception as e:
    print(f"Failed to import autonomous_courtlistener: {e}")

try:
    from backend.app.api import autonomous_scraping
    print("Successfully imported autonomous_scraping")
except Exception as e:
    print(f"Failed to import autonomous_scraping: {e}")
