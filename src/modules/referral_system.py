"""
NPS 口碑传播模块 - 基于金融行业和医疗行业基准数据
数据来源：integrated_data_config.py 中的 nps_parameters 配置

NPS = 推荐者(17.5%) - 批评者(40%) = -22.5%
口碑贡献新客：5-10%（目标提升至10%）
付费获客占比：90-95%
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class UserNPSCategory(Enum):
    """用户 NPS 分类"""
    PROMOTER = "promoter"    # 推荐者（评分9-10）
    PASSIVE = "passive"      # 被动者（评分7-8）
    DETRACTOR = "detractor"  # 批评者（评分0-6）


@dataclass
class ReferralRecord:
    """推荐记录"""
    referrer_user_id: str
    referred_user_id: str
    referral_day: int
    converted: bool = False       # 是否成功转化为订单
    conversion_day: Optional[int] = None


class ReferralSystem:
    """
    NPS 口碑传播系统

    基于医疗行业数据：
    - NPS = 推荐者17.5% - 批评者40% = -22.5%
    - 口碑贡献新客：5-10%（取中值7.5%）
    - 付费获客占比：90-95%
    - 患者推荐→新患者下单率：5-10%
    """

    # NPS 分类比例（来自 integrated_data_config.py）
    NPS_DISTRIBUTION = {
        UserNPSCategory.PROMOTER: 0.175,   # 推荐者17.5%
        UserNPSCategory.PASSIVE: 0.425,    # 被动者42.5%
        UserNPSCategory.DETRACTOR: 0.40,   # 批评者40%
    }

    # 推荐转化率（患者推荐→新患者下单率5-10%）
    REFERRAL_CONVERSION_RATE = 0.075  # 取中值7.5%

    # 口碑贡献新客比例（5-10%，取中值7.5%）
    ORGANIC_REFERRAL_RATIO = 0.075

    def __init__(self):
        # 用户 NPS 分类 {user_id: UserNPSCategory}
        self.user_nps: Dict[str, UserNPSCategory] = {}

        # 推荐记录
        self.referral_records: List[ReferralRecord] = []

        # 累计统计
        self.total_referrals: int = 0
        self.converted_referrals: int = 0
        self.total_organic_new_users: int = 0

        # 当前 NPS 分数
        self.current_nps: float = -0.225  # 初始值 -22.5%

        # 推荐激励机制是否启用
        self.referral_incentive_enabled: bool = False
        self.incentive_multiplier: float = 1.0  # 激励倍数

    def classify_user_nps(self, user_id: str, rating: float) -> UserNPSCategory:
        """
        根据评分对用户进行 NPS 分类

        Args:
            user_id: 用户ID
            rating: 用户对服务的评分（1-5分）

        Returns:
            UserNPSCategory: NPS 分类
        """
        # 将5分制转换为10分制
        score_10 = rating * 2

        if score_10 >= 9:
            category = UserNPSCategory.PROMOTER
        elif score_10 >= 7:
            category = UserNPSCategory.PASSIVE
        else:
            category = UserNPSCategory.DETRACTOR

        self.user_nps[user_id] = category
        return category

    def simulate_referral(self, user_id: str, day: int) -> Optional[str]:
        """
        模拟用户推荐行为

        只有推荐者（Promoter）才会主动推荐，
        且推荐转化率仅5-10%（医疗隐私敏感）

        Args:
            user_id: 用户ID
            day: 当前模拟天数

        Returns:
            Optional[str]: 被推荐的新用户ID（如果推荐成功）
        """
        category = self.user_nps.get(user_id)
        if category != UserNPSCategory.PROMOTER:
            return None

        # 推荐者推荐概率（考虑医疗隐私敏感性，推荐意愿低）
        referral_prob = min(1.0, 0.15 * self.incentive_multiplier)  # 上限1.0

        if random.random() > referral_prob:
            return None

        referred_id = f"referred_{user_id[:8]}_{day}"
        self.total_referrals += 1

        # 判断是否转化（5-10%转化率，上限1.0）
        conversion_rate = min(1.0, self.REFERRAL_CONVERSION_RATE * self.incentive_multiplier)
        converted = random.random() < conversion_rate

        record = ReferralRecord(
            referrer_user_id=user_id,
            referred_user_id=referred_id,
            referral_day=day,
            converted=converted,
            conversion_day=day + random.randint(1, 7) if converted else None,
        )
        self.referral_records.append(record)

        if converted:
            self.converted_referrals += 1
            self.total_organic_new_users += 1
            return referred_id

        return None

    def calculate_organic_new_users(self, total_new_users: int) -> int:
        """
        计算口碑带来的自然新用户数

        Args:
            total_new_users: 当日总新用户数

        Returns:
            int: 口碑贡献的新用户数
        """
        # 口碑贡献新客7.5%（5-10%取中值）
        organic_ratio = self.ORGANIC_REFERRAL_RATIO * self.incentive_multiplier
        return max(0, int(total_new_users * organic_ratio))

    def update_nps_score(self):
        """更新当前 NPS 分数"""
        if not self.user_nps:
            return

        promoters = sum(1 for c in self.user_nps.values() if c == UserNPSCategory.PROMOTER)
        detractors = sum(1 for c in self.user_nps.values() if c == UserNPSCategory.DETRACTOR)
        total = len(self.user_nps)

        self.current_nps = (promoters - detractors) / total if total > 0 else -0.225

    def enable_referral_incentive(self, multiplier: float = 2.0):
        """
        启用推荐激励机制

        Args:
            multiplier: 激励倍数（默认2倍，即推荐意愿和转化率翻倍）
        """
        self.referral_incentive_enabled = True
        self.incentive_multiplier = multiplier

    def get_statistics(self) -> Dict:
        """获取口碑传播统计数据"""
        self.update_nps_score()

        nps_distribution = {
            "promoters": sum(1 for c in self.user_nps.values() if c == UserNPSCategory.PROMOTER),
            "passives": sum(1 for c in self.user_nps.values() if c == UserNPSCategory.PASSIVE),
            "detractors": sum(1 for c in self.user_nps.values() if c == UserNPSCategory.DETRACTOR),
        }

        referral_conversion_rate = (
            self.converted_referrals / self.total_referrals
            if self.total_referrals > 0 else 0
        )

        return {
            "current_nps": self.current_nps,
            "nps_distribution": nps_distribution,
            "total_referrals": self.total_referrals,
            "converted_referrals": self.converted_referrals,
            "referral_conversion_rate": referral_conversion_rate,
            "total_organic_new_users": self.total_organic_new_users,
            "organic_referral_ratio": self.ORGANIC_REFERRAL_RATIO,
            "referral_incentive_enabled": self.referral_incentive_enabled,
            # 健康指标
            "is_nps_positive": self.current_nps > 0,
            "nps_target": 0,  # 目标：从-22.5%提升至0
        }
