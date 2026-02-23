# 滴滴陪诊业务沙箱模拟系统

基于真实行业数据的陪诊业务沙箱模拟环境，用于 GMV 预测、运营决策支持和业务参数验证。

## 项目背景

本项目模拟滴滴陪诊业务的完整运营流程，核心参数基于外部研究数据修正（v2.0），相比原始假设更贴近真实市场表现：

| 参数 | 原假设 | 修正后 | 数据来源 |
|------|--------|--------|---------|
| 首单复购率 | 30% | **13.5%** | Dialog Health 患者留存研究 |
| 30天留存率 | 未定义 | **45%** | 医疗 App 行业数据 |
| NPS 评分 | 未定义 | **-22.5%** | 金融/医疗行业基准 |

## 核心功能

- **蒙特卡洛模拟** — 保守/中性/乐观三场景 GMV 预测
- **三级匹配引擎** — 指定陪诊师（82%复购）→ 历史陪诊师 → 地理就近匹配
- **用户生命周期追踪** — 首单流失、留存曲线、复购分层
- **投诉处理系统** — 滑动窗口投诉率计算，转化率动态修正（每↑1%投诉率 → 转化率↓0.45%）
- **NPS 口碑传播** — 推荐者/被动者/批评者分类，推荐转化率 7.5%
- **地理位置匹配** — 北京 16 区就近分配，Haversine 距离计算

## 项目结构

```
src/
├── config/
│   ├── settings.py              # 核心配置（含修正参数）
│   └── integrated_data_config.py
├── models/
│   └── entities.py              # User、Order、Escort 数据模型
├── modules/
│   ├── demand.py                # 需求生成（漏斗转化 + 子女代购分层）
│   ├── supply.py                # 供给模拟（陪诊员招募/培训/流失）
│   ├── matching.py              # 三级匹配引擎
│   ├── analytics.py             # 数据分析（LTV/CAC/GMV）
│   ├── monte_carlo.py           # 蒙特卡洛模拟
│   ├── complaint_handler.py     # 投诉处理
│   ├── geo_matcher.py           # 地理位置匹配
│   ├── referral_system.py       # NPS 口碑传播
│   └── user_lifecycle_tracker.py
├── simulation/
│   ├── base.py                  # 模板方法基类
│   └── simulation.py            # 主模拟引擎
└── agents/                      # 多智能体团队
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行 90 天模拟
python -c "
from src.config.settings import SimulationConfig
from src.simulation import Simulation

config = SimulationConfig(total_days=90, enable_llm=False)
sim = Simulation(config)
result = sim.run()
"
```

## 关键业务指标

| 指标 | 当前基准 | 目标（3个月） |
|------|---------|-------------|
| 首单复购率 | 13.5% | 18% |
| 30天留存率 | 45% | 60% |
| 指定陪诊师渗透率 | 20% | 70% |
| NPS 评分 | -22.5% | 0% |

## GMV 预测（年度，基于修正参数）

| 场景 | 年度 GMV |
|------|---------|
| 保守 | 0.20 亿元 |
| 中性 | 0.39 亿元 |
| 乐观 | 0.77 亿元 |

## 技术栈

- Python 3.10+
- NumPy / Pandas — 数值计算
- Rich — 终端可视化
- 模板方法模式 — 模拟引擎架构
