"""
Jira Export Server
==================
REST API och Webbgränssnitt för att exportera Jira-issues
till PDF, Word, Markdown och PNG.
"""
import os
import sys
import base64
import tempfile
import io
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from PIL import Image as PILImage

# Lägg till parent directory för att importera befintlig kod
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jira_client import JiraClient
from pdf_generator import PDFGenerator
from config import Config

# Importera Word-generator
try:
    from word_generator import WordGenerator
    WORD_AVAILABLE = True
    print("✅ Word-export tillgänglig")
except ImportError as e:
    WORD_AVAILABLE = False
    print(f"⚠️  Word-export ej tillgänglig: {e}")

# Importera Markdown-generator
try:
    from markdown_generator import MarkdownGenerator
    MARKDOWN_AVAILABLE = True
    print("✅ Markdown-export tillgänglig")
except ImportError as e:
    MARKDOWN_AVAILABLE = False
    print(f"⚠️  Markdown-export ej tillgänglig: {e}")

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
CORS(app)  # Tillåt anrop från Forge-appen och webbgränssnittet

# Temporär mapp för filer
TEMP_DIR = tempfile.mkdtemp(prefix='jira_export_')


# ===========================================
# Webbgränssnitt Routes
# ===========================================

@app.route('/', methods=['GET'])
def index():
    """Servera huvudsidan"""
    return render_template('index.html')


@app.route('/health', methods=['GET'])
def health_check():
    """Hälsokontroll för servern"""
    return jsonify({
        'status': 'ok',
        'service': 'Jira Export Server',
        'version': '2.1.0',
        'formats': {
            'pdf': True,
            'docx': WORD_AVAILABLE,
            'md': MARKDOWN_AVAILABLE,
            'png': True
        }
    })


@app.route('/api/test-credentials', methods=['POST'])
def test_credentials():
    """
    Testa Jira-credentials
    
    Request body:
    {
        "jira_url": "https://company.atlassian.net",
        "email": "user@company.com",
        "api_token": "xxx"
    }
    """
    try:
        data = request.get_json()
        
        jira_url = data.get('jira_url', '').rstrip('/')
        email = data.get('email', '')
        api_token = data.get('api_token', '')
        
        if not all([jira_url, email, api_token]):
            return jsonify({'success': False, 'error': 'Fyll i alla fält'})
        
        # Skapa klient och testa anslutning
        jira = JiraClient(jira_url, email, api_token)
        
        # Testa genom att hämta serverinfo
        import requests
        from requests.auth import HTTPBasicAuth
        
        response = requests.get(
            f"{jira_url}/rest/api/3/myself",
            auth=HTTPBasicAuth(email, api_token),
            headers={'Accept': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            user_data = response.json()
            return jsonify({
                'success': True,
                'site_name': jira_url.replace('https://', '').replace('.atlassian.net', ''),
                'user': user_data.get('displayName', email)
            })
        elif response.status_code == 401:
            return jsonify({'success': False, 'error': 'Felaktig e-post eller API-token'})
        elif response.status_code == 403:
            return jsonify({'success': False, 'error': 'Åtkomst nekad. Kontrollera behörigheter.'})
        else:
            return jsonify({'success': False, 'error': f'Kunde inte ansluta (HTTP {response.status_code})'})
            
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'Timeout - kontrollera URL:en'})
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'error': 'Kunde inte ansluta - kontrollera URL:en'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/search', methods=['POST'])
def search_issues():
    """
    Sök efter issues
    
    Request body (alternativ 1 - issue keys):
    {
        "jira_url": "...",
        "email": "...",
        "api_token": "...",
        "issue_keys": ["PROJ-1", "PROJ-2"]
    }
    
    Request body (alternativ 2 - JQL):
    {
        "jira_url": "...",
        "email": "...",
        "api_token": "...",
        "jql": "project = PROJ ORDER BY created DESC",
        "max_results": 50
    }
    """
    try:
        data = request.get_json()
        
        jira_url = data.get('jira_url', '').rstrip('/')
        email = data.get('email', '')
        api_token = data.get('api_token', '')
        
        if not all([jira_url, email, api_token]):
            return jsonify({'success': False, 'error': 'Saknar Jira-credentials'})
        
        import requests
        from requests.auth import HTTPBasicAuth
        
        auth = HTTPBasicAuth(email, api_token)
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        
        issues = []
        
        if 'issue_keys' in data:
            # Hämta specifika issues
            for key in data['issue_keys']:
                try:
                    response = requests.get(
                        f"{jira_url}/rest/api/3/issue/{key}",
                        auth=auth,
                        headers=headers,
                        timeout=10
                    )
                    if response.status_code == 200:
                        issue_data = response.json()
                        issues.append({
                            'key': issue_data['key'],
                            'summary': issue_data['fields']['summary'],
                            'type': issue_data['fields']['issuetype']['name'],
                            'status': issue_data['fields']['status']['name']
                        })
                except:
                    pass
                    
        elif 'jql' in data:
            # JQL-sökning - använd nya API:et /rest/api/3/search/jql
            jql = data['jql']
            max_results = min(data.get('max_results', 50), 100)
            
            response = requests.post(
                f"{jira_url}/rest/api/3/search/jql",
                auth=auth,
                headers=headers,
                json={
                    'jql': jql,
                    'maxResults': max_results,
                    'fields': ['summary', 'issuetype', 'status']
                },
                timeout=30
            )
            
            if response.status_code == 200:
                search_data = response.json()
                for issue_data in search_data.get('issues', []):
                    issues.append({
                        'key': issue_data['key'],
                        'summary': issue_data['fields']['summary'],
                        'type': issue_data['fields']['issuetype']['name'],
                        'status': issue_data['fields']['status']['name']
                    })
            else:
                return jsonify({
                    'success': False, 
                    'error': f'JQL-sökning misslyckades: {response.text}'
                })
        else:
            return jsonify({'success': False, 'error': 'Ange issue_keys eller jql'})
        
        return jsonify({
            'success': True,
            'issues': issues,
            'count': len(issues)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/export', methods=['POST'])
def export_issues():
    """
    Exportera issues till valfritt format
    
    Request body:
    {
        "issue_keys": ["PROJ-123", "PROJ-124"],
        "format": "pdf" | "docx" | "png",
        "jira_url": "https://company.atlassian.net",  (optional)
        "email": "user@company.com",                  (optional)
        "api_token": "xxx"                            (optional)
    }
    
    Response:
    {
        "success": true,
        "files": [
            {
                "issue_key": "PROJ-123",
                "filename": "PROJ-123.pdf",
                "file_base64": "...",
                "format": "pdf"
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
        export_format = data.get('format', 'pdf').lower()
        
        # Credentials: använd request-data eller miljövariabler
        jira_url = data.get('jira_url') or os.getenv('JIRA_URL') or Config.JIRA_URL
        email = data.get('email') or os.getenv('JIRA_EMAIL') or Config.JIRA_EMAIL
        api_token = data.get('api_token') or os.getenv('JIRA_API_TOKEN') or Config.JIRA_API_TOKEN
        
        if not issue_keys:
            return jsonify({'success': False, 'error': 'No issue_keys provided'}), 400
        
        if not all([jira_url, email, api_token]):
            return jsonify({'success': False, 'error': 'Missing Jira credentials. Configure JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN environment variables.'}), 400
        
        # Validera format
        valid_formats = ['pdf', 'docx', 'png', 'md']
        if export_format not in valid_formats:
            return jsonify({'success': False, 'error': f'Invalid format. Use: {valid_formats}'}), 400
        
        if export_format == 'docx' and not WORD_AVAILABLE:
            return jsonify({'success': False, 'error': 'Word export not available on this server'}), 400
        
        if export_format == 'md' and not MARKDOWN_AVAILABLE:
            return jsonify({'success': False, 'error': 'Markdown export not available on this server'}), 400
        
        # Initiera klienter
        jira = JiraClient(jira_url, email, api_token)
        pdf_gen = PDFGenerator(output_dir=TEMP_DIR)
        word_gen = WordGenerator(output_dir=TEMP_DIR) if WORD_AVAILABLE else None
        md_gen = MarkdownGenerator(output_dir=TEMP_DIR) if MARKDOWN_AVAILABLE else None
        
        results = []
        errors = []
        
        for issue_key in issue_keys:
            try:
                print(f"📥 Exporterar {issue_key} till {export_format.upper()}...")
                
                # Hämta issue
                issue_data = jira.get_issue(issue_key)
                
                # Ladda ner bilagor
                attachment_paths = []
                attachments = issue_data.get('attachments', [])
                print(f"   📎 Issue har {len(attachments)} bilagor")
                
                if attachments:
                    att_dir = os.path.join(TEMP_DIR, 'attachments', issue_key)
                    os.makedirs(att_dir, exist_ok=True)
                    
                    for att in attachments:
                        print(f"      - {att['filename']} ({att['mime_type']}, {att['size']} bytes)")
                    
                    attachment_paths = jira.download_all_attachments(issue_data, att_dir)
                    print(f"   ✅ Laddade ner {len(attachment_paths)} av {len(attachments)} bilagor")
                    
                    for path in attachment_paths:
                        print(f"      - Sparad: {path}")
                
                # Generera fil baserat på format
                if export_format == 'pdf':
                    file_path = pdf_gen.generate_pdf(issue_data, attachment_paths)
                    mime_type = 'application/pdf'
                    file_ext = 'pdf'
                    
                elif export_format == 'docx':
                    file_path = word_gen.generate_docx(issue_data, attachment_paths)
                    mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    file_ext = 'docx'
                    
                elif export_format == 'md':
                    file_path = md_gen.generate_markdown(issue_data, attachment_paths)
                    mime_type = 'text/markdown'
                    file_ext = 'md'
                    
                elif export_format == 'png':
                    # För PNG: skapa en sammanfattningsbild
                    file_path = create_png_summary(issue_data, attachment_paths, TEMP_DIR)
                    mime_type = 'image/png'
                    file_ext = 'png'
                
                # Läs fil som base64
                with open(file_path, 'rb') as f:
                    file_base64 = base64.b64encode(f.read()).decode('utf-8')
                
                results.append({
                    'issue_key': issue_key,
                    'filename': f'{issue_key}.{file_ext}',
                    'file_base64': file_base64,
                    'pdf_base64': file_base64,  # Bakåtkompatibilitet
                    'format': export_format,
                    'size': len(file_base64)
                })
                
                print(f"   ✅ {issue_key} exporterad")
                
                # Städa temporära filer
                try:
                    os.remove(file_path)
                except:
                    pass
                
            except Exception as e:
                print(f"   ❌ Fel för {issue_key}: {e}")
                errors.append({
                    'issue_key': issue_key,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'pdfs': results,  # Bakåtkompatibilitet
            'files': results,
            'errors': errors,
            'total': len(issue_keys),
            'exported': len(results),
            'failed': len(errors),
            'format': export_format
        })
        
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/single/<issue_key>', methods=['GET'])
def export_single_issue(issue_key):
    """
    Exportera en enskild issue
    
    Query params:
    - format: pdf (default), docx, png
    - download: true/false (returnera fil eller base64)
    """
    try:
        export_format = request.args.get('format', 'pdf').lower()
        
        jira_url = os.getenv('JIRA_URL') or Config.JIRA_URL
        email = os.getenv('JIRA_EMAIL') or Config.JIRA_EMAIL
        api_token = os.getenv('JIRA_API_TOKEN') or Config.JIRA_API_TOKEN
        
        if not all([jira_url, email, api_token]):
            return jsonify({'success': False, 'error': 'Server not configured with Jira credentials'}), 500
        
        jira = JiraClient(jira_url, email, api_token)
        pdf_gen = PDFGenerator(output_dir=TEMP_DIR)
        word_gen = WordGenerator(output_dir=TEMP_DIR) if WORD_AVAILABLE else None
        
        # Hämta issue
        issue_data = jira.get_issue(issue_key)
        
        # Ladda ner bilagor
        attachment_paths = []
        if issue_data.get('attachments'):
            att_dir = os.path.join(TEMP_DIR, 'attachments', issue_key)
            attachment_paths = jira.download_all_attachments(issue_data, att_dir)
        
        # Generera fil
        if export_format == 'pdf':
            file_path = pdf_gen.generate_pdf(issue_data, attachment_paths)
            mime_type = 'application/pdf'
            file_ext = 'pdf'
        elif export_format == 'docx':
            if not WORD_AVAILABLE:
                return jsonify({'success': False, 'error': 'Word export not available'}), 400
            file_path = word_gen.generate_docx(issue_data, attachment_paths)
            mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            file_ext = 'docx'
        elif export_format == 'png':
            file_path = create_png_summary(issue_data, attachment_paths, TEMP_DIR)
            mime_type = 'image/png'
            file_ext = 'png'
        else:
            return jsonify({'success': False, 'error': f'Invalid format: {export_format}'}), 400
        
        # Returnera fil eller base64
        if request.args.get('download', 'false').lower() == 'true':
            return send_file(
                file_path,
                mimetype=mime_type,
                as_attachment=True,
                download_name=f'{issue_key}.{file_ext}'
            )
        else:
            with open(file_path, 'rb') as f:
                file_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            return jsonify({
                'success': True,
                'issue_key': issue_key,
                'filename': f'{issue_key}.{file_ext}',
                'file_base64': file_base64,
                'format': export_format
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def create_png_summary(issue_data: dict, attachment_paths: list, output_dir: str) -> str:
    """
    Skapa en PNG-sammanfattning av issue
    Innehåller första bildbilagan eller en enkel textbaserad bild
    """
    issue_key = issue_data['key']
    filepath = os.path.join(output_dir, f'{issue_key}.png')
    
    # Bildformat att leta efter
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
    
    # Hitta första bilden bland bilagor
    first_image = None
    for path in (attachment_paths or []):
        ext = os.path.splitext(path)[1].lower()
        if ext in image_extensions and os.path.exists(path):
            first_image = path
            break
    
    if first_image:
        # Kopiera och konvertera första bilden till PNG
        with PILImage.open(first_image) as img:
            # Konvertera till RGB om nödvändigt
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = PILImage.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Begränsa storlek
            max_size = (1920, 1080)
            img.thumbnail(max_size, PILImage.Resampling.LANCZOS)
            
            # Spara som PNG
            img.save(filepath, 'PNG', optimize=True)
    else:
        # Skapa en enkel textbild om inga bilder finns
        width, height = 800, 600
        img = PILImage.new('RGB', (width, height), color=(250, 251, 252))
        
        # Rita text (enkel version utan PIL.ImageDraw.text)
        # Spara bilden som är
        img.save(filepath, 'PNG')
    
    return filepath


@app.route('/api/formats', methods=['GET'])
def get_formats():
    """Lista tillgängliga exportformat"""
    return jsonify({
        'formats': [
            {'id': 'pdf', 'name': 'PDF', 'extension': '.pdf', 'available': True, 'description': 'Portabelt dokumentformat med bilder'},
            {'id': 'docx', 'name': 'Word', 'extension': '.docx', 'available': WORD_AVAILABLE, 'description': 'Microsoft Word-dokument'},
            {'id': 'md', 'name': 'Markdown', 'extension': '.md', 'available': MARKDOWN_AVAILABLE, 'description': 'Markdown för GPT/AI-sökning'},
            {'id': 'png', 'name': 'PNG', 'extension': '.png', 'available': True, 'description': 'Första bifogade bilden som PNG'}
        ]
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║       Jira Export Server v2.1                             ║
║       http://localhost:{port}                                ║
║                                                           ║
║  Formats: PDF ✓  Word {'✓' if WORD_AVAILABLE else '✗'}  Markdown {'✓' if MARKDOWN_AVAILABLE else '✗'}  PNG ✓       ║
║                                                           ║
║  🌐 Webbgränssnitt: http://localhost:{port}                  ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
