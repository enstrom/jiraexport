"""
PDF-generator för Jira-tickets
Skapar snygga PDF-dokument med alla fält och bilagor
"""
import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable, ListFlowable, ListItem
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage

from config import Config


class PDFGenerator:
    """Genererar PDF-dokument från Jira-data"""
    
    # Färgschema baserat på Jira's design
    COLORS = {
        'primary': colors.HexColor('#0052CC'),      # Jira blå
        'secondary': colors.HexColor('#172B4D'),    # Mörk text
        'accent': colors.HexColor('#00875A'),       # Grön (Done)
        'warning': colors.HexColor('#FF991F'),      # Orange
        'error': colors.HexColor('#DE350B'),        # Röd
        'light_bg': colors.HexColor('#F4F5F7'),     # Ljus bakgrund
        'border': colors.HexColor('#DFE1E6'),       # Kantlinje
        'text': colors.HexColor('#172B4D'),         # Text
        'text_light': colors.HexColor('#5E6C84'),   # Ljusare text
    }
    
    # Status-färger
    STATUS_COLORS = {
        'done': colors.HexColor('#00875A'),
        'in progress': colors.HexColor('#0052CC'),
        'to do': colors.HexColor('#5E6C84'),
    }
    
    def __init__(self, output_dir: str = None):
        """
        Initiera PDF-generatorn
        
        Args:
            output_dir: Mapp för exporterade PDF:er
        """
        self.output_dir = output_dir or Config.OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        self.styles = self._create_styles()
    
    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Skapa anpassade textstilar"""
        base_styles = getSampleStyleSheet()
        
        styles = {
            'title': ParagraphStyle(
                'Title',
                parent=base_styles['Heading1'],
                fontSize=24,
                textColor=self.COLORS['secondary'],
                spaceAfter=6*mm,
                fontName='Helvetica-Bold'
            ),
            'issue_key': ParagraphStyle(
                'IssueKey',
                parent=base_styles['Normal'],
                fontSize=14,
                textColor=self.COLORS['primary'],
                fontName='Helvetica-Bold',
                spaceAfter=2*mm
            ),
            'heading': ParagraphStyle(
                'Heading',
                parent=base_styles['Heading2'],
                fontSize=14,
                textColor=self.COLORS['secondary'],
                spaceBefore=8*mm,
                spaceAfter=4*mm,
                fontName='Helvetica-Bold',
                borderPadding=2*mm,
            ),
            'subheading': ParagraphStyle(
                'SubHeading',
                parent=base_styles['Heading3'],
                fontSize=11,
                textColor=self.COLORS['text_light'],
                spaceBefore=4*mm,
                spaceAfter=2*mm,
                fontName='Helvetica-Bold'
            ),
            'body': ParagraphStyle(
                'Body',
                parent=base_styles['Normal'],
                fontSize=10,
                textColor=self.COLORS['text'],
                spaceAfter=2*mm,
                leading=14
            ),
            'field_label': ParagraphStyle(
                'FieldLabel',
                parent=base_styles['Normal'],
                fontSize=9,
                textColor=self.COLORS['text_light'],
                fontName='Helvetica-Bold'
            ),
            'field_value': ParagraphStyle(
                'FieldValue',
                parent=base_styles['Normal'],
                fontSize=10,
                textColor=self.COLORS['text'],
            ),
            'status_badge': ParagraphStyle(
                'StatusBadge',
                parent=base_styles['Normal'],
                fontSize=9,
                textColor=colors.white,
                fontName='Helvetica-Bold',
                alignment=TA_CENTER
            ),
            'comment': ParagraphStyle(
                'Comment',
                parent=base_styles['Normal'],
                fontSize=9,
                textColor=self.COLORS['text'],
                leftIndent=10*mm,
                borderPadding=2*mm,
            ),
            'comment_meta': ParagraphStyle(
                'CommentMeta',
                parent=base_styles['Normal'],
                fontSize=8,
                textColor=self.COLORS['text_light'],
                leftIndent=10*mm,
            ),
        }
        
        return styles
    
    def generate_pdf(self, issue_data: Dict[str, Any], 
                     attachment_paths: List[str] = None) -> str:
        """
        Generera PDF för en Jira-issue
        
        Args:
            issue_data: Parsad issue-data från JiraClient
            attachment_paths: Lista med sökvägar till nedladdade bilagor
            
        Returns:
            Sökväg till genererad PDF
        """
        issue_key = issue_data['key']
        filename = f"{issue_key}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        # Skapa PDF-dokument
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # Bygg innehåll
        story = []
        
        # Header med issue-nyckel och typ
        story.extend(self._build_header(issue_data))
        
        # Titel/Summary
        story.append(Paragraph(
            self._escape_html(issue_data['summary']),
            self.styles['title']
        ))
        
        # Status och prioritet-rad
        story.extend(self._build_status_row(issue_data))
        
        # Separator
        story.append(Spacer(1, 4*mm))
        story.append(HRFlowable(
            width="100%", 
            thickness=1, 
            color=self.COLORS['border'],
            spaceAfter=4*mm
        ))
        
        # Detaljfält (två kolumner)
        story.extend(self._build_details_section(issue_data))
        
        # Description
        story.extend(self._build_description_section(issue_data))
        
        # Custom fields
        story.extend(self._build_custom_fields_section(issue_data))
        
        # Bilagor och bilder
        story.extend(self._build_attachments_section(issue_data, attachment_paths))
        
        # Subtasks
        story.extend(self._build_subtasks_section(issue_data))
        
        # Länkade issues
        story.extend(self._build_links_section(issue_data))
        
        # Kommentarer
        story.extend(self._build_comments_section(issue_data))
        
        # Footer med metadata
        story.extend(self._build_footer(issue_data))
        
        # Generera PDF
        doc.build(story)
        
        return filepath
    
    def _build_header(self, issue_data: Dict[str, Any]) -> List:
        """Bygg dokumenthuvud"""
        elements = []
        
        issue_type = issue_data['issue_type']['name']
        issue_key = issue_data['key']
        
        # Issue-typ och nyckel
        header_text = f"<font color='#5E6C84'>{issue_type}</font> | <font color='#0052CC'><b>{issue_key}</b></font>"
        elements.append(Paragraph(header_text, self.styles['issue_key']))
        
        return elements
    
    def _build_status_row(self, issue_data: Dict[str, Any]) -> List:
        """Bygg status och prioritet-rad"""
        elements = []
        
        status = issue_data['status']['name']
        priority = issue_data['priority']['name']
        
        # Bestäm status-färg
        status_lower = status.lower()
        if 'done' in status_lower or 'closed' in status_lower:
            status_color = self.COLORS['accent']
        elif 'progress' in status_lower:
            status_color = self.COLORS['primary']
        else:
            status_color = self.COLORS['text_light']
        
        # Skapa status-tabell
        status_data = [[
            Paragraph(f"<b>Status:</b> <font color='{status_color.hexval()}'>{status}</font>", 
                     self.styles['field_value']),
            Paragraph(f"<b>Prioritet:</b> {priority}", self.styles['field_value']),
        ]]
        
        status_table = Table(status_data, colWidths=[85*mm, 85*mm])
        status_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        elements.append(status_table)
        
        return elements
    
    def _build_details_section(self, issue_data: Dict[str, Any]) -> List:
        """Bygg detalj-sektion med grundläggande fält"""
        elements = []
        
        elements.append(Paragraph("Detaljer", self.styles['heading']))
        
        # Samla detaljfält
        details = []
        
        # Assignee
        if issue_data.get('assignee'):
            details.append(('Tilldelad', issue_data['assignee']['name']))
        else:
            details.append(('Tilldelad', 'Ej tilldelad'))
        
        # Reporter
        if issue_data.get('reporter'):
            details.append(('Rapportör', issue_data['reporter']['name']))
        
        # Fix Versions
        if issue_data.get('fix_versions'):
            versions = ', '.join([v['name'] for v in issue_data['fix_versions']])
            details.append(('Fix Versions', versions))
        
        # Components
        if issue_data.get('components'):
            details.append(('Komponenter', ', '.join(issue_data['components'])))
        
        # Labels
        if issue_data.get('labels'):
            details.append(('Etiketter', ', '.join(issue_data['labels'])))
        
        # Sprint
        if issue_data.get('sprints'):
            sprint_names = [s['name'] for s in issue_data['sprints']]
            details.append(('Sprint', ', '.join(sprint_names)))
        
        # Story Points
        if issue_data.get('story_points'):
            details.append(('Story Points', str(issue_data['story_points'])))
        
        # Epic
        if issue_data.get('epic'):
            details.append(('Epic', str(issue_data['epic'])))
        
        # Parent
        if issue_data.get('parent'):
            details.append(('Parent', f"{issue_data['parent']['key']} - {issue_data['parent']['summary']}"))
        
        # Datum
        if issue_data.get('created'):
            details.append(('Skapad', self._format_date(issue_data['created'])))
        if issue_data.get('updated'):
            details.append(('Uppdaterad', self._format_date(issue_data['updated'])))
        if issue_data.get('resolved'):
            details.append(('Löst', self._format_date(issue_data['resolved'])))
        
        # Skapa tabell med två kolumner
        table_data = []
        for i in range(0, len(details), 2):
            row = []
            
            # Första kolumnen
            label1, value1 = details[i]
            row.append(Paragraph(f"<b>{label1}:</b>", self.styles['field_label']))
            row.append(Paragraph(self._escape_html(str(value1)), self.styles['field_value']))
            
            # Andra kolumnen (om den finns)
            if i + 1 < len(details):
                label2, value2 = details[i + 1]
                row.append(Paragraph(f"<b>{label2}:</b>", self.styles['field_label']))
                row.append(Paragraph(self._escape_html(str(value2)), self.styles['field_value']))
            else:
                row.extend(['', ''])
            
            table_data.append(row)
        
        if table_data:
            detail_table = Table(
                table_data, 
                colWidths=[30*mm, 55*mm, 30*mm, 55*mm]
            )
            detail_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
                ('BACKGROUND', (0, 0), (-1, -1), self.COLORS['light_bg']),
                ('BOX', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
                ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3*mm),
            ]))
            elements.append(detail_table)
        
        return elements
    
    def _build_description_section(self, issue_data: Dict[str, Any]) -> List:
        """Bygg beskrivnings-sektion"""
        elements = []
        
        description = issue_data.get('description', '')
        if not description:
            return elements
        
        elements.append(Paragraph("Beskrivning", self.styles['heading']))
        
        # Konvertera Jira-formatering till enkel text
        clean_description = self._clean_jira_markup(description)
        
        # Dela upp i stycken
        paragraphs = clean_description.split('\n\n')
        for para in paragraphs:
            if para.strip():
                # Hantera listor
                lines = para.split('\n')
                for line in lines:
                    if line.strip():
                        # Kontrollera om det är en list-punkt
                        if line.strip().startswith('* ') or line.strip().startswith('- '):
                            text = line.strip()[2:]
                            elements.append(Paragraph(
                                f"• {self._escape_html(text)}",
                                self.styles['body']
                            ))
                        elif re.match(r'^\d+\.\s', line.strip()):
                            elements.append(Paragraph(
                                self._escape_html(line.strip()),
                                self.styles['body']
                            ))
                        else:
                            elements.append(Paragraph(
                                self._escape_html(line.strip()),
                                self.styles['body']
                            ))
        
        return elements
    
    def _build_custom_fields_section(self, issue_data: Dict[str, Any]) -> List:
        """Bygg sektion för custom fields"""
        elements = []
        
        custom_fields = issue_data.get('custom_fields', {})
        if not custom_fields:
            return elements
        
        # Filtrera bort redan visade fält och tomma värden
        skip_patterns = ['story point', 'sprint', 'epic', 'rank', 'flagged']
        filtered_fields = {}
        
        for name, value in custom_fields.items():
            # Hoppa över redan visade eller irrelevanta fält
            name_lower = name.lower()
            if any(pattern in name_lower for pattern in skip_patterns):
                continue
            if value is None or value == '' or value == []:
                continue
            
            # Formatera värdet
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            elif isinstance(value, dict):
                value = str(value)
            
            filtered_fields[name] = value
        
        if not filtered_fields:
            return elements
        
        elements.append(Paragraph("Ytterligare fält", self.styles['heading']))
        
        # Skapa tabell
        table_data = []
        for name, value in filtered_fields.items():
            table_data.append([
                Paragraph(f"<b>{self._escape_html(name)}:</b>", self.styles['field_label']),
                Paragraph(self._escape_html(str(value)[:500]), self.styles['field_value'])
            ])
        
        if table_data:
            fields_table = Table(table_data, colWidths=[50*mm, 120*mm])
            fields_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
                ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
            ]))
            elements.append(fields_table)
        
        return elements
    
    def _build_attachments_section(self, issue_data: Dict[str, Any], 
                                   attachment_paths: List[str] = None) -> List:
        """Bygg bilagor-sektion med bilder"""
        elements = []
        
        attachments = issue_data.get('attachments', [])
        if not attachments:
            return elements
        
        elements.append(Paragraph("Bilagor", self.styles['heading']))
        
        # Skapa mappning av filnamn till sökvägar
        path_map = {}
        if attachment_paths:
            for path in attachment_paths:
                filename = os.path.basename(path)
                path_map[filename] = path
        
        # Bildformat som vi kan visa inline
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        
        for att in attachments:
            filename = att['filename']
            file_ext = os.path.splitext(filename)[1].lower()
            filepath = path_map.get(filename)
            
            # Visa bilaga-info
            size_kb = att['size'] / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            
            att_info = f"📎 <b>{self._escape_html(filename)}</b> ({size_str}) - {att['author']}"
            elements.append(Paragraph(att_info, self.styles['body']))
            
            # Om det är en bild och vi har filen, visa den
            if file_ext in image_extensions and filepath and os.path.exists(filepath):
                try:
                    elements.append(Spacer(1, 2*mm))
                    img = self._create_image(filepath)
                    if img:
                        elements.append(img)
                        elements.append(Spacer(1, 4*mm))
                except Exception as e:
                    elements.append(Paragraph(
                        f"<i>(Kunde inte visa bild: {e})</i>",
                        self.styles['comment']
                    ))
        
        return elements
    
    def _create_image(self, filepath: str, max_width: float = 160*mm, 
                      max_height: float = 200*mm) -> Optional[Image]:
        """
        Skapa en bild-element med korrekt storlek
        
        Args:
            filepath: Sökväg till bildfil
            max_width: Maximal bredd
            max_height: Maximal höjd
            
        Returns:
            ReportLab Image-objekt eller None
        """
        try:
            # Använd PIL för att få dimensioner
            with PILImage.open(filepath) as pil_img:
                orig_width, orig_height = pil_img.size
            
            # Beräkna skalning
            width_ratio = max_width / orig_width
            height_ratio = max_height / orig_height
            ratio = min(width_ratio, height_ratio, 1.0)  # Förstora aldrig
            
            new_width = orig_width * ratio
            new_height = orig_height * ratio
            
            return Image(filepath, width=new_width, height=new_height)
        except Exception as e:
            print(f"⚠️  Kunde inte bearbeta bild {filepath}: {e}")
            return None
    
    def _build_subtasks_section(self, issue_data: Dict[str, Any]) -> List:
        """Bygg subtasks-sektion"""
        elements = []
        
        subtasks = issue_data.get('subtasks', [])
        if not subtasks:
            return elements
        
        elements.append(Paragraph("Underuppgifter", self.styles['heading']))
        
        table_data = [['Nyckel', 'Sammanfattning', 'Status']]
        
        for st in subtasks:
            table_data.append([
                Paragraph(f"<font color='#0052CC'>{st['key']}</font>", self.styles['field_value']),
                Paragraph(self._escape_html(st['summary'][:80]), self.styles['field_value']),
                Paragraph(st['status'], self.styles['field_value'])
            ])
        
        subtask_table = Table(table_data, colWidths=[25*mm, 115*mm, 30*mm])
        subtask_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['light_bg']),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLORS['border']),
            ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 2*mm),
        ]))
        elements.append(subtask_table)
        
        return elements
    
    def _build_links_section(self, issue_data: Dict[str, Any]) -> List:
        """Bygg länkade issues-sektion"""
        elements = []
        
        links = issue_data.get('links', [])
        if not links:
            return elements
        
        elements.append(Paragraph("Länkade ärenden", self.styles['heading']))
        
        for link in links:
            link_text = f"<font color='#5E6C84'>{link['type']}</font> " \
                       f"<font color='#0052CC'><b>{link['key']}</b></font> - " \
                       f"{self._escape_html(link['summary'][:60])}"
            elements.append(Paragraph(link_text, self.styles['body']))
        
        return elements
    
    def _build_comments_section(self, issue_data: Dict[str, Any]) -> List:
        """Bygg kommentars-sektion"""
        elements = []
        
        comments = issue_data.get('comments', [])
        if not comments:
            return elements
        
        elements.append(Paragraph(f"Kommentarer ({len(comments)})", self.styles['heading']))
        
        for comment in comments:
            # Författare och datum
            meta = f"<b>{comment['author']}</b> - {self._format_date(comment['created'])}"
            elements.append(Paragraph(meta, self.styles['comment_meta']))
            
            # Kommentarstext
            body = self._clean_jira_markup(comment['body'])
            elements.append(Paragraph(
                self._escape_html(body[:1000]),
                self.styles['comment']
            ))
            elements.append(Spacer(1, 3*mm))
        
        return elements
    
    def _build_footer(self, issue_data: Dict[str, Any]) -> List:
        """Bygg dokumentfot med metadata"""
        elements = []
        
        elements.append(Spacer(1, 10*mm))
        elements.append(HRFlowable(
            width="100%",
            thickness=0.5,
            color=self.COLORS['border'],
            spaceAfter=3*mm
        ))
        
        # Exportinformation
        export_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        footer_text = f"<font size='8' color='#5E6C84'>" \
                     f"Exporterad: {export_time} | " \
                     f"Issue: {issue_data['key']} | " \
                     f"URL: {issue_data.get('self', 'N/A')}</font>"
        elements.append(Paragraph(footer_text, self.styles['body']))
        
        return elements
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML-tecken för ReportLab"""
        if not text:
            return ''
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text
    
    def _clean_jira_markup(self, text: str) -> str:
        """Rensa Jira-markup till läsbar text"""
        if not text:
            return ''
        
        # Ta bort Jira-specifik markup
        patterns = [
            (r'\{code[^}]*\}', ''),       # Kodblocksmarkörer
            (r'\{noformat\}', ''),         # Noformat
            (r'\{color[^}]*\}', ''),       # Färgmarkörer
            (r'\{panel[^}]*\}', ''),       # Paneler
            (r'h[1-6]\.\s*', ''),          # Rubriker
            (r'\[([^\]|]+)\|([^\]]+)\]', r'\1'),  # Länkar [text|url] -> text
            (r'\[([^\]]+)\]', r'\1'),      # Enkla länkar
            (r'\*([^*]+)\*', r'\1'),       # Fetstil
            (r'_([^_]+)_', r'\1'),         # Kursiv
            (r'\+([^+]+)\+', r'\1'),       # Understruken
            (r'\-([^-]+)\-', r'\1'),       # Genomstruken
            (r'\^([^^]+)\^', r'\1'),       # Upphöjd
            (r'~([^~]+)~', r'\1'),         # Nedsänkt
            (r'\{\{([^}]+)\}\}', r'\1'),   # Monospace
            (r'bq\.\s*', ''),              # Blockcitat
        ]
        
        result = text
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result)
        
        return result.strip()
    
    def _format_date(self, date_str: str) -> str:
        """Formatera datum till läsbart format"""
        if not date_str:
            return 'N/A'
        
        try:
            # Jira-datum är ofta i ISO-format
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except (ValueError, AttributeError):
            # Om parsning misslyckas, returnera original
            return str(date_str)[:19]
