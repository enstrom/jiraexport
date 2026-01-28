#!/usr/bin/env python3
"""
Jira Export to PDF
==================
Exporterar Jira-tickets till PDF med alla fält och bilagor.

Användning:
    python main.py                          # Interaktivt läge
    python main.py PROJ-123                 # Exportera specifik issue
    python main.py --project PROJ           # Exportera alla issues i projekt
    python main.py --jql "project = PROJ"   # Exportera med JQL-query
"""
import argparse
import os
import sys
from typing import List, Optional

from config import Config
from jira_client import JiraClient
from pdf_generator import PDFGenerator


def export_single_issue(jira: JiraClient, pdf_gen: PDFGenerator, 
                        issue_key: str, download_attachments: bool = True) -> Optional[str]:
    """
    Exportera en enskild issue till PDF
    
    Args:
        jira: JiraClient-instans
        pdf_gen: PDFGenerator-instans
        issue_key: Jira issue-nyckel
        download_attachments: Om bilagor ska laddas ner
        
    Returns:
        Sökväg till genererad PDF eller None vid fel
    """
    try:
        print(f"📥 Hämtar {issue_key}...")
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
        
        print(f"   ✅ Exporterad: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        print(f"   ❌ Fel vid export av {issue_key}: {e}")
        return None


def export_multiple_issues(jira: JiraClient, pdf_gen: PDFGenerator,
                          issues: List[dict], download_attachments: bool = True) -> List[str]:
    """
    Exportera flera issues till PDF
    
    Args:
        jira: JiraClient-instans
        pdf_gen: PDFGenerator-instans
        issues: Lista med issue-data
        download_attachments: Om bilagor ska laddas ner
        
    Returns:
        Lista med sökvägar till genererade PDF:er
    """
    exported = []
    total = len(issues)
    
    for i, issue_data in enumerate(issues, 1):
        issue_key = issue_data['key']
        print(f"\n[{i}/{total}] Bearbetar {issue_key}...")
        
        try:
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
            exported.append(pdf_path)
            
        except Exception as e:
            print(f"   ❌ Fel: {e}")
    
    return exported


def interactive_mode(jira: JiraClient, pdf_gen: PDFGenerator):
    """Interaktivt läge för att exportera issues"""
    print("\n" + "="*60)
    print("  🎫 JIRA EXPORT TILL PDF")
    print("="*60)
    print("\nAnsluten till:", Config.JIRA_URL)
    print("\nAlternativ:")
    print("  1. Exportera en specifik issue")
    print("  2. Exportera alla issues i ett projekt")
    print("  3. Exportera med JQL-query")
    print("  4. Avsluta")
    
    while True:
        print()
        choice = input("Välj alternativ (1-4): ").strip()
        
        if choice == '1':
            issue_key = input("Ange issue-nyckel (t.ex. PROJ-123): ").strip().upper()
            if issue_key:
                export_single_issue(jira, pdf_gen, issue_key)
        
        elif choice == '2':
            project_key = input("Ange projektnyckel: ").strip().upper()
            if project_key:
                issue_type = input("Filtrera på issue-typ (tom = alla): ").strip()
                
                print(f"\n🔍 Söker issues i {project_key}...")
                issues = jira.get_project_issues(project_key, issue_type or None)
                
                if issues:
                    print(f"   Hittade {len(issues)} issues")
                    confirm = input(f"Exportera alla? (j/n): ").strip().lower()
                    if confirm == 'j':
                        exported = export_multiple_issues(jira, pdf_gen, issues)
                        print(f"\n✅ Exporterade {len(exported)}/{len(issues)} issues")
                else:
                    print("   Inga issues hittades")
        
        elif choice == '3':
            jql = input("Ange JQL-query: ").strip()
            if jql:
                max_results = input("Max antal resultat (standard 50): ").strip()
                max_results = int(max_results) if max_results.isdigit() else 50
                
                print(f"\n🔍 Kör JQL-sökning...")
                issues = jira.get_issues_by_jql(jql, max_results)
                
                if issues:
                    print(f"   Hittade {len(issues)} issues")
                    confirm = input(f"Exportera alla? (j/n): ").strip().lower()
                    if confirm == 'j':
                        exported = export_multiple_issues(jira, pdf_gen, issues)
                        print(f"\n✅ Exporterade {len(exported)}/{len(issues)} issues")
                else:
                    print("   Inga issues hittades")
        
        elif choice == '4':
            print("\n👋 Hej då!")
            break
        
        else:
            print("❌ Ogiltigt val, försök igen")


def main():
    """Huvudfunktion"""
    parser = argparse.ArgumentParser(
        description='Exportera Jira-tickets till PDF med alla fält och bilagor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exempel:
  python main.py PROJ-123                    Exportera specifik issue
  python main.py PROJ-123 PROJ-124 PROJ-125  Exportera flera issues
  python main.py --project PROJ              Exportera alla issues i projekt
  python main.py --project PROJ --type Story Exportera endast Stories
  python main.py --jql "assignee = currentUser()" Exportera med JQL
        """
    )
    
    parser.add_argument(
        'issues', 
        nargs='*', 
        help='Issue-nycklar att exportera (t.ex. PROJ-123)'
    )
    parser.add_argument(
        '--project', '-p',
        help='Projektnyckel för att exportera alla issues'
    )
    parser.add_argument(
        '--type', '-t',
        help='Filtrera på issue-typ (t.ex. Story, Bug, Task)'
    )
    parser.add_argument(
        '--jql', '-j',
        help='JQL-query för att välja issues'
    )
    parser.add_argument(
        '--max-results', '-m',
        type=int,
        default=100,
        help='Max antal issues att exportera (standard: 100)'
    )
    parser.add_argument(
        '--no-attachments',
        action='store_true',
        help='Hoppa över nedladdning av bilagor'
    )
    parser.add_argument(
        '--output', '-o',
        help='Utdatamapp för PDF:er'
    )
    
    args = parser.parse_args()
    
    # Validera konfiguration
    if not Config.validate():
        print("\n💡 Tips: Kopiera env_example.txt till .env och fyll i dina Jira-uppgifter")
        sys.exit(1)
    
    # Sätt utdatamapp
    if args.output:
        Config.OUTPUT_DIR = args.output
    
    # Initiera klienter
    print("🔌 Ansluter till Jira...")
    try:
        jira = JiraClient()
        pdf_gen = PDFGenerator()
    except Exception as e:
        print(f"❌ Kunde inte ansluta till Jira: {e}")
        sys.exit(1)
    
    download_attachments = not args.no_attachments
    
    # Bestäm vad som ska exporteras
    if args.issues:
        # Exportera specifika issues
        print(f"\n📋 Exporterar {len(args.issues)} issue(s)...")
        for issue_key in args.issues:
            export_single_issue(jira, pdf_gen, issue_key.upper(), download_attachments)
    
    elif args.project:
        # Exportera projekt
        print(f"\n🔍 Söker issues i projekt {args.project}...")
        issues = jira.get_project_issues(args.project, args.type)
        
        if issues:
            print(f"   Hittade {len(issues)} issues")
            exported = export_multiple_issues(jira, pdf_gen, issues, download_attachments)
            print(f"\n✅ Exporterade {len(exported)}/{len(issues)} issues till {Config.OUTPUT_DIR}/")
        else:
            print("   Inga issues hittades")
    
    elif args.jql:
        # Exportera med JQL
        print(f"\n🔍 Kör JQL: {args.jql}")
        issues = jira.get_issues_by_jql(args.jql, args.max_results)
        
        if issues:
            print(f"   Hittade {len(issues)} issues")
            exported = export_multiple_issues(jira, pdf_gen, issues, download_attachments)
            print(f"\n✅ Exporterade {len(exported)}/{len(issues)} issues till {Config.OUTPUT_DIR}/")
        else:
            print("   Inga issues hittades")
    
    else:
        # Interaktivt läge
        interactive_mode(jira, pdf_gen)


if __name__ == '__main__':
    main()
