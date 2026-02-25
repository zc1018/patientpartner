"""
蒙特卡洛模拟模块 - 不确定性分析和置信区间计算
"""
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

from ..config.settings import SimulationConfig
from ..config.beijing_real_data import BeijingRealDataConfig
from ..simulation_competitive import CompetitiveSimulation


@dataclass
class ParameterDistribution:
    """参数分布定义"""
    name: str
    base_value: float
    distribution_type: str  # uniform/normal/triangular
    min_value: float = 0.0
    max_value: float = 0.0
    std_dev: float = 0.0
    mode_value: float = 0.0  # 用于三角分布


@dataclass
class MonteCarloResult:
    """蒙特卡洛模拟结果"""
    parameter_name: str
    runs: int

    # 关键指标的统计数据
    gmv_mean: float = 0.0
    gmv_std: float = 0.0
    gmv_ci_lower: float = 0.0  # 95% 置信区间下限
    gmv_ci_upper: float = 0.0  # 95% 置信区间上限

    net_profit_mean: float = 0.0
    net_profit_std: float = 0.0
    net_profit_ci_lower: float = 0.0
    net_profit_ci_upper: float = 0.0

    market_share_mean: float = 0.0
    market_share_std: float = 0.0
    market_share_ci_lower: float = 0.0
    market_share_ci_upper: float = 0.0

    completion_rate_mean: float = 0.0
    completion_rate_std: float = 0.0
    completion_rate_ci_lower: float = 0.0
    completion_rate_ci_upper: float = 0.0

    # 所有运行的详细结果
    all_results: List[Dict] = field(default_factory=list)


class MonteCarloSimulator:
    """蒙特卡洛模拟器"""

    def __init__(self, base_config: SimulationConfig, beijing_data: BeijingRealDataConfig):
        self.base_config = base_config
        self.beijing_data = beijing_data

        # 定义关键参数的分布
        self.parameter_distributions = self._define_parameter_distributions()

    def _define_parameter_distributions(self) -> List[ParameterDistribution]:
        """定义关键参数的不确定性分布"""
        distributions = [
            # 需求侧参数
            ParameterDistribution(
                name="exposure_rate",
                base_value=0.05,
                distribution_type="uniform",
                min_value=0.03,
                max_value=0.08
            ),
            ParameterDistribution(
                name="click_rate",
                base_value=0.02,
                distribution_type="uniform",
                min_value=0.015,
                max_value=0.03
            ),
            ParameterDistribution(
                name="order_rate",
                base_value=0.20,
                distribution_type="uniform",
                min_value=0.15,
                max_value=0.25
            ),
            ParameterDistribution(
                name="price_mean",
                base_value=235,
                distribution_type="normal",
                std_dev=30
            ),
            ParameterDistribution(
                name="repurchase_prob",
                base_value=0.135,  # 首单复购率基准值 13.5%（基于Dialog Health研究修正后）
                distribution_type="uniform",
                min_value=0.10,   # 下限10%（保守估计）
                max_value=0.20    # 上限20%（乐观估计）
            ),

            # P0级关键参数 - 指定陪诊师复购率
            ParameterDistribution(
                name="designated_escort_repeat_rate",
                base_value=0.82,  # 指定陪诊师复购率 82%
                distribution_type="uniform",
                min_value=0.75,   # 下限75%（保守估计）
                max_value=0.88    # 上限88%（乐观估计）
            ),

            # P0级关键参数 - NPS评分
            ParameterDistribution(
                name="nps_score",
                base_value=-0.225,  # NPS评分 -22.5%
                distribution_type="uniform",
                min_value=-0.30,    # 下限-30%（更差情况）
                max_value=-0.15     # 上限-15%（改善情况）
            ),

            # P0级关键参数 - 投诉率
            ParameterDistribution(
                name="complaint_rate",
                base_value=0.01,  # 投诉率 1%
                distribution_type="uniform",
                min_value=0.005,  # 下限0.5%（优秀服务水平）
                max_value=0.03    # 上限3%（服务水平下降）
            ),

            # 供给侧参数
            ParameterDistribution(
                name="initial_escorts",
                base_value=15,
                distribution_type="uniform",
                min_value=10,
                max_value=25
            ),
            ParameterDistribution(
                name="training_pass_rate",
                base_value=0.80,
                distribution_type="uniform",
                min_value=0.70,
                max_value=0.90
            ),
            ParameterDistribution(
                name="monthly_churn_rate",
                base_value=0.15,
                distribution_type="uniform",
                min_value=0.10,
                max_value=0.25
            ),

            # 服务参数
            ParameterDistribution(
                name="service_success_rate",
                base_value=0.95,
                distribution_type="uniform",
                min_value=0.90,
                max_value=0.98
            ),
            ParameterDistribution(
                name="satisfaction_mean",
                base_value=4.5,
                distribution_type="normal",
                std_dev=0.2
            ),

            # 成本参数
            ParameterDistribution(
                name="cac_didi_app",
                base_value=50,
                distribution_type="uniform",
                min_value=40,
                max_value=70
            ),
        ]
        return distributions

    def run_monte_carlo(
        self,
        num_runs: int = 100,
        confidence_level: float = 0.95,
        parallel: bool = True
    ) -> MonteCarloResult:
        """运行蒙特卡洛模拟"""

        print(f"\n🎲 开始蒙特卡洛模拟 - {num_runs} 次运行")
        print(f"📊 置信水平: {confidence_level*100:.0f}%")
        print(f"⚙️  并行处理: {'是' if parallel else '否'}\n")

        all_results = []

        if parallel:
            # 并行运行
            with ProcessPoolExecutor(max_workers=4) as executor:
                futures = []
                for i in range(num_runs):
                    future = executor.submit(self._run_single_simulation, i)
                    futures.append(future)

                # 使用 tqdm 显示进度
                for future in tqdm(as_completed(futures), total=num_runs, desc="模拟进度"):
                    result = future.result()
                    if result:
                        all_results.append(result)
        else:
            # 串行运行
            for i in tqdm(range(num_runs), desc="模拟进度"):
                result = self._run_single_simulation(i)
                if result:
                    all_results.append(result)

        # 计算统计数据
        mc_result = self._calculate_statistics(all_results, confidence_level)

        return mc_result

    def _run_single_simulation(self, run_id: int) -> Optional[Dict]:  # type: ignore[return]
        """运行单次模拟"""
        try:
            # 1. 采样参数
            config = self._sample_parameters()

            # 2. 运行模拟
            sim = CompetitiveSimulation(config, self.beijing_data)
            result = sim.run(verbose=False)

            # 3. 提取关键指标
            return {
                "run_id": run_id,
                "gmv": result.total_gmv,
                "net_profit": result.total_net_profit,
                "market_share": result.market_share,
                "completion_rate": result.avg_completion_rate,
                "total_orders": result.total_orders,
                "total_completed": result.total_completed,
                "avg_cac": result.avg_cac,
                "ltv_cac_ratio": result.ltv_cac_ratio,
            }
        except Exception as e:
            print(f"运行 {run_id} 失败: {e}")
            return None

    def _sample_parameters(self) -> SimulationConfig:
        """从分布中采样参数"""
        config = SimulationConfig(
            total_days=self.base_config.total_days,
            enable_llm=False,  # 禁用 LLM 加快速度
            random_seed=np.random.randint(0, 10000)  # 每次使用不同的随机种子
        )

        # 需要整数的参数列表
        integer_params = ['initial_escorts', 'weekly_recruit', 'training_days', 'daily_order_limit']

        # 对每个参数进行采样
        for param_dist in self.parameter_distributions:
            sampled_value = self._sample_from_distribution(param_dist)

            # 如果是整数参数，转换为整数
            if param_dist.name in integer_params:
                sampled_value = int(round(sampled_value))

            setattr(config, param_dist.name, sampled_value)

        return config

    def _sample_from_distribution(self, param_dist: ParameterDistribution) -> float:
        """从指定分布中采样"""
        if param_dist.distribution_type == "uniform":
            return np.random.uniform(param_dist.min_value, param_dist.max_value)

        elif param_dist.distribution_type == "normal":
            value = np.random.normal(param_dist.base_value, param_dist.std_dev)
            # 确保值在合理范围内
            if param_dist.min_value is not None:
                value = max(value, param_dist.min_value)
            if param_dist.max_value is not None:
                value = min(value, param_dist.max_value)
            return value

        elif param_dist.distribution_type == "triangular":
            return np.random.triangular(
                param_dist.min_value,
                param_dist.mode_value,
                param_dist.max_value
            )

        else:
            return param_dist.base_value

    def _calculate_statistics(
        self,
        all_results: List[Dict],
        confidence_level: float
    ) -> MonteCarloResult:
        """计算统计数据和置信区间"""

        # 转换为 DataFrame
        df = pd.DataFrame(all_results)

        # 计算置信区间
        alpha = 1 - confidence_level

        def calc_ci(data):
            """计算置信区间"""
            mean = np.mean(data)
            std = np.std(data)
            ci_lower = np.percentile(data, alpha/2 * 100)
            ci_upper = np.percentile(data, (1 - alpha/2) * 100)
            return mean, std, ci_lower, ci_upper

        # GMV
        gmv_mean, gmv_std, gmv_ci_lower, gmv_ci_upper = calc_ci(df['gmv'])

        # 净利润
        np_mean, np_std, np_ci_lower, np_ci_upper = calc_ci(df['net_profit'])

        # 市场份额
        ms_mean, ms_std, ms_ci_lower, ms_ci_upper = calc_ci(df['market_share'])

        # 完成率
        cr_mean, cr_std, cr_ci_lower, cr_ci_upper = calc_ci(df['completion_rate'])

        result = MonteCarloResult(
            parameter_name="all_parameters",
            runs=len(all_results),
            gmv_mean=float(gmv_mean),
            gmv_std=float(gmv_std),
            gmv_ci_lower=float(gmv_ci_lower),
            gmv_ci_upper=float(gmv_ci_upper),
            net_profit_mean=float(np_mean),
            net_profit_std=float(np_std),
            net_profit_ci_lower=float(np_ci_lower),
            net_profit_ci_upper=float(np_ci_upper),
            market_share_mean=float(ms_mean),
            market_share_std=float(ms_std),
            market_share_ci_lower=float(ms_ci_lower),
            market_share_ci_upper=float(ms_ci_upper),
            completion_rate_mean=float(cr_mean),
            completion_rate_std=float(cr_std),
            completion_rate_ci_lower=float(cr_ci_lower),
            completion_rate_ci_upper=float(cr_ci_upper),
            all_results=all_results
        )

        return result

    def sensitivity_analysis(self, mc_result: MonteCarloResult) -> pd.DataFrame:
        """敏感性分析 - 识别关键参数"""

        df = pd.DataFrame(mc_result.all_results)

        # 计算每个参数与净利润的相关性
        # 这里简化处理，实际应该记录每次运行的参数值

        print("\n📊 敏感性分析")
        print("=" * 60)
        print("关键指标的变异系数（CV = 标准差 / 均值）：")
        print(f"  GMV: {mc_result.gmv_std / mc_result.gmv_mean:.2%}")
        print(f"  净利润: {abs(mc_result.net_profit_std / mc_result.net_profit_mean):.2%}")
        print(f"  市场份额: {mc_result.market_share_std / mc_result.market_share_mean:.2%}")
        print(f"  完成率: {mc_result.completion_rate_std / mc_result.completion_rate_mean:.2%}")

        return df
