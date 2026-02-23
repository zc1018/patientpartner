"""
增强版配置 - 基于北京真实数据
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import yaml


@dataclass
class BeijingRealDataConfig:
    """基于北京真实数据的增强配置"""

    # ========== 医院真实数据 ==========
    hospitals: List[Dict] = field(default_factory=lambda: [
        # 顶级三甲（日门诊量 1-2 万）
        {"name": "协和医院", "daily_visits": 15000, "elderly_ratio": 0.45, "tier": "top",
         "district": "东城", "lat": 39.9139, "lon": 116.4147},
        {"name": "301医院", "daily_visits": 12000, "elderly_ratio": 0.50, "tier": "top",
         "district": "海淀", "lat": 39.9075, "lon": 116.3395},
        {"name": "北医三院", "daily_visits": 10000, "elderly_ratio": 0.40, "tier": "top",
         "district": "海淀", "lat": 39.9987, "lon": 116.3644},

        # 大型三甲（日门诊量 5000-8000）
        {"name": "阜外医院", "daily_visits": 8000, "elderly_ratio": 0.55, "tier": "large",
         "district": "西城", "lat": 39.9247, "lon": 116.3486},
        {"name": "天坛医院", "daily_visits": 7000, "elderly_ratio": 0.50, "tier": "large",
         "district": "东城", "lat": 39.8826, "lon": 116.4117},
        {"name": "安贞医院", "daily_visits": 6500, "elderly_ratio": 0.52, "tier": "large",
         "district": "朝阳", "lat": 39.9789, "lon": 116.4119},
        {"name": "朝阳医院", "daily_visits": 6000, "elderly_ratio": 0.42, "tier": "large",
         "district": "朝阳", "lat": 39.9214, "lon": 116.4357},

        # 中型三甲（日门诊量 3000-5000）
        {"name": "宣武医院", "daily_visits": 5000, "elderly_ratio": 0.48, "tier": "medium",
         "district": "西城", "lat": 39.8889, "lon": 116.3611},
        {"name": "友谊医院", "daily_visits": 4500, "elderly_ratio": 0.45, "tier": "medium",
         "district": "西城", "lat": 39.8736, "lon": 116.3564},
        {"name": "同仁医院", "daily_visits": 4000, "elderly_ratio": 0.40, "tier": "medium",
         "district": "东城", "lat": 39.9042, "lon": 116.4178},
    ])

    # ========== 疾病真实分布 ==========
    disease_distribution: Dict[str, float] = field(default_factory=lambda: {
        "高血压": 0.35,      # 最常见
        "糖尿病": 0.20,      # 第二常见
        "心脏病": 0.15,      # 较常见
        "骨科疾病": 0.10,    # 老年人常见
        "呼吸系统": 0.08,    # 季节性高发
        "消化系统": 0.07,    # 常见
        "其他": 0.05,        # 其他疾病
    })

    # ========== 北京区域付费能力 ==========
    district_payment_ability: Dict[str, Dict] = field(default_factory=lambda: {
        # 高端区域（人均可支配收入 10-15 万/年）
        "朝阳": {"income_level": "high", "price_multiplier": 1.3, "population": 3_500_000},
        "海淀": {"income_level": "high", "price_multiplier": 1.25, "population": 3_600_000},
        "西城": {"income_level": "high", "price_multiplier": 1.35, "population": 1_200_000},
        "东城": {"income_level": "high", "price_multiplier": 1.30, "population": 900_000},

        # 中端区域（人均可支配收入 7-10 万/年）
        "丰台": {"income_level": "medium", "price_multiplier": 1.0, "population": 2_200_000},
        "石景山": {"income_level": "medium", "price_multiplier": 0.95, "population": 600_000},
        "昌平": {"income_level": "medium", "price_multiplier": 0.90, "population": 2_100_000},

        # 低端区域（人均可支配收入 5-7 万/年）
        "大兴": {"income_level": "low", "price_multiplier": 0.80, "population": 1_800_000},
        "通州": {"income_level": "low", "price_multiplier": 0.85, "population": 1_600_000},
        "房山": {"income_level": "low", "price_multiplier": 0.75, "population": 1_200_000},
    })

    # ========== 多渠道获客配置 ==========
    acquisition_channels: List[Dict] = field(default_factory=lambda: [
        {
            "name": "滴滴App推荐",
            "type": "online",
            "daily_exposure": 100_000,  # 日曝光量
            "click_rate": 0.02,         # 点击率
            "conversion_rate": 0.15,    # 转化率
            "cost_per_order": 50,       # 获客成本
        },
        {
            "name": "医院驻点推广",
            "type": "offline",
            "daily_exposure": 500,      # 日接触人数
            "click_rate": 0.60,         # 咨询率
            "conversion_rate": 0.40,    # 转化率
            "cost_per_order": 30,       # 获客成本（人力成本分摊）
            "hospitals": ["协和医院", "301医院", "北医三院"],  # 驻点医院
        },
        {
            "name": "社区推广",
            "type": "offline",
            "daily_exposure": 2_000,    # 日接触人数
            "click_rate": 0.25,         # 咨询率
            "conversion_rate": 0.25,    # 转化率
            "cost_per_order": 40,       # 获客成本
            "target_districts": ["朝阳", "海淀", "西城"],  # 目标区域
        },
        {
            "name": "口碑传播",
            "type": "organic",
            "daily_exposure": 0,        # 基于已有用户
            "click_rate": 0.80,         # 推荐率
            "conversion_rate": 0.50,    # 转化率
            "cost_per_order": 0,        # 零成本
            "trigger_condition": "rating >= 4.5",  # 触发条件
        },
    ])

    # ========== 老年人付费能力分布 ==========
    elderly_income_distribution: Dict[str, Dict] = field(default_factory=lambda: {
        "低收入": {
            "ratio": 0.30,              # 占比 30%
            "monthly_income": 3500,     # 月收入 3500 元
            "max_price": 150,           # 最高接受价格
            "repurchase_prob": 0.15,    # 复购概率低
        },
        "中等收入": {
            "ratio": 0.50,              # 占比 50%
            "monthly_income": 6000,     # 月收入 6000 元
            "max_price": 250,           # 最高接受价格
            "repurchase_prob": 0.30,    # 复购概率中等
        },
        "高收入": {
            "ratio": 0.20,              # 占比 20%
            "monthly_income": 12000,    # 月收入 12000 元
            "max_price": 500,           # 最高接受价格
            "repurchase_prob": 0.45,    # 复购概率高
        },
    })

    # ========== 季节性因素 ==========
    seasonal_factors: Dict[str, float] = field(default_factory=lambda: {
        "春季": 1.1,   # 3-5月，呼吸道疾病高发
        "夏季": 0.9,   # 6-8月，就诊量下降
        "秋季": 1.0,   # 9-11月，正常
        "冬季": 1.2,   # 12-2月，心脑血管疾病高发
    })

    # ========== 驻点推广配置 ==========
    station_promotion: Dict = field(default_factory=lambda: {
        "enabled": True,
        "stations_per_hospital": 2,      # 每个医院驻点人数
        "daily_cost_per_station": 300,   # 每个驻点日成本
        "work_hours": (8, 18),           # 工作时间
        "target_hospitals": ["协和医院", "301医院", "北医三院"],  # 重点医院
    })

    def to_yaml(self, file_path: str):
        """保存配置到 YAML 文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.__dict__, f, allow_unicode=True, default_flow_style=False)


# 创建默认配置实例
beijing_config = BeijingRealDataConfig()

if __name__ == "__main__":
    # 保存配置
    beijing_config.to_yaml("src/config/beijing_real_data.yaml")
    print("✓ 北京真实数据配置已生成")

    # 打印统计
    print("\n【医院统计】")
    total_daily_visits = sum(h["daily_visits"] for h in beijing_config.hospitals)
    total_elderly = sum(h["daily_visits"] * h["elderly_ratio"] for h in beijing_config.hospitals)
    print(f"  总日门诊量: {total_daily_visits:,}")
    print(f"  老年人日门诊量: {total_elderly:,.0f}")

    print("\n【疾病分布】")
    for disease, ratio in beijing_config.disease_distribution.items():
        print(f"  {disease}: {ratio:.0%}")

    print("\n【区域付费能力】")
    total_pop = sum(d["population"] for d in beijing_config.district_payment_ability.values())
    print(f"  覆盖人口: {total_pop:,}")
    high_income_pop = sum(
        d["population"] for d in beijing_config.district_payment_ability.values()
        if d["income_level"] == "high"
    )
    print(f"  高收入区域人口: {high_income_pop:,} ({high_income_pop/total_pop:.1%})")

    print("\n【获客渠道】")
    for channel in beijing_config.acquisition_channels:
        print(f"  {channel['name']}: 日曝光 {channel['daily_exposure']:,}, 转化率 {channel['conversion_rate']:.0%}")
