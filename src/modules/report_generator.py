"""
业务报告生成器 - 周报和月报
"""
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
from dataclasses import dataclass, field

from ..modules.analytics import SimulationResult
from ..modules.event_generator import EventGenerator, BusinessEvent


@dataclass
class WeeklyReport:
    """周报数据"""
    week_number: int
    start_day: int
    end_day: int

    # 核心指标
    total_orders: int
    completed_orders: int
    completion_rate: float
    gmv: float
    gross_profit: float
    margin_rate: float

    # 供给指标
    total_escorts: int
    available_escorts: int
    new_escorts: int
    churned_escorts: int

    # 增长指标
    order_growth: float
    gmv_growth: float

    # 业务事件
    events: List[BusinessEvent] = field(default_factory=list)

    # 问题和建议
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class MonthlyReport:
    """月报数据"""
    month_number: int
    start_day: int
    end_day: int

    # 核心指标
    total_orders: int
    completed_orders: int
    completion_rate: float
    gmv: float
    gross_profit: float
    margin_rate: float

    # 供给指标
    total_escorts: int
    avg_escorts_per_day: float
    new_escorts: int
    churned_escorts: int
    retention_rate: float

    # 用户指标
    new_users: int
    repurchase_users: int
    repurchase_rate: float

    # 增长指标
    order_growth: float
    gmv_growth: float

    # 周报列表
    weekly_reports: List[WeeklyReport] = field(default_factory=list)

    # 业务事件（月度重大事件）
    events: List[BusinessEvent] = field(default_factory=list)

    # 问题和建议
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class ReportGenerator:
    """报告生成器"""

    def __init__(self, result: SimulationResult):
        self.result = result
        self.df = result.to_dataframe()
        self.event_generator = EventGenerator(self.df)

    def generate_weekly_reports(self) -> List[WeeklyReport]:
        """生成所有周报"""
        reports = []
        total_days = len(self.df)
        weeks = (total_days + 6) // 7  # 向上取整

        for week in range(weeks):
            start_day = week * 7
            end_day = min((week + 1) * 7 - 1, total_days - 1)

            report = self._generate_weekly_report(week + 1, start_day, end_day)
            reports.append(report)

        return reports

    def _generate_weekly_report(self, week_number: int, start_day: int, end_day: int) -> WeeklyReport:
        """生成单周报告"""
        week_data = self.df.iloc[start_day:end_day + 1]

        # 核心指标
        total_orders = week_data['total_orders'].sum()
        completed_orders = week_data['completed_orders'].sum()
        completion_rate = completed_orders / total_orders if total_orders > 0 else 0
        gmv = week_data['gmv'].sum()
        gross_profit = week_data['gross_profit'].sum()
        margin_rate = gross_profit / gmv if gmv > 0 else 0

        # 供给指标
        total_escorts = week_data['total_escorts'].iloc[-1]
        available_escorts = week_data['available_escorts'].iloc[-1]

        # 计算新增和流失
        if start_day > 0:
            prev_escorts = self.df.iloc[start_day - 1]['total_escorts']
            new_escorts = max(0, total_escorts - prev_escorts)
            churned_escorts = 0  # 简化处理
        else:
            new_escorts = total_escorts
            churned_escorts = 0

        # 增长指标
        if week_number > 1 and start_day >= 7:
            prev_week_data = self.df.iloc[start_day - 7:start_day]
            prev_orders = prev_week_data['total_orders'].sum()
            prev_gmv = prev_week_data['gmv'].sum()

            order_growth = (total_orders - prev_orders) / prev_orders if prev_orders > 0 else 0
            gmv_growth = (gmv - prev_gmv) / prev_gmv if prev_gmv > 0 else 0
        else:
            order_growth = 0
            gmv_growth = 0

        # 识别问题
        issues = self._identify_weekly_issues(week_data, completion_rate, margin_rate)

        # 生成建议
        recommendations = self._generate_weekly_recommendations(
            week_data, completion_rate, margin_rate, order_growth
        )

        # 生成业务事件
        events = self.event_generator.generate_weekly_events(start_day, end_day)

        return WeeklyReport(
            week_number=week_number,
            start_day=start_day,
            end_day=end_day,
            total_orders=int(total_orders),
            completed_orders=int(completed_orders),
            completion_rate=completion_rate,
            gmv=gmv,
            gross_profit=gross_profit,
            margin_rate=margin_rate,
            total_escorts=int(total_escorts),
            available_escorts=int(available_escorts),
            new_escorts=int(new_escorts),
            churned_escorts=int(churned_escorts),
            order_growth=order_growth,
            gmv_growth=gmv_growth,
            events=events,
            issues=issues,
            recommendations=recommendations,
        )

    def generate_monthly_reports(self) -> List[MonthlyReport]:
        """生成所有月报"""
        reports = []
        total_days = len(self.df)
        months = (total_days + 29) // 30  # 向上取整

        for month in range(months):
            start_day = month * 30
            end_day = min((month + 1) * 30 - 1, total_days - 1)

            report = self._generate_monthly_report(month + 1, start_day, end_day)
            reports.append(report)

        return reports

    def _generate_monthly_report(self, month_number: int, start_day: int, end_day: int) -> MonthlyReport:
        """生成单月报告"""
        month_data = self.df.iloc[start_day:end_day + 1]

        # 核心指标
        total_orders = month_data['total_orders'].sum()
        completed_orders = month_data['completed_orders'].sum()
        completion_rate = completed_orders / total_orders if total_orders > 0 else 0
        gmv = month_data['gmv'].sum()
        gross_profit = month_data['gross_profit'].sum()
        margin_rate = gross_profit / gmv if gmv > 0 else 0

        # 供给指标
        total_escorts = month_data['total_escorts'].iloc[-1]
        avg_escorts_per_day = month_data['total_escorts'].mean()

        if start_day > 0:
            prev_escorts = self.df.iloc[start_day - 1]['total_escorts']
            new_escorts = max(0, total_escorts - prev_escorts)
            churned_escorts = 0
            retention_rate = 1.0 - (churned_escorts / prev_escorts) if prev_escorts > 0 else 1.0
        else:
            new_escorts = total_escorts
            churned_escorts = 0
            retention_rate = 1.0

        # 用户指标
        new_users = month_data['new_orders'].sum()
        repurchase_users = month_data['repurchase_orders'].sum()
        repurchase_rate = repurchase_users / (new_users + repurchase_users) if (new_users + repurchase_users) > 0 else 0

        # 增长指标
        if month_number > 1 and start_day >= 30:
            prev_month_data = self.df.iloc[start_day - 30:start_day]
            prev_orders = prev_month_data['total_orders'].sum()
            prev_gmv = prev_month_data['gmv'].sum()

            order_growth = (total_orders - prev_orders) / prev_orders if prev_orders > 0 else 0
            gmv_growth = (gmv - prev_gmv) / prev_gmv if prev_gmv > 0 else 0
        else:
            order_growth = 0
            gmv_growth = 0

        # 生成周报
        weekly_reports = []
        for week in range(4):  # 每月4周
            week_start = start_day + week * 7
            week_end = min(week_start + 6, end_day)
            if week_start <= end_day:
                weekly_report = self._generate_weekly_report(week + 1, week_start, week_end)
                weekly_reports.append(weekly_report)

        # 识别问题
        issues = self._identify_monthly_issues(
            month_data, completion_rate, margin_rate, repurchase_rate
        )

        # 生成建议
        recommendations = self._generate_monthly_recommendations(
            month_data, completion_rate, margin_rate, order_growth, repurchase_rate
        )

        return MonthlyReport(
            month_number=month_number,
            start_day=start_day,
            end_day=end_day,
            total_orders=int(total_orders),
            completed_orders=int(completed_orders),
            completion_rate=completion_rate,
            gmv=gmv,
            gross_profit=gross_profit,
            margin_rate=margin_rate,
            total_escorts=int(total_escorts),
            avg_escorts_per_day=avg_escorts_per_day,
            new_escorts=int(new_escorts),
            churned_escorts=int(churned_escorts),
            retention_rate=retention_rate,
            new_users=int(new_users),
            repurchase_users=int(repurchase_users),
            repurchase_rate=repurchase_rate,
            order_growth=order_growth,
            gmv_growth=gmv_growth,
            weekly_reports=weekly_reports,
            issues=issues,
            recommendations=recommendations,
        )

    def _identify_weekly_issues(self, week_data: pd.DataFrame, completion_rate: float, margin_rate: float) -> List[str]:
        """识别周度问题"""
        issues = []

        if completion_rate < 0.70:
            issues.append(f"⚠️ 完成率偏低（{completion_rate:.1%}），供给不足")

        if margin_rate < 0.25:
            issues.append(f"⚠️ 毛利率偏低（{margin_rate:.1%}），成本控制需加强")

        # 检查等待订单堆积
        avg_waiting = week_data['waiting_orders'].mean()
        if avg_waiting > 100:
            issues.append(f"⚠️ 等待订单堆积严重（平均 {avg_waiting:.0f} 单）")

        # 检查陪诊员利用率
        avg_available = week_data['available_escorts'].mean()
        avg_serving = week_data['serving_escorts'].mean()
        if avg_available > 0:
            utilization = avg_serving / (avg_available + avg_serving)
            if utilization < 0.50:
                issues.append(f"⚠️ 陪诊员利用率低（{utilization:.1%}），需求不足")

        return issues

    def _generate_weekly_recommendations(
        self, week_data: pd.DataFrame, completion_rate: float, margin_rate: float, order_growth: float
    ) -> List[str]:
        """生成周度建议"""
        recommendations = []

        if completion_rate < 0.70:
            recommendations.append("💡 建议：加快陪诊员招募，提高培训通过率")

        if margin_rate < 0.25:
            recommendations.append("💡 建议：优化定价策略或降低陪诊员分成比例")

        if order_growth < 0:
            recommendations.append("💡 建议：加大市场推广力度，优化获客渠道")
        elif order_growth > 0.50:
            recommendations.append("💡 建议：保持增长势头，提前储备陪诊员")

        return recommendations

    def _identify_monthly_issues(
        self, month_data: pd.DataFrame, completion_rate: float, margin_rate: float, repurchase_rate: float
    ) -> List[str]:
        """识别月度问题"""
        issues = []

        if completion_rate < 0.75:
            issues.append(f"⚠️ 月度完成率未达标（{completion_rate:.1%}，目标 75%+）")

        if margin_rate < 0.28:
            issues.append(f"⚠️ 月度毛利率偏低（{margin_rate:.1%}，目标 28%+）")

        if repurchase_rate < 0.20:
            issues.append(f"⚠️ 复购率偏低（{repurchase_rate:.1%}），用户粘性不足")

        # 检查评分趋势
        avg_rating = month_data['avg_rating'].mean()
        if avg_rating < 4.3:
            issues.append(f"⚠️ 用户评分偏低（{avg_rating:.2f}），服务质量需提升")

        return issues

    def _generate_monthly_recommendations(
        self, month_data: pd.DataFrame, completion_rate: float, margin_rate: float,
        order_growth: float, repurchase_rate: float
    ) -> List[str]:
        """生成月度建议"""
        recommendations = []

        if completion_rate < 0.75:
            recommendations.append("💡 战略建议：扩大陪诊员规模，优化培训体系")

        if margin_rate < 0.28:
            recommendations.append("💡 战略建议：实施差异化定价，提高高端市场占比")

        if repurchase_rate < 0.20:
            recommendations.append("💡 战略建议：建立会员体系，推出订阅制服务")

        if order_growth > 0.30:
            recommendations.append("💡 战略建议：业务增长强劲，可考虑扩展到新城市")

        return recommendations

    def format_weekly_report(self, report: WeeklyReport) -> str:
        """格式化周报为 Markdown"""
        lines = []
        lines.append(f"# 陪诊服务业务周报 - 第 {report.week_number} 周")
        lines.append(f"**报告周期**：第 {report.start_day + 1} 天 - 第 {report.end_day + 1} 天")
        lines.append(f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        lines.append("## 📊 核心业务指标")
        lines.append("")
        lines.append("| 指标 | 数值 | 说明 |")
        lines.append("|------|------|------|")
        lines.append(f"| 总订单数 | {report.total_orders:,} | 本周新增订单 |")
        lines.append(f"| 完成订单数 | {report.completed_orders:,} | 成功完成的订单 |")
        lines.append(f"| 完成率 | {report.completion_rate:.1%} | 订单完成率 |")
        lines.append(f"| GMV | ¥{report.gmv:,.0f} | 本周总交易额 |")
        lines.append(f"| 毛利 | ¥{report.gross_profit:,.0f} | 扣除成本后利润 |")
        lines.append(f"| 毛利率 | {report.margin_rate:.1%} | 毛利占GMV比例 |")
        lines.append("")

        lines.append("## 👥 供给侧指标")
        lines.append("")
        lines.append("| 指标 | 数值 | 说明 |")
        lines.append("|------|------|------|")
        lines.append(f"| 陪诊员总数 | {report.total_escorts} | 周末时点数 |")
        lines.append(f"| 可用陪诊员 | {report.available_escorts} | 可接单状态 |")
        lines.append(f"| 新增陪诊员 | {report.new_escorts} | 本周新招募 |")
        lines.append(f"| 流失陪诊员 | {report.churned_escorts} | 本周流失 |")
        lines.append("")

        lines.append("## 📈 增长指标")
        lines.append("")
        if report.week_number > 1:
            lines.append(f"- **订单增长率**：{report.order_growth:+.1%}（环比上周）")
            lines.append(f"- **GMV 增长率**：{report.gmv_growth:+.1%}（环比上周）")
        else:
            lines.append("- 首周数据，无环比")
        lines.append("")

        # 添加业务事件
        if report.events:
            lines.append("## 📋 本周重要事件")
            lines.append("")
            lines.append(self.event_generator.format_events_for_report(report.events))

        if report.issues:
            lines.append("## ⚠️ 问题识别")
            lines.append("")
            for issue in report.issues:
                lines.append(f"- {issue}")
            lines.append("")

        if report.recommendations:
            lines.append("## 💡 改进建议")
            lines.append("")
            for rec in report.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        lines.append("---")
        lines.append("*本报告由沙盘模拟系统自动生成*")

        return "\n".join(lines)

    def format_monthly_report(self, report: MonthlyReport) -> str:
        """格式化月报为 Markdown"""
        lines = []
        lines.append(f"# 陪诊服务业务月报 - 第 {report.month_number} 月")
        lines.append(f"**报告周期**：第 {report.start_day + 1} 天 - 第 {report.end_day + 1} 天")
        lines.append(f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        lines.append("## 📊 核心业务指标")
        lines.append("")
        lines.append("| 指标 | 数值 | 说明 |")
        lines.append("|------|------|------|")
        lines.append(f"| 总订单数 | {report.total_orders:,} | 本月累计订单 |")
        lines.append(f"| 完成订单数 | {report.completed_orders:,} | 成功完成的订单 |")
        lines.append(f"| 完成率 | {report.completion_rate:.1%} | 订单完成率 |")
        lines.append(f"| GMV | ¥{report.gmv:,.0f} | 本月总交易额 |")
        lines.append(f"| 毛利 | ¥{report.gross_profit:,.0f} | 扣除成本后利润 |")
        lines.append(f"| 毛利率 | {report.margin_rate:.1%} | 毛利占GMV比例 |")
        lines.append(f"| 日均 GMV | ¥{report.gmv / (report.end_day - report.start_day + 1):,.0f} | 平均每日交易额 |")
        lines.append("")

        lines.append("## 👥 供给侧指标")
        lines.append("")
        lines.append("| 指标 | 数值 | 说明 |")
        lines.append("|------|------|------|")
        lines.append(f"| 陪诊员总数 | {report.total_escorts} | 月末时点数 |")
        lines.append(f"| 日均陪诊员数 | {report.avg_escorts_per_day:.1f} | 本月平均 |")
        lines.append(f"| 新增陪诊员 | {report.new_escorts} | 本月新招募 |")
        lines.append(f"| 流失陪诊员 | {report.churned_escorts} | 本月流失 |")
        lines.append(f"| 留存率 | {report.retention_rate:.1%} | 陪诊员留存率 |")
        lines.append("")

        lines.append("## 👤 用户指标")
        lines.append("")
        lines.append("| 指标 | 数值 | 说明 |")
        lines.append("|------|------|------|")
        lines.append(f"| 新用户订单 | {report.new_users:,} | 首次下单用户 |")
        lines.append(f"| 复购订单 | {report.repurchase_users:,} | 再次下单用户 |")
        lines.append(f"| 复购率 | {report.repurchase_rate:.1%} | 复购占比 |")
        lines.append("")

        lines.append("## 📈 增长指标")
        lines.append("")
        if report.month_number > 1:
            lines.append(f"- **订单增长率**：{report.order_growth:+.1%}（环比上月）")
            lines.append(f"- **GMV 增长率**：{report.gmv_growth:+.1%}（环比上月）")
        else:
            lines.append("- 首月数据，无环比")
        lines.append("")

        lines.append("## 📅 周度数据明细")
        lines.append("")
        lines.append("| 周次 | 订单数 | 完成率 | GMV | 毛利率 | 环比增长 |")
        lines.append("|------|--------|--------|-----|--------|----------|")
        for week_report in report.weekly_reports:
            lines.append(
                f"| 第 {week_report.week_number} 周 | "
                f"{week_report.total_orders:,} | "
                f"{week_report.completion_rate:.1%} | "
                f"¥{week_report.gmv:,.0f} | "
                f"{week_report.margin_rate:.1%} | "
                f"{week_report.order_growth:+.1%} |"
            )
        lines.append("")

        if report.issues:
            lines.append("## ⚠️ 问题识别")
            lines.append("")
            for issue in report.issues:
                lines.append(f"- {issue}")
            lines.append("")

        if report.recommendations:
            lines.append("## 💡 战略建议")
            lines.append("")
            for rec in report.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        lines.append("---")
        lines.append("*本报告由沙盘模拟系统自动生成*")

        return "\n".join(lines)
