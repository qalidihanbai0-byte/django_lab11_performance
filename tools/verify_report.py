import json
from pathlib import Path
import sys

from PIL import Image, ImageOps, ImageDraw
import pypdfium2 as pdfium

sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).resolve().parents[1]
target = root / 'output/pdf/Қали_Диханбай_ЗС11.pdf'
folder = root / 'tmp/pdfs'
folder.mkdir(parents=True, exist_ok=True)
document = pdfium.PdfDocument(target)
texts, thumbs = [], []
for index, page in enumerate(document):
    text = page.get_textpage().get_text_range()
    texts.append(text)
    bitmap = page.render(scale=1.5)
    image = bitmap.to_pil().convert('RGB')
    image.save(folder / f'page-{index + 1}.png')
    thumb = ImageOps.contain(image, (300, 425))
    panel = Image.new('RGB', (320, 455), '#d5dce2')
    panel.paste(thumb, ((320 - thumb.width) // 2, 8))
    ImageDraw.Draw(panel).text((10, 435), f'Page {index + 1}', fill='black')
    thumbs.append(panel)
    print(index + 1, len(text), text[:95].replace('\r\n', ' | '))
combined = '\n'.join(texts)
for required in ('Қали Диханбай', 'Тақырыбы және мақсаты', 'EXPLAIN', 'Кэштеу', 'Қорытынды', '115,056'):
    assert required in combined, required
assert '\ufffd' not in combined
columns = 3
rows = (len(thumbs) + columns - 1) // columns
sheet = Image.new('RGB', (columns * 320, rows * 455), 'white')
for i, thumb in enumerate(thumbs):
    sheet.paste(thumb, ((i % columns) * 320, (i // columns) * 455))
sheet.save(folder / 'contact-sheet.png')
result = {'pages': len(document), 'text_characters': len(combined),
          'kazakh_text_extracted': True, 'replacement_characters': False,
          'rendered_pages': len(thumbs), 'visual_review': 'pending'}
(root / 'evidence/pdf-validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
