"""
业务事件生成器 - 为报告添加具体事件描述
"""
import random
from typing import List, Dict
import pandas as pd
from dataclasses import dataclass


# 政策风险事件定义
POLICY_RISK_EVENTS = [
    {
        "name": "医院禁入政策",
        "event_type": "policy_risk",
        "probability_per_day": 0.02 / 365,  # 年概率2%
        "demand_impact": -0.50,
        "duration_days": 90,
        "description": "某三甲医院禁止平台陪诊师进入，需要重新谈判准入"
    },
    {
        "name": "持证上岗要求",
        "event_type": "policy_risk",
        "probability_per_day": 0.01 / 365,
        "demand_impact": -0.30,
        "supply_impact": -0.30,  # 70%陪诊师需要重新培训
        "duration_days": 180,
        "description": "政策要求陪诊师持有护理证，供给侧受冲击"
    },
    {
        "name": "患者隐私泄露事件",
        "event_type": "brand_crisis",
        "probability_per_day": 0.005 / 365,
        "demand_impact": -0.60,
        "nps_impact": -20,  # NPS额外下降20点
        "duration_days": 60,
        "description": "陪诊师泄露患者隐私，导致品牌危机和监管处罚"
    },
    {
        "name": "医保报销陪诊费",
        "event_type": "policy_benefit",
        "probability_per_day": 0.002 / 365,
        "demand_impact": +0.80,
        "duration_days": 365,
        "description": "政策允许医保报销陪诊费，需求爆发式增长"
    }
]


@dataclass
class BusinessEvent:
    """业务事件"""
    day: int
    category: str  # 服务事件/市场事件/运营事件/用户事件
    title: str
    description: str
    impact: str  # 正面/负面/中性
    metrics: Dict[str, float]  # 相关指标


class EventGenerator:
    """事件生成器"""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.active_policy_events: List[Dict] = []  # 当前生效的政策事件

    def generate_policy_risk_events(self, day: int) -> List[BusinessEvent]:
        """生成政策风险事件（每日调用）"""
        events = []

        # 清理过期的政策事件
        self.active_policy_events = [
            e for e in self.active_policy_events
            if day < e["start_day"] + e["duration_days"]
        ]

        # 检查是否触发新的政策事件
        for policy_event in POLICY_RISK_EVENTS:
            if random.random() < policy_event["probability_per_day"]:
                # 避免同类型事件重复触发
                active_names = [e["name"] for e in self.active_policy_events]
                if policy_event["name"] in active_names:
                    continue

                active_event = {**policy_event, "start_day": day}
                self.active_policy_events.append(active_event)

                impact = "负面" if policy_event["demand_impact"] < 0 else "正面"
                events.append(BusinessEvent(
                    day=day,
                    category="政策事件",
                    title=policy_event["name"],
                    description=policy_event["description"],
                    impact=impact,
                    metrics={
                        "需求影响": policy_event["demand_impact"],
                        "持续天数": policy_event["duration_days"],
                    }
                ))

        return events

    def get_active_policy_demand_modifier(self, day: int) -> float:
        """获取当前生效的政策事件对需求的累计影响系数"""
        modifier = 0.0
        for event in self.active_policy_events:
            if day < event["start_day"] + event["duration_days"]:
                modifier += event.get("demand_impact", 0)
        return modifier

    def get_active_policy_supply_modifier(self, day: int) -> float:
        """获取当前生效的政策事件对供给的累计影响系数"""
        modifier = 0.0
        for event in self.active_policy_events:
            if day < event["start_day"] + event["duration_days"]:
                modifier += event.get("supply_impact", 0)
        return modifier

    def generate_weekly_events(self, start_day: int, end_day: int) -> List[BusinessEvent]:
        """生成一周内的关键事件"""
        events = []
        week_data = self.df.iloc[start_day:end_day + 1]

        # 1. 服务质量事件
        service_events = self._generate_service_events(week_data, start_day)
        events.extend(service_events)

        # 2. 市场增长事件
        market_events = self._generate_market_events(week_data, start_day)
        events.extend(market_events)

        # 3. 运营事件
        operation_events = self._generate_operation_events(week_data, start_day)
        events.extend(operation_events)

        # 4. 用户事件
        user_events = self._generate_user_events(week_data, start_day)
        events.extend(user_events)

        # 按影响力排序，返回最重要的 3-5 个事件
        events.sort(key=lambda e: self._calculate_importance(e), reverse=True)
        return events[:5]

    def _generate_service_events(self, week_data: pd.DataFrame, start_day: int) -> List[BusinessEvent]:
        """生成服务相关事件"""
        events = []

        # 检查评分变化
        if len(week_data) > 1:
            avg_rating = week_data['avg_rating'].mean()
            rating_change = week_data['avg_rating'].iloc[-1] - week_data['avg_rating'].iloc[0]

            if rating_change > 0.2:
                # 评分显著提升
                best_day: int = week_data['avg_rating'].idxmax()  # type: ignore[assignment]
                best_rating = week_data.loc[best_day, 'avg_rating']

                events.append(BusinessEvent(
                    day=best_day,
                    category="服务事件",
                    title="用户满意度显著提升",
                    description=f"第 {best_day + 1} 天，用户评分达到 {best_rating:.2f} 分（满分 5 分），"
                               f"较周初提升 {rating_change:.2f} 分。经分析，主要原因是新培训的陪诊员服务质量提升，"
                               f"以及优化了医院驻点服务流程。多位用户反馈'陪诊员非常专业，帮助解读报告很清楚'。",
                    impact="正面",
                    metrics={
                        "评分": best_rating,
                        "提升幅度": rating_change,
                    }
                ))
            elif rating_change < -0.2:
                # 评分下降
                worst_day: int = week_data['avg_rating'].idxmin()  # type: ignore[assignment]
                worst_rating = week_data.loc[worst_day, 'avg_rating']

                events.append(BusinessEvent(
                    day=worst_day,
                    category="服务事件",
                    title="服务质量预警",
                    description=f"第 {worst_day + 1} 天，用户评分降至 {worst_rating:.2f} 分，"
                               f"较周初下降 {abs(rating_change):.2f} 分。主要问题集中在等待时间过长和陪诊员经验不足。"
                               f"已紧急召开服务质量会议，加强新人培训和老带新机制。",
                    impact="负面",
                    metrics={
                        "评分": worst_rating,
                        "下降幅度": abs(rating_change),
                    }
                ))

        # 检查完成率突破
        completion_rates = week_data['completion_rate']
        if completion_rates.max() > 0.80 and completion_rates.iloc[0] < 0.70:  # type: ignore[operator]
            breakthrough_day: int = completion_rates.idxmax()  # type: ignore[assignment]
            breakthrough_rate = completion_rates.loc[breakthrough_day]

            events.append(BusinessEvent(
                day=breakthrough_day,
                category="服务事件",
                title="订单完成率突破 80%",
                description=f"第 {breakthrough_day + 1} 天，订单完成率首次突破 80%，达到 {breakthrough_rate:.1%}。"
                           f"这标志着供需平衡进入新阶段。本周新增 {week_data['training_escorts'].iloc[-1]} 名陪诊员完成培训上岗，"
                           f"同时优化了订单分配算法，匹配效率提升 15%。",
                impact="正面",
                metrics={
                    "完成率": breakthrough_rate,
                    "新增陪诊员": int(week_data['training_escorts'].iloc[-1]),
                }
            ))

        return events

    def _generate_market_events(self, week_data: pd.DataFrame, start_day: int) -> List[BusinessEvent]:
        """生成市场相关事件"""
        events = []

        # 检查订单量激增
        daily_orders = week_data['total_orders']
        if len(daily_orders) > 1:
            max_orders = daily_orders.max()
            avg_orders = daily_orders.mean()

            if max_orders > avg_orders * 1.5:  # type: ignore[operator]
                peak_day: int = daily_orders.idxmax()  # type: ignore[assignment]
                peak_orders = daily_orders.loc[peak_day]

                # 判断是哪天（周几）
                day_of_week = (peak_day % 7) + 1
                weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                weekday = weekday_names[day_of_week - 1]

                events.append(BusinessEvent(
                    day=peak_day,
                    category="市场事件",
                    title=f"{weekday}订单量激增",
                    description=f"第 {peak_day + 1} 天（{weekday}），订单量达到 {int(peak_orders)} 单，"
                               f"较日均水平增长 {(peak_orders / avg_orders - 1) * 100:.0f}%。"
                               f"经分析，主要原因是协和医院和 301 医院当天专家门诊集中，"
                               f"加上滴滴 App 首页推荐位曝光量增加 30%。已协调增派陪诊员到重点医院。",
                    impact="正面",
                    metrics={
                        "订单量": peak_orders,
                        "增长率": (peak_orders / avg_orders - 1),
                    }
                ))

        # 检查 GMV 里程碑
        cumulative_gmv = week_data['gmv'].sum()
        if 900_000 < cumulative_gmv < 1_100_000:
            events.append(BusinessEvent(
                day=int(week_data.index[-1]),  # type: ignore[arg-type]
                category="市场事件",
                title="周 GMV 突破百万",
                description=f"本周 GMV 达到 ¥{cumulative_gmv:,.0f}，首次突破百万大关。"
                           f"日均 GMV 达到 ¥{cumulative_gmv / len(week_data):,.0f}，"
                           f"其中高端区域（朝阳、海淀）贡献占比 65%。"
                           f"客单价稳定在 ¥200 左右，复购用户占比提升至 18%。",
                impact="正面",
                metrics={
                    "周GMV": cumulative_gmv,
                    "日均GMV": cumulative_gmv / len(week_data),
                }
            ))

        return events

    def _generate_operation_events(self, week_data: pd.DataFrame, start_day: int) -> List[BusinessEvent]:
        """生成运营相关事件"""
        events = []

        # 检查陪诊员招募
        escorts_change = week_data['total_escorts'].iloc[-1] - week_data['total_escorts'].iloc[0]
        if escorts_change >= 8:
            events.append(BusinessEvent(
                day=int(week_data.index[-1]),  # type: ignore[arg-type]
                category="运营事件",
                title="陪诊员团队扩充",
                description=f"本周成功招募 {int(escorts_change)} 名新陪诊员，团队规模达到 {int(week_data['total_escorts'].iloc[-1])} 人。"
                           f"新人主要来自医院周边社区和退休护士群体，平均年龄 45 岁，"
                           f"具备丰富的医疗常识。已安排资深陪诊员进行一对一带教，"
                           f"预计 7 天后可独立接单。",
                impact="正面",
                metrics={
                    "新增人数": escorts_change,
                    "团队规模": week_data['total_escorts'].iloc[-1],
                }
            ))

        # 检查等待订单堆积
        avg_waiting = week_data['waiting_orders'].mean()
        if avg_waiting > 500:
            peak_waiting_day: int = week_data['waiting_orders'].idxmax()  # type: ignore[assignment]
            peak_waiting = week_data.loc[peak_waiting_day, 'waiting_orders']

            events.append(BusinessEvent(
                day=peak_waiting_day,
                category="运营事件",
                title="订单堆积预警",
                description=f"第 {peak_waiting_day + 1} 天，等待订单数达到 {int(peak_waiting)} 单，"
                           f"平均等待时长超过 2 小时。主要原因是早高峰时段（8-10点）订单集中，"
                           f"而可用陪诊员不足。已采取应急措施：1）启动弹性排班，增加早班人员；"
                           f"2）优化匹配算法，优先分配距离近的陪诊员；3）向用户发送等待提醒和优惠券。",
                impact="负面",
                metrics={
                    "等待订单": float(peak_waiting),
                    "平均等待": float(avg_waiting),
                }
            ))

        # 检查供需平衡改善
        if len(week_data) > 1:
            completion_improvement = week_data['completion_rate'].iloc[-1] - week_data['completion_rate'].iloc[0]
            if completion_improvement > 0.15:
                events.append(BusinessEvent(
                    day=int(week_data.index[-1]),  # type: ignore[arg-type]
                    category="运营事件",
                    title="供需平衡显著改善",
                    description=f"本周完成率从 {week_data['completion_rate'].iloc[0]:.1%} 提升至 "
                               f"{week_data['completion_rate'].iloc[-1]:.1%}，提升 {completion_improvement:.1%}。"
                               f"得益于陪诊员规模扩大和培训效率提升，供给能力增长 {escorts_change / week_data['total_escorts'].iloc[0]:.1%}。"
                               f"同时优化了医院驻点布局，重点覆盖协和、301、北医三院等高需求医院。",
                    impact="正面",
                    metrics={
                        "完成率提升": completion_improvement,
                        "供给增长": escorts_change / week_data['total_escorts'].iloc[0] if week_data['total_escorts'].iloc[0] > 0 else 0,
                    }
                ))

        return events

    def _generate_user_events(self, week_data: pd.DataFrame, start_day: int) -> List[BusinessEvent]:
        """生成用户相关事件"""
        events = []

        # 检查复购情况
        if 'repurchase_orders' in week_data.columns:
            repurchase_orders = week_data['repurchase_orders'].sum()
            total_orders = week_data['total_orders'].sum()

            if repurchase_orders > 0:
                repurchase_rate = repurchase_orders / total_orders

                if repurchase_rate > 0.20:
                    events.append(BusinessEvent(
                        day=int(week_data.index[-1]),  # type: ignore[arg-type]
                        category="用户事件",
                        title="复购率创新高",
                        description=f"本周复购订单达到 {int(repurchase_orders)} 单，复购率达到 {repurchase_rate:.1%}，"
                                   f"创历史新高。典型案例：朝阳区张女士（65岁，糖尿病患者）本周第 3 次使用服务，"
                                   f"评价'陪诊员小李非常专业，每次都能帮我问到关键问题，比家人陪着还放心'。"
                                   f"高复购用户主要集中在慢病管理场景，建议推出订阅制会员服务。",
                        impact="正面",
                        metrics={
                            "复购订单": repurchase_orders,
                            "复购率": repurchase_rate,
                        }
                    ))

        # 检查新用户增长
        if 'new_orders' in week_data.columns:
            new_orders = week_data['new_orders'].sum()

            if new_orders > 100:
                events.append(BusinessEvent(
                    day=int(week_data.index[-1]),  # type: ignore[arg-type]
                    category="用户事件",
                    title="新用户快速增长",
                    description=f"本周新增用户 {int(new_orders)} 人，主要来源于：1）滴滴 App 首页推荐（45%）；"
                               f"2）医院驻点推广（30%）；3）老用户推荐（25%）。"
                               f"用户画像分析显示，60-75 岁老年人占比 70%，主要需求是慢病复查和专家门诊陪同。"
                               f"海淀区和朝阳区用户占比超过 60%，客单价较其他区域高 20-30%。",
                    impact="正面",
                    metrics={
                        "新用户": new_orders,
                    }
                ))

        return events

    def _calculate_importance(self, event: BusinessEvent) -> float:
        """计算事件重要性（用于排序）"""
        importance = 0

        # 正面事件加分
        if event.impact == "正面":
            importance += 2
        elif event.impact == "负面":
            importance += 3  # 负面事件更重要，需要关注

        # 根据类别加分
        category_weights = {
            "市场事件": 3,
            "服务事件": 2,
            "运营事件": 2,
            "用户事件": 1,
            "政策事件": 4,  # 政策事件影响最大
        }
        importance += category_weights.get(event.category, 1)

        # 根据指标数量加分
        importance += len(event.metrics) * 0.5

        return importance

    def format_events_for_report(self, events: List[BusinessEvent]) -> str:
        """格式化事件为报告文本"""
        if not events:
            return "本周无重大事件。"

        lines = []
        for i, event in enumerate(events, 1):
            icon = "📈" if event.impact == "正面" else "⚠️" if event.impact == "负面" else "📊"

            lines.append(f"### {icon} 事件 {i}：{event.title}")
            lines.append(f"**类别**：{event.category} | **日期**：第 {event.day + 1} 天")
            lines.append("")
            lines.append(event.description)
            lines.append("")

            if event.metrics:
                lines.append("**关键数据**：")
                for key, value in event.metrics.items():
                    if isinstance(value, float):
                        if value < 1:
                            lines.append(f"- {key}：{value:.1%}")
                        else:
                            lines.append(f"- {key}：{value:,.2f}")
                    else:
                        lines.append(f"- {key}：{value:,}")
                lines.append("")

        return "\n".join(lines)
