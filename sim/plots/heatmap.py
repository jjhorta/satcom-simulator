"""
Heatmap plot rendering: matplotlib, plotly, and bokeh backends.
"""

import numpy as np
from .. import backends
from ..constants import COMMS_PAYLOADS


def save_heatmap_plot(lat_grid, lon_grid, coverage_grid, filename, title, comms_desc=""):
    """Save heatmap using the active graphics backend"""
    import matplotlib
    import matplotlib.pyplot as plt

    if backends.GRAPHICS_BACKEND == 'matplotlib':
        fig, ax = plt.subplots(figsize=(16, 8))
        im = ax.imshow(coverage_grid, extent=[-180, 180, -90, 90], origin='lower',
                       cmap='RdYlGn', vmin=0, vmax=100, aspect='auto')
        ax.set_xlabel('Longitude (°)')
        ax.set_ylabel('Latitude (°)')
        ax.set_title(title)
        plt.colorbar(im, ax=ax, label='Availability (%)')
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"💾 Saved: {filename}")
        if matplotlib.get_backend().lower() != 'agg':
            plt.show()
        plt.close()

    elif backends.GRAPHICS_BACKEND == 'plotly':
        backends.load_backend_modules('plotly')
        if backends.plotly_available:
            import plotly.graph_objects as go
            fig = go.Figure(data=go.Heatmap(
                z=coverage_grid,
                x=np.linspace(-180, 180, coverage_grid.shape[1]),
                y=np.linspace(-90, 90, coverage_grid.shape[0]),
                colorscale='RdYlGn',
                zmin=0,
                zmax=100,
                colorbar=dict(title='Availability (%)')
            ))
            fig.update_layout(
                title=title,
                xaxis_title='Longitude (°)',
                yaxis_title='Latitude (°)',
                width=1600,
                height=800
            )
            html_filename = filename.replace('.png', '.html')
            fig.write_html(html_filename)
            print(f"💾 Saved interactive: {html_filename}")

    elif backends.GRAPHICS_BACKEND == 'bokeh':
        backends.load_backend_modules('bokeh')
        if backends.bokeh_available:
            from bokeh.plotting import figure, output_file
            from bokeh.plotting import save as bokeh_save
            from bokeh.models import ColorBar, LinearColorMapper
            from bokeh.palettes import RdYlGn11

            p = figure(width=1600, height=800, title=title,
                       x_axis_label='Longitude (°)', y_axis_label='Latitude (°)',
                       x_range=(-180, 180), y_range=(-90, 90))

            color_mapper = LinearColorMapper(palette=RdYlGn11, low=0, high=100)
            p.image(image=[coverage_grid], x=-180, y=-90, dw=360, dh=180,
                    color_mapper=color_mapper)

            color_bar = ColorBar(color_mapper=color_mapper, label_standoff=12,
                                 border_line_color=None, location=(0, 0),
                                 title='Availability (%)')
            p.add_layout(color_bar, 'right')

            html_filename = filename.replace('.png', '.html')
            output_file(html_filename)
            bokeh_save(p)
            print(f"💾 Saved interactive: {html_filename}")
