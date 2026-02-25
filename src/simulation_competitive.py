"""
竞争版模拟引擎 - 包含市场竞争模拟
"""
import random
from typing import Optional
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from .config.settings import SimulationConfig
from .config.beijing_real_data import BeijingRealDataConfig
from .modules.demand_enhanced import EnhancedDemandGenerator
from .modules.supply import SupplySimulator
from .modules.matching_enhanced import EnhancedMatchingEngine
from .modules.analytics import Analytics, SimulationResult
from .modules.competition import CompetitionSimulator
from .modules.complaint_handler import ComplaintHandler
from .modules.referral_system import ReferralSystem
from .modules.event_generator import EventGenerator
from .modules.geo_matcher import GeoMatcher
from .llm.client import LLMClient


class CompetitiveSimulation:
    """竞争版沙盘模拟引擎 - 包含市场竞争"""

    def __init__(self, config: SimulationConfig, beijing_data: Optional[BeijingRealDataConfig] = None):
        self.config = config
        self.config.validate()

        # 加载北京真实数据
        self.beijing_data = beijing_data or BeijingRealDataConfig()

        # 初始化模块
        self.demand_gen = EnhancedDemandGenerator(config, self.beijing_data)
        self.supply_sim = SupplySimulator(config)
        self.matching_engine = EnhancedMatchingEngine(config, self.beijing_data)
        self.analytics = Analytics()

        # 竞争模拟器
        self.competition_sim = CompetitionSimulator(config)

        # 投诉处理器
        self.complaint_handler = ComplaintHandler()

        # NPS 口碑传播系统
        self.referral_system = ReferralSystem()

        # 地理位置匹配器
        self.geo_matcher = GeoMatcher()

        # 政策风险事件生成器
        self.event_generator = EventGenerator(pd.DataFrame())

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
        self.console.print(f"\n[bold cyan]🚀 开始竞争版模拟 - 共 {self.config.total_days} 天[/bold cyan]")
        self.console.print("[dim]包含市场竞争：医院自营40%、个人陪诊师35%、滴滴15%、其他平台10%[/dim]\n")

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
        self._print_competition_summary()

        return result

    def _simulate_day(self, day: int):
        """模拟单日运转"""
        # 1. 更新供给状态
        self.supply_sim.daily_update(day)

        # 2. 生成需求（考虑竞争）
        base_orders = self.demand_gen.generate_daily_orders(day)

        # 2.5 应用政策风险事件影响
        self.event_generator.generate_policy_risk_events(day)
        policy_modifier = self.event_generator.get_active_policy_demand_modifier(day)
        if policy_modifier < 0:
            keep_ratio = max(0.1, 1 + policy_modifier)
            base_orders = random.sample(base_orders, int(len(base_orders) * keep_ratio))

        # 根据市场份额调整订单量（订单量已基于滴滴流量生成，不需要额外调整）

        new_orders = base_orders

        # 3. 获取可用陪诊员
        available_escorts = self.supply_sim.get_available_escorts()

        # 4. 订单匹配与履约
        self.matching_engine.process_orders(new_orders, available_escorts, day)

        # 5. 计算当日平均价格和评分
        completed_orders = self.matching_engine.completed_orders
        if completed_orders:
            avg_price = sum(o.price for o in completed_orders) / len(completed_orders)
            avg_rating = sum(o.rating for o in completed_orders if o.rating) / len([o for o in completed_orders if o.rating])
        else:
            avg_price = 235
            avg_rating = 4.5

        # 6. 模拟竞争（更新市场份额）
        self.competition_sim.simulate_competition(
            day=day,
            our_orders=len(completed_orders),
            our_avg_price=avg_price,
            our_avg_rating=avg_rating
        )

        # 7. 计算流失到竞品的用户
        failed_orders = len(self.matching_engine.failed_orders)
        churned_users = self.competition_sim.calculate_user_churn_to_competitors(failed_orders)

        # 8. LLM 事件生成（可选）
        if self.llm_client and random.random() < self.config.llm_event_probability:
            self._trigger_llm_event(day)

        # 9. 将完成订单的用户加入复购池
        for order in completed_orders:
            if order.is_success and order.rating and order.rating >= 4.0:
                self.demand_gen.add_to_repurchase_pool(order.user, order.rating)

                # NPS 分类（集成 referral_system）
                is_child = getattr(order.user, 'is_child_purchase', False)
                self.referral_system.classify_user_nps(
                    order.user.id, order.rating, is_child_purchase=is_child
                )
                # 推荐者尝试推荐新用户
                self.referral_system.simulate_referral(order.user.id, day)

        # 9.5 投诉处理（集成 complaint_handler）
        for order in self.matching_engine.failed_orders:
            if order.cancel_reason and order.cancel_reason != "超时未匹配":
                self.complaint_handler.generate_complaint(
                    order_id=order.id,
                    user_id=order.user.id,
                    escort_id=order.escort.id if order.escort else None,
                    order_price=order.price,
                    day=day,
                )
        self.complaint_handler.process_daily_complaints(day, len(new_orders))

        # 9.7 负面口碑传播（差评用户）
        detractors = [
            o.user for o in self.matching_engine.completed_orders[-50:]
            if o.rating and o.rating < 3.5
        ]
        if detractors:
            self.referral_system.simulate_negative_word_of_mouth(detractors)

        # 10. 记录每日数据
        self._record_daily_metrics(day, new_orders, churned_users)

        # 11. 重置每日计数
        self.matching_engine.reset_daily_count()

    def _trigger_llm_event(self, day: int):
        """触发 LLM 事件"""
        state = {
            "day": day,
            "total_orders": len(self.matching_engine.completed_orders),
            "available_escorts": len(self.supply_sim.get_available_escorts()),
            "completion_rate": self.matching_engine.get_statistics().get("completion_rate", 0),
            "market_share": self.competition_sim.get_our_market_share(),
        }

        event = self.llm_client.generate_event(state) if self.llm_client else None
        if event:
            self.console.print(f"\n[yellow]📢 突发事件（第{day}天）：{event.get('description', '')}[/yellow]\n")

    def _record_daily_metrics(self, day: int, new_orders: list, churned_users: int):
        """记录每日指标"""
        new_orders_count = len([o for o in new_orders if not o.user.is_repurchase])
        repurchase_orders_count = len([o for o in new_orders if o.user.is_repurchase])

        demand_stats = {
            "new_orders": new_orders_count,
            "repurchase_orders": repurchase_orders_count,
            "total_orders": len(new_orders),
            "churned_users": churned_users,  # 流失到竞品的用户
        }

        supply_stats = self.supply_sim.get_statistics()
        supply_stats["daily_recruit_cost"] = 0

        matching_stats = self.matching_engine.get_statistics()
        matching_stats["completed_orders_list"] = self.matching_engine.completed_orders

        self.analytics.record_daily(day, demand_stats, supply_stats, matching_stats, self.config)

    def _generate_final_report(self) -> SimulationResult:
        """生成最终报告"""
        result = self.analytics.generate_report(self.config)

        # 添加竞争数据
        market_stats = self.competition_sim.get_market_statistics()
        result.market_share = market_stats["our_market_share"]
        result.competitors = market_stats["competitors"]

        # 高级分析
        self.break_even_analysis = self.analytics.calculate_break_even(self.config)
        self.channel_roi = self.analytics.calculate_channel_roi(self.config)
        self.lifecycle_funnel = self.analytics.calculate_user_lifecycle_funnel()

        # 投诉统计
        self.complaint_stats = self.complaint_handler.get_statistics()

        # NPS 统计
        self.referral_stats = self.referral_system.get_statistics()

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
                "market_share": result.market_share,
            }
            result.llm_report = self.llm_client.generate_analysis_report(report_data)

        return result

    def _print_progress(self, day: int):
        """打印进度信息"""
        stats = self.matching_engine.get_statistics()
        market_share = self.competition_sim.get_our_market_share()
        self.console.print(
            f"第 {day} 天 | "
            f"订单: {stats['completed_orders']} | "
            f"完成率: {stats['completion_rate']:.1%} | "
            f"市场份额: {market_share:.1%}"
        )

    def _print_summary(self, result: SimulationResult):
        """打印汇总信息"""
        self.console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
        self.console.print("[bold cyan]📊 竞争版模拟结果汇总[/bold cyan]")
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
        self.console.print(f"  商业模式健康度: {health_status}\n")

        # 市场份额
        self.console.print("[bold cyan]🏆 市场竞争[/bold cyan]")
        self.console.print(f"  我们的市场份额: {result.market_share:.1%}")

        self.console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]\n")

    def _print_competition_summary(self):
        """打印竞争总结"""
        market_stats = self.competition_sim.get_market_statistics()

        self.console.print("[bold cyan]📊 市场竞争格局[/bold cyan]\n")

        # 创建表格
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("平台", style="cyan", width=12)
        table.add_column("市场份额", justify="right", width=10)
        table.add_column("平均价格", justify="right", width=10)
        table.add_column("平均评分", justify="right", width=10)
        table.add_column("总订单数", justify="right", width=12)

        for name, data in market_stats["competitors"].items():
            table.add_row(
                name,
                f"{data['market_share']:.1%}",
                f"¥{data['avg_price']:.0f}",
                f"{data['avg_rating']:.1f}",
                f"{data['total_orders']:,}"
            )

        self.console.print(table)
        self.console.print()
