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

### 需求侧
- **时段需求建模** — 早高峰(1.8x)/午间(1.2x)/下午(1.5x)/晚间(0.8x) 真实需求分布
- **年龄分层行为** — 60-70岁(子女代购40%)/70-80岁(70%)/80+岁(90%，无法独立使用App)
- **用户生命周期状态机** — active → at_risk(30天) → silent(60天) → churned(90天)，5%/周重激活概率
- **NPS 口碑传播** — 推荐者/被动者/批评者分类，推荐转化率 7.5%

### 供给侧
- **陪诊员招募衰减** — 52周后最低维持40%招募能力
- **培训体系** — 基础培训(7天)/专业培训(21天)，通过率70%

### 匹配引擎
- **增强匹配引擎** — 三级匹配（指定陪诊师82%复购 → 历史陪诊师 → 地理就近）
- **时间冲突检测** — 实时检测陪诊师时间冲突
- **地理距离约束** — Haversine距离计算，通勤时间不超过90分钟

### 财务分析
- **CAC 渠道差异化** — 线上广告80元/口碑推荐20元/医院合作150元/地推60元
- **盈亏平衡分析** — 固定成本/边际贡献计算，预测盈亏平衡周数
- **单位经济模型** — LTV/CAC 比率（健康指标 >3）

### 市场竞争
- **真实竞争格局** — 医院自营40%/个人陪诊师35%/滴滴15%/其他10%
- **竞品挖角模拟** — 陪诊师流失率动态调整

## 项目结构

```
src/
├── config/
│   ├── settings.py              # 核心配置（含修正参数）
│   └── integrated_data_config.yaml
├── models/
│   └── entities.py             # User、Order、Escort 数据模型
├── modules/
│   ├── demand.py                # 需求生成（年龄分层 + 子女代购）
│   ├── demand_enhanced.py       # 增强需求（时段分布 + 渠道细分）
│   ├── supply.py                # 供给模拟（招募衰减 + 培训体系）
│   ├── matching.py              # 三级匹配引擎
│   ├── matching_enhanced.py     # 增强匹配（时间冲突 + 地理约束）
│   ├── analytics.py             # 数据分析（LTV/CAC/盈亏平衡）
│   ├── monte_carlo.py           # 蒙特卡洛模拟
│   ├── competition.py           # 市场竞争模型
│   ├── complaint_handler.py     # 投诉处理
│   ├── geo_matcher.py          # 地理位置匹配
│   ├── referral_system.py       # NPS 口碑传播
│   └── user_lifecycle_tracker.py
├── agents/
│   ├── user_behavior_agent.py  # 用户行为（生命周期 + 年龄分层）
│   └── market_dynamics_agent.py # 市场动态
├── simulation/
│   ├── simulation.py            # 基础模拟引擎
│   └── simulation_competitive.py # 竞争模拟引擎
└── simulation.py               # 主入口
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行 90 天模拟
python -c "
from src.config.settings import SimulationConfig
from src.simulation_competitive import CompetitiveSimulation

config = SimulationConfig(total_days=90, enable_llm=False)
sim = CompetitiveSimulation(config)
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
- 多智能体系统 — 用户行为和市场动态模拟

## 版本历史

- **v2.0** — 基于外部研究数据全面修正核心参数
- **v2.1** — 增强匹配引擎、时段需求建模、CAC渠道差异化
- **v2.2** — 年龄分层行为、用户生命周期状态机、盈亏平衡分析
