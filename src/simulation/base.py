"""
模拟引擎基类 - 使用模板方法模式
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import random
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from ..config.settings import SimulationConfig
from ..modules.analytics import Analytics, SimulationResult


class BaseSimulation(ABC):
    """模拟引擎抽象基类 - 定义模板方法"""

    def __init__(self, config: SimulationConfig):
        self.config = config

        # 初始化分析模块（所有子类共用）
        self.analytics = Analytics()

        # 初始化控制台
        self.console = Console()

        # 子类特定的模块初始化
        self._init_modules()

    @abstractmethod
    def _init_modules(self):
        """初始化业务模块 - 子类必须实现"""
        pass

    def run(self, verbose: bool = True) -> SimulationResult:
        """
        模板方法: 运行模拟的主流程
        子类不应覆盖此方法，而是通过钩子方法扩展
        """
        # 钩子: 模拟开始前
        self._before_simulation()

        # 显示开始信息
        self._print_start_message()

        # 主循环
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
                # 模拟单日
                self._simulate_day(day)
                progress.update(task, advance=1)

                # 定期打印进度
                if verbose and day % 10 == 0:
                    self._print_progress(day)

                # 钩子: 每日模拟后
                self._after_day_simulation(day)

        # 生成报告
        result = self._generate_final_report()

        # 钩子: 模拟结束后
        self._after_simulation(result)

        # 打印汇总
        self.console.print("\n[bold green]✓ 模拟完成！[/bold green]\n")
        self._print_summary(result)

        return result

    def _simulate_day(self, day: int):
        """
        模板方法: 单日模拟流程
        定义标准8步流程，子类可通过钩子扩展
        """
        # 步骤1: 更新供给状态
        self._update_supply(day)

        # 步骤2: 生成需求
        new_orders = self._generate_demand(day)

        # 步骤3: 获取可用陪诊员
        available_escorts = self._get_available_escorts()

        # 步骤4: 订单匹配与履约
        self._process_matching(new_orders, available_escorts, day)

        # 步骤5: 处理LLM事件（钩子）
        self._handle_llm_events(day)

        # 步骤6: 更新复购池
        self._update_repurchase_pool()

        # 步骤7: 记录每日指标
        self._record_daily_metrics(day, new_orders)

        # 步骤8: 重置每日状态
        self._reset_daily_state()

    @abstractmethod
    def _update_supply(self, day: int):
        """步骤1: 更新供给状态"""
        pass

    @abstractmethod
    def _generate_demand(self, day: int) -> List[Any]:
        """步骤2: 生成需求，返回订单列表"""
        pass

    @abstractmethod
    def _get_available_escorts(self) -> List[Any]:
        """步骤3: 获取可用陪诊员列表"""
        pass

    @abstractmethod
    def _process_matching(self, orders: List[Any], escorts: List[Any], day: int):
        """步骤4: 处理订单匹配与履约"""
        pass

    @abstractmethod
    def _update_repurchase_pool(self):
        """步骤6: 更新复购池"""
        pass

    @abstractmethod
    def _record_daily_metrics(self, day: int, new_orders: List[Any]):
        """步骤7: 记录每日指标"""
        pass

    @abstractmethod
    def _reset_daily_state(self):
        """步骤8: 重置每日状态"""
        pass

    def _before_simulation(self):
        """钩子: 模拟开始前的初始化"""
        pass

    def _after_day_simulation(self, day: int):
        """钩子: 每日模拟后的处理"""
        pass

    def _after_simulation(self, result: SimulationResult):
        """钩子: 模拟结束后的处理"""
        pass

    def _handle_llm_events(self, day: int):
        """钩子: 处理LLM事件"""
        pass

    def _generate_final_report(self) -> SimulationResult:
        """生成最终报告"""
        result = self.analytics.generate_report(self.config)
        return result

    def _print_start_message(self):
        """打印开始信息"""
        self.console.print(
            f"\n[bold cyan]开始模拟 - 共 {self.config.total_days} 天[/bold cyan]\n"
        )

    def _print_progress(self, day: int):
        """打印进度信息 - 子类可覆盖"""
        self.console.print(f"第 {day} 天 | 模拟进行中...")

    def _print_summary(self, result: SimulationResult):
        """打印汇总信息 - 子类可覆盖"""
        self._print_financial_summary(result)
        self._print_unit_economics(result)

    def _print_financial_summary(self, result: SimulationResult):
        """打印财务汇总"""
        self.console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
        self.console.print("[bold cyan]📊 模拟结果汇总[/bold cyan]")
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

    def _print_unit_economics(self, result: SimulationResult):
        """打印单位经济模型"""
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
