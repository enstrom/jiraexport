#!/usr/bin/env python3
"""Test Jira-anslutningen"""
from jira import JIRA
from config import Config

print("🔌 Testar anslutning till Jira...")
print(f"   URL: {Config.JIRA_URL}")
print(f"   Email: {Config.JIRA_EMAIL}")
print(f"   Token: {Config.JIRA_API_TOKEN[:20]}...")
print()

try:
    jira = JIRA(
        server=Config.JIRA_URL,
        basic_auth=(Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)
    )
    
    # Testa med att hämta användaren
    myself = jira.myself()
    print(f"✅ Anslutning lyckades!")
    print(f"   Inloggad som: {myself['displayName']}")
    print(f"   Email: {myself.get('emailAddress', 'N/A')}")
    print()
    
    # Lista tillgängliga projekt
    print("📋 Tillgängliga projekt:")
    projects = jira.projects()
    for p in projects[:10]:
        print(f"   • {p.key}: {p.name}")
    
    if len(projects) > 10:
        print(f"   ... och {len(projects) - 10} till")
    
except Exception as e:
    print(f"❌ Anslutning misslyckades: {e}")
    print()
    print("💡 Kontrollera att:")
    print("   1. API-token är korrekt kopierad (hela strängen)")
    print("   2. E-postadressen matchar ditt Atlassian-konto")
    print("   3. Du har behörighet till Jira-instansen")
