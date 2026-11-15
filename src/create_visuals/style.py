"""Shared chart style for the README charts."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Surface, text, and grid colors.
SURFACE = '#fcfcfb'
TEXT = '#0b0b0b'
TEXT_2 = '#52514e'
GRID = '#e4e3df'

# Categorical series colors, assigned in this order: blue, orange, aqua. Checked for colorblind separation.
# Aqua is below 3:1 contrast on the surface, so any chart using it must label it (legend or direct label).
SERIES = ['#2a78d6', '#eb6834', '#1baf7a']

# Sequential blue ramp, light to dark, for magnitudes such as pass rates.
BLUE_RAMP = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']

# Neutral fill for missing values.
MISSING = '#efeeea'

# Run outcomes in the run grid. Each is paired with a symbol and a legend label, never color alone.
RUN_PASS = SERIES[0]    # blue, with ✓
RUN_FAIL = SERIES[1]    # orange, with ✗
RUN_LIMIT = '#8d8c87'   # gray, with L

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.edgecolor': GRID, 'axes.labelcolor': TEXT_2,
  'xtick.color': TEXT_2, 'ytick.color': TEXT_2, 'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE})


def header(f, title, subtitle, mock=False, title_y=0.95, subtitle_y=0.885):
    """Draw the title, subtitle, and an optional MOCK DATA badge at the top of a figure."""
    f.text(0.035, title_y, title, fontsize=14, fontweight='bold', color=TEXT, va='top')
    f.text(0.035, subtitle_y, subtitle, fontsize=10.5, color=TEXT_2, va='top')
    if mock:
        f.text(0.965, title_y, 'MOCK DATA', fontsize=9, fontweight='bold', color='#a33a2f', va='top', ha='right',
               bbox=dict(boxstyle='round,pad=0.35', fc='#f8e3e0', ec='none'))
