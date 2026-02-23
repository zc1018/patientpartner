"""
报告Agent - 自动生成报告
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_agent import BaseAgent, AgentMessage, AgentType, MessageType


class ReportingAgent(BaseAgent):
    """
    报告Agent

    职责：
    1. 自动生成周报、月报
    2. 分析业务趋势
    3. 提供决策建议
    """

    def __init__(self):
        super().__init__(agent_id="reporting_agent", agent_type=AgentType.REPORTING)

        # 报告历史
        self.state.memory['reports'] = []

    def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理消息"""
        if message.message_type == MessageType.REQUEST:
            report_type = message.content.get('report_type')

            if report_type == 'weekly':
                return self._generate_weekly_report(message.content)
            elif report_type == 'monthly':
                return self._generate_monthly_report(message.content)

        return None

    def take_action(self, simulation_state: Dict[str, Any]) -> List[AgentMessage]:
        """报告agent不主动执行action"""
        return []

    def _generate_weekly_report(self, content: Dict) -> Optional[AgentMessage]:
        """生成周报"""
        day = content.get('day', 0)
        week_number = day // 7

        report = {
            'type': 'weekly',
            'week': week_number,
            'day': day,
            'timestamp': datetime.now(),
            'content': f"第{week_number}周运营周报"
        }

        self.state.memory['reports'].append(report)

        return self.send_message(
            receiver="monitoring_agent",
            message_type=MessageType.REPORT,
            content={
                'report_type': 'weekly',
                'report': report
            }
        )

    def _generate_monthly_report(self, content: Dict) -> Optional[AgentMessage]:
        """生成月报"""
        day = content.get('day', 0)
        month_number = day // 30

        report = {
            'type': 'monthly',
            'month': month_number,
            'day': day,
            'timestamp': datetime.now(),
            'content': f"第{month_number}个月运营月报"
        }

        self.state.memory['reports'].append(report)

        return self.send_message(
            receiver="monitoring_agent",
            message_type=MessageType.REPORT,
            content={
                'report_type': 'monthly',
                'report': report
            }
        )

    def get_all_reports(self) -> List[Dict]:
        """获取所有报告"""
        return self.state.memory['reports']
