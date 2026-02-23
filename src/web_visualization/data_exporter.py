"""
Data Exporter for Web Visualization
Extracts data from the simulation and exports it to JSON for the frontend.
"""
import json
import os
import random
import shutil
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta

from ..config.integrated_data_config import integrated_config
from .simulation_runner import VisualizableSimulation
from ..config.settings import SimulationConfig


class DataExporter:
    """
    Exports simulation data to JSON files.
    """

    def __init__(self, output_dir: str = "output/web_visualization/data"):
        self.output_dir = Path(output_dir)
        self.static_dir = self.output_dir / "static"
        self.dynamic_dir = self.output_dir / "dynamic"
        
        # Initialize directories
        self._init_directories()

        # Cache for generated locations
        self.communities = []
        self.hospitals = []
        self.districts = []
        self.user_community_map = {} # user_id -> community_id

    def _init_directories(self):
        """Initialize output directories"""
        if self.output_dir.exists():
            # Optional: Clean up previous data? 
            # For safety, maybe just overwrite files.
            pass
        
        os.makedirs(self.static_dir, exist_ok=True)
        os.makedirs(self.dynamic_dir, exist_ok=True)

    def run_and_export(self, days: int = 7):
        """Run simulation and export data"""
        print(f"Starting simulation for {days} days...")
        
        # Configure simulation
        config = SimulationConfig()
        config.total_days = days
        config.training_days = 0 # Ensure initial escorts are available immediately
        
        # --- Apply Corrected Parameters from Week 1 Report (IntegratedDataConfig) ---
        # 1. Platform Base
        config.dau_base = integrated_config.beijing_dau
        
        # 2. Conversion Funnel
        config.exposure_rate = integrated_config.exposure_rate # 0.03
        config.click_rate = integrated_config.click_rate # 0.02
        config.consult_rate = integrated_config.consult_conversion_rate # 0.35
        config.order_rate = integrated_config.order_conversion_rate # 0.65
        
        # 3. Repurchase (CRITICAL FIX: 30% -> 13.5%)
        config.repurchase_prob = integrated_config.repeat_rate_first_order # 0.135
        config.repurchase_cycle_days = integrated_config.repeat_cycle_days
        
        # 4. Supply Side
        # Week 1 Report says 150 escorts. Config default is 15.
        config.initial_escorts = 150 
        
        print(f"Applied Corrected Parameters:")
        print(f"  - DAU: {config.dau_base}")
        print(f"  - Exposure: {config.exposure_rate}")
        print(f"  - Repurchase: {config.repurchase_prob}")
        print(f"  - Initial Escorts: {config.initial_escorts}")
        # --------------------------------------------------------------------------
        
        # Create runner
        sim = VisualizableSimulation(config)
        result = sim.run(verbose=True)
        
        print("Simulation completed. Exporting data...")
        
        # 1. Generate and Export Static Data
        self._generate_static_data(sim)
        self._export_static_data()
        
        # 2. Export Dynamic Data
        self._export_dynamic_data(sim, sim.daily_events)
        
        print(f"Data export completed to {self.output_dir}")

    def _generate_static_data(self, sim: VisualizableSimulation):
        """Generate static data (hospitals, communities)"""
        
        # --- Districts ---
        # Define districts with approximate center coordinates (Beijing)
        self.districts = [
            {"id": "chaoyang", "name": "朝阳区", "center": [39.9219, 116.4437]},
            {"id": "haidian", "name": "海淀区", "center": [39.9590, 116.2983]},
            {"id": "xicheng", "name": "西城区", "center": [39.9127, 116.3660]},
            {"id": "dongcheng", "name": "东城区", "center": [39.9180, 116.4163]}, # Corrected from plan
        ]

        # --- Hospitals ---
        # We use the list from SimulationConfig or generate them
        # sim.config.covered_hospitals is a list of names strings
        
        # Define real coordinates for key hospitals
        real_hospitals = {
            "协和医院": {"lat": 39.907221, "lon": 116.448751, "district": "东城区"},
            "301医院": {"lat": 39.902798, "lon": 116.278567, "district": "海淀区"}, # PLA General Hospital
            "北医三院": {"lat": 39.974652, "lon": 116.352612, "district": "海淀区"}, # Peking Univ Third Hospital
            "阜外医院": {"lat": 39.923921, "lon": 116.340275, "district": "西城区"},
            "天坛医院": {"lat": 39.883633, "lon": 116.434504, "district": "丰台区"}, # New campus
            "同仁医院": {"lat": 39.9008, "lon": 116.4168, "district": "东城区"},
            "朝阳医院": {"lat": 39.9270, "lon": 116.4550, "district": "朝阳区"},
            "安贞医院": {"lat": 39.9735, "lon": 116.4050, "district": "朝阳区"},
            "宣武医院": {"lat": 39.8895, "lon": 116.3680, "district": "西城区"},
            "积水潭医院": {"lat": 39.9430, "lon": 116.3700, "district": "西城区"}
        }
        
        hospital_names = sim.config.covered_hospitals
        self.hospitals = []
        
        for i, name in enumerate(hospital_names):
            if name in real_hospitals:
                info = real_hospitals[name]
                self.hospitals.append({
                    "id": f"hospital_{i+1}",
                    "name": name,
                    "lat": info["lat"],
                    "lon": info["lon"],
                    "district": info["district"],
                    "level": "三甲",
                    "capacity": 200
                })
            else:
                # Fallback for unknown
                district = random.choice(self.districts)
                self.hospitals.append({
                    "id": f"hospital_{i+1}",
                    "name": name,
                    "lat": round(district["center"][0] + random.uniform(-0.02, 0.02), 6),
                    "lon": round(district["center"][1] + random.uniform(-0.02, 0.02), 6),
                    "district": district["name"],
                    "level": "三甲",
                    "capacity": 100
                })

        # --- Communities ---
        # Generate communities around districts
        self.communities = []
        community_id_counter = 1
        
        for district in self.districts:
            # Generate 5-10 communities per district
            num_communities = random.randint(5, 10)
            for _ in range(num_communities):
                lat = district["center"][0] + random.uniform(-0.04, 0.04)
                lon = district["center"][1] + random.uniform(-0.04, 0.04)
                
                self.communities.append({
                    "id": f"community_{community_id_counter}",
                    "name": f"{district['name']}小区{community_id_counter}",
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "district": district["name"],
                    "population": random.randint(3000, 10000)
                })
                community_id_counter += 1

    def _export_static_data(self):
        """Export static data to JSON"""
        
        # Districts
        with open(self.static_dir / "districts.json", "w", encoding="utf-8") as f:
            json.dump({"version": "1.0", "districts": self.districts}, f, ensure_ascii=False, indent=2)

        # Hospitals
        with open(self.static_dir / "hospitals.json", "w", encoding="utf-8") as f:
            json.dump({"version": "1.0", "hospitals": self.hospitals}, f, ensure_ascii=False, indent=2)

        # Communities
        with open(self.static_dir / "communities.json", "w", encoding="utf-8") as f:
            json.dump({"version": "1.0", "communities": self.communities}, f, ensure_ascii=False, indent=2)

    def _assign_user_community(self, user_id: str) -> str:
        """Assign a community to a user consistently"""
        if user_id not in self.user_community_map:
            community = random.choice(self.communities)
            self.user_community_map[user_id] = community["id"]
        return self.user_community_map[user_id]

    def _get_hospital_by_name(self, name: str) -> Dict:
        """Find hospital by name"""
        for h in self.hospitals:
            if h["name"] == name:
                return h
        # Fallback if not found (should match config)
        if self.hospitals:
            return self.hospitals[0]
        return {"id": "unknown", "lat": 39.9, "lon": 116.4}

    def _export_dynamic_data(self, sim: VisualizableSimulation, daily_events: Dict[int, Dict[str, Any]]):
        """Export dynamic event data"""
        
        start_date = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        # Real implementation of export loop with history tracking
        processed_matched_ids = set()
        processed_completed_ids = set()
        
        for day in sorted(daily_events.keys()):
            events_data = daily_events[day]
            export_events = []
            
            # 1. New Orders
            new_orders = events_data.get("new_orders", [])
            
            # Map order_id to its created timestamp to ensure consistency
            order_created_times = {}

            for order in new_orders:
                # Assign community to user
                community_id = self._assign_user_community(order.user.id)
                community = next((c for c in self.communities if c["id"] == community_id), self.communities[0])
                
                hospital_data = self._get_hospital_by_name(order.user.target_hospital)
                
                # --- FIX: Generate random timestamp between 08:00 and 17:00 ---
                # Default created_at is likely process time. We want simulation time.
                # Random hour between 8 and 16 (4 PM) to allow time for service
                hour = random.randint(8, 16)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                
                # Create a base datetime for this order on this day
                # We use the 'day' loop variable to determine the date
                # Note: simulation start_date might differ, but we construct a date here
                today_base = start_date + timedelta(days=day)
                order_time = today_base.replace(hour=hour, minute=minute, second=second)
                
                order_created_times[order.id] = order_time
                
                ts = order_time.strftime("%H:%M:%S")
                
                export_events.append({
                    "event_id": f"evt_create_{order.id[:8]}",
                    "timestamp": ts,
                    "type": "order_created",
                    "order_id": order.id,
                    "user": {
                        "user_id": order.user.id,
                        "location": [community["lat"], community["lon"]],
                        "community_id": community_id
                    },
                    "hospital": {
                        "hospital_id": hospital_data["id"],
                        "location": [hospital_data["lat"], hospital_data["lon"]]
                    },
                    "metadata": {
                        "is_first_order": not order.user.is_repurchase,
                        "disease_type": order.user.disease_type
                    }
                })

            # 2. Scan all relevant lists for status updates
            serving_snapshot = events_data.get("serving_orders_snapshot", [])
            completed_snapshot = events_data.get("completed_orders", [])
            
            all_touched_orders = serving_snapshot + completed_snapshot
            
            for order in all_touched_orders:
                if order.id not in processed_matched_ids:
                    # It's a new match event
                    processed_matched_ids.add(order.id)
                    
                    escort_loc = [order.escort.location_lat, order.escort.location_lon] if order.escort else [39.9, 116.4]
                    
                    # Estimate match time: 5-30 mins after creation, or random if creation time unknown
                    if order.id in order_created_times:
                        creation_time = order_created_times[order.id]
                    else:
                        # Fallback: created earlier today?
                        hour = random.randint(8, 16)
                        creation_time = (start_date + timedelta(days=day)).replace(hour=hour, minute=random.randint(0,59))

                    # Match delay: 5 to 30 mins
                    delay_mins = random.randint(5, 30)
                    match_time = creation_time + timedelta(minutes=delay_mins)
                    
                    ts = match_time.strftime("%H:%M:%S")
                    
                    export_events.append({
                        "event_id": f"evt_match_{order.id[:8]}",
                        "timestamp": ts,
                        "type": "order_matched",
                        "order_id": order.id,
                        "escort": {
                            "escort_id": order.escort.id,
                            "location": escort_loc
                        }
                    })
                    
                    # Generate Service Start Event (Same time usually)
                    export_events.append({
                        "event_id": f"evt_start_{order.id[:8]}",
                        "timestamp": ts,
                        "type": "service_start",
                        "order_id": order.id
                    })

            # Find all orders that are new to "completed" state
            for order in completed_snapshot:
                if order.id not in processed_completed_ids:
                    processed_completed_ids.add(order.id)
                    
                    # Estimate completion time: 2-4 hours after match
                    # We need match time. 
                    # If we just processed match, use it. If not, guess.
                    
                    # For consistency, we need to store match times? 
                    # Simpler: Random time between 10:00 and 19:00, ensuring it's later?
                    # Or just random 2-4h duration.
                    
                    # Re-calculate or retrieve match time?
                    # Since we don't have persistent state of match times easily here, 
                    # we'll approximate: hour = random(10, 18)
                    
                    end_hour = random.randint(10, 18)
                    end_min = random.randint(0, 59)
                    
                    complete_time = (start_date + timedelta(days=day)).replace(hour=end_hour, minute=end_min)
                    ts = complete_time.strftime("%H:%M:%S")
                    
                    export_events.append({
                        "event_id": f"evt_complete_{order.id[:8]}",
                        "timestamp": ts,
                        "type": "order_completed",
                        "order_id": order.id,
                        "rating": order.rating,
                        "is_success": order.is_success,
                        "price": random.randint(200, 270) # Avg ~235
                    })

            # Inject Feedback Cases from Report
            self._inject_highlight_cases(export_events, day)

            # Sort events by timestamp
            export_events.sort(key=lambda x: x["timestamp"])
            
            # Generate Summary
            completed_events = [e for e in export_events if e["type"] == "order_completed"]
            completed_count = len(completed_events)
            
            # GMV & Price
            total_gmv = sum(e.get("price", 0) for e in completed_events)
            avg_price = round(total_gmv / completed_count, 1) if completed_count > 0 else 0
            
            # Avg Rating
            ratings = [e["rating"] for e in completed_events if "rating" in e]
            avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
            
            # Hourly Stats
            hourly_stats = {}
            for e in export_events:
                h = e["timestamp"].split(":")[0]
                if h not in hourly_stats: hourly_stats[h] = 0
                hourly_stats[h] += 1

            summary = {
                "total_orders": len(new_orders), # New orders today
                "completed_orders": completed_count,
                "gmv": total_gmv,
                "avg_price": avg_price,
                "avg_rating": avg_rating,
                "hourly_stats": hourly_stats
            }
            
            # Export Day Data
            day_file = self.dynamic_dir / f"day_{day+1}_events.json"
            summary_file = self.dynamic_dir / f"day_{day+1}_summary.json"
            
            with open(day_file, "w", encoding="utf-8") as f:
                json.dump({
                    "version": "1.0",
                    "day": day + 1,
                    "date": (start_date + timedelta(days=day)).strftime("%Y-%m-%d"),
                    "events": export_events
                }, f, ensure_ascii=False, indent=2)
                
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump({
                    "version": "1.0",
                    "day": day + 1,
                    "summary": summary
                }, f, ensure_ascii=False, indent=2)

    def _inject_highlight_cases(self, export_events: List[Dict], day: int):
        """Inject specific feedback cases from the report into the event stream"""
        
        # Case 1: Ms. Wang (王女士) - Day 1 (Index 0)
        if day == 0:
            export_events.append({
                "event_id": "evt_case_1_wang",
                "timestamp": "09:30:00",
                "type": "order_completed", # Using completed to show feedback immediately
                "order_id": "ORDER-CASE-001",
                "user": {"user_id": "u_wang_35", "location": [39.9180, 116.4163], "community_id": "community_case_1"},
                "hospital": {"hospital_id": "h_xiehe", "location": [39.907221, 116.448751]}, # Xiehe
                "rating": 5.0,
                "is_success": True,
                "metadata": {
                    "is_highlight": True,
                    "highlight_title": "案例1: 子女代购型 - 王女士",
                    "feedback_content": "父亲有高血压和冠心病，每周都要去协和医院复诊。我工作太忙，经常要出差，无法每次都陪他去。通过滴滴陪诊找到了李阿姨，她很细心，挂号、缴费、取药都不用操心。父亲说有她在身边很安心。如果这次体验好，我打算以后每次都指定李阿姨。",
                    "tags": ["子女代购", "复购意向强", "指定服务"]
                }
            })

        # Case 2: Uncle Li (李大爷) - Day 2 (Index 1)
        if day == 1:
            export_events.append({
                "event_id": "evt_case_2_li",
                "timestamp": "14:15:00",
                "type": "order_completed",
                "order_id": "ORDER-CASE-002",
                "user": {"user_id": "u_li_68", "location": [39.9127, 116.3660], "community_id": "community_case_2"},
                "hospital": {"hospital_id": "h_tiantan", "location": [39.883633, 116.434504]}, # Tiantan
                "rating": 4.0,
                "is_success": True,
                "metadata": {
                    "is_highlight": True,
                    "highlight_title": "案例2: 老年自主型 - 李大爷",
                    "feedback_content": "我一个人住，儿女都在深圳工作。上次去天坛医院看头晕，排队4个小时，累得不行。朋友推荐了陪诊服务，小张帮我提前挂号，还推着轮椅带我去各个科室，省了很多力气。就是价格有点贵，180块钱，我退休金只有4000多，希望能便宜点。如果能有100多块的服务就更好了。",
                    "tags": ["老年自主", "价格敏感", "退休独居"]
                }
            })
            
        # Case 3: Escort Xiao Li (小李) - Day 3 (Index 2)
        if day == 2:
            export_events.append({
                "event_id": "evt_case_3_escort_li",
                "timestamp": "17:45:00",
                "type": "order_completed",
                "order_id": "ORDER-CASE-003",
                "user": {"user_id": "u_random_1", "location": [39.9590, 116.2983], "community_id": "community_case_3"},
                "hospital": {"hospital_id": "h_any", "location": [39.9, 116.4]},
                "rating": 5.0,
                "is_success": True,
                "metadata": {
                    "is_highlight": True,
                    "highlight_title": "案例3: 资深陪诊员 - 小李",
                    "feedback_content": "我做陪诊员已经半年了，现在每天能接2-3单，收入稳定。最让我有成就感的是，很多老人家都指定要我服务。有个王大爷已经连续5次指定我了，他说我像他女儿一样。我觉得这份工作很有意义，能帮助到需要帮助的人。",
                    "tags": ["资深陪诊员", "高指定率", "职业认同感"]
                }
            })

        # Case 4: Escort Xiao Zhang (小张) - Day 4 (Index 3)
        if day == 3:
             export_events.append({
                "event_id": "evt_case_4_escort_zhang",
                "timestamp": "10:30:00",
                "type": "order_completed", # Using completed/feedback type
                "order_id": "ORDER-CASE-004",
                "user": {"user_id": "u_random_2", "location": [39.9219, 116.4437], "community_id": "community_case_4"},
                "hospital": {"hospital_id": "h_any", "location": [39.9, 116.4]},
                "rating": 4.0,
                "is_success": True,
                "metadata": {
                    "is_highlight": True,
                    "highlight_title": "案例4: 新手陪诊员 - 小张",
                    "feedback_content": "我刚做陪诊员1个月，培训很系统，但实际接单还是有点困难。有时候一天能接2单，有时候一单都没有。这周只接了10单，收入不太稳定。而且我还没有被用户指定过，都是随机分配的订单。我担心如果一直这样，收入太不稳定。",
                    "tags": ["新手陪诊员", "订单不稳定", "收入焦虑"]
                }
            })

