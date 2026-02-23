"""
模拟引擎模块 - 使用模板方法模式重构

重构后的模块结构:
- BaseSimulation: 抽象基类，定义模板方法
- Simulation: 基础版实现

向后兼容:
所有原有接口保持不变，现有代码无需修改即可使用。
"""

from .base import BaseSimulation
from .simulation import Simulation

__all__ = [
    'BaseSimulation',
    'Simulation',
]
