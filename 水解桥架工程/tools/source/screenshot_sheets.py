from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
root=Path(__file__).parent
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
for level in range(1,4):
 files=sorted((root/'连接件').glob(f'L{level}*.png'))
 for page in range((len(files)+7)//8):
  batch=files[page*8:page*8+8];canvas=Image.new('RGB',(1800,((len(batch)+1)//2)*390),'#202838');draw=ImageDraw.Draw(canvas)
  for k,p in enumerate(batch):
   im=Image.open(p).convert('RGB');im.thumbnail((880,345));x=(k%2)*900;y=(k//2)*390
   canvas.paste(im,(x+(900-im.width)//2,y+40));draw.text((x+12,y+5),p.stem,font=font,fill='white')
  canvas.save(root/f'screenshot_L{level}_{page+1}.jpg')
print('Sheets created')
