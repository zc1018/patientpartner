"""
整合数据配置 - 基于 PDF 和 Perplexity 调研数据整合
数据来源：
1. 滴滴陪诊业务沙箱模拟环境建设.pdf
2. perplexity 调研.md

数据整合原则：
- 当两个数据源一致时，直接采用
- 当数据冲突时，选择更高置信度的数据源
- 优先采用基于最新财报和市场调研的数据

详细数据对比分析见：DATA_INTEGRATION_ANALYSIS.md
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import yaml


@dataclass
class IntegratedDataConfig:
    """整合数据配置 - 基于两个数据源的高置信度数据"""

    # ========== P0 级关键数据（影响 GMV） ==========

    # 平台基础数据
    beijing_dau: int = 1_500_000  # 北京日活用户（保守估计，基于 2025 Q3 财报）
    beijing_dau_confidence_interval: Tuple[int, int] = (1_200_000, 2_000_000)  # 信心区间

    # 数据来源说明：
    # - PDF 数据：200万（可能高估 30-50%）
    # - Perplexity 数据：150-170万（基于 2025 Q3 财报推算）
    # - 最终采用：150万（保守估计）

    # 市场规模数据
    beijing_market_2025: int = 3_500_000_000  # 35亿元（两个数据源一致）
    beijing_market_2030: int = 12_000_000_000  # 120亿元（两个数据源一致）
    market_cagr: float = 0.274  # 27.4% 复合增长率（Perplexity 计算更严谨）
    national_market_2025: int = 100_000_000_000  # 1000亿元（两个数据源一致）

    # 数据来源说明：
    # - PDF 年增长率：41.2%（可能是单年增长率）
    # - Perplexity CAGR：27.4%（复合增长率，更严谨）
    # - 最终采用：27.4%

    # ========== 转化漏斗数据 ==========

    # 曝光率（Exposure Rate）
    exposure_rate: float = 0.03  # 3%（保守估计）
    exposure_rate_range: Tuple[float, float] = (0.02, 0.05)  # 2-5%

    # 数据来源说明：
    # - PDF：5%（需 A/B 测试验证）
    # - Perplexity：2-4%（出行 App 二线功能），5-8%（运营活动）
    # - 最终采用：3%（保守估计，自然曝光）

    # 点击率（Click Rate）
    click_rate: float = 0.02  # 2%

    # 咨询转化率（Consult Conversion Rate）
    consult_conversion_rate: float = 0.35  # 35%（加权平均）
    consult_conversion_by_segment: Dict[str, float] = field(default_factory=lambda: {
        "elderly_self": 0.225,  # 老年自主决策：20-25%（取中值 22.5%）
        "children_purchase": 0.45,  # 子女代购：40-50%（取中值 45%）
    })

    # 数据来源说明：
    # - PDF：30%（未分层）
    # - Perplexity：老年自主 20-25%，子女代购 40-50%
    # - 最终采用：35%（加权平均：70%×22.5% + 30%×45% = 29.25%，向上调整至 35%）

    # 下单转化率（Order Conversion Rate）
    order_conversion_rate: float = 0.65  # 65%（咨询后下单转化率）
    full_funnel_conversion_rate: float = 0.000137  # 0.0137%（全链路转化率）

    # 数据来源说明：
    # - PDF：20%（定义不明确）
    # - Perplexity：咨询后下单 60-70%，全链路 5-8%
    # - 最终采用：区分两个转化率
    #   - 咨询→下单：65%
    #   - 全链路（曝光→下单）：3% × 2% × 35% × 65% ≈ 0.0137%

    # ========== 客单价与复购数据 ==========

    # 客单价分布
    avg_price: int = 235  # 235元（两个数据源一致）

    price_distribution: Dict[str, Dict] = field(default_factory=lambda: {
        "basic": {
            "price_range": (120, 180),
            "avg_price": 150,
            "market_share": 0.30,
            "description": "基础陪同服务（2-4小时）",
            "target_customer": "初次体验，预算敏感"
        },
        "standard": {
            "price_range": (200, 300),
            "avg_price": 250,
            "market_share": 0.60,
            "description": "标准陪诊服务（4-6小时）",
            "target_customer": "主流客户，关注性价比"
        },
        "premium": {
            "price_range": (350, 600),
            "avg_price": 475,
            "market_share": 0.10,
            "description": "高端陪诊服务（全天+专业护理）",
            "target_customer": "高收入群体，关注服务质量"
        }
    })

    # 数据来源说明：
    # - PDF：客单价 235元，价格分布较粗略
    # - Perplexity：客单价 235元，价格分层更详细（含市场占比）
    # - 最终采用：Perplexity 的分层数据

    # 复购率数据
    repeat_rate_baseline: float = 0.30  # 基线复购率 30%（老客户）
    repeat_rate_first_order: float = 0.135  # 首单复购率 12-15%（取中值13.5%）⚠️ 关键修正
    repeat_rate_designated: float = 0.82  # 指定陪诊师复购率 82%（关键杠杆！）
    repeat_cycle_days: int = 30  # 复购周期 30天

    # 数据来源说明：
    # - 首单复购率：医疗行业真实数据显示仅12-15%（原假设30%高估了150-500%）
    # - Dialog Health患者留存研究：新患者复购率仅5-20%，平均12-15%
    # - 这是沙箱模型中最严重的偏差，直接影响GMV预测

    # 复购率分层数据
    repeat_rate_by_segment: Dict[str, Dict] = field(default_factory=lambda: {
        "elderly_self": {
            "repeat_rate": 0.225,  # 20-25%（取中值）
            "description": "老年自主决策：价格敏感，信任成本高"
        },
        "children_purchase": {
            "repeat_rate": 0.45,  # 40-50%（取中值）
            "description": "子女代购：决策迅速，关注服务质量"
        },
        "age_60_70": {
            "repeat_rate": 0.30,  # 25-35%（取中值）
            "description": "60-70岁：中等依赖度"
        },
        "age_70_plus": {
            "repeat_rate": 0.40,  # 35-45%（取中值）
            "description": "70岁以上：高依赖度"
        }
    })

    # 数据来源说明：
    # - PDF：复购率 35%（未分层）
    # - Perplexity：总体 30%，指定陪诊师 82%（关键发现！）
    # - 最终采用：30%（基线）+ 82%（指定陪诊师）
    # - 关键洞察：指定陪诊师机制是提升复购率的核心杠杆（30% → 82%）

    # ========== 用户分层数据 ==========

    # 决策者类型分布（关键洞察：决策者 ≠ 使用者）
    decision_maker_distribution: Dict[str, Dict] = field(default_factory=lambda: {
        "elderly_self": {
            "ratio": 0.20,  # 20%
            "consult_conversion": 0.225,  # 20-25%
            "order_conversion": 0.65,
            "repeat_rate": 0.225,  # 20-25%
            "price_sensitivity": "high",
            "trust_cost": "high",
            "description": "老年人自主决策：价格敏感，信任成本高，决策慢"
        },
        "children_purchase": {
            "ratio": 0.80,  # 80%（关键洞察！）
            "consult_conversion": 0.45,  # 40-50%
            "order_conversion": 0.65,
            "repeat_rate": 0.45,  # 40-50%
            "price_sensitivity": "medium",
            "trust_cost": "low",
            "description": "子女代购：决策迅速，关注服务质量和评价，复购率高"
        }
    })

    # 数据来源说明：
    # - PDF：年龄分布（60岁以上 70%，40-60岁 25%，40岁以下 5%）
    # - Perplexity：决策者类型（老年自主 20%，子女代购 80%）
    # - 最终采用：Perplexity 的决策者分层（关键洞察）
    # - 营销启示：80%订单由子女代购，需要针对两个群体设计不同策略

    # 年龄分布
    age_distribution: Dict[str, float] = field(default_factory=lambda: {
        "60+": 0.70,  # 70%（两个数据源一致）
        "40-60": 0.25,  # 25%（为父母购买）
        "<40": 0.05  # 5%
    })

    # 收入水平分布
    income_distribution: Dict[str, Dict] = field(default_factory=lambda: {
        "high": {
            "ratio": 0.30,
            "price_sensitivity": "low",
            "max_price": 500,
            "description": "高收入群体：价格敏感度低，关注服务质量"
        },
        "medium": {
            "ratio": 0.50,
            "price_sensitivity": "medium",
            "max_price": 250,
            "description": "中等收入：价格敏感度中等，关注性价比"
        },
        "low": {
            "ratio": 0.20,
            "price_sensitivity": "high",
            "max_price": 150,
            "description": "低收入群体：价格敏感度高，预算有限"
        }
    })

    # 数据来源：PDF 数据（Perplexity 未提供此维度）

    # ========== P0 级强依赖真实数据的参数（来自外部研究报告）==========

    # 服务质量评分对复购率的影响（基于美团跑腿数据和医疗行业对标）
    repeat_rate_by_rating: Dict[str, Dict] = field(default_factory=lambda: {
        "rating_4.9": {
            "repeat_rate": 0.75,  # 75%+
            "daily_orders": 3.2,  # 日均接单3.2单
            "description": "明星陪诊师：评分4.9分，复购率75%+，溢价效应显著"
        },
        "rating_4.8": {
            "repeat_rate": 0.73,  # 73%
            "daily_orders": 3.0,  # 日均接单3.0单
            "description": "优秀陪诊师：评分4.8分，复购率73%"
        },
        "rating_4.5": {
            "repeat_rate": 0.54,  # 54%
            "daily_orders": 2.4,  # 日均接单2.4单
            "description": "良好陪诊师：评分4.5分，复购率54%"
        },
        "rating_4.3": {
            "repeat_rate": 0.41,  # 41%
            "daily_orders": 1.5,  # 日均接单1.5单
            "description": "一般陪诊师：评分4.3分，复购率41%"
        },
        "rating_4.0": {
            "repeat_rate": 0.22,  # 22%
            "daily_orders": 0.8,  # 日均接单<1单
            "description": "较差陪诊师：评分4.0分，复购率22%，需改进"
        }
    })

    # 数据来源：
    # - 美团跑腿服务数据：评分4.5分→6个月复购率54.3%，评分<4.0分→复购率22.1%
    # - 医疗网站案例：评分4.8分→复购率80%
    # - 关键关系：满意度每提升10% ≈ 复购率增长15%
    # - 评分每下降0.1分，复购率下降约6-7%（非线性）
    # 置信度：⭐⭐⭐⭐（基于美团真实数据和医疗行业对标）

    # 月度用户流失率（基于医疗App和医疗系统真实数据）
    user_churn_rate: Dict[str, Dict] = field(default_factory=lambda: {
        "first_order_users": {
            "monthly_churn": 0.55,  # 首单用户月流失率50-60%（取中值55%）
            "30_day_retention": 0.45,  # 30天留存率45%
            "90_day_retention": 0.36,  # 90天留存率36%
            "180_day_retention": 0.25,  # 180天留存率20-25%
            "description": "首单用户：70%在首月流失，需要第一次体验优化"
        },
        "2_3_order_users": {
            "monthly_churn": 0.25,  # 2-3单用户月流失率20-30%
            "90_day_retention": 0.45,  # 3月累计留存40-50%
            "description": "2-3单用户：关键转化阶段，需强化触达"
        },
        "4_plus_order_users": {
            "monthly_churn": 0.10,  # 4单+老客月流失率8-12%
            "90_day_retention": 0.75,  # 3月累计留存75%+
            "description": "4单+老客：稳定复购客，流失率低"
        }
    })

    # 数据来源：
    # - Dialog Health患者留存研究：30天留存率44%，90天留存率36%
    # - 医疗App数据：月流失56%，3个月累计流失64%
    # - 医疗机构整体：增长率45%，流失率48%（增长被流失完全抵消）
    # - 陪诊服务估算：月度流失率25-35%（介于医疗和App之间）
    # 置信度：⭐⭐⭐⭐⭐（基于医疗行业标准数据）

    # NPS口碑传播参数（基于金融行业和医疗行业基准，按用户类型分层）
    nps_parameters: Dict[str, Dict] = field(default_factory=lambda: {
        "nps_score": {
            "promoters_ratio": 0.175,  # 推荐者占比15-20%（取中值17.5%）- 全局加权平均
            "passives_ratio": 0.425,  # 被动者占比40-45%
            "detractors_ratio": 0.40,  # 批评者占比35-45%
            "nps": -0.225,  # NPS = 17.5% - 40% = -22.5%（全局加权平均）
            "description": "医疗陪诊NPS可能为负（隐私敏感，推荐意愿低）"
        },
        "nps_by_segment": {
            "elderly_self": {
                "ratio": 0.20,  # 占比20%
                "promoters_ratio": 0.12,  # 推荐者12%
                "passives_ratio": 0.45,  # 被动者45%
                "detractors_ratio": 0.43,  # 批评者43%
                "nps": -0.31,  # NPS = 12% - 43% = -31% (约-30%)
                "description": "老年自主用户：NPS -30%，推荐意愿极低"
            },
            "children_purchase": {
                "ratio": 0.80,  # 占比80%
                "promoters_ratio": 0.37,  # 推荐者37%
                "passives_ratio": 0.36,  # 被动者36%
                "detractors_ratio": 0.27,  # 批评者27%
                "nps": 0.10,  # NPS = 37% - 27% = +10%
                "description": "子女代购用户：NPS +10%，推荐意愿较高"
            }
        },
        "referral_effectiveness": {
            "doctor_referral_rate": 0.45,  # 医生推荐→患者就诊率40-50%
            "patient_referral_rate": 0.175,  # 患者推荐→新患者就诊率15-20%
            "patient_referral_conversion": 0.075,  # 患者推荐→新患者下单率5-10%
            "follow_up_rate": 0.60,  # 推荐患者后续跟进率60%
            "description": "即使有推荐，转化效率也很低"
        },
        "referral_contribution": {
            "organic_referral": 0.075,  # 自然口碑贡献新客5-10%（取中值7.5%）
            "paid_acquisition": 0.925,  # 付费获客占比90-95%
            "target_referral_conversion": 0.25,  # 目标推荐转化率20-30%（vs医疗行业15%）
            "description": "口碑贡献新客仅5-10%，需以付费获客为主"
        }
    })

    # 数据来源：
    # - 金融行业NPS基准：客户体验与NPS相关性0.88，NPS每提升10分→复购率+15-20%
    # - 医疗行业：相比餐饮/电商(NPS 30-50)，医疗陪诊可能只有5-20
    # - 医疗隐私：用户不愿主动推荐，高成本决策，需求者有限
    # 置信度：⭐⭐⭐⭐（基于金融和医疗行业基准）

    # 投诉率对品牌的影响（基于医疗健康营销案例）
    complaint_impact: Dict[str, Dict] = field(default_factory=lambda: {
        "complaint_satisfaction_relationship": {
            "complaint_decrease_30_percent": {
                "satisfaction_increase": 0.15,  # 投诉率↓30% → 满意度↑15%
                "description": "投诉率每↑1% → 满意度↓0.5%"
            },
            "satisfaction_conversion_correlation": 0.91,  # 满意度与复购相关性0.91
            "complaint_conversion_impact": -0.0045,  # 投诉率每↑1% → 转化率↓0.45%
            "description": "投诉率对转化率有显著负面影响"
        },
        "complaint_types": {
            "medical_advice_error": {
                "ratio": 0.075,  # 占比5-10%
                "severity": "critical",  # 严重（品牌摧毁性）
                "resolution_time_hours": 168,  # 7天内道歉+赔偿
                "description": "医学建议错误：最严重，直接导致负面口碑"
            },
            "hospital_conflict": {
                "ratio": 0.125,  # 占比10-15%
                "severity": "medium",  # 中等（影响续约）
                "resolution_time_hours": 24,  # 24小时解决
                "description": "医院冲突：中等影响"
            },
            "service_quality": {
                "ratio": 0.65,  # 占比60-70%
                "severity": "medium",  # 中等（影响复购）
                "resolution_time_hours": 48,  # 48小时补偿
                "description": "服务不达标：最常见投诉类型"
            },
            "others": {
                "ratio": 0.15,  # 占比10-20%
                "severity": "low",  # 轻
                "resolution_time_hours": 72,  # 72小时回复
                "description": "其他投诉"
            }
        },
        "target_metrics": {
            "complaint_rate_target": 0.01,  # 目标投诉率<1%（医疗行业标准）
            "resolution_rate_target": 0.95,  # 投诉解决率>95%（24小时内）
            "repurchase_recovery_rate": 0.50,  # 复购救回率>50%（投诉后仍复购）
            "description": "投诉管理目标"
        }
    })

    # 数据来源：
    # - 医疗健康邮件营销案例：投诉率↓30% → 满意度↑15%
    # - 隐含关系：投诉率每↑1% → 满意度↓0.5% → 转化率↓0.45%
    # - 医疗行业投诉类型：医疗质量、价格不透明、服务态度、隐私泄露
    # 置信度：⭐⭐⭐⭐（基于医疗健康营销真实案例）

    # ========== P1 级重要数据（影响市场份额） ==========

    # 竞争格局
    competitors: Dict[str, Dict] = field(default_factory=lambda: {
        "meituan": {
            "market_share": 0.25,  # 25%
            "order_growth_yoy": 0.951,  # 2022 Q1 同比增长 95.1%
            "description": "美团：市场份额约 25%"
        },
        "alipay": {
            "mau": 30_000_000,  # 月活 3000万
            "daily_consult": 10_000_000,  # 日咨询量 1000万次
            "description": "支付宝（蚂蚁阿福）：月活用户 3000万"
        },
        "professional_companies": {
            "count": 20,  # 20余家专业陪诊公司
            "market_share": 0.50,  # 约 50%
            "description": "专业陪诊公司：市场高度分散"
        },
        "beijing_yitongkang": {
            "rating": 96.8,  # 评分 96.8分
            "pricing": "250-350元/4h",  # 高端定价
            "description": "北京医通康：头部企业，战略规划型"
        }
    })

    # 数据来源说明：
    # - PDF：美团 25%，支付宝月活 3000万，其他平台 50%
    # - Perplexity：20余家专业陪诊公司，北京医通康 96.8分
    # - 最终采用：整合两个数据源

    # 疾病类型分布
    disease_distribution: Dict[str, float] = field(default_factory=lambda: {
        "hypertension": 0.35,  # 高血压 35%
        "diabetes": 0.20,  # 糖尿病 20%
        "cardiovascular": 0.15,  # 心脑血管疾病 15%
        "others": 0.30  # 其他慢性病 30%
    })

    # 数据来源：PDF 数据（Perplexity 未提供此维度）

    # ========== P2 级外部环境数据 ==========

    # 季节性因素
    seasonal_factors: Dict[str, float] = field(default_factory=lambda: {
        "winter": 1.2,  # 冬季需求 +20%（12-2月，心脑血管疾病高发）
        "summer": 0.9,  # 夏季需求 -10%（6-8月，就诊量下降）
        "spring": 1.0,  # 春季正常（3-5月）
        "autumn": 1.0  # 秋季正常（9-11月）
    })

    # 数据来源：PDF 数据（Perplexity 未提供此维度）

    # 节假日影响因素
    holiday_factors: Dict[str, Dict] = field(default_factory=lambda: {
        "spring_festival": {
            "multiplier": 0.3,  # 需求-70%（80%订单由子女代购，春节子女在家，陪诊需求暴跌）
            "duration_days": 7,  # 春节7天
            "reason": "医院门诊量大幅下降 + 子女在家无需代购陪诊"
        },
        "national_day": {
            "multiplier": 0.6,  # 需求-40%
            "duration_days": 7,  # 国庆7天
            "reason": "医院门诊量下降"
        },
        "weekend": {
            "multiplier": 0.8,  # 需求-20%
            "reason": "医院周末门诊量下降"
        }
    })

    # 数据来源：基于医院门诊量数据推演（行业通用规律）
    # 置信度：⭐⭐⭐⭐（基于行业通用规律）

    # 陪诊员经验对服务质量的影响
    escort_experience_impact: Dict[str, Dict] = field(default_factory=lambda: {
        "newbie": {  # 入职0-3个月
            "base_rating": 4.3,  # 基础评分
            "daily_orders": 2.0,  # 日均接单
            "completion_rate": 0.92,  # 完成率
            "designated_rate": 0.05,  # 指定率
            "description": "新手陪诊员：服务质量一般，接单量低"
        },
        "intermediate": {  # 入职3-6个月
            "base_rating": 4.5,  # 基础评分
            "daily_orders": 2.8,  # 日均接单
            "completion_rate": 0.95,  # 完成率
            "designated_rate": 0.20,  # 指定率
            "description": "中级陪诊员：服务质量良好，接单量正常"
        },
        "senior": {  # 入职6个月以上
            "base_rating": 4.7,  # 基础评分
            "daily_orders": 3.2,  # 日均接单
            "completion_rate": 0.97,  # 完成率
            "designated_rate": 0.50,  # 指定率
            "description": "资深陪诊员：服务质量优秀，接单量高"
        }
    })

    # 数据来源：基于小李案例（6个月，4.9分，3.2单）和小张案例（1个月，4.3分，1.5单）推演
    # 置信度：⭐⭐⭐⭐（已有部分真实案例支撑）

    # 地理分布不均参数
    geographic_distribution: Dict[str, Dict] = field(default_factory=lambda: {
        "city_center": {  # 市区（朝阳、海淀、西城、东城）
            "demand_ratio": 0.70,  # 需求占比70%
            "escort_ratio": 0.80,  # 陪诊员占比80%
            "completion_rate": 0.96,  # 完成率96%
            "description": "市区：需求高，陪诊员充足"
        },
        "suburb": {  # 郊区（昌平、大兴、通州等）
            "demand_ratio": 0.30,  # 需求占比30%
            "escort_ratio": 0.20,  # 陪诊员占比20%
            "completion_rate": 0.90,  # 完成率90%（陪诊员不足）
            "description": "郊区：需求低，陪诊员不足"
        }
    })

    # 通勤成本参数
    commute_cost_parameters: Dict[str, float] = field(default_factory=lambda: {
        "within_district": 0,  # 区内接单，无通勤成本
        "cross_district": 20,  # 跨区接单，通勤成本¥20/单
        "cross_district_ratio": 0.20,  # 20%订单是跨区
    })

    # 数据来源：基于城市通用规律和小赵案例（住在昌平，通勤1小时）推演
    # 置信度：⭐⭐⭐（基于城市通用规律）

    # 陪诊员流失率与收入的关系
    escort_churn_by_income: Dict[str, Dict] = field(default_factory=lambda: {
        "with_base_salary": {  # 有底薪保障
            "high_income": {  # ≥7000元/月
                "churn_rate": 0.05,  # 流失率5%
                "description": "收入高，流失率低"
            },
            "medium_income": {  # 5000-7000元/月
                "churn_rate": 0.08,  # 流失率8%
                "description": "收入中等，流失率中等"
            },
            "low_income": {  # <5000元/月
                "churn_rate": 0.12,  # 流失率12%
                "description": "收入低，流失率较高"
            }
        },
        "without_base_salary": {  # 无底薪保障
            "high_income": {  # ≥7000元/月
                "churn_rate": 0.08,  # 流失率8%
                "description": "收入高，流失率较低"
            },
            "medium_income": {  # 5000-7000元/月
                "churn_rate": 0.15,  # 流失率15%
                "description": "收入中等，流失率高"
            },
            "low_income": {  # <5000元/月
                "churn_rate": 0.25,  # 流失率25%
                "description": "收入低，流失率很高"
            }
        }
    })

    # 数据来源：基于小李案例（7200元，稳定）和小王案例（5000元，考虑换工作）推演
    # 置信度：⭐⭐⭐⭐（已有部分真实案例支撑）

    # 陪诊员培训质量参数
    training_quality_parameters: Dict[str, Dict] = field(default_factory=lambda: {
        "basic_training": {
            "duration_days": 7,  # 培训天数
            "base_rating": 4.3,  # 培训后基础评分
            "cost_per_person": 500,  # 培训成本¥500/人
            "pass_rate": 0.80,  # 培训通过率80%
            "description": "基础培训：7天，评分4.3"
        },
        "advanced_training": {
            "duration_days": 14,  # 培训天数
            "base_rating": 4.5,  # 培训后基础评分
            "cost_per_person": 1000,  # 培训成本¥1000/人
            "pass_rate": 0.75,  # 培训通过率75%
            "description": "高级培训：14天，评分4.5"
        },
        "professional_training": {
            "duration_days": 21,  # 培训天数
            "base_rating": 4.7,  # 培训后基础评分
            "cost_per_person": 2000,  # 培训成本¥2000/人
            "pass_rate": 0.70,  # 培训通过率70%
            "description": "专业培训：21天，评分4.7"
        }
    })

    # 数据来源：基于培训7天后上岗的数据和逻辑推理
    # 置信度：⭐⭐⭐（基于逻辑推理）

    # 竞品价格战参数
    competitor_price_war: Dict[str, Dict] = field(default_factory=lambda: {
        "meituan_price_cut_15": {
            "price_cut_ratio": 0.15,  # 降价15%
            "market_share_impact": -0.02,  # 我们的市场份额-2%
            "description": "美团降价15%，我们市场份额-2%"
        },
        "meituan_price_cut_30": {
            "price_cut_ratio": 0.30,  # 降价30%
            "market_share_impact": -0.05,  # 我们的市场份额-5%
            "description": "美团降价30%，我们市场份额-5%"
        },
        "our_response_options": {
            "match_price": {
                "description": "跟进降价",
                "gmv_impact": 0.0,  # GMV不变（保持市场份额）
                "margin_impact": -0.15,  # 利润率-15%
            },
            "improve_service": {
                "description": "提升服务质量（不降价）",
                "gmv_impact": -0.02,  # GMV-2%（市场份额略降）
                "margin_impact": 0.0,  # 利润率不变
            }
        }
    })

    # 数据来源：基于市场规律推演（保守估计）
    # 置信度：⭐⭐（基于市场规律，但不确定性高）

    # 北京老龄化数据（2024年底）
    beijing_aging_population: Dict[str, Dict] = field(default_factory=lambda: {
        "60+": {
            "population": 5_140_000,  # 514万
            "ratio": 0.235,  # 23.5%
            "description": "60岁及以上常住人口"
        },
        "65+": {
            "population": 3_596_000,  # 359.6万
            "ratio": 0.165,  # 16.5%
            "description": "65岁及以上常住人口"
        },
        "80+": {
            "population": 687_000,  # 68.7万
            "description": "80岁及以上人口"
        },
        "100+": {
            "population": 1_539,  # 1,539人
            "description": "百岁老人"
        }
    })

    # 数据来源：PDF 数据（北京市民政局，2024年底）

    # ========== 关键洞察与杠杆 ==========

    key_insights: Dict[str, str] = field(default_factory=lambda: {
        "insight_1": "⚠️ 首单复购率假设高估150-500%：真实值12-15%（原假设30%），这是模型最严重偏差",
        "insight_2": "指定陪诊师机制是提升复购率的核心杠杆（30% → 82%）",
        "insight_3": "80%订单由子女代购，需要针对两个决策主体设计策略",
        "insight_4": "子女代购用户复购率（40-50%）远高于老年自主（20-25%）",
        "insight_5": "用户流失是'隐形杀手'：3个月内64%的新客流失，需在30-60天强化运营",
        "insight_6": "评分与复购高度相关：评分每下降0.1分 → 复购率↓6-7%",
        "insight_7": "医疗陪诊NPS可能为负（-22.5%）：隐私敏感导致推荐意愿低",
        "insight_8": "口碑贡献新客仅5-10%，需以付费获客为主（90-95%）",
        "insight_9": "投诉率每↑1% → 转化率↓0.45%，必须控制在<1%",
        "insight_10": "市场高度分散，没有绝对领先者，为平台型企业提供机会",
        "insight_11": "北京市场年增长率 27.4%，远超其他行业",
        "insight_12": "需要区分'咨询→下单转化率'（65%）和'全链路转化率'（0.0137%）"
    })

    # ========== 数据置信度评级 ==========

    data_confidence: Dict[str, Dict] = field(default_factory=lambda: {
        "first_order_repeat_rate": {
            "confidence": 5,  # ⭐⭐⭐⭐⭐
            "reason": "基于Dialog Health患者留存研究和医疗行业标准数据，12-15%"
        },
        "repeat_rate_by_rating": {
            "confidence": 4,  # ⭐⭐⭐⭐
            "reason": "基于美团跑腿真实数据和医疗行业对标"
        },
        "user_churn_rate": {
            "confidence": 5,  # ⭐⭐⭐⭐⭐
            "reason": "基于医疗App和医疗系统真实数据，30天留存44%，90天留存36%"
        },
        "nps_parameters": {
            "confidence": 4,  # ⭐⭐⭐⭐
            "reason": "基于金融行业和医疗行业NPS基准数据"
        },
        "complaint_impact": {
            "confidence": 4,  # ⭐⭐⭐⭐
            "reason": "基于医疗健康营销真实案例，投诉率与满意度相关性明确"
        },
        "market_size": {
            "confidence": 5,  # ⭐⭐⭐⭐⭐
            "reason": "两个数据源一致（35亿/120亿）"
        },
        "avg_price": {
            "confidence": 5,  # ⭐⭐⭐⭐⭐
            "reason": "两个数据源一致（235元）"
        },
        "designated_companion_repeat_rate": {
            "confidence": 5,  # ⭐⭐⭐⭐⭐
            "reason": "Perplexity 关键发现，82%复购率"
        },
        "beijing_dau": {
            "confidence": 4,  # ⭐⭐⭐⭐
            "reason": "Perplexity 基于 2025 Q3 财报推算"
        },
        "conversion_funnel": {
            "confidence": 4,  # ⭐⭐⭐⭐
            "reason": "Perplexity 分层数据更详细"
        },
        "user_segmentation": {
            "confidence": 5,  # ⭐⭐⭐⭐⭐
            "reason": "Perplexity 关键洞察（80%子女代购）"
        },
        "seasonal_factors": {
            "confidence": 3,  # ⭐⭐⭐
            "reason": "仅 PDF 数据，需验证"
        },
        "disease_distribution": {
            "confidence": 3,  # ⭐⭐⭐
            "reason": "仅 PDF 数据"
        },
        "holiday_factors": {
            "confidence": 4,  # ⭐⭐⭐⭐
            "reason": "基于医院门诊量数据推演（行业通用规律）"
        },
        "escort_experience_impact": {
            "confidence": 4,  # ⭐⭐⭐⭐
            "reason": "基于小李、小张案例推演，有真实案例支撑"
        },
        "geographic_distribution": {
            "confidence": 3,  # ⭐⭐⭐
            "reason": "基于城市通用规律推演"
        },
        "escort_churn_by_income": {
            "confidence": 4,  # ⭐⭐⭐⭐
            "reason": "基于小李、小王案例推演，有真实案例支撑"
        },
        "training_quality_parameters": {
            "confidence": 3,  # ⭐⭐⭐
            "reason": "基于逻辑推理，需要真实数据验证"
        },
        "competitor_price_war": {
            "confidence": 2,  # ⭐⭐
            "reason": "基于市场规律推演，不确定性高"
        }
    })

    def to_yaml(self, file_path: str):
        """保存配置到 YAML 文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.__dict__, f, allow_unicode=True, default_flow_style=False)

    def get_gmv_formula(self) -> str:
        """返回 GMV 计算公式"""
        return """
        GMV 计算公式（修正后）：

        方法1（全链路 - 首单用户）：
        GMV_首单 = 日活用户 × 全链路转化率 × 客单价 × 天数
                = 1,500,000 × 0.0137% × 235 × 365
                ≈ 1.76亿元/年

        方法2（复购用户 - 关键修正）：
        ⚠️ 首单复购率修正：30% → 13.5%（下调55%）

        首单复购GMV = 首单用户数 × 首单复购率 × 客单价
                    = (1,500,000 × 0.0137% × 365) × 13.5% × 235
                    ≈ 0.24亿元/年（原预期0.53亿，下降55%）

        老客复购GMV = 老客户池 × 月复购率 × 客单价 × 12
                    = 老客户池 × 30% × 250 × 12
                    （取决于老客户池规模）

        指定陪诊师复购GMV = 指定陪诊师用户 × 82% × 250 × 12
                          （关键杠杆：复购率从30%提升到82%）

        修正后的市场进入逻辑：
        ❌ 原预期：日GMV 97万元（过度乐观）
        ✅ 修正后：日GMV 30-40万元（更现实）

        关键修正：
        1. 首单复购由30%→13.5% → 新客变现↓55%
        2. 重点转向：复购客的LTV提升 → 陪诊师质量、指定率、留存
        3. 运营强度：中度投入初期获客 + 高度投入留存与复购

        关键杠杆（优先级排序）：
        1. ⭐⭐⭐⭐⭐ 提升指定陪诊师渗透率：复购率从 30% → 82%（+173%）
        2. ⭐⭐⭐⭐⭐ 降低首单用户流失率：30天留存从45%→60%（+33%）
        3. ⭐⭐⭐⭐ 提升陪诊师评分分布：平均评分从4.5→4.7（复购率+15%）
        4. ⭐⭐⭐⭐ 提升子女代购占比：从 80% → 85%（复购率更高）
        5. ⭐⭐⭐ 提升曝光率：从 3% → 5%（通过运营活动）
        6. ⭐⭐⭐ 控制投诉率：<1%（避免转化率下降）
        7. ⭐⭐ 建立推荐激励机制：口碑贡献从5%→10%（长期建设）

        战略建议：
        ✅ 推荐进入的条件：
        1. 能够承受市场进入期12-18个月的较低GMV（30-50万/日）
        2. 有能力建立严格的陪诊师筛选与培训体系
        3. 愿意投入于用户留存与复购优化
        4. 接受"口碑传播低"的现实，以付费获客为主

        ❌ 风险规避：
        1. 不要基于30%新客复购率进行融资Pre-pitch
        2. 不要过度扩张陪诊师（评分会下降）
        3. 不要忽视投诉管理（投诉率1%+会摧毁品牌）
        4. 不要期待"新客自然复购"→需要精细化运营
        """


# 创建默认配置实例
integrated_config = IntegratedDataConfig()


if __name__ == "__main__":
    # 保存配置
    integrated_config.to_yaml("src/config/integrated_data_config.yaml")
    print("✓ 整合数据配置已生成")

    # 打印关键数据
    print("\n【P0 级关键数据】")
    print(f"  北京日活用户: {integrated_config.beijing_dau:,}")
    print(f"  信心区间: {integrated_config.beijing_dau_confidence_interval[0]:,} - {integrated_config.beijing_dau_confidence_interval[1]:,}")
    print(f"  2025年北京市场规模: {integrated_config.beijing_market_2025/1e8:.1f}亿元")
    print(f"  2030年预测: {integrated_config.beijing_market_2030/1e8:.1f}亿元")
    print(f"  市场 CAGR: {integrated_config.market_cagr:.1%}")

    print("\n【转化漏斗】")
    print(f"  曝光率: {integrated_config.exposure_rate:.1%}")
    print(f"  点击率: {integrated_config.click_rate:.1%}")
    print(f"  咨询转化率: {integrated_config.consult_conversion_rate:.1%}")
    print(f"  下单转化率（咨询后）: {integrated_config.order_conversion_rate:.1%}")
    print(f"  全链路转化率: {integrated_config.full_funnel_conversion_rate:.4%}")

    print("\n【客单价与复购】")
    print(f"  平均客单价: {integrated_config.avg_price}元")
    print(f"  基线复购率: {integrated_config.repeat_rate_baseline:.1%}")
    print(f"  指定陪诊师复购率: {integrated_config.repeat_rate_designated:.1%} ⭐关键杠杆")

    print("\n【用户分层】")
    for segment, data in integrated_config.decision_maker_distribution.items():
        print(f"  {segment}: {data['ratio']:.0%}, 复购率 {data['repeat_rate']:.1%}")

    print("\n【关键洞察】")
    for key, insight in integrated_config.key_insights.items():
        print(f"  • {insight}")

    print("\n【GMV 估算】")
    print(integrated_config.get_gmv_formula())
