"""
数据统计与分析模块
"""
from typing import Dict, List
from dataclasses import dataclass, field
import pandas as pd
import numpy as np


@dataclass
class DailyMetrics:
    """每日指标"""
    day: int

    # 需求侧
    new_orders: int = 0
    repurchase_orders: int = 0
    total_orders: int = 0

    # 供给侧
    total_escorts: int = 0
    available_escorts: int = 0
    training_escorts: int = 0
    serving_escorts: int = 0

    # 履约
    completed_orders: int = 0
    failed_orders: int = 0
    waiting_orders: int = 0
    completion_rate: float = 0.0
    avg_rating: float = 0.0

    # 财务 - 收入
    gmv: float = 0.0  # 当日GMV（总交易额）

    # 财务 - 成本
    escort_cost: float = 0.0  # 陪诊员分成
    recruit_cost: float = 0.0  # 招募成本
    cac_cost: float = 0.0  # 获客成本（CAC）
    platform_cost: float = 0.0  # 平台抽成
    payment_fee: float = 0.0  # 支付手续费
    insurance_cost: float = 0.0  # 保险成本
    customer_service_cost: float = 0.0  # 客服成本
    daily_operation_cost: float = 0.0  # 日均运营成本
    refund_cost: float = 0.0  # 退款成本
    bad_debt_cost: float = 0.0  # 坏账成本

    # 财务 - 利润
    gross_profit: float = 0.0  # 毛利（GMV - 直接成本）
    net_profit: float = 0.0  # 净利（毛利 - 运营成本）
    margin_rate: float = 0.0  # 毛利率
    net_margin_rate: float = 0.0  # 净利率

    # 财务 - 其他指标
    total_cost: float = 0.0  # 总成本
    cac_per_order: float = 0.0  # 单均获客成本


@dataclass
class SimulationResult:
    """模拟结果"""
    config: Dict
    daily_metrics: List[DailyMetrics] = field(default_factory=list)

    # 累计指标 - 订单
    total_gmv: float = 0.0
    total_orders: int = 0
    total_completed: int = 0
    avg_completion_rate: float = 0.0

    # 累计指标 - 成本
    total_escort_cost: float = 0.0
    total_recruit_cost: float = 0.0
    total_cac_cost: float = 0.0
    total_platform_cost: float = 0.0
    total_insurance_cost: float = 0.0
    total_operation_cost: float = 0.0
    total_cost: float = 0.0

    # 累计指标 - 利润
    total_gross_profit: float = 0.0
    total_net_profit: float = 0.0
    avg_margin: float = 0.0
    avg_net_margin: float = 0.0

    # 单位经济模型（Unit Economics）
    avg_cac: float = 0.0  # 平均获客成本
    avg_order_value: float = 0.0  # 平均客单价
    avg_ltv: float = 0.0  # 平均用户生命周期价值
    ltv_cac_ratio: float = 0.0  # LTV/CAC 比率（健康指标：>3）

    # 市场竞争数据
    market_share: float = 0.0  # 我们的市场份额
    competitors: Dict = field(default_factory=dict)  # 竞品数据

    # LLM 生成的报告
    llm_report: str = ""

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame"""
        data = []
        for metric in self.daily_metrics:
            data.append(metric.__dict__)
        return pd.DataFrame(data)

    def calculate_summary(self):
        """计算汇总指标"""
        if not self.daily_metrics:
            return

        # 累计订单指标
        self.total_gmv = sum(m.gmv for m in self.daily_metrics)
        self.total_orders = sum(m.total_orders for m in self.daily_metrics)
        self.total_completed = sum(m.completed_orders for m in self.daily_metrics)

        # 完成率：完成订单数 / 总订单数
        self.avg_completion_rate = self.total_completed / self.total_orders if self.total_orders > 0 else 0

        # 累计成本指标
        self.total_escort_cost = sum(m.escort_cost for m in self.daily_metrics)
        self.total_recruit_cost = sum(m.recruit_cost for m in self.daily_metrics)
        self.total_cac_cost = sum(m.cac_cost for m in self.daily_metrics)
        self.total_platform_cost = sum(m.platform_cost for m in self.daily_metrics)
        self.total_insurance_cost = sum(m.insurance_cost for m in self.daily_metrics)
        self.total_operation_cost = sum(m.daily_operation_cost for m in self.daily_metrics)
        self.total_cost = sum(m.total_cost for m in self.daily_metrics)

        # 累计利润指标
        self.total_gross_profit = sum(m.gross_profit for m in self.daily_metrics)
        self.total_net_profit = sum(m.net_profit for m in self.daily_metrics)
        self.avg_margin = self.total_gross_profit / self.total_gmv if self.total_gmv > 0 else 0
        self.avg_net_margin = self.total_net_profit / self.total_gmv if self.total_gmv > 0 else 0

        # 单位经济模型
        new_orders = sum(m.new_orders for m in self.daily_metrics)
        self.avg_cac = self.total_cac_cost / new_orders if new_orders > 0 else 0

        # 平均客单价：基于完成订单计算
        self.avg_order_value = self.total_gmv / self.total_completed if self.total_completed > 0 else 0

        # 计算 LTV（基于留存率数据修正）
        # 首单复购率13.5%，老客户复购率30%，指定陪诊师复购率82%
        # 首单用户30天留存率45%，90天留存率36%
        # 老客90天留存率75%

        # 计算 LTV（从 config 读取留存率参数）
        first_order_retention_30d = self.config.get("first_order_retention_30d", 0.45)
        first_order_retention_90d = self.config.get("first_order_retention_90d", 0.36)
        first_order_repeat_rate = self.config.get("repurchase_prob", 0.135)

        existing_retention_90d = self.config.get("existing_retention_90d", 0.75)
        baseline_repeat_rate = self.config.get("baseline_repeat_rate", 0.30)

        # 新客平均复购次数：首单 + 30天后可能复购 + 90天后可能复购
        new_customer_repurchase_times = (
            1 +  # 首单
            first_order_retention_30d * first_order_repeat_rate +  # 第2单
            first_order_retention_90d * first_order_repeat_rate * 0.5  # 第3单及以后
        )

        # 老客平均复购次数：当前订单 + 后续复购（基于留存率和复购率）
        existing_customer_repurchase_times = (
            1 +  # 当前订单
            baseline_repeat_rate * (1 + existing_retention_90d)  # 后续复购
        )

        # 计算新客LTV和老客LTV
        self.new_customer_ltv = self.avg_order_value * new_customer_repurchase_times
        self.existing_customer_ltv = self.avg_order_value * existing_customer_repurchase_times

        # 综合平均LTV（按新客:老客 = 7:3 加权，基于业务阶段）
        new_customer_ratio = 0.7
        self.avg_ltv = (
            self.new_customer_ltv * new_customer_ratio +
            self.existing_customer_ltv * (1 - new_customer_ratio)
        )

        # LTV/CAC 比率（健康指标：>3）
        self.ltv_cac_ratio = self.avg_ltv / self.avg_cac if self.avg_cac > 0 else 0


class Analytics:
    """数据分析器"""

    def __init__(self):
        self.daily_metrics: List[DailyMetrics] = []

    def record_daily(
        self,
        day: int,
        demand_stats: Dict,
        supply_stats: Dict,
        matching_stats: Dict,
        config
    ):
        """记录每日数据"""
        # 基础数据
        completed_orders_list = matching_stats.get("completed_orders_list", [])
        new_orders_count = demand_stats.get("new_orders", 0)
        total_orders_count = demand_stats.get("total_orders", 0)

        # 计算收入
        gmv = sum(o.price for o in completed_orders_list)

        # 计算各项成本
        # 1. 陪诊员分成
        escort_cost = gmv * config.escort_commission

        # 2. 招募成本
        recruit_cost = supply_stats.get("daily_recruit_cost", 0)

        # 3. 获客成本（CAC）- 只对新订单计算
        # 简化处理：假设所有新订单平均分配到各渠道
        cac_cost = new_orders_count * config.cac_didi_app

        # 4. 平台抽成
        platform_cost = gmv * config.platform_commission

        # 5. 支付手续费
        payment_fee = gmv * config.payment_fee_rate

        # 6. 保险成本
        insurance_cost = len(completed_orders_list) * (
            config.escort_insurance_per_order + config.user_insurance_per_order
        )

        # 7. 客服成本
        customer_service_cost = total_orders_count * config.customer_service_cost_per_order

        # 8. 日均运营成本（月度成本 / 30）
        daily_operation_cost = (
            config.monthly_staff_cost +
            config.monthly_office_cost +
            config.monthly_tech_cost +
            config.monthly_marketing_cost
        ) / 30.0

        # 9. 退款成本
        refund_cost = gmv * config.refund_rate

        # 10. 坏账成本
        bad_debt_cost = gmv * config.bad_debt_rate

        # 总成本
        total_cost = (
            escort_cost +
            recruit_cost +
            cac_cost +
            platform_cost +
            payment_fee +
            insurance_cost +
            customer_service_cost +
            daily_operation_cost +
            refund_cost +
            bad_debt_cost
        )

        # 计算利润
        # 毛利 = GMV - 直接成本（陪诊员分成 + 平台抽成 + 支付费）
        gross_profit = gmv - escort_cost - platform_cost - payment_fee

        # 净利 = GMV - 总成本
        net_profit = gmv - total_cost

        # 利润率
        margin_rate = gross_profit / gmv if gmv > 0 else 0
        net_margin_rate = net_profit / gmv if gmv > 0 else 0

        # 单均获客成本
        cac_per_order = cac_cost / new_orders_count if new_orders_count > 0 else 0

        metric = DailyMetrics(
            day=day,
            new_orders=new_orders_count,
            repurchase_orders=demand_stats.get("repurchase_orders", 0),
            total_orders=total_orders_count,
            total_escorts=supply_stats.get("total_escorts", 0),
            available_escorts=supply_stats.get("available_escorts", 0),
            training_escorts=supply_stats.get("by_status", {}).get("培训中", 0),
            serving_escorts=supply_stats.get("by_status", {}).get("服务中", 0),
            completed_orders=matching_stats.get("completed_orders", 0),
            failed_orders=matching_stats.get("failed_orders", 0),
            waiting_orders=matching_stats.get("waiting_orders", 0),
            completion_rate=matching_stats.get("completion_rate", 0),
            avg_rating=matching_stats.get("avg_rating", 0),
            gmv=gmv,
            escort_cost=escort_cost,
            recruit_cost=recruit_cost,
            cac_cost=cac_cost,
            platform_cost=platform_cost,
            payment_fee=payment_fee,
            insurance_cost=insurance_cost,
            customer_service_cost=customer_service_cost,
            daily_operation_cost=daily_operation_cost,
            refund_cost=refund_cost,
            bad_debt_cost=bad_debt_cost,
            total_cost=total_cost,
            gross_profit=gross_profit,
            net_profit=net_profit,
            margin_rate=margin_rate,
            net_margin_rate=net_margin_rate,
            cac_per_order=cac_per_order,
        )

        self.daily_metrics.append(metric)

    def generate_report(self, config) -> SimulationResult:
        """生成模拟报告"""
        result = SimulationResult(
            config=config.__dict__,
            daily_metrics=self.daily_metrics,
        )
        result.calculate_summary()
        return result

    def calculate_break_even(self, config) -> Dict:
        """计算盈亏平衡点

        盈亏平衡订单量 = 固定成本 / (客单价 × 毛利率 - 变动成本)
        """
        if not self.daily_metrics:
            return {"break_even_orders": 0, "break_even_weeks": 0}

        # 计算平均客单价和毛利率
        total_gmv = sum(m.gmv for m in self.daily_metrics)
        total_orders = sum(m.completed_orders for m in self.daily_metrics)

        if total_orders == 0:
            return {"break_even_orders": 0, "break_even_weeks": 0}

        avg_order_value = total_gmv / total_orders

        # 固定成本（周均）- 招募成本 + 运营成本
        weekly_fixed_cost = 0.0
        for m in self.daily_metrics:
            weekly_fixed_cost += m.daily_operation_cost
        weekly_fixed_cost /= max(1, len(self.daily_metrics) / 7)

        # 变动成本（每单）- 陪诊员分成 + 支付手续费 + 坏账
        avg_variable_cost_per_order = 0.0
        for m in self.daily_metrics:
            if m.completed_orders > 0:
                avg_variable_cost_per_order = (
                    m.escort_cost / m.completed_orders +
                    m.payment_fee / m.completed_orders +
                    m.bad_debt_cost / m.completed_orders
                )

        # 毛利率（从config读取）
        gross_margin = getattr(config, 'gross_margin_rate', 0.30)
        contribution_per_order = avg_order_value * gross_margin - avg_variable_cost_per_order

        if contribution_per_order <= 0:
            return {
                "break_even_orders": float('inf'),
                "break_even_weeks": float('inf'),
                "avg_order_value": avg_order_value,
                "weekly_fixed_cost": weekly_fixed_cost,
                "contribution_per_order": contribution_per_order,
            }

        break_even_orders = weekly_fixed_cost / contribution_per_order

        # 假设每周订单量
        avg_weekly_orders = total_orders / max(1, len(self.daily_metrics) / 7)
        break_even_weeks = break_even_orders / avg_weekly_orders if avg_weekly_orders > 0 else float('inf')

        return {
            "break_even_orders": int(break_even_orders),
            "break_even_weeks": round(break_even_weeks, 1),
            "avg_order_value": avg_order_value,
            "weekly_fixed_cost": weekly_fixed_cost,
            "contribution_per_order": contribution_per_order,
        }

    def calculate_channel_roi(self, config) -> Dict:
        """计算渠道ROI分析

        使用 config 中的 channel_cac 配置来计算各渠道的 ROI
        """
        # 从 config 获取渠道CAC配置
        channel_cac_config = getattr(config, 'channel_cac', {
            "default": 50,
            "online_ad": 80,
            "referral": 20,
            "hospital_partner": 150,
            "offline_promotion": 60,
        })

        # 按渠道统计（需要在 record_daily 时传入渠道信息）
        channel_stats: Dict[str, Dict] = {}

        for m in self.daily_metrics:
            # 简化处理：使用 CAC 成本作为渠道指标
            if m.cac_per_order > 0:
                channel = "default"
                if channel not in channel_stats:
                    channel_stats[channel] = {"gmv": 0, "cac_cost": 0, "orders": 0}

                channel_stats[channel]["gmv"] += m.gmv
                channel_stats[channel]["cac_cost"] += m.cac_cost
                channel_stats[channel]["orders"] += m.completed_orders

        # 计算各渠道 ROI（使用 config 中的 channel_cac）
        channel_roi = {}
        for channel, stats in channel_stats.items():
            # 使用配置中的CAC值
            cac_value = channel_cac_config.get(channel, channel_cac_config.get("default", 50))
            cac_cost = cac_value * stats["orders"]
            roi = stats["gmv"] / cac_cost if cac_cost > 0 else 0
            channel_roi[channel] = {
                "gmv": stats["gmv"],
                "cac_cost": cac_cost,
                "orders": stats["orders"],
                "roi": round(roi, 2),
                "cac_per_order": cac_value,
            }

        return channel_roi

    def calculate_user_lifecycle_funnel(self) -> Dict:
        """计算用户生命周期漏斗分析"""
        # 简化实现：基于流失率估算
        funnel = {
            "new_users": 0,
            "at_risk": 0,
            "silent": 0,
            "churned": 0,
            "reactivated": 0,
        }

        for m in self.daily_metrics:
            # 估算新用户转化
            funnel["new_users"] += m.new_orders
            # 假设流失率
            funnel["churned"] += int(m.new_orders * 0.55 * (len(self.daily_metrics) / 30))

        funnel["at_risk"] = int(funnel["new_users"] * 0.15)
        funnel["silent"] = int(funnel["new_users"] * 0.10)

        return funnel
