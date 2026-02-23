"""
增强版模拟引擎 - 使用真实数据
"""
import random
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .config.settings import SimulationConfig
from .config.beijing_real_data import BeijingRealDataConfig
from .modules.demand_enhanced import EnhancedDemandGenerator
from .modules.supply import SupplySimulator
from .modules.matching_enhanced import EnhancedMatchingEngine
from .modules.analytics import Analytics, SimulationResult
from .llm.client import LLMClient


class EnhancedSimulation:
    """增强版沙盘模拟引擎 - 基于真实数据"""

    def __init__(self, config: SimulationConfig, beijing_data: BeijingRealDataConfig = None):
        self.config = config
        self.config.validate()

        # 加载北京真实数据
        self.beijing_data = beijing_data or BeijingRealDataConfig()

        # 初始化模块
        self.demand_gen = EnhancedDemandGenerator(config, self.beijing_data)
        self.supply_sim = SupplySimulator(config)
        self.matching_engine = EnhancedMatchingEngine(config, self.beijing_data)
        self.analytics = Analytics()

        # LLM 客户端（可选）
        self.llm_client: Optional[LLMClient] = None
        if config.enable_llm:
            try:
                self.llm_client = LLMClient(
                    provider=config.llm_provider,
                    model=config.llm_model
                )
            except Exception as e:
                print(f"LLM 初始化失败: {e}，将禁用 LLM 功能")
                self.llm_client = None

        self.console = Console()

    def run(self, verbose: bool = True) -> SimulationResult:
        """运行模拟"""
        self.console.print(f"\n[bold cyan]🚀 开始增强版模拟 - 共 {self.config.total_days} 天[/bold cyan]")
        self.console.print("[dim]使用北京真实数据：医院、疾病分布、区域付费能力、多渠道获客[/dim]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
        ) as progress:
            task = progress.add_task(
                "[cyan]模拟进行中...",
                total=self.config.total_days
            )

            for day in range(self.config.total_days):
                self._simulate_day(day)
                progress.update(task, advance=1)

                if verbose and day % 10 == 0:
                    self._print_progress(day)

        # 生成最终报告
        result = self._generate_final_report()

        self.console.print("\n[bold green]✓ 模拟完成！[/bold green]\n")
        self._print_summary(result)

        return result

    def _simulate_day(self, day: int):
        """模拟单日运转"""
        # 1. 更新供给状态
        self.supply_sim.daily_update(day)

        # 2. 生成需求（使用增强版生成器）
        new_orders = self.demand_gen.generate_daily_orders(day)

        # 3. 获取可用陪诊员
        available_escorts = self.supply_sim.get_available_escorts()

        # 4. 订单匹配与履约
        self.matching_engine.process_orders(new_orders, available_escorts, day)

        # 5. LLM 事件生成（可选）
        if self.llm_client and random.random() < self.config.llm_event_probability:
            self._trigger_llm_event(day)

        # 6. 将完成订单的用户加入复购池
        for order in self.matching_engine.completed_orders:
            if order.is_success and order.rating and order.rating >= 4.0:
                self.demand_gen.add_to_repurchase_pool(order.user, order.rating)

        # 7. 记录每日数据（使用增强版统计）
        self._record_daily_metrics(day, new_orders)

        # 8. 重置每日计数
        self.matching_engine.reset_daily_count()

    def _trigger_llm_event(self, day: int):
        """触发 LLM 事件"""
        state = {
            "day": day,
            "total_orders": len(self.matching_engine.completed_orders),
            "available_escorts": len(self.supply_sim.get_available_escorts()),
            "completion_rate": self.matching_engine.get_statistics().get("completion_rate", 0),
        }

        event = self.llm_client.generate_event(state)
        if event:
            self.console.print(f"\n[yellow]📢 突发事件（第{day}天）：{event.get('description', '')}[/yellow]\n")

    def _record_daily_metrics(self, day: int, new_orders: list):
        """记录每日指标 - 增强版"""
        # 统计新订单和复购订单
        new_orders_count = len([o for o in new_orders if not o.user.is_repurchase])
        repurchase_orders_count = len([o for o in new_orders if o.user.is_repurchase])

        # 统计各渠道订单数
        channel_stats = {}
        for order in new_orders:
            channel = getattr(order, 'acquisition_channel', '未知')
            channel_stats[channel] = channel_stats.get(channel, 0) + 1

        demand_stats = {
            "new_orders": new_orders_count,
            "repurchase_orders": repurchase_orders_count,
            "total_orders": len(new_orders),
            "channel_stats": channel_stats,
        }

        supply_stats = self.supply_sim.get_statistics()
        supply_stats["daily_recruit_cost"] = 0  # 简化处理

        matching_stats = self.matching_engine.get_statistics()
        matching_stats["completed_orders_list"] = self.matching_engine.completed_orders

        self.analytics.record_daily(day, demand_stats, supply_stats, matching_stats, self.config)

    def _generate_final_report(self) -> SimulationResult:
        """生成最终报告"""
        result = self.analytics.generate_report(self.config)

        # 使用 LLM 生成分析报告
        if self.llm_client:
            self.console.print("\n[cyan]正在生成 AI 分析报告...[/cyan]")
            report_data = {
                "total_days": self.config.total_days,
                "total_gmv": result.total_gmv,
                "total_orders": result.total_orders,
                "total_completed": result.total_completed,
                "avg_completion_rate": result.avg_completion_rate,
                "total_gross_profit": result.total_gross_profit,
                "total_net_profit": result.total_net_profit,
                "avg_margin": result.avg_margin,
                "avg_net_margin": result.avg_net_margin,
                "ltv_cac_ratio": result.ltv_cac_ratio,
            }
            result.llm_report = self.llm_client.generate_analysis_report(report_data)

        return result

    def _print_progress(self, day: int):
        """打印进度信息"""
        stats = self.matching_engine.get_statistics()
        self.console.print(
            f"第 {day} 天 | "
            f"订单: {stats['completed_orders']} | "
            f"完成率: {stats['completion_rate']:.1%}"
        )

    def _print_summary(self, result: SimulationResult):
        """打印汇总信息"""
        self.console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
        self.console.print("[bold cyan]📊 增强版模拟结果汇总[/bold cyan]")
        self.console.print("[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")

        # 订单指标
        self.console.print("[bold yellow]📦 订单指标[/bold yellow]")
        self.console.print(f"  总订单数: {result.total_orders:,}")
        self.console.print(f"  完成订单数: {result.total_completed:,}")
        self.console.print(f"  平均完成率: {result.avg_completion_rate:.1%}")
        self.console.print(f"  平均客单价: ¥{result.avg_order_value:.2f}\n")

        # 收入指标
        self.console.print("[bold green]💰 收入指标[/bold green]")
        self.console.print(f"  总 GMV: ¥{result.total_gmv:,.2f}\n")

        # 成本指标
        self.console.print("[bold red]💸 成本指标[/bold red]")
        self.console.print(f"  陪诊员分成: ¥{result.total_escort_cost:,.2f}")
        self.console.print(f"  获客成本(CAC): ¥{result.total_cac_cost:,.2f}")
        self.console.print(f"  平台抽成: ¥{result.total_platform_cost:,.2f}")
        self.console.print(f"  保险成本: ¥{result.total_insurance_cost:,.2f}")
        self.console.print(f"  运营成本: ¥{result.total_operation_cost:,.2f}")
        self.console.print(f"  招募成本: ¥{result.total_recruit_cost:,.2f}")
        self.console.print(f"  [bold]总成本: ¥{result.total_cost:,.2f}[/bold]\n")

        # 利润指标
        self.console.print("[bold magenta]📈 利润指标[/bold magenta]")
        self.console.print(f"  毛利: ¥{result.total_gross_profit:,.2f}")
        self.console.print(f"  毛利率: {result.avg_margin:.1%}")
        self.console.print(f"  净利: ¥{result.total_net_profit:,.2f}")
        self.console.print(f"  净利率: {result.avg_net_margin:.1%}\n")

        # 单位经济模型
        self.console.print("[bold blue]🎯 单位经济模型[/bold blue]")
        self.console.print(f"  平均获客成本(CAC): ¥{result.avg_cac:.2f}")
        self.console.print(f"  平均用户价值(LTV): ¥{result.avg_ltv:.2f}")
        self.console.print(f"  LTV/CAC 比率: {result.ltv_cac_ratio:.2f}")

        # 健康度评估
        if result.ltv_cac_ratio > 3:
            health_status = "[bold green]✓ 健康[/bold green]"
        elif result.ltv_cac_ratio > 1:
            health_status = "[bold yellow]⚠ 需改进[/bold yellow]"
        else:
            health_status = "[bold red]✗ 不健康[/bold red]"
        self.console.print(f"  商业模式健康度: {health_status}")

        self.console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")
