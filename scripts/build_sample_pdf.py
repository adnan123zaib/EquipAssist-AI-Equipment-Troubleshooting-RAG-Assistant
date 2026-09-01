from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak

root=Path(__file__).resolve().parents[1]; source=root/'sample_data/PX-200_manual.md'; target=root/'sample_data/PX-200_manual.pdf'
styles=getSampleStyleSheet(); styles.add(ParagraphStyle(name='ManualBody',parent=styles['BodyText'],fontName='Helvetica',fontSize=10,leading=14,spaceAfter=7))
story=[]
for line in source.read_text().splitlines():
    if line.startswith('# '): story.append(Paragraph(line[2:],styles['Title'])); story.append(Spacer(1,8*mm))
    elif line.startswith('## '): story.append(PageBreak()); story.append(Paragraph(line[3:],styles['Heading1']))
    elif line.startswith('### '): story.append(Paragraph(line[4:],styles['Heading2']))
    elif line.strip(): story.append(Paragraph(line.replace('  ',' '),styles['ManualBody']))
def footer(canvas,doc):
    canvas.saveState(); canvas.setFont('Helvetica',8); canvas.drawString(20*mm,12*mm,'PX-200 Industrial Hydraulic Pump Controller · Manual v1.4'); canvas.drawRightString(190*mm,12*mm,f'Page {doc.page}'); canvas.restoreState()
SimpleDocTemplate(str(target),pagesize=A4,rightMargin=20*mm,leftMargin=20*mm,topMargin=18*mm,bottomMargin=20*mm,title='PX-200 Manual').build(story,onFirstPage=footer,onLaterPages=footer)
print(target)

