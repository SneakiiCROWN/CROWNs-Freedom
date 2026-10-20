"""Current-build identity for historical art/audio extraction fixtures."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def identity(z,namespace,prefix='CROWN',marker=True):
    z.writestr(prefix+'/__init__.py',(R/'SOURCE/__init__.py').read_bytes())
    if marker:z.writestr(prefix+'/CROWN_CC0_ASSETS/NEON_WORDMARK_COMPACT.png',(R/'CROWN_CC0_ASSETS/NEON_WORDMARK_COMPACT.png').read_bytes())
