"""
Agent基础类 - 所有agent的基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from uuid import uuid4


class AgentType(Enum):
    """Agent类型"""
    USER_BEHAVIOR = "用户行为"
    ESCORT_BEHAVIOR = "陪诊员行为"
    MARKET_DYNAMICS = "市场动态"
    OPERATIONS = "运营决策"
    COMPETITION = "竞争对手"
    MONITORING = "监控告警"
    REPORTING = "报告生成"
    COORDINATOR = "协调器"


class MessageType(Enum):
    """消息类型"""
    EVENT = "事件"
    DECISION = "决策"
    ALERT = "告警"
    REPORT = "报告"
    REQUEST = "请求"
    RESPONSE = "响应"


@dataclass
class AgentMessage:
    """Agent之间的消息"""
    id: str = field(default_factory=lambda: str(uuid4()))
    sender: str = ""  # 发送者agent ID
    receiver: str = ""  # 接收者agent ID（空表示广播）
    message_type: MessageType = MessageType.EVENT
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 0  # 优先级（0-10，越高越优先）

    def __repr__(self):
        return f"Message({self.message_type.value}, {self.sender}->{self.receiver})"


@dataclass
class AgentState:
    """Agent状态"""
    agent_id: str
    agent_type: AgentType
    is_active: bool = True
    last_action_time: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)
    memory: Dict[str, Any] = field(default_factory=dict)  # Agent的记忆/状态


class BaseAgent(ABC):
    """Agent基类"""

    def __init__(self, agent_id: str, agent_type: AgentType):
        self.state = AgentState(agent_id=agent_id, agent_type=agent_type)
        self.message_queue: List[AgentMessage] = []
        self.sent_messages: List[AgentMessage] = []

    @abstractmethod
    def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """处理接收到的消息"""
        pass

    @abstractmethod
    def take_action(self, simulation_state: Dict[str, Any]) -> List[AgentMessage]:
        """执行agent的主要行动"""
        pass

    def send_message(self, receiver: str, message_type: MessageType,
                    content: Dict[str, Any], priority: int = 0) -> AgentMessage:
        """发送消息"""
        message = AgentMessage(
            sender=self.state.agent_id,
            receiver=receiver,
            message_type=message_type,
            content=content,
            priority=priority
        )
        self.sent_messages.append(message)
        return message

    def receive_message(self, message: AgentMessage):
        """接收消息"""
        self.message_queue.append(message)

    def process_queue(self) -> List[AgentMessage]:
        """处理消息队列"""
        responses = []
        # 按优先级排序
        self.message_queue.sort(key=lambda m: m.priority, reverse=True)

        for message in self.message_queue:
            response = self.process_message(message)
            if response:
                responses.append(response)

        self.message_queue.clear()
        return responses

    def update_metrics(self, metrics: Dict[str, Any]):
        """更新指标"""
        self.state.metrics.update(metrics)
        self.state.last_action_time = datetime.now()

    def get_state(self) -> AgentState:
        """获取agent状态"""
        return self.state
