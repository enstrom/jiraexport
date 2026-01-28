#!/usr/bin/env python3
"""
Exportera alla tickets från en CSV-fil till PDF
"""
import csv
import sys
import os
from config import Config
from jira_client import JiraClient
from pdf_generator import PDFGenerator


def export_from_csv(csv_path: str, download_attachments: bool = True):
    """
    Exportera alla tickets från CSV-fil till PDF
    
    Args:
        csv_path: Sökväg till CSV-fil
        download_attachments: Om bilagor ska laddas ner
    """
    # Läs issue keys från CSV
    issue_keys = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Hitta rätt kolumnnamn (kan vara "Issue key" eller liknande)
        key_column = None
        for col in reader.fieldnames:
            if 'issue' in col.lower() and 'key' in col.lower():
                key_column = col
                break
        
        if not key_column:
            print(f"❌ Kunde inte hitta 'Issue key'-kolumn i CSV-filen")
            print(f"   Tillgängliga kolumner: {reader.fieldnames}")
            return
        
        print(f"📋 Läser tickets från kolumn: '{key_column}'")
        
        for row in reader:
            key = row.get(key_column, '').strip()
            if key and key not in issue_keys:
                issue_keys.append(key)
    
    print(f"   Hittade {len(issue_keys)} unika tickets")
    print()
    
    # Bekräfta
    if len(issue_keys) > 10:
        print(f"Första 10: {', '.join(issue_keys[:10])}")
        print(f"...")
        print(f"Sista 5: {', '.join(issue_keys[-5:])}")
        print()
    
    # Initiera klienter
    print("🔌 Ansluter till Jira...")
    jira = JiraClient()
    pdf_gen = PDFGenerator()
    
    # Exportera alla
    exported = []
    failed = []
    
    for i, issue_key in enumerate(issue_keys, 1):
        print(f"\n[{i}/{len(issue_keys)}] 📥 Hämtar {issue_key}...")
        
        try:
            issue_data = jira.get_issue(issue_key)
            
            # Ladda ner bilagor
            attachment_paths = []
            if download_attachments and issue_data.get('attachments'):
                print(f"   📎 Laddar ner {len(issue_data['attachments'])} bilagor...")
                att_dir = os.path.join(Config.OUTPUT_DIR, 'attachments', issue_key)
                attachment_paths = jira.download_all_attachments(issue_data, att_dir)
            
            # Generera PDF
            print(f"   📄 Genererar PDF...")
            pdf_path = pdf_gen.generate_pdf(issue_data, attachment_paths)
            
            print(f"   ✅ Klar!")
            exported.append(issue_key)
            
        except Exception as e:
            print(f"   ❌ Fel: {e}")
            failed.append(issue_key)
    
    # Sammanfattning
    print("\n" + "="*60)
    print("📊 SAMMANFATTNING")
    print("="*60)
    print(f"✅ Exporterade: {len(exported)} tickets")
    print(f"❌ Misslyckade: {len(failed)} tickets")
    
    if failed:
        print(f"\nMisslyckade tickets:")
        for key in failed:
            print(f"   • {key}")
    
    print(f"\n📁 PDF:er sparade i: {os.path.abspath(Config.OUTPUT_DIR)}/")


if __name__ == '__main__':
    # Validera konfiguration
    if not Config.validate():
        sys.exit(1)
    
    # Hitta CSV-fil
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        # Sök efter CSV-fil i nuvarande mapp
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
        if csv_files:
            csv_path = csv_files[0]
            print(f"📄 Använder: {csv_path}")
        else:
            print("❌ Ingen CSV-fil hittades")
            print("   Användning: python export_from_csv.py <fil.csv>")
            sys.exit(1)
    
    if not os.path.exists(csv_path):
        print(f"❌ Filen finns inte: {csv_path}")
        sys.exit(1)
    
    export_from_csv(csv_path)
