"""
竞争Agent - 模拟竞争对手行为
"""

import random
from typing import Dict, List, Any, Optional

from .base_agent import BaseAgent, AgentMessage, AgentType, MessageType


class CompetitionAgent(BaseAgent):
    """
    竞争Agent

    职责：
    1. 模拟竞争对手的行为
    2. 影响市场份额
    3. 模拟价格战
    4. 模拟营销战
    """

    def __init__(self):
        super().__init__(agent_id="competition_agent", agent_type=AgentType.COMPETITION)

        # 竞争对手列表
        self.competitors = [
            {'name': '美团陪诊', 'market_share': 0.30},
            {'name': '滴滴陪诊', 'market_share': 0.25},
            {'name': '其他平台', 'market_share': 0.45}
        ]

    def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理消息"""
        return None

    def take_action(self, simulation_state: Dict[str, Any]) -> List[AgentMessage]:
        """执行竞争模拟"""
        messages = []
        current_day = simulation_state.get('current_day', 0)

        # 每周评估一次竞争态势
        if current_day % 7 == 0:
            # 10%概率竞争对手有大动作
            if random.random() < 0.1:
                action = self._simulate_competitor_action()
                messages.append(self.send_message(
                    receiver="",  # 广播
                    message_type=MessageType.EVENT,
                    content={
                        'event_type': 'competitor_action',
                        'action': action,
                        'day': current_day
                    },
                    priority=6
                ))

        return messages

    def _simulate_competitor_action(self) -> Dict:
        """模拟竞争对手行动"""
        actions = [
            {
                'type': 'price_war',
                'description': '竞争对手降价促销',
                'impact': -0.15
            },
            {
                'type': 'marketing_campaign',
                'description': '竞争对手大规模营销',
                'impact': -0.10
            },
            {
                'type': 'service_upgrade',
                'description': '竞争对手升级服务',
                'impact': -0.08
            }
        ]
        return random.choice(actions)
