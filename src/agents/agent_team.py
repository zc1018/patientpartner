"""
Agent Team 系统 - 主入口

这个系统通过多个智能agent协作，让沙箱环境更接近现实情况。

Agent架构：
1. UserBehaviorAgent - 模拟用户行为（下单、复购、流失）
2. EscortBehaviorAgent - 模拟陪诊员行为（接单、服务、流失）
3. MarketDynamicsAgent - 模拟市场环境变化（季节性、突发事件）
4. OperationsAgent - 模拟运营决策（营销、招募、价格调整）
5. CompetitionAgent - 模拟竞争对手行为
6. MonitoringAgent - 实时监控业务指标和告警
7. ReportingAgent - 自动生成报告
8. CoordinatorAgent - 协调所有agent的工作

使用方法：
```python
from src.agents.agent_team import AgentTeam

# 创建agent team
team = AgentTeam()

# 运行模拟
team.run_simulation(days=365, verbose=True)

# 获取模拟结果
summary = team.get_summary()
print(summary)
```
"""

from typing import Dict, Any

# 尝试导入rich，如果失败则使用简单的print
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from .user_behavior_agent import UserBehaviorAgent
from .escort_behavior_agent import EscortBehaviorAgent
from .market_dynamics_agent import MarketDynamicsAgent
from .operations_agent import OperationsAgent
from .competition_agent import CompetitionAgent
from .monitoring_agent import MonitoringAgent
from .reporting_agent import ReportingAgent
from .coordinator_agent import CoordinatorAgent


class SimpleConsole:
    """简单的控制台输出（当rich不可用时）"""
    def print(self, *args, **kwargs):
        print(*args)


class AgentTeam:
    """Agent Team 系统"""

    def __init__(self):
        if HAS_RICH:
            self.console = Console()
        else:
            self.console = SimpleConsole()

        # 创建所有agent
        self.agents = {
            'user_behavior_agent': UserBehaviorAgent(),
            'escort_behavior_agent': EscortBehaviorAgent(),
            'market_dynamics_agent': MarketDynamicsAgent(),
            'operations_agent': OperationsAgent(),
            'competition_agent': CompetitionAgent(),
            'monitoring_agent': MonitoringAgent(),
            'reporting_agent': ReportingAgent(),
        }

        # 创建协调器
        self.coordinator = CoordinatorAgent(self.agents)

        self.console.print("\n✓ Agent Team 初始化完成")
        self.console.print(f"共创建 {len(self.agents)} 个agent\n")

    def run_simulation(self, days: int = 365, verbose: bool = True):
        """运行模拟"""
        self.coordinator.simulation_state['total_days'] = days
        self.coordinator.simulation_state['is_running'] = True

        self.console.print(f"\n开始运行Agent Team模拟 - 共 {days} 天\n")

        if HAS_RICH:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]模拟进行中...",
                    total=days
                )

                for day in range(days):
                    # 运行一个模拟步骤
                    step_result = self.coordinator.run_simulation_step()

                    progress.update(task, advance=1)

                    if verbose and day % 30 == 0:
                        self._print_progress(day, step_result)
        else:
            # 简单模式（无rich）
            for day in range(days):
                step_result = self.coordinator.run_simulation_step()

                if verbose and day % 10 == 0:
                    print(f"进度: {day}/{days} 天 ({day/days*100:.0f}%)")
                    self._print_progress(day, step_result)

        self.coordinator.simulation_state['is_running'] = False

        self.console.print("\n✓ 模拟完成！\n")
        self._print_final_summary()

    def _print_progress(self, day: int, step_result: Dict):
        """打印进度"""
        self.console.print(f"\n第 {day} 天进度：")

        for agent_id, state in step_result['agent_states'].items():
            metrics = state.metrics
            if metrics:
                self.console.print(f"  {state.agent_type.value}: {metrics}")

    def _print_final_summary(self):
        """打印最终摘要"""
        summary = self.coordinator.get_simulation_summary()

        self.console.print("\n" + "="*60)
        self.console.print("📊 Agent Team 模拟结果汇总")
        self.console.print("="*60 + "\n")

        self.console.print(f"模拟天数： {summary['current_day']} 天\n")

        self.console.print("📋 各Agent状态：")
        for agent_id, agent_info in summary['agents'].items():
            self.console.print(f"\n  {agent_info['type']}")
            self.console.print(f"    状态: {'✓ 活跃' if agent_info['is_active'] else '✗ 停止'}")
            if agent_info['metrics']:
                self.console.print(f"    指标: {agent_info['metrics']}")

        # 打印监控摘要
        monitoring_agent = self.agents.get('monitoring_agent')
        if monitoring_agent:
            event_summary = monitoring_agent.get_event_summary()
            self.console.print(f"\n⚠️  告警统计：")
            self.console.print(f"  总事件数: {event_summary['total_events']}")
            self.console.print(f"  总告警数: {event_summary['total_alerts']}")

        # 打印报告摘要
        reporting_agent = self.agents.get('reporting_agent')
        if reporting_agent:
            reports = reporting_agent.get_all_reports()
            self.console.print(f"\n📄 报告统计：")
            self.console.print(f"  生成报告数: {len(reports)}")
            weekly_reports = [r for r in reports if r['type'] == 'weekly']
            monthly_reports = [r for r in reports if r['type'] == 'monthly']
            self.console.print(f"  周报: {len(weekly_reports)} 份")
            self.console.print(f"  月报: {len(monthly_reports)} 份")

        self.console.print("\n" + "="*60 + "\n")

    def get_summary(self) -> Dict[str, Any]:
        """获取模拟摘要"""
        return self.coordinator.get_simulation_summary()

    def get_agent(self, agent_id: str):
        """获取指定agent"""
        return self.agents.get(agent_id)

    def get_monitoring_events(self, count: int = 10):
        """获取监控事件"""
        monitoring_agent = self.agents.get('monitoring_agent')
        if monitoring_agent:
            return monitoring_agent.get_recent_alerts(count)
        return []

    def get_reports(self):
        """获取所有报告"""
        reporting_agent = self.agents.get('reporting_agent')
        if reporting_agent:
            return reporting_agent.get_all_reports()
        return []
