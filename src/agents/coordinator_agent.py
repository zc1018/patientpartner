"""
协调器Agent - 协调所有agent的工作
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_agent import BaseAgent, AgentMessage, AgentType, MessageType


class CoordinatorAgent(BaseAgent):
    """
    协调器Agent

    职责：
    1. 协调所有agent的工作
    2. 管理agent之间的消息传递
    3. 控制模拟的节奏和状态
    4. 收集和汇总各agent的数据
    5. 触发定时任务（如报告生成）
    """

    def __init__(self, agents: Dict[str, BaseAgent]):
        super().__init__(agent_id="coordinator", agent_type=AgentType.COORDINATOR)
        self.agents = agents
        self.simulation_state = {
            'current_day': 0,
            'total_days': 365,
            'is_running': False,
            'market_size': 10000,
            'exposure_rate': 0.03,
            'conversion_rate': 0.15,
        }

    def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理消息并路由到目标agent"""
        receiver = message.receiver

        if receiver == "coordinator":
            # 处理发给协调器的消息
            return self._handle_coordinator_message(message)
        elif receiver in self.agents:
            # 转发给目标agent
            self.agents[receiver].receive_message(message)
        elif receiver == "":
            # 广播消息
            for agent in self.agents.values():
                agent.receive_message(message)

        return None

    def take_action(self, simulation_state: Dict[str, Any]) -> List[AgentMessage]:
        """协调器不主动执行action，而是协调其他agent"""
        return []

    def run_simulation_step(self) -> Dict[str, Any]:
        """运行一个模拟步骤（一天）"""
        current_day = self.simulation_state['current_day']

        # 1. 让所有agent执行action
        all_messages = []
        for agent_id, agent in self.agents.items():
            messages = agent.take_action(self.simulation_state)
            all_messages.extend(messages)

        # 2. 分发消息
        for message in all_messages:
            self.process_message(message)

        # 3. 让所有agent处理消息队列
        for agent in self.agents.values():
            responses = agent.process_queue()
            for response in responses:
                self.process_message(response)

        # 4. 收集各agent的状态
        agent_states = {
            agent_id: agent.get_state()
            for agent_id, agent in self.agents.items()
        }

        # 5. 更新模拟状态
        self.simulation_state['current_day'] += 1

        # 6. 定时任务
        if current_day % 7 == 0:  # 每周
            self._trigger_weekly_report()
        if current_day % 30 == 0:  # 每月
            self._trigger_monthly_report()

        return {
            'day': current_day,
            'agent_states': agent_states,
            'messages_count': len(all_messages)
        }

    def _handle_coordinator_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理发给协调器的消息"""
        event_type = message.content.get('event_type')

        if event_type == 'new_orders':
            # 新订单，触发匹配
            orders = message.content.get('orders', [])
            self._trigger_order_matching(orders)

        elif event_type == 'repurchase_orders':
            # 复购订单，触发匹配
            orders = message.content.get('orders', [])
            self._trigger_order_matching(orders)

        return None

    def _trigger_order_matching(self, orders: List[Dict]):
        """触发订单匹配"""
        # 发送消息给匹配系统（这里简化处理）
        for order in orders:
            # 选择陪诊员
            escort_id = self._select_escort(order)
            if escort_id:
                # 通知陪诊员agent
                self.agents['escort_behavior_agent'].receive_message(
                    AgentMessage(
                        sender="coordinator",
                        receiver="escort_behavior_agent",
                        message_type=MessageType.EVENT,
                        content={
                            'event_type': 'order_assigned',
                            'order_id': order.get('user_id') + '_order',
                            'escort_id': escort_id
                        }
                    )
                )

    def _select_escort(self, order: Dict) -> Optional[str]:
        """选择陪诊员（简化版）"""
        escort_agent = self.agents.get('escort_behavior_agent')
        if not escort_agent:
            return None

        active_escorts = escort_agent.state.memory.get('active_escorts', [])
        if not active_escorts:
            return None

        # 如果是指定陪诊师订单
        if order.get('is_designated') and order.get('designated_escort'):
            return order.get('designated_escort')

        # 否则随机选择
        import random
        return random.choice(active_escorts)

    def _trigger_weekly_report(self):
        """触发周报生成"""
        if 'reporting_agent' in self.agents:
            self.agents['reporting_agent'].receive_message(
                AgentMessage(
                    sender="coordinator",
                    receiver="reporting_agent",
                    message_type=MessageType.REQUEST,
                    content={
                        'report_type': 'weekly',
                        'day': self.simulation_state['current_day']
                    },
                    priority=8
                )
            )

    def _trigger_monthly_report(self):
        """触发月报生成"""
        if 'reporting_agent' in self.agents:
            self.agents['reporting_agent'].receive_message(
                AgentMessage(
                    sender="coordinator",
                    receiver="reporting_agent",
                    message_type=MessageType.REQUEST,
                    content={
                        'report_type': 'monthly',
                        'day': self.simulation_state['current_day']
                    },
                    priority=9
                )
            )

    def get_simulation_summary(self) -> Dict[str, Any]:
        """获取模拟摘要"""
        summary = {
            'current_day': self.simulation_state['current_day'],
            'agents': {}
        }

        for agent_id, agent in self.agents.items():
            summary['agents'][agent_id] = {
                'type': agent.state.agent_type.value,
                'is_active': agent.state.is_active,
                'metrics': agent.state.metrics
            }

        return summary