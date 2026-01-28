"""
Jira PDF Export Server
======================
REST API för att generera PDF:er med bilder från Jira-issues.
Anropas av Forge-appen.
"""
import os
import sys
import base64
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

# Lägg till parent directory för att importera befintlig kod
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jira_client import JiraClient
from pdf_generator import PDFGenerator
from config import Config

app = Flask(__name__)
CORS(app)  # Tillåt anrop från Forge-appen

# Temporär mapp för PDF:er
TEMP_DIR = tempfile.mkdtemp(prefix='jira_pdf_')


@app.route('/health', methods=['GET'])
def health_check():
    """Hälsokontroll för servern"""
    return jsonify({
        'status': 'ok',
        'service': 'Jira PDF Export Server',
        'version': '1.0.0'
    })


@app.route('/api/export', methods=['POST'])
def export_issues():
    """
    Exportera issues till PDF
    
    Request body:
    {
        "issue_keys": ["PROJ-123", "PROJ-124"],
        "jira_url": "https://company.atlassian.net",
        "email": "user@company.com",
        "api_token": "xxx"
    }
    
    Response:
    {
        "success": true,
        "pdfs": [
            {
                "issue_key": "PROJ-123",
                "filename": "PROJ-123.pdf",
                "pdf_base64": "..."
            }
        ],
        "errors": []
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        issue_keys = data.get('issue_keys', [])
        jira_url = data.get('jira_url') or os.getenv('JIRA_URL') or Config.JIRA_URL
        email = data.get('email') or os.getenv('JIRA_EMAIL') or Config.JIRA_EMAIL
        api_token = data.get('api_token') or os.getenv('JIRA_API_TOKEN') or Config.JIRA_API_TOKEN
        
        if not issue_keys:
            return jsonify({'success': False, 'error': 'No issue_keys provided'}), 400
        
        if not all([jira_url, email, api_token]):
            return jsonify({'success': False, 'error': 'Missing Jira credentials'}), 400
        
        # Initiera klienter med credentials
        jira = JiraClient(jira_url, email, api_token)
        pdf_gen = PDFGenerator(output_dir=TEMP_DIR)
        
        results = []
        errors = []
        
        for issue_key in issue_keys:
            try:
                print(f"📥 Exporterar {issue_key}...")
                
                # Hämta issue
                issue_data = jira.get_issue(issue_key)
                
                # Ladda ner bilagor
                attachment_paths = []
                if issue_data.get('attachments'):
                    att_dir = os.path.join(TEMP_DIR, 'attachments', issue_key)
                    attachment_paths = jira.download_all_attachments(issue_data, att_dir)
                
                # Generera PDF
                pdf_path = pdf_gen.generate_pdf(issue_data, attachment_paths)
                
                # Läs PDF som base64
                with open(pdf_path, 'rb') as f:
                    pdf_base64 = base64.b64encode(f.read()).decode('utf-8')
                
                results.append({
                    'issue_key': issue_key,
                    'filename': f'{issue_key}.pdf',
                    'pdf_base64': pdf_base64,
                    'size': len(pdf_base64)
                })
                
                print(f"   ✅ {issue_key} exporterad")
                
            except Exception as e:
                print(f"   ❌ Fel för {issue_key}: {e}")
                errors.append({
                    'issue_key': issue_key,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'pdfs': results,
            'errors': errors,
            'total': len(issue_keys),
            'exported': len(results),
            'failed': len(errors)
        })
        
    except Exception as e:
        print(f"❌ Server error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/single/<issue_key>', methods=['GET'])
def export_single_issue(issue_key):
    """
    Exportera en enskild issue och returnera PDF-fil direkt
    
    Query params:
    - download: true/false (returnera fil eller base64)
    """
    try:
        jira_url = os.getenv('JIRA_URL') or Config.JIRA_URL
        email = os.getenv('JIRA_EMAIL') or Config.JIRA_EMAIL
        api_token = os.getenv('JIRA_API_TOKEN') or Config.JIRA_API_TOKEN
        
        if not all([jira_url, email, api_token]):
            return jsonify({'success': False, 'error': 'Server not configured with Jira credentials'}), 500
        
        jira = JiraClient(jira_url, email, api_token)
        pdf_gen = PDFGenerator(output_dir=TEMP_DIR)
        
        # Hämta issue
        issue_data = jira.get_issue(issue_key)
        
        # Ladda ner bilagor
        attachment_paths = []
        if issue_data.get('attachments'):
            att_dir = os.path.join(TEMP_DIR, 'attachments', issue_key)
            attachment_paths = jira.download_all_attachments(issue_data, att_dir)
        
        # Generera PDF
        pdf_path = pdf_gen.generate_pdf(issue_data, attachment_paths)
        
        # Returnera fil eller base64
        if request.args.get('download', 'false').lower() == 'true':
            return send_file(
                pdf_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'{issue_key}.pdf'
            )
        else:
            with open(pdf_path, 'rb') as f:
                pdf_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            return jsonify({
                'success': True,
                'issue_key': issue_key,
                'filename': f'{issue_key}.pdf',
                'pdf_base64': pdf_base64
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    print(f"""
╔═══════════════════════════════════════════════════╗
║       Jira PDF Export Server                      ║
║       http://localhost:{port}                        ║
╚═══════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
