"""
数据模型 - 用户、陪诊员、订单
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import uuid4


class EscortStatus(Enum):
    """陪诊员状态"""
    TRAINING = "培训中"
    AVAILABLE = "可接单"
    SERVING = "服务中"
    REST = "休息"
    CHURNED = "已流失"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "待匹配"
    MATCHED = "已匹配"
    SERVING = "服务中"
    COMPLETED = "已完成"
    CANCELLED = "已取消"
    FAILED = "失败"


@dataclass
class User:
    """用户模型"""
    id: str = field(default_factory=lambda: str(uuid4()))
    order_time: datetime = field(default_factory=datetime.now)
    target_hospital: str = ""
    disease_type: str = ""
    service_period: str = "全天"  # 上午/下午/全天
    price_sensitivity: float = 0.5  # 0-1，越高越敏感
    is_repurchase: bool = False
    last_order_id: Optional[str] = None
    total_orders: int = 0

    # 决策者类型（子女代购 vs 老年自主）
    is_children_purchase: bool = True  # 80%子女代购，20%老年自主

    # 地理位置（北京坐标）
    location_lat: float = 39.9042   # 默认天安门
    location_lon: float = 116.4074
    location_district: str = "朝阳"  # 所在区域

    # 年龄分层
    age: int = 70  # 用户年龄
    is_app_capable: bool = True  # 是否能独立使用App（80+岁为False）

    # 增强版需求生成器扩展字段
    income_level: str = "中等收入"   # 收入等级
    channel_type: str = "online"     # 获客渠道类型

    # 用户生命周期状态
    lifecycle_state: str = "active"  # active/at_risk/silent/churned/reactivated
    days_since_last_order: int = 0

    # 指定陪诊师相关字段（新增）
    designated_escort_id: Optional[str] = None  # 用户指定的陪诊师ID
    history_escort_ids: List[str] = field(default_factory=list)  # 历史服务过的陪诊师ID列表
    last_escort_id: Optional[str] = None  # 上次服务的陪诊师ID
    last_escort_rating: Optional[float] = None  # 对上次陪诊师的评分

    def has_designated_escort(self) -> bool:
        """检查是否有指定陪诊师"""
        return self.designated_escort_id is not None

    def has_history_escort(self) -> bool:
        """检查是否有历史陪诊师"""
        return self.last_escort_id is not None

    def add_history_escort(self, escort_id: str, rating: float):
        """添加历史陪诊师记录"""
        if escort_id not in self.history_escort_ids:
            self.history_escort_ids.append(escort_id)
        self.last_escort_id = escort_id
        self.last_escort_rating = rating

        # 如果评分高（>=4.8），自动设为指定陪诊师
        if rating >= 4.8:
            self.designated_escort_id = escort_id

    def __repr__(self):
        return f"User({self.id[:8]}, {self.disease_type}, {self.target_hospital})"


@dataclass
class Escort:
    """陪诊员模型"""
    id: str = field(default_factory=lambda: str(uuid4()))
    status: EscortStatus = EscortStatus.TRAINING
    join_date: datetime = field(default_factory=datetime.now)
    training_complete_date: Optional[datetime] = None

    total_orders: int = 0
    total_income: float = 0.0
    rating: float = 5.0  # 初始评分

    specialized_hospitals: List[str] = field(default_factory=list)
    current_order_id: Optional[str] = None

    # 地理位置（经纬度）
    location_lat: float = 39.9042  # 默认北京市中心（天安门）
    location_lon: float = 116.4074
    home_district: str = "朝阳"  # 居住区域

    # 流失风险评分 (0-1，越高越容易流失)
    churn_risk: float = 0.5

    # 医院准入资质
    has_certification: bool = False  # 是否持有陪诊资质证书

    # 接单意愿相关
    daily_income_target: float = 200.0  # 日收入目标
    current_daily_income: float = 0.0   # 当日已获收入

    def __repr__(self):
        return f"Escort({self.id[:8]}, {self.status.value}, 订单:{self.total_orders}, 收入:{self.total_income:.0f})"

    def update_churn_risk(self):
        """更新流失风险（收入越高、订单越多，流失风险越低）"""
        income_factor = max(0, 1 - self.total_income / 10000)  # 收入1万元时风险降为0
        order_factor = max(0, 1 - self.total_orders / 50)  # 50单时风险降为0
        self.churn_risk = (income_factor + order_factor) / 2


@dataclass
class Order:
    """订单模型"""
    id: str = field(default_factory=lambda: str(uuid4()))
    user: User = field(default_factory=User)
    escort: Optional[Escort] = None

    status: OrderStatus = OrderStatus.PENDING
    price: float = 0.0

    created_at: datetime = field(default_factory=datetime.now)
    matched_at: Optional[datetime] = None
    service_start_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    service_duration: float = 0.0  # 实际服务时长（小时）
    rating: Optional[float] = None  # 用户评分
    is_success: bool = False

    cancel_reason: Optional[str] = None

    # 获客渠道信息（增强版需求生成器使用）
    acquisition_channel: Optional[str] = None
    acquisition_cost: float = 0.0

    # 时段信息
    hour_of_day: Optional[int] = None  # 订单创建时的小时（0-23）

    # 匹配类型追踪（新增）
    match_type: str = "normal"  # "designated"/"history"/"normal"
    is_designated_matched: bool = False  # 是否成功匹配指定陪诊师

    def __repr__(self):
        return f"Order({self.id[:8]}, {self.status.value}, ¥{self.price:.0f})"
