"""
Simulation Runner for Web Visualization
 Wraps the existing Simulation class to capture data for visualization
"""
from typing import Dict, List, Any
import copy
from ..simulation import Simulation
from ..models.entities import Order

class VisualizableSimulation(Simulation):
    """
    Subclass of Simulation that captures daily events for visualization.
    This ensures we don't modify the original Simulation code.
    """
    def __init__(self, config):
        super().__init__(config)
        self.daily_events: Dict[int, Dict[str, Any]] = {}

    def _record_daily_metrics(self, day: int, new_orders: List[Order]):
        """Override to capture raw data before aggregation"""
        
        # Capture raw data
        self._capture_daily_events(day, new_orders)
        
        # Call original method to maintain simulation integrity
        super()._record_daily_metrics(day, new_orders)

    def _capture_daily_events(self, day: int, new_orders: List[Order]):
        """Capture daily events and store them"""
        
        # Deep copy to ensure we capture the state at this moment
        # (Though entities are modified in place, we extract specific fields later)
        # For memory efficiency, we might just store references if we process them immediately after run
        # But simulation modifies objects steps by step.
        # Actually, completed orders are final. 
        # New orders are just created.
        
        # We need to capture:
        # 1. New orders created today
        # 2. Orders completed today
        # 3. Orders failed today
        # 4. Serving orders (snapshot)
        
        # Note: self.matching_engine.completed_orders accumulates ALL completed orders?
        # No, let's check matching.py: 
        # self.completed_orders is initialized in __init__.
        # in _process_serving_orders, it appends to self.completed_orders.
        # It does NEVER clear self.completed_orders in process_orders.
        
        # BUT, in Simulation._simulate_day:
        # self.matching_engine.reset_daily_count()
        # -> This only resets daily_order_count for escorts.
        
        # The completed_orders list grows indefinitely in the original simulation?
        # Yes, Simulation._record_daily_metrics calls matching_engine.get_statistics()
        # which returns len(self.completed_orders).
        
        # Use simple difference to find today's completed orders if list grows
        # OR check completed_at timestamp.
        
        completed_today = []
        for order in self.matching_engine.completed_orders:
            # We assume simulation runs day by day accurately
            # order.completed_at is datetime.
            # We can check if it matches current day (relative to start)
            # But here we are in _record_daily_metrics(day, ...)
            # So we can just filter by day if we had date.
            
            # Optimization: since this method is called at end of day,
            # and we want "events of the day", we can just look at orders 
            # that were completed "today".
            # Since we don't have previous day's index stored easily, 
            # we can filter by completion time corresponding to 'day'.
            # However, matching engine doesn't explicitly clear completed orders.
             pass

        # For visualization, we just need to dump the state or events.
        # To avoid duplicating too much data, let's store the lists.
        # We will process them in DataExporter.
        
        self.daily_events[day] = {
            "new_orders": new_orders,  # List[Order]
            "completed_orders": list(self.matching_engine.completed_orders), # Snapshot of all completed so far?
            # Ideally we want valid pointers or copies. 
            # Since simulation keeps adding to the same list, valid pointers are fine IF we filter later.
            # But waiting_queue changes (items removed).
            # Serving orders changes.
            
            "waiting_queue_snapshot": list(self.matching_engine.waiting_queue),
            "serving_orders_snapshot": list(self.matching_engine.serving_orders),
            "failed_orders_snapshot": list(self.matching_engine.failed_orders),
            
            "available_escorts_snapshot": list(self.supply_sim.get_available_escorts()) # Snapshot
        }

