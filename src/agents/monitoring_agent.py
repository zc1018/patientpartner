"""
监控Agent - 实时监控业务指标
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_agent import BaseAgent, AgentMessage, AgentType, MessageType


class MonitoringAgent(BaseAgent):
    """
    监控Agent

    职责：
    1. 实时监控业务指标
    2. 发现异常和风险
    3. 触发告警
    4. 记录关键事件
    """

    def __init__(self):
        super().__init__(agent_id="monitoring_agent", agent_type=AgentType.MONITORING)

        # 告警阈值
        self.thresholds = {
            'completion_rate_min': 0.85,  # 完成率最低85%
            'user_churn_rate_max': 0.60,  # 用户流失率最高60%
            'escort_churn_rate_max': 0.25,  # 陪诊员流失率最高25%
            'avg_rating_min': 4.5,  # 平均评分最低4.5
            'complaint_rate_max': 0.01,  # 投诉率最高1%
        }

        # 事件日志
        self.state.memory['event_log'] = []
        self.state.memory['alerts'] = []

    def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理消息"""
        # 记录所有事件
        self._log_event(message)

        if message.message_type == MessageType.ALERT:
            # 记录告警
            self._log_alert(message)

        elif message.message_type == MessageType.EVENT:
            # 检查是否需要触发告警
            return self._check_thresholds(message)

        return None

    def take_action(self, simulation_state: Dict[str, Any]) -> List[AgentMessage]:
        """执行监控"""
        messages = []
        current_day = simulation_state.get('current_day', 0)

        # 每天检查业务指标
        alerts = self._check_business_metrics(simulation_state)
        messages.extend(alerts)

        # 更新指标
        self.update_metrics({
            'total_events': len(self.state.memory['event_log']),
            'total_alerts': len(self.state.memory['alerts']),
            'alerts_today': len([a for a in self.state.memory['alerts']
                                if a.get('day') == current_day])
        })

        return messages

    def _log_event(self, message: AgentMessage):
        """记录事件"""
        event = {
            'timestamp': datetime.now(),
            'sender': message.sender,
            'type': message.message_type.value,
            'content': message.content
        }
        self.state.memory['event_log'].append(event)

    def _log_alert(self, message: AgentMessage):
        """记录告警"""
        alert = {
            'timestamp': datetime.now(),
            'alert_type': message.content.get('alert_type'),
            'content': message.content,
            'priority': message.priority
        }
        self.state.memory['alerts'].append(alert)

    def _check_thresholds(self, message: AgentMessage) -> Optional[AgentMessage]:
        """检查阈值"""
        content = message.content

        # 检查完成率
        if 'completion_rate' in content:
            completion_rate = content['completion_rate']
            if completion_rate < self.thresholds['completion_rate_min']:
                return self.send_message(
                    receiver="operations_agent",
                    message_type=MessageType.ALERT,
                    content={
                        'alert_type': 'low_completion_rate',
                        'value': completion_rate,
                        'threshold': self.thresholds['completion_rate_min']
                    },
                    priority=7
                )

        # 检查平均评分
        if 'avg_rating' in content:
            avg_rating = content['avg_rating']
            if avg_rating < self.thresholds['avg_rating_min']:
                return self.send_message(
                    receiver="operations_agent",
                    message_type=MessageType.ALERT,
                    content={
                        'alert_type': 'low_rating',
                        'value': avg_rating,
                        'threshold': self.thresholds['avg_rating_min']
                    },
                    priority=6
                )

        return None

    def _check_business_metrics(self, simulation_state: Dict[str, Any]) -> List[AgentMessage]:
        """检查业务指标"""
        messages = []

        # 这里可以添加更多的业务指标检查逻辑

        return messages

    def get_recent_alerts(self, count: int = 10) -> List[Dict]:
        """获取最近的告警"""
        alerts = self.state.memory['alerts']
        return alerts[-count:] if len(alerts) > count else alerts

    def get_event_summary(self) -> Dict[str, Any]:
        """获取事件摘要"""
        events = self.state.memory['event_log']
        alerts = self.state.memory['alerts']

        return {
            'total_events': len(events),
            'total_alerts': len(alerts),
            'recent_events': events[-10:],
            'recent_alerts': alerts[-10:]
        }