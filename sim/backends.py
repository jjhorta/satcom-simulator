"""
Graphics backend management.
Sets up matplotlib (Agg) and provides lazy loaders for plotly/bokeh.
Import this module before any other sim module to ensure matplotlib is configured.
"""

import os
import matplotlib
matplotlib.use('Agg')  # Must be set before importing pyplot
os.environ['MPLCONFIGDIR'] = os.path.expanduser('~/.cache/matplotlib')

import warnings
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 - registers 3d projection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.animation import FuncAnimation, PillowWriter
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Bitstream Vera Sans', 'Liberation Sans']

from .constants import AVAILABLE_BACKENDS  # noqa: E402

GRAPHICS_BACKEND = 'matplotlib'
plotly_available = False
bokeh_available = False


def set_graphics_backend(backend):
    global GRAPHICS_BACKEND
    if backend.lower() not in AVAILABLE_BACKENDS:
        print(f"⚠️  Unknown backend '{backend}'. Using matplotlib.")
        GRAPHICS_BACKEND = 'matplotlib'
    else:
        GRAPHICS_BACKEND = backend.lower()
        print(f"🎨 Graphics backend: {GRAPHICS_BACKEND}")


def load_backend_modules(backend):
    global plotly_available, bokeh_available

    if backend == 'plotly' and not plotly_available:
        try:
            import plotly.graph_objects  # noqa: F401
            plotly_available = True
            print("✅ Plotly backend loaded (interactive HTML output)")
        except ImportError:
            print("❌ Plotly not installed. Install with: pip install plotly")
            print("   Falling back to matplotlib")
            set_graphics_backend('matplotlib')

    elif backend == 'bokeh' and not bokeh_available:
        try:
            import bokeh.plotting  # noqa: F401
            bokeh_available = True
            print("✅ Bokeh backend loaded (interactive HTML output)")
        except ImportError:
            print("❌ Bokeh not installed. Install with: pip install bokeh")
            print("   Falling back to matplotlib")
            set_graphics_backend('matplotlib')
