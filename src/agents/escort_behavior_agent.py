"""
陪诊员行为Agent - 模拟真实陪诊员行为
"""

import random
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_agent import BaseAgent, AgentMessage, AgentType, MessageType


class EscortBehaviorAgent(BaseAgent):
    """
    陪诊员行为Agent

    职责：
    1. 模拟陪诊员接单行为
    2. 模拟陪诊员服务质量波动
    3. 模拟陪诊员流失（基于收入、订单量）
    4. 模拟陪诊员评分分布
    5. 模拟陪诊员的工作状态变化
    """

    def __init__(self):
        super().__init__(agent_id="escort_behavior_agent", agent_type=AgentType.ESCORT_BEHAVIOR)

        # 陪诊员池
        self.state.memory['active_escorts'] = []  # 活跃陪诊员
        self.state.memory['churned_escorts'] = []  # 流失陪诊员
        self.state.memory['escort_stats'] = {}  # 陪诊员统计数据

        # 评分分布（基于美团跑腿数据）
        self.rating_distribution = {
            '5.0': 0.15,  # 15%的陪诊员评分5.0
            '4.9': 0.25,  # 25%的陪诊员评分4.9
            '4.8': 0.30,  # 30%的陪诊员评分4.8
            '4.5-4.7': 0.25,  # 25%的陪诊员评分4.5-4.7
            '<4.5': 0.05,  # 5%的陪诊员评分<4.5
        }

    def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理消息"""
        if message.message_type == MessageType.EVENT:
            event_type = message.content.get('event_type')

            if event_type == 'order_assigned':
                # 订单分配给陪诊员
                return self._handle_order_assigned(message.content)

            elif event_type == 'order_completed':
                # 订单完成，更新陪诊员状态
                return self._handle_order_completed(message.content)

            elif event_type == 'recruit_escorts':
                # 招募新陪诊员
                return self._handle_recruit_escorts(message.content)

        return None

    def take_action(self, simulation_state: Dict[str, Any]) -> List[AgentMessage]:
        """执行陪诊员行为模拟"""
        messages = []
        current_day = simulation_state.get('current_day', 0)

        # 1. 模拟陪诊员服务质量波动
        quality_changes = self._simulate_quality_fluctuation()
        if quality_changes:
            messages.append(self.send_message(
                receiver="monitoring_agent",
                message_type=MessageType.EVENT,
                content={
                    'event_type': 'quality_change',
                    'changes': quality_changes,
                    'day': current_day
                }
            ))

        # 2. 模拟陪诊员流失
        churned_escorts = self._simulate_escort_churn(current_day)
        if churned_escorts:
            messages.append(self.send_message(
                receiver="operations_agent",
                message_type=MessageType.ALERT,
                content={
                    'alert_type': 'escort_churn',
                    'churned_count': len(churned_escorts),
                    'day': current_day
                },
                priority=7
            ))

        # 3. 更新指标
        self.update_metrics({
            'active_escorts': len(self.state.memory['active_escorts']),
            'churned_escorts': len(self.state.memory['churned_escorts']),
            'avg_rating': self._calculate_avg_rating(),
            'avg_daily_orders': self._calculate_avg_daily_orders(),
        })

        return messages

    def _simulate_quality_fluctuation(self) -> List[Dict]:
        """模拟服务质量波动"""
        changes = []

        for escort_id in self.state.memory['active_escorts']:
            stats = self.state.memory['escort_stats'].get(escort_id, {})

            # 基于订单量和收入，服务质量可能波动
            total_orders = stats.get('total_orders', 0)
            total_income = stats.get('total_income', 0)
            current_rating = stats.get('rating', 4.5)

            # 订单量过多可能导致服务质量下降
            if total_orders > 100:
                if random.random() < 0.1:
                    new_rating = max(4.0, current_rating - random.uniform(0.1, 0.3))
                    stats['rating'] = new_rating
                    changes.append({
                        'escort_id': escort_id,
                        'old_rating': current_rating,
                        'new_rating': new_rating,
                        'reason': '订单量过多导致服务质量下降'
                    })

            # 收入低可能导致积极性下降
            elif total_income < 3000:
                if random.random() < 0.05:
                    new_rating = max(4.0, current_rating - random.uniform(0.05, 0.15))
                    stats['rating'] = new_rating
                    changes.append({
                        'escort_id': escort_id,
                        'old_rating': current_rating,
                        'new_rating': new_rating,
                        'reason': '收入低导致积极性下降'
                    })

        return changes

    def _simulate_escort_churn(self, current_day: int) -> List[str]:
        """模拟陪诊员流失"""
        churned_escorts = []

        for escort_id in list(self.state.memory['active_escorts']):
            stats = self.state.memory['escort_stats'].get(escort_id, {})

            # 计算流失概率
            churn_probability = self._calculate_churn_probability(stats)

            if random.random() < churn_probability / 30:  # 转换为日流失概率
                churned_escorts.append(escort_id)
                self.state.memory['active_escorts'].remove(escort_id)
                self.state.memory['churned_escorts'].append(escort_id)

        return churned_escorts

    def _calculate_churn_probability(self, stats: Dict) -> float:
        """计算陪诊员流失概率"""
        total_orders = stats.get('total_orders', 0)
        total_income = stats.get('total_income', 0)
        rating = stats.get('rating', 4.5)

        # 基础流失率
        base_churn_rate = 0.20  # 年流失率20%

        # 收入因素（收入越高，流失率越低）
        if total_income > 10000:
            income_factor = 0.5
        elif total_income > 5000:
            income_factor = 0.8
        else:
            income_factor = 1.5

        # 订单量因素（订单越多，流失率越低）
        if total_orders > 50:
            order_factor = 0.6
        elif total_orders > 20:
            order_factor = 0.9
        else:
            order_factor = 1.3

        # 评分因素（评分越高，流失率越低）
        if rating >= 4.8:
            rating_factor = 0.7
        elif rating >= 4.5:
            rating_factor = 1.0
        else:
            rating_factor = 1.4

        return base_churn_rate * income_factor * order_factor * rating_factor

    def _handle_order_assigned(self, content: Dict) -> Optional[AgentMessage]:
        """处理订单分配"""
        escort_id = content.get('escort_id')
        order_id = content.get('order_id')

        if escort_id in self.state.memory['escort_stats']:
            stats = self.state.memory['escort_stats'][escort_id]
            stats['current_orders'] = stats.get('current_orders', 0) + 1

        return None

    def _handle_order_completed(self, content: Dict) -> Optional[AgentMessage]:
        """处理订单完成"""
        escort_id = content.get('escort_id')
        order_value = content.get('order_value', 0)
        rating = content.get('rating', 4.5)

        if escort_id not in self.state.memory['escort_stats']:
            self.state.memory['escort_stats'][escort_id] = {
                'total_orders': 0,
                'total_income': 0,
                'rating': 4.5,
                'ratings': [],
                'current_orders': 0
            }

        stats = self.state.memory['escort_stats'][escort_id]
        stats['total_orders'] += 1
        stats['total_income'] += order_value * 0.7  # 陪诊员分成70%
        stats['ratings'].append(rating)
        stats['rating'] = sum(stats['ratings']) / len(stats['ratings'])
        stats['current_orders'] = max(0, stats.get('current_orders', 1) - 1)

        return None

    def _handle_recruit_escorts(self, content: Dict) -> Optional[AgentMessage]:
        """处理招募陪诊员"""
        recruit_count = content.get('count', 0)

        for i in range(recruit_count):
            escort_id = f"escort_{len(self.state.memory['active_escorts']) + 1}"
            self.state.memory['active_escorts'].append(escort_id)

            # 根据评分分布初始化陪诊员
            rating = self._assign_initial_rating()
            self.state.memory['escort_stats'][escort_id] = {
                'total_orders': 0,
                'total_income': 0,
                'rating': rating,
                'ratings': [rating],
                'current_orders': 0,
                'join_date': datetime.now()
            }

        return self.send_message(
            receiver="monitoring_agent",
            message_type=MessageType.EVENT,
            content={
                'event_type': 'escorts_recruited',
                'count': recruit_count
            }
        )

    def _assign_initial_rating(self) -> float:
        """分配初始评分（基于评分分布）"""
        rand = random.random()
        cumulative = 0

        for rating_range, probability in self.rating_distribution.items():
            cumulative += probability
            if rand < cumulative:
                if rating_range == '5.0':
                    return 5.0
                elif rating_range == '4.9':
                    return 4.9
                elif rating_range == '4.8':
                    return 4.8
                elif rating_range == '4.5-4.7':
                    return random.uniform(4.5, 4.7)
                else:  # '<4.5'
                    return random.uniform(4.0, 4.5)

        return 4.5

    def _calculate_avg_rating(self) -> float:
        """计算平均评分"""
        if not self.state.memory['escort_stats']:
            return 4.5

        ratings = [stats.get('rating', 4.5) for stats in self.state.memory['escort_stats'].values()]
        return sum(ratings) / len(ratings) if ratings else 4.5

    def _calculate_avg_daily_orders(self) -> float:
        """计算平均日接单量"""
        if not self.state.memory['escort_stats']:
            return 0

        total_orders = sum(stats.get('total_orders', 0) for stats in self.state.memory['escort_stats'].values())
        active_days = 30  # 简化处理
        return total_orders / (len(self.state.memory['active_escorts']) * active_days) if self.state.memory['active_escorts'] else 0