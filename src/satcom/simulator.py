"""
Simulation engine for satellite constellations.
"""

from typing import List, Dict, Callable, Optional
import numpy as np
from .constellation import Constellation


class Simulator:
    """
    Simulation engine for satellite constellation dynamics and communications.
    """
    
    def __init__(self, constellation: Constellation, time_step: float = 60.0):
        """
        Initialize the simulator.
        
        Args:
            constellation: Constellation object to simulate
            time_step: Time step for simulation in seconds (default: 60s)
        """
        self.constellation = constellation
        self.time_step = time_step
        self.current_time = 0.0
        self.history: List[Dict] = []
        self.callbacks: List[Callable] = []
    
    def add_callback(self, callback: Callable):
        """
        Add a callback function to be called at each time step.
        
        The callback should accept the simulator instance as an argument:
            callback(simulator: Simulator)
        
        Args:
            callback: Callback function
        """
        self.callbacks.append(callback)
    
    def step(self):
        """
        Advance the simulation by one time step.
        """
        # Propagate all satellites
        self.constellation.propagate(self.time_step)
        self.current_time += self.time_step
        
        # Record state
        self._record_state()
        
        # Execute callbacks
        for callback in self.callbacks:
            callback(self)
    
    def run(self, duration: float, verbose: bool = False):
        """
        Run the simulation for a specified duration.
        
        Args:
            duration: Simulation duration in seconds
            verbose: Print progress information
        """
        num_steps = int(duration / self.time_step)
        
        if verbose:
            print(f"Running simulation for {duration}s ({num_steps} steps)")
        
        for step in range(num_steps):
            self.step()
            
            if verbose and (step + 1) % 100 == 0:
                print(f"  Step {step + 1}/{num_steps} (t={self.current_time:.1f}s)")
        
        if verbose:
            print(f"Simulation complete. Final time: {self.current_time:.1f}s")
    
    def _record_state(self):
        """
        Record the current state of the simulation.
        """
        state = {
            "time": self.current_time,
            "coverage_stats": self.constellation.get_coverage_statistics(),
        }
        self.history.append(state)
    
    def get_coverage_over_time(self) -> List[Dict]:
        """
        Get coverage statistics over time.
        
        Returns:
            List of dictionaries with time and coverage statistics
        """
        return self.history
    
    def reset(self):
        """
        Reset the simulation to initial state.
        """
        self.current_time = 0.0
        self.history.clear()
        
        # Reset all satellites to initial conditions
        for satellite in self.constellation.satellites:
            satellite.time = 0.0
            satellite.update_state()
    
    def get_summary(self) -> Dict:
        """
        Get a summary of the simulation.
        
        Returns:
            Dictionary with simulation summary
        """
        if not self.history:
            return {
                "total_time": 0.0,
                "num_steps": 0,
                "time_step": self.time_step,
            }
        
        # Calculate average coverage
        coverage_percentages = [
            state["coverage_stats"]["coverage_percentage"]
            for state in self.history
        ]
        avg_coverage = np.mean(coverage_percentages) if coverage_percentages else 0.0
        min_coverage = np.min(coverage_percentages) if coverage_percentages else 0.0
        max_coverage = np.max(coverage_percentages) if coverage_percentages else 0.0
        
        return {
            "total_time": self.current_time,
            "num_steps": len(self.history),
            "time_step": self.time_step,
            "avg_coverage_percentage": avg_coverage,
            "min_coverage_percentage": min_coverage,
            "max_coverage_percentage": max_coverage,
        }
