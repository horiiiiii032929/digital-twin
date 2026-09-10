"""Embed the existing demo into the CTO deck without changing earlier builds."""
from pathlib import Path
import embed_presentation_video as media
media.BUILD=Path(__file__).resolve().parents[1]/'reports/generated/cto-slide-build'
if __name__=='__main__':
    media.run()
