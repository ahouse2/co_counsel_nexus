import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

print("Testing imports...")

try:
    from backend.app.services.autonomous_courtlistener_service import AutonomousCourtListenerService
    print("Successfully imported AutonomousCourtListenerService")
except Exception as e:
    print(f"Failed to import AutonomousCourtListenerService: {e}")

try:
    from backend.app.services.autonomous_scraper_service import AutonomousScraperService
    print("Successfully imported AutonomousScraperService")
except Exception as e:
    print(f"Failed to import AutonomousScraperService: {e}")
