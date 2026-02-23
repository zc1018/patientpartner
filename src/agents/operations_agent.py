"""
运营Agent - 模拟运营决策
"""

import random
from typing import Dict, List, Any, Optional

from .base_agent import BaseAgent, AgentMessage, AgentType, MessageType


class OperationsAgent(BaseAgent):
    """
    运营Agent

    职责：
    1. 基于业务指标自动调整策略
    2. 模拟营销活动决策
    3. 模拟价格调整决策
    4. 模拟陪诊员招募决策
    5. 模拟补贴策略
    """

    def __init__(self):
        super().__init__(agent_id="operations_agent", agent_type=AgentType.OPERATIONS)

        # 运营策略参数
        self.target_completion_rate = 0.90  # 目标完成率90%
        self.target_retention_rate = 0.60  # 目标留存率60%
        self.target_escort_utilization = 0.70  # 目标陪诊员利用率70%

    def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理消息"""
        if message.message_type == MessageType.ALERT:
            alert_type = message.content.get('alert_type')

            if alert_type == 'escort_churn':
                # 陪诊员流失，触发招募
                return self._handle_escort_churn(message.content)

            elif alert_type == 'user_churn':
                # 用户流失，触发留存活动
                return self._handle_user_churn(message.content)

            elif alert_type == 'low_completion_rate':
                # 完成率低，触发供给侧优化
                return self._handle_low_completion_rate(message.content)

        return None

    def take_action(self, simulation_state: Dict[str, Any]) -> List[AgentMessage]:
        """执行运营决策"""
        messages = []
        current_day = simulation_state.get('current_day', 0)

        # 每周评估一次运营策略
        if current_day % 7 == 0:
            # 1. 评估是否需要招募陪诊员
            recruit_decision = self._evaluate_recruit_need(simulation_state)
            if recruit_decision:
                messages.append(self.send_message(
                    receiver="escort_behavior_agent",
                    message_type=MessageType.EVENT,
                    content={
                        'event_type': 'recruit_escorts',
                        'count': recruit_decision['count'],
                        'reason': recruit_decision['reason']
                    }
                ))

            # 2. 评估是否需要营销活动
            marketing_decision = self._evaluate_marketing_need(simulation_state)
            if marketing_decision:
                messages.append(self.send_message(
                    receiver="user_behavior_agent",
                    message_type=MessageType.EVENT,
                    content={
                        'event_type': 'marketing_campaign',
                        'campaign_type': marketing_decision['type'],
                        'intensity': marketing_decision['intensity']
                    }
                ))

        return messages

    def _evaluate_recruit_need(self, simulation_state: Dict[str, Any]) -> Optional[Dict]:
        """评估是否需要招募陪诊员"""
        # 简化处理：如果陪诊员数量不足，就招募
        # 实际应该基于订单量、完成率等指标
        return {
            'count': random.randint(1, 5),
            'reason': '订单量增长，需要更多陪诊员'
        }

    def _evaluate_marketing_need(self, simulation_state: Dict[str, Any]) -> Optional[Dict]:
        """评估是否需要营销活动"""
        # 30%概率启动营销活动
        if random.random() < 0.3:
            return {
                'type': random.choice(['retention', 'acquisition', 'reactivation']),
                'intensity': random.uniform(0.5, 1.5)
            }
        return None

    def _handle_escort_churn(self, content: Dict) -> Optional[AgentMessage]:
        """处理陪诊员流失"""
        churned_count = content.get('churned_count', 0)

        # 招募新陪诊员补充
        return self.send_message(
            receiver="escort_behavior_agent",
            message_type=MessageType.EVENT,
            content={
                'event_type': 'recruit_escorts',
                'count': churned_count + 2,  # 多招募2个
                'reason': '补充流失的陪诊员'
            }
        )

    def _handle_user_churn(self, content: Dict) -> Optional[AgentMessage]:
        """处理用户流失"""
        # 启动留存营销活动
        return self.send_message(
            receiver="user_behavior_agent",
            message_type=MessageType.EVENT,
            content={
                'event_type': 'marketing_campaign',
                'campaign_type': 'retention',
                'intensity': 1.5
            }
        )

    def _handle_low_completion_rate(self, content: Dict) -> Optional[AgentMessage]:
        """处理低完成率"""
        # 招募更多陪诊员
        return self.send_message(
            receiver="escort_behavior_agent",
            message_type=MessageType.EVENT,
            content={
                'event_type': 'recruit_escorts',
                'count': 5,
                'reason': '提升完成率'
            }
        )