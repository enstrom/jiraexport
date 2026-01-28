#!/usr/bin/env python3
"""Sök efter projekt"""
from jira import JIRA
from config import Config

jira = JIRA(
    server=Config.JIRA_URL,
    basic_auth=(Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)
)

# Sök efter SOMU
print("🔍 Söker efter projekt som innehåller 'SOMU' eller 'Icon'...")
print()

projects = jira.projects()
matches = [p for p in projects if 'somu' in p.key.lower() or 'somu' in p.name.lower() 
           or 'icon' in p.name.lower() or 'media' in p.name.lower()]

if matches:
    print("Hittade matchande projekt:")
    for p in matches:
        print(f"   • {p.key}: {p.name}")
else:
    print("Inga projekt hittades med 'SOMU', 'Icon' eller 'Media'")
    print()
    print("Alla tillgängliga projekt (första 30):")
    for p in projects[:30]:
        print(f"   • {p.key}: {p.name}")
