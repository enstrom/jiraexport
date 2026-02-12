#!/usr/bin/env python3
"""
Quick Export - Exportera Jira-issues via servern
Kör: python3 quick_export.py SOMU-48 SOMU-31 --format pdf
"""
import requests
import base64
import sys
import os

SERVER_URL = "https://jiraexport.onrender.com"

def export_issues(issue_keys, export_format='pdf'):
    """Exportera issues till valt format"""
    print(f"\n🚀 Exporterar {len(issue_keys)} issues till {export_format.upper()}...")
    
    response = requests.post(
        f"{SERVER_URL}/api/export",
        json={
            "issue_keys": issue_keys,
            "format": export_format
        },
        timeout=120
    )
    
    if response.status_code != 200:
        print(f"❌ Serverfel: {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    
    if not data.get('success'):
        print(f"❌ Export misslyckades: {data.get('error')}")
        return
    
    print(f"✅ Exporterade {data.get('exported')} av {data.get('total')} issues")
    
    # Spara filer
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)
    
    for file_info in data.get('files', []):
        filename = file_info.get('filename')
        file_base64 = file_info.get('file_base64') or file_info.get('pdf_base64')
        
        if file_base64:
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(file_base64))
            print(f"   📁 Sparad: {filepath}")
    
    # Visa fel
    for error in data.get('errors', []):
        print(f"   ❌ {error.get('issue_key')}: {error.get('error')}")
    
    print(f"\n✨ Klart! Filer sparade i '{output_dir}/' mappen")

def check_server():
    """Kolla serverstatus"""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=10)
        if response.ok:
            data = response.json()
            print(f"✅ Server online: {data.get('service')} v{data.get('version')}")
            formats = data.get('formats', {})
            print(f"   PDF: {'✅' if formats.get('pdf') else '❌'}")
            print(f"   Word: {'✅' if formats.get('docx') else '❌'}")
            print(f"   Markdown: {'✅' if formats.get('md') else '❌'}")
            print(f"   PNG: {'✅' if formats.get('png') else '❌'}")
            return True
    except Exception as e:
        print(f"❌ Server ej tillgänglig: {e}")
    return False

def main():
    print("=" * 50)
    print("  Jira Export Tool")
    print("=" * 50)
    
    # Kolla server
    if not check_server():
        return
    
    # Parsa argument
    args = sys.argv[1:]
    
    if not args or args[0] in ['-h', '--help']:
        print("""
Användning:
  python3 quick_export.py ISSUE-1 ISSUE-2 --format pdf

Format:
  --format pdf    PDF med bilder (default)
  --format docx   Microsoft Word
  --format md     Markdown (för GPT/AI)
  --format png    PNG-bild

Exempel:
  python3 quick_export.py SOMU-48
  python3 quick_export.py SOMU-48 SOMU-31 --format md
  python3 quick_export.py SOMU-48 --format docx
""")
        return
    
    # Hitta format
    export_format = 'pdf'
    issue_keys = []
    
    i = 0
    while i < len(args):
        if args[i] == '--format' and i + 1 < len(args):
            export_format = args[i + 1].lower()
            i += 2
        else:
            issue_keys.append(args[i].upper())
            i += 1
    
    if not issue_keys:
        print("❌ Ange minst en issue key!")
        return
    
    export_issues(issue_keys, export_format)

if __name__ == '__main__':
    main()
