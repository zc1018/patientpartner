"""
用户行为Agent - 模拟真实用户行为
"""

import random
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .base_agent import BaseAgent, AgentMessage, AgentType, MessageType


# 年龄分层行为差异模型
AGE_BEHAVIOR = {
    "60-70": {"children_purchase_rate": 0.4, "price_sensitivity": 0.6, "is_app_capable": True},
    "70-80": {"children_purchase_rate": 0.7, "price_sensitivity": 0.7, "is_app_capable": True},
    "80+":   {"children_purchase_rate": 0.9, "price_sensitivity": 0.5, "is_app_capable": False},
}


def get_age_group(age: int) -> str:
    """根据年龄返回分层key"""
    if age < 70:
        return "60-70"
    elif age < 80:
        return "70-80"
    else:
        return "80+"


# 用户分层模型
USER_SEGMENTS = {
    "high_freq_chronic": {
        "name": "高频慢病用户",
        "ratio": 0.15,
        "avg_orders_per_month": 4,
        "price_sensitivity": 0.3,
        "retention_rate_30d": 0.80,
        "ltv_annual": 9600,
        "scenarios": ["慢病复查", "专家门诊"]
    },
    "low_freq_occasional": {
        "name": "低频偶尔用户",
        "ratio": 0.60,
        "avg_orders_per_month": 0.5,
        "price_sensitivity": 0.7,
        "retention_rate_30d": 0.40,
        "ltv_annual": 1200,
        "scenarios": ["偶尔就医", "体检"]
    },
    "one_time_surgery": {
        "name": "一次性手术用户",
        "ratio": 0.25,
        "avg_orders_per_month": 0.1,
        "price_sensitivity": 0.5,
        "retention_rate_30d": 0.10,
        "ltv_annual": 240,
        "scenarios": ["手术陪同", "住院陪护"]
    }
}


class UserBehaviorAgent(BaseAgent):
    """
    用户行为Agent

    职责：
    1. 模拟用户下单行为（基于真实数据）
    2. 模拟用户复购决策（首单复购率13.5%）
    3. 模拟用户流失（30天留存率45%）
    4. 模拟用户评价行为
    5. 模拟用户对价格、服务质量的敏感度
    """

    def __init__(self):
        super().__init__(agent_id="user_behavior_agent", agent_type=AgentType.USER_BEHAVIOR)

        # 基于修正后的参数
        self.first_order_repeat_rate = 0.135  # 首单复购率13.5%
        self.regular_repeat_rate = 0.30  # 老客户复购率30%
        self.designated_repeat_rate = 0.82  # 指定陪诊师复购率82%

        # 用户留存率（基于外部研究数据）
        self.retention_30_day = 0.45  # 30天留存率45%
        self.retention_90_day = 0.36  # 90天留存率36%

        # 用户分层比例（用于随机分配）
        self.segment_keys = list(USER_SEGMENTS.keys())
        self.segment_weights = [USER_SEGMENTS[k]["ratio"] for k in self.segment_keys]

        # 用户池
        self.state.memory['active_users'] = []  # 活跃用户
        self.state.memory['churned_users'] = []  # 流失用户
        self.state.memory['user_history'] = {}  # 用户历史记录

    def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理消息"""
        if message.message_type == MessageType.EVENT:
            event_type = message.content.get('event_type')

            if event_type == 'order_completed':
                # 订单完成后，更新用户状态
                return self._handle_order_completed(message.content)

            elif event_type == 'price_change':
                # 价格变化，影响用户下单意愿
                return self._handle_price_change(message.content)

            elif event_type == 'marketing_campaign':
                # 营销活动，影响用户行为
                return self._handle_marketing_campaign(message.content)

        return None

    def take_action(self, simulation_state: Dict[str, Any]) -> List[AgentMessage]:
        """执行用户行为模拟"""
        messages = []
        current_day = simulation_state.get('current_day', 0)

        # 1. 模拟新用户下单
        new_orders = self._simulate_new_user_orders(simulation_state)
        if new_orders:
            messages.append(self.send_message(
                receiver="coordinator",
                message_type=MessageType.EVENT,
                content={
                    'event_type': 'new_orders',
                    'orders': new_orders,
                    'day': current_day
                }
            ))

        # 2. 模拟复购用户下单
        repurchase_orders = self._simulate_repurchase_orders(simulation_state)
        if repurchase_orders:
            messages.append(self.send_message(
                receiver="coordinator",
                message_type=MessageType.EVENT,
                content={
                    'event_type': 'repurchase_orders',
                    'orders': repurchase_orders,
                    'day': current_day
                }
            ))

        # 3. 模拟用户流失
        churned_users = self._simulate_user_churn(current_day)
        if churned_users:
            messages.append(self.send_message(
                receiver="monitoring_agent",
                message_type=MessageType.ALERT,
                content={
                    'alert_type': 'user_churn',
                    'churned_count': len(churned_users),
                    'day': current_day
                },
                priority=5
            ))

        # 4. 更新指标
        self.update_metrics({
            'active_users': len(self.state.memory['active_users']),
            'churned_users': len(self.state.memory['churned_users']),
            'new_orders': len(new_orders) if new_orders else 0,
            'repurchase_orders': len(repurchase_orders) if repurchase_orders else 0,
        })

        return messages

    def _simulate_new_user_orders(self, simulation_state: Dict[str, Any]) -> List[Dict]:
        """模拟新用户下单"""
        # 基于市场规模和曝光率计算新用户数
        market_size = simulation_state.get('market_size', 1000)
        exposure_rate = simulation_state.get('exposure_rate', 0.03)
        conversion_rate = simulation_state.get('conversion_rate', 0.15)
        current_day = simulation_state.get('current_day', 0)

        # 计算新用户订单数
        potential_users = int(market_size * exposure_rate)
        new_order_count = int(potential_users * conversion_rate * random.uniform(0.8, 1.2))

        orders = []
        for _ in range(new_order_count):
            user_id = f"user_{len(self.state.memory['active_users']) + 1}"

            # 根据分层比例随机分配用户类型
            segment_key = random.choices(self.segment_keys, weights=self.segment_weights, k=1)[0]
            segment = USER_SEGMENTS[segment_key]

            order = {
                'user_id': user_id,
                'is_first_order': True,
                'price_sensitivity': segment["price_sensitivity"],
                'quality_expectation': random.uniform(4.0, 5.0),
                'day': current_day,
                'segment': segment_key,
            }
            orders.append(order)

            # 添加到活跃用户池
            self.state.memory['active_users'].append(user_id)
            self.state.memory['user_history'][user_id] = {
                'first_order_day': current_day,
                'total_orders': 1,
                'last_order_day': current_day,
                'ratings': [],
                'designated_escort': None,
                'segment': segment_key,
                'retention_rate_30d': segment["retention_rate_30d"],
            }

        return orders

    def _simulate_repurchase_orders(self, simulation_state: Dict[str, Any]) -> List[Dict]:
        """模拟复购订单"""
        orders = []
        current_day = simulation_state.get('current_day', 0)

        for user_id in self.state.memory['active_users']:
            user_history = self.state.memory['user_history'].get(user_id, {})

            # 判断是否复购
            if self._should_repurchase(user_history, current_day):
                order = {
                    'user_id': user_id,
                    'is_first_order': False,
                    'is_designated': user_history.get('designated_escort') is not None,
                    'designated_escort': user_history.get('designated_escort'),
                    'day': current_day
                }
                orders.append(order)

                # 更新用户历史
                user_history['total_orders'] += 1
                user_history['last_order_day'] = current_day

        return orders

    def _should_repurchase(self, user_history: Dict, current_day: int) -> bool:
        """判断用户是否会复购"""
        total_orders = user_history.get('total_orders', 0)
        designated_escort = user_history.get('designated_escort')
        avg_rating = sum(user_history.get('ratings', [])) / len(user_history.get('ratings', [1])) if user_history.get('ratings') else 4.5

        # 首单用户
        if total_orders == 1:
            # 基于评分调整复购率
            if avg_rating >= 4.9:
                repeat_rate = self.first_order_repeat_rate * 1.5
            elif avg_rating >= 4.5:
                repeat_rate = self.first_order_repeat_rate
            else:
                repeat_rate = self.first_order_repeat_rate * 0.5

            return random.random() < repeat_rate / 30  # 转换为日复购概率

        # 指定陪诊师用户
        elif designated_escort:
            return random.random() < self.designated_repeat_rate / 30

        # 老客户
        else:
            return random.random() < self.regular_repeat_rate / 30

    def _simulate_user_churn(self, current_day: int) -> List[str]:
        """模拟用户流失 (按用户分层 + 周留存模型)"""
        churned_users = []

        for user_id in list(self.state.memory['active_users']):
            user_history = self.state.memory['user_history'].get(user_id, {})
            first_order_day = user_history.get('first_order_day', 0)

            # 计算用户活跃天数 (模拟时间)
            days_since_first_order = current_day - first_order_day

            # 获取用户分层的30天留存率，用于调整流失概率
            segment_retention = user_history.get('retention_rate_30d', 0.45)
            # 留存率越高，流失概率越低（基准0.45对应原始流失率）
            retention_modifier = 0.45 / max(segment_retention, 0.01)

            # 基于周期的流失概率模型（乘以分层修正系数）
            if days_since_first_order <= 7:
                churn_probability = 0.05 * retention_modifier
            elif days_since_first_order <= 30:
                churn_probability = 0.021 * retention_modifier
            elif days_since_first_order <= 90:
                churn_probability = 0.004 * retention_modifier
            else:
                churn_probability = 0.002 * retention_modifier

            # 评分低的用户更容易流失
            avg_rating = sum(user_history.get('ratings', [])) / len(user_history.get('ratings', [1])) if user_history.get('ratings') else 4.5
            if avg_rating < 4.0:
                churn_probability *= 2.0

            if random.random() < churn_probability:
                churned_users.append(user_id)
                self.state.memory['active_users'].remove(user_id)
                self.state.memory['churned_users'].append(user_id)

        return churned_users

    def _handle_order_completed(self, content: Dict) -> Optional[AgentMessage]:
        """处理订单完成事件"""
        user_id = content.get('user_id')
        rating = content.get('rating', 4.5)
        escort_id = content.get('escort_id')

        if user_id in self.state.memory['user_history']:
            user_history = self.state.memory['user_history'][user_id]
            user_history['ratings'].append(rating)

            # 如果评分高，可能指定陪诊师
            if rating >= 4.8 and random.random() < 0.7:
                user_history['designated_escort'] = escort_id

        return None

    def _handle_price_change(self, content: Dict) -> Optional[AgentMessage]:
        """处理价格变化"""
        price_change_rate = content.get('price_change_rate', 0)

        # 价格上涨会降低转化率和复购率
        if price_change_rate > 0:
            self.first_order_repeat_rate *= (1 - price_change_rate * 0.5)
            self.regular_repeat_rate *= (1 - price_change_rate * 0.3)

        return self.send_message(
            receiver="monitoring_agent",
            message_type=MessageType.ALERT,
            content={
                'alert_type': 'user_behavior_change',
                'reason': 'price_change',
                'impact': f"复购率预计下降{price_change_rate * 30:.1f}%"
            }
        )

    def _handle_marketing_campaign(self, content: Dict) -> Optional[AgentMessage]:
        """处理营销活动"""
        campaign_type = content.get('campaign_type')
        intensity = content.get('intensity', 1.0)

        # 营销活动可以提升复购率
        if campaign_type == 'retention':
            self.first_order_repeat_rate *= (1 + intensity * 0.2)
            self.regular_repeat_rate *= (1 + intensity * 0.15)

        return None
