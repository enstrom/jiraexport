#!/usr/bin/env python3
"""
Demo-script som genererar en exempel-PDF med mockdata
Kör detta för att se hur en exporterad PDF ser ut!
"""
import os
from pdf_generator import PDFGenerator

# Mockdata baserat på SOMU-121 "Icon bibliotek"
DEMO_ISSUE = {
    'key': 'SOMU-121',
    'id': '12345',
    'self': 'https://example.atlassian.net/rest/api/2/issue/12345',
    'summary': 'Icon bibliotek',
    'description': """User Story
Som redaktör vill jag kunna lägga in Icon framför en text eller länk på en sida. I länkfält, titlfält (ex. en fil har att göra med bildarssjuka och vill ha en bloddroppe), titel fält. Kunna ladda upp icon i en promo. SVG filen måste vara korrekt gjord. Här måste vi undersöka djupare.

Story Points: 3

Description
Skapa en komponent för Icon bibliotek Icon bibliotek - Strukturerad data. Finns idag på Liberate life men vi kan bygga något ännu bättre. Finns en variant i LocalGov

Vart kommer ikonerna ifrån?
- Uppladdningsfält för ikon att använda i teaser och callout box

Alltså kan man välja mellan bild eller ikon helt enkelt.

Använd samma ikonbibliotek som för liberatelife.eu som start, fler ikoner kan läggas till av redaktör som png eller svg.

TODO:
* bygga en media typ med namn "icon"
* redaktörer för en microsite kan ladda upp sina egna ikoner för sin site
* För "teaser" och "callout box" ska man kunna byta ut bilden mot en ikon på något sätt. (icon i wysiwyg är kanske att föredra före ett mei a uppladdningsfält)
* Vi vill kunna ha en ikon för teaser + callout box.
* vi stödjer "svg" och "png"

Saknas design men behöver vi får vi bolla med davidE

How to Demo
* Gå till din Microsite
* Gå till en sida eller skapa en ny
* Lägg till en sektion och gör nedanstående punkter för både Featured teaser och Call out box
  - Klicka på Image
  - Välj Icon och lägg till en SVG ikon
  - Fyll i resterande content som titel och länk
  - Spara och verifiera design
  - Testa olika kombinationer som image position m.m
""",
    'rendered_description': '',
    'issue_type': {
        'name': 'Story',
        'icon_url': None
    },
    'status': {
        'name': 'Done',
        'category': 'Done'
    },
    'priority': {
        'name': 'Trivial',
        'icon_url': None
    },
    'created': '2024-11-15T10:30:00+01:00',
    'updated': '2025-01-10T14:22:00+01:00',
    'resolved': '2025-01-08T16:45:00+01:00',
    'assignee': {
        'name': 'Alessandro Gasperini',
        'email': 'alessandro@example.com',
        'avatar_url': None
    },
    'reporter': {
        'name': 'Kristian Enström',
        'email': 'kristian@example.com',
        'avatar_url': None
    },
    'story_points': 3,
    'fix_versions': [
        {'name': 'Release 1 - 2025', 'released': False}
    ],
    'components': [],
    'labels': [],
    'sprints': [
        {'name': 'Sprint 42', 'state': 'closed'},
        {'name': 'Sprint 43', 'state': 'closed'}
    ],
    'epic': None,
    'parent': {
        'key': 'SOMU-120',
        'summary': 'Mediabibliotek'
    },
    'subtasks': [],
    'links': [
        {
            'type': 'is child of',
            'key': 'SOMU-120',
            'summary': 'Mediabibliotek'
        }
    ],
    'attachments': [
        {
            'id': '1',
            'filename': 'icon-selector-dialog.png',
            'size': 251187,
            'mime_type': 'image/png',
            'content_url': 'https://example.com/att1',
            'thumbnail_url': None,
            'created': '2024-12-01T09:15:00+01:00',
            'author': 'Alessandro Gasperini'
        },
        {
            'id': '2', 
            'filename': 'media-library-empty.png',
            'size': 45321,
            'mime_type': 'image/png',
            'content_url': 'https://example.com/att2',
            'thumbnail_url': None,
            'created': '2024-12-01T09:16:00+01:00',
            'author': 'Alessandro Gasperini'
        }
    ],
    'comments': [
        {
            'id': '101',
            'author': 'Alessandro Gasperini',
            'body': 'Jag har implementerat grundfunktionaliteten för icon-väljaren. Testat med SVG och PNG, båda fungerar bra. Behöver feedback på UI:t.',
            'created': '2024-12-05T11:30:00+01:00',
            'updated': None
        },
        {
            'id': '102',
            'author': 'Kristian Enström',
            'body': 'Ser bra ut! Kan vi lägga till en sökfunktion i icon-biblioteket? Skulle underlätta när det blir många ikoner.',
            'created': '2024-12-06T14:20:00+01:00',
            'updated': None
        },
        {
            'id': '103',
            'author': 'Alessandro Gasperini',
            'body': 'Absolut, lägger till det som en förbättring. Stänger denna som klar nu.',
            'created': '2025-01-08T16:40:00+01:00',
            'updated': None
        }
    ],
    'custom_fields': {
        'Developer Notes': 'Implementerat med Drupal Media Library. SVG:er saniteras för säkerhet.',
        'Code reviewed by': 'David E.',
        'Tester': 'QA Team',
        'Harvest Time Tracking': 'Open Harvest Time Tracking',
        'Organisations': 'Microsite Team',
        'QAUid': 'QA-2025-0121'
    }
}


def main():
    print("🎨 Genererar demo-PDF...")
    print()
    
    # Skapa output-mapp
    os.makedirs('exports', exist_ok=True)
    
    # Generera PDF
    pdf_gen = PDFGenerator(output_dir='exports')
    pdf_path = pdf_gen.generate_pdf(DEMO_ISSUE, attachment_paths=[])
    
    print(f"✅ PDF genererad: {pdf_path}")
    print()
    print("📂 Öppna filen för att se resultatet!")
    print(f"   Sökväg: {os.path.abspath(pdf_path)}")
    print()
    print("💡 Tips: I Cursor kan du högerklicka på filen i sidofältet")
    print("   och välja 'Reveal in Finder' för att öppna den.")


if __name__ == '__main__':
    main()
