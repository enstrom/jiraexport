"""
Konfiguration för Jira Export
"""
import os
from dotenv import load_dotenv

# Ladda miljövariabler från .env fil
load_dotenv()


class Config:
    """Konfigurationsklass för Jira-anslutning"""
    
    # Jira-anslutning
    JIRA_URL = os.getenv("JIRA_URL", "")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
    JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "")
    
    # Export-inställningar
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "exports")
    DOWNLOAD_ATTACHMENTS = True
    
    # PDF-inställningar
    PDF_PAGE_SIZE = "A4"
    PDF_MARGIN = 50
    
    @classmethod
    def validate(cls) -> bool:
        """Validera att alla nödvändiga konfigurationer finns"""
        required = ["JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"]
        missing = [field for field in required if not getattr(cls, field)]
        
        if missing:
            print(f"❌ Saknade konfigurationer: {', '.join(missing)}")
            print("   Kopiera .env.example till .env och fyll i dina uppgifter")
            return False
        return True
