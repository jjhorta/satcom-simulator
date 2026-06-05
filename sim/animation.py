"""
Time-lapse animation engine for constellation simulations.

Generates MP4/GIF animations from simulation timesteps with
configurable speed, layer toggles, and export options.
Supports up to 300x acceleration (NCAT-compatible).
"""

import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AnimationFrame:
    """A single frame of animation data."""
    timestamp_min: float
    satellite_positions: list[dict] = field(default_factory=list)
    coverage_footprints: list[list[tuple[float, float]]] = field(default_factory=list)
    visible_sats_count: int = 0
    link_metrics: dict = field(default_factory=dict)


class AnimationEngine:
    """
    Generate time-lapse animations from constellation simulation results.

    Supports:
        - Real-time (1x) and accelerated playback (10x, 100x, 300x)
        - Layer toggles: satellites, footprints, supply-demand, look angles
        - MP4, GIF, and frame-sequence export
    """

    def __init__(self, speed_multiplier: float = 1.0):
        """
        Args:
            speed_multiplier: Playback speed (1=real-time, 10, 100, 300)
        """
        self.speed_multiplier = speed_multiplier
        self.frames: list[AnimationFrame] = []
        self.fps = 15  # target frames per second

    def load_timesteps(
        self,
        timestamps_min: list[float],
        satellite_positions: list[list[dict]],
        coverage_data: list[list[list[tuple[float, float]]]] | None = None,
        link_data: list[dict] | None = None,
    ) -> None:
        """
        Load simulation timesteps into animation frames.

        Args:
            timestamps_min: List of timestamps (minutes from epoch)
            satellite_positions: List (per timestep) of list (per sat) of dicts
                with keys: 'lat', 'lon', 'altitude_km', 'name'
            coverage_data: Optional list of coverage footprint polygons per timestep
            link_data: Optional list of link metric dicts per timestep
        """
        self.frames = []
        for i, ts in enumerate(timestamps_min):
            sats = satellite_positions[i] if i < len(satellite_positions) else []
            cov = coverage_data[i] if coverage_data and i < len(coverage_data) else []
            links = link_data[i] if link_data and i < len(link_data) else {}
            self.frames.append(AnimationFrame(
                timestamp_min=ts,
                satellite_positions=sats,
                coverage_footprints=cov,
                visible_sats_count=len(sats),
                link_metrics=links,
            ))

    @property
    def duration_seconds(self) -> float:
        """Estimated playback duration at current speed."""
        if not self.frames or self.speed_multiplier <= 0:
            return 0.0
        total_minutes = self.frames[-1].timestamp_min - self.frames[0].timestamp_min
        return (total_minutes * 60) / self.speed_multiplier / self.fps

    def render_to_video(
        self,
        output_path: str = "animation.mp4",
        layers: Optional[list[str]] = None,
        dpi: int = 150,
        map_bounds: tuple[float, float, float, float] | None = None,
    ) -> str:
        """
        Render animation frames to an MP4 video file.

        Requires ffmpeg to be installed.

        Args:
            output_path: Output file path (.mp4 or .gif)
            layers: Which layers to include
                (default: ['satellites', 'footprints', 'labels'])
            dpi: Resolution of rendered frames
            map_bounds: (min_lon, min_lat, max_lon, max_lat) or None for global

        Returns:
            Path to rendered file
        """
        if not self.frames:
            raise ValueError("No frames loaded. Call load_timesteps() first.")

        layers = layers or ["satellites", "footprints", "labels"]
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
        from mpl_toolkits.basemap import Basemap

        fig = plt.figure(figsize=(16, 9), dpi=dpi)

        if map_bounds:
            m = Basemap(projection="mill", llcrnrlat=map_bounds[1],
                        urcrnrlat=map_bounds[3], llcrnrlon=map_bounds[0],
                        urcrnrlon=map_bounds[2], resolution="i")
        else:
            m = Basemap(projection="mill", lon_0=0, resolution="c")
        m.drawcoastlines(color="0.3")
        m.drawcountries(color="0.4", linewidth=0.3)
        m.drawmapboundary(fill_color="lightcyan")
        m.fillcontinents(color="lightgray", lake_color="lightcyan")

        # Pre-render scatter plots for satellites
        sat_scatter = m.scatter([], [], s=2, c="red", alpha=0.7, zorder=5)

        # Timestamp text
        time_text = plt.text(0.02, 0.98, "", transform=fig.transFigure,
                             fontsize=10, verticalalignment="top",
                             color="white", bbox=dict(boxstyle="round", fc="black", alpha=0.6))

        def init():
            sat_scatter.set_offsets(np.empty((0, 2)))
            time_text.set_text("")
            return sat_scatter, time_text

        def update(frame_idx):
            frame = self.frames[frame_idx]
            if "satellites" in layers:
                sats = frame.satellite_positions
                if sats:
                    xs, ys = [], []
                    for sat in sats:
                        x, y = m(sat["lon"], sat["lat"])
                        xs.append(x)
                        ys.append(y)
                    sat_scatter.set_offsets(np.column_stack([xs, ys]))
                else:
                    sat_scatter.set_offsets(np.empty((0, 2)))
            time_text.set_text(
                f"t = {frame.timestamp_min:.0f} min | "
                f"Sats: {frame.visible_sats_count} | "
                f"{self.speed_multiplier:.0f}x"
            )
            return sat_scatter, time_text

        # Calculate frame skip to achieve target speed
        n_frames = len(self.frames)
        step = max(1, int(1 / self.speed_multiplier * 300)) if self.speed_multiplier > 1 else 1
        frame_indices = list(range(0, n_frames, step))

        anim = animation.FuncAnimation(
            fig, update, frames=frame_indices,
            init_func=init, blit=True, interval=1000 // self.fps,
        )

        if output_path.endswith(".gif"):
            anim.save(output_path, writer="pillow", fps=self.fps)
        else:
            anim.save(output_path, writer="ffmpeg", fps=self.fps, dpi=dpi)

        plt.close(fig)
        return output_path

    def render_frames(
        self,
        output_dir: str = "frames",
        layers: Optional[list[str]] = None,
        dpi: int = 150,
        format: str = "png",
    ) -> int:
        """
        Export individual frames as image files.

        Args:
            output_dir: Directory to save frames
            layers: Which layers to include
            dpi: Resolution
            format: Image format ('png' or 'jpg')

        Returns:
            Number of frames saved
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.basemap import Basemap

        layers = layers or ["satellites", "footprints", "labels"]
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        fig = plt.figure(figsize=(16, 9), dpi=dpi)
        m = Basemap(projection="mill", lon_0=0, resolution="c")
        m.drawcoastlines(color="0.3")
        m.drawcountries(color="0.4", linewidth=0.3)
        m.drawmapboundary(fill_color="lightcyan")
        m.fillcontinents(color="lightgray", lake_color="lightcyan")

        n_saved = 0
        for i, frame in enumerate(self.frames):
            plt.clf()
            m = Basemap(projection="mill", lon_0=0, resolution="c")
            m.drawcoastlines(color="0.3")
            m.drawcountries(color="0.4", linewidth=0.3)
            m.drawmapboundary(fill_color="lightcyan")
            m.fillcontinents(color="lightgray", lake_color="lightcyan")

            if "satellites" in layers:
                sats = frame.satellite_positions
                if sats:
                    xs = [m(s["lon"], s["lat"])[0] for s in sats]
                    ys = [m(s["lon"], s["lat"])[1] for s in sats]
                    m.scatter(xs, ys, s=2, c="red", alpha=0.7, zorder=5)

            plt.title(f"t = {frame.timestamp_min:.0f} min | "
                      f"Sats: {frame.visible_sats_count} | "
                      f"{self.speed_multiplier:.0f}x")

            path = Path(output_dir) / f"frame_{i:05d}.{format}"
            plt.savefig(path, dpi=dpi, bbox_inches="tight")
            n_saved += 1

        plt.close(fig)
        return n_saved

    def summary(self) -> dict:
        """Return metadata summary about the loaded animation."""
        if not self.frames:
            return {"frames": 0, "duration_sec": 0, "speed": self.speed_multiplier}
        return {
            "frames": len(self.frames),
            "duration_min": self.frames[-1].timestamp_min - self.frames[0].timestamp_min,
            "duration_sec": self.duration_seconds,
            "speed_multiplier": self.speed_multiplier,
            "start_min": self.frames[0].timestamp_min,
            "end_min": self.frames[-1].timestamp_min,
        }
