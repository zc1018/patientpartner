"""
配置模块 - 定义所有模拟参数
"""
from dataclasses import dataclass, field
from typing import Tuple, List, Dict
import yaml


@dataclass
class SimulationConfig:
    """沙盘模拟配置参数"""

    # ========== 时间参数 ==========
    total_days: int = 90  # 模拟总天数
    time_step: str = "day"  # 时间步长: day/hour
    work_hours: Tuple[int, int] = (8, 18)  # 工作时间窗口

    # ========== 需求侧参数 ==========
    dau_base: int = 2_000_000  # 北京滴滴日活基数
    exposure_rate: float = 0.05  # 陪诊服务入口曝光率
    click_rate: float = 0.02  # 点击率
    consult_rate: float = 0.30  # 咨询转化率
    order_rate: float = 0.20  # 下单转化率

    price_mean: float = 200.0  # 客单价均值（元）
    price_std: float = 50.0  # 客单价标准差

    repurchase_prob: float = 0.135  # 首单复购概率 13.5%（基于Dialog Health研究修正后）
    repurchase_cycle_days: int = 30  # 复购周期（天）
    baseline_repeat_rate: float = 0.30  # 老客户复购率30%

    # 用户留存率参数（基于外部研究数据）
    first_order_retention_30d: float = 0.45  # 首单用户30天留存率
    first_order_retention_90d: float = 0.36  # 首单用户90天留存率
    existing_retention_90d: float = 0.75     # 老客90天留存率

    demand_volatility: float = 0.15  # 需求波动系数

    # ========== 供给侧参数 ==========
    initial_escorts: int = 15  # 初始陪诊员数量
    weekly_recruit: int = 5  # 每周招募人数
    recruit_cost: float = 500.0  # 单人招募成本（元）

    training_days: int = 7  # 培训周期（天）
    training_pass_rate: float = 0.80  # 培训通过率

    daily_order_limit: int = 3  # 陪诊员日接单上限
    monthly_churn_rate: float = 0.15  # 月流失率

    escort_commission: float = 0.70  # 陪诊员分成比例

    # ========== 服务参数 ==========
    service_duration_mean: float = 3.0  # 平均服务时长（小时）
    service_duration_std: float = 1.0  # 服务时长标准差

    service_success_rate: float = 0.95  # 服务成功率

    satisfaction_mean: float = 4.5  # 用户满意度均值（5分制）
    satisfaction_std: float = 0.3  # 满意度标准差

    covered_hospitals: List[str] = field(default_factory=lambda: [
        "协和医院", "301医院", "北医三院", "阜外医院", "天坛医院",
        "同仁医院", "朝阳医院", "安贞医院", "宣武医院", "积水潭医院"
    ])

    disease_types: List[str] = field(default_factory=lambda: [
        "糖尿病", "高血压", "心脏病", "慢性肾病", "呼吸系统疾病", "其他"
    ])

    # ========== 成本参数 ==========
    # 获客成本（CAC - Customer Acquisition Cost）
    cac_didi_app: float = 50.0  # 滴滴App推荐获客成本（元/单）
    cac_hospital_station: float = 30.0  # 医院驻点获客成本（元/单）
    cac_community: float = 40.0  # 社区推广获客成本（元/单）
    cac_organic: float = 0.0  # 口碑传播获客成本（元/单）

    # 运营成本（月度）
    monthly_staff_cost: float = 50_000.0  # 人力成本（客服、运营、技术）
    monthly_office_cost: float = 15_000.0  # 办公场地成本
    monthly_tech_cost: float = 10_000.0  # 技术维护成本（服务器、软件）
    monthly_marketing_cost: float = 30_000.0  # 营销推广成本

    # 保险成本
    escort_insurance_per_order: float = 5.0  # 陪诊员意外险（元/单）
    user_insurance_per_order: float = 3.0  # 用户服务险（元/单）

    # 平台成本
    platform_commission: float = 0.05  # 滴滴平台抽成比例（5%）
    payment_fee_rate: float = 0.006  # 支付手续费率（0.6%）

    # 毛利率
    gross_margin_rate: float = 0.30  # 毛利率30%（默认）

    # 渠道获客成本配置（从 integrated_data_config.yaml 读取）
    channel_cac: Dict = field(default_factory=lambda: {
        "default": 50,
        "online_ad": 80,
        "referral": 20,
        "hospital_partner": 150,
        "offline_promotion": 60,
    })

    # 其他成本
    customer_service_cost_per_order: float = 2.0  # 客服成本（元/单）
    refund_rate: float = 0.02  # 退款率（2%）
    bad_debt_rate: float = 0.01  # 坏账率（1%）

    # ========== LLM 参数 ==========
    llm_provider: str = "anthropic"  # openai / anthropic
    llm_model: str = "claude-sonnet-4-5-20250929"
    llm_api_key: str = ""  # 从环境变量读取
    llm_event_probability: float = 0.10  # 每日触发 LLM 事件的概率

    # ========== 招募参数 ==========
    recruit_decay_factor: float = 0.3  # 招募难度递增系数

    # ========== 其他参数 ==========
    random_seed: int = 42  # 随机种子
    enable_llm: bool = True  # 是否启用 LLM 功能

    @classmethod
    def from_yaml(cls, file_path: str) -> "SimulationConfig":
        """从 YAML 文件加载配置"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, file_path: str):
        """保存配置到 YAML 文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.__dict__, f, allow_unicode=True, default_flow_style=False)

    def validate(self):
        """验证配置参数的合理性"""
        assert self.total_days > 0, "模拟天数必须大于0"
        assert 0 < self.exposure_rate <= 1, "曝光率必须在(0,1]之间"
        assert 0 < self.click_rate <= 1, "点击率必须在(0,1]之间"
        assert 0 < self.consult_rate <= 1, "咨询转化率必须在(0,1]之间"
        assert 0 < self.order_rate <= 1, "下单转化率必须在(0,1]之间"
        assert self.price_mean > 0, "客单价均值必须大于0"
        assert 0 < self.escort_commission < 1, "分成比例必须在(0,1)之间"
        assert 0 < self.service_success_rate <= 1, "服务成功率必须在(0,1]之间"
        return True
