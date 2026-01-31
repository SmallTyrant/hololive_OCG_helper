@echo off
set PNG=app\app_icon.png
set ICO=app\app_icon.ico

if not exist "%ICO%" if exist "%PNG%" (
  python -c "from pathlib import Path; from PIL import Image; png=Path(r'app/app_icon.png'); ico=Path(r'app/app_icon.ico'); ico.parent.mkdir(parents=True, exist_ok=True); img=Image.open(png); img = img.convert('RGBA') if img.mode not in ('RGBA','RGB') else img; img.save(ico, format='ICO', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])"
)

flet pack app/main.py --icon %ICO%
