"""
市场动态Agent - 模拟市场环境变化
"""

import random
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_agent import BaseAgent, AgentMessage, AgentType, MessageType


class MarketDynamicsAgent(BaseAgent):
    """
    市场动态Agent

    职责：
    1. 模拟季节性需求波动
    2. 模拟突发事件（天气、节假日、疫情等）
    3. 模拟市场规模变化
    4. 模拟竞争环境变化
    """

    def __init__(self):
        super().__init__(agent_id="market_dynamics_agent", agent_type=AgentType.MARKET_DYNAMICS)

        # 季节性因子
        self.seasonal_factors = {
            'spring': 1.0,  # 春季
            'summer': 0.9,  # 夏季（需求略降）
            'autumn': 1.1,  # 秋季（需求上升）
            'winter': 1.2,  # 冬季（需求最高）
        }

        # 节假日因子
        self.holiday_factors = {
            'normal': 1.0,
            'weekend': 0.8,  # 周末需求下降
            'holiday': 0.6,  # 一般节假日需求大幅下降
            'spring_festival': 0.3,  # 春节需求-70%（80%订单由子女代购，春节子女在家）
        }

    def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理消息"""
        return None

    def take_action(self, simulation_state: Dict[str, Any]) -> List[AgentMessage]:
        """执行市场动态模拟"""
        messages = []
        current_day = simulation_state.get('current_day', 0)

        # 1. 计算当前市场因子
        market_factor = self._calculate_market_factor(current_day)

        # 2. 检查是否有突发事件
        event = self._check_random_events(current_day)
        if event:
            messages.append(self.send_message(
                receiver="",  # 广播
                message_type=MessageType.EVENT,
                content={
                    'event_type': 'market_event',
                    'event': event,
                    'day': current_day
                },
                priority=8
            ))

        # 3. 更新市场状态
        messages.append(self.send_message(
            receiver="coordinator",
            message_type=MessageType.EVENT,
            content={
                'event_type': 'market_update',
                'market_factor': market_factor,
                'day': current_day
            }
        ))

        # 4. 更新指标
        self.update_metrics({
            'market_factor': market_factor,
            'season': self._get_season(current_day),
            'day_type': self._get_day_type(current_day)
        })

        return messages

    def _calculate_market_factor(self, current_day: int) -> float:
        """计算市场因子"""
        # 季节因子
        season = self._get_season(current_day)
        seasonal_factor = self.seasonal_factors.get(season, 1.0)

        # 节假日因子
        day_type = self._get_day_type(current_day)
        holiday_factor = self.holiday_factors.get(day_type, 1.0)

        # 随机波动
        random_factor = random.uniform(0.9, 1.1)

        return seasonal_factor * holiday_factor * random_factor

    def _get_season(self, current_day: int) -> str:
        """获取季节"""
        month = (current_day % 365) // 30 + 1
        if month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        elif month in [9, 10, 11]:
            return 'autumn'
        else:
            return 'winter'

    def _get_day_type(self, current_day: int) -> str:
        """获取日期类型"""
        day_of_week = current_day % 7
        if day_of_week in [5, 6]:  # 周六、周日
            return 'weekend'
        # 简化处理，假设每月1-3号是节假日
        if (current_day % 30) in [0, 1, 2]:
            return 'holiday'
        return 'normal'

    def _check_random_events(self, current_day: int) -> Optional[Dict]:
        """检查随机事件"""
        # 5%概率发生随机事件
        if random.random() < 0.05:
            events = [
                {
                    'name': '恶劣天气',
                    'impact': -0.3,
                    'description': '大雨/大雪导致需求下降30%'
                },
                {
                    'name': '流感高发',
                    'impact': 0.2,
                    'description': '流感季节，医院就诊需求上升20%'
                },
                {
                    'name': '医保政策调整',
                    'impact': 0.15,
                    'description': '医保政策调整，陪诊需求上升15%'
                },
                {
                    'name': '竞争对手促销',
                    'impact': -0.2,
                    'description': '竞争对手大力促销，需求下降20%'
                }
            ]
            return random.choice(events)

        return None