"""
LLM 客户端 - 支持 OpenAI 和 Anthropic
"""
import os
import time
import logging
from typing import Optional, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMClient:
    """LLM 客户端"""

    def __init__(self, provider: str = "anthropic", model: str = "claude-sonnet-4-5-20250929"):
        self.provider = LLMProvider(provider)
        self.model = model
        self.api_key = self._get_api_key()

        # 初始化客户端
        if self.provider == LLMProvider.OPENAI:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("请安装 openai: pip install openai")
        elif self.provider == LLMProvider.ANTHROPIC:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("请安装 anthropic: pip install anthropic")

    def _get_api_key(self) -> str:
        """从环境变量获取 API Key"""
        if self.provider == LLMProvider.OPENAI:
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError("请设置环境变量 OPENAI_API_KEY")
        else:
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key:
                raise ValueError("请设置环境变量 ANTHROPIC_API_KEY")
        return key

    def generate(self, prompt: str, max_tokens: int = 2000, timeout: float = 30.0) -> str:
        """生成文本 - 带指数退避重试（最多3次，间隔1s/2s/4s）"""
        max_retries = 3
        base_delay = 1.0

        for attempt in range(1, max_retries + 1):
            try:
                if self.provider == LLMProvider.OPENAI:
                    response = self.client.chat.completions.create(  # type: ignore[union-attr]
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        timeout=timeout,
                    )
                    return response.choices[0].message.content or ""

                elif self.provider == LLMProvider.ANTHROPIC:
                    response = self.client.messages.create(  # type: ignore[union-attr]
                        model=self.model,
                        max_tokens=max_tokens,
                        messages=[{"role": "user", "content": prompt}],
                        timeout=timeout,
                    )
                    return response.content[0].text  # type: ignore[union-attr]

            except Exception as e:
                delay = base_delay * (2 ** (attempt - 1))  # 1s, 2s, 4s
                logger.warning(
                    f"LLM 调用失败 (第{attempt}/{max_retries}次): {type(e).__name__}: {e}"
                )
                if attempt < max_retries:
                    logger.info(f"将在 {delay}s 后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"LLM 调用在 {max_retries} 次重试后仍然失败，放弃请求")
                    return ""

        return ""

    def generate_event(self, state: Dict) -> Optional[Dict]:
        """生成突发事件"""
        prompt = f"""
你是一个商业沙盘模拟系统的事件生成器。基于当前业务状态，生成一个合理的突发事件。

当前状态：
- 第 {state['day']} 天
- 总订单数：{state['total_orders']}
- 可用陪诊员：{state['available_escorts']}
- 完成率：{state['completion_rate']:.1%}

请生成一个突发事件，格式如下：
事件类型：[医院故障/需求激增/竞争对手/其他]
事件描述：[具体描述]
影响：[对业务的影响]
持续天数：[数字]

只返回事件内容，不要其他解释。
"""
        response = self.generate(prompt, max_tokens=500)
        # 简化处理，实际应该解析返回的结构化数据
        return {"description": response} if response else None

    def analyze_user_behavior(self, user_context: Dict) -> str:
        """分析用户行为决策"""
        prompt = f"""
用户画像：
- 等待时长：{user_context.get('wait_time', 0)} 小时
- 历史订单数：{user_context.get('total_orders', 0)}
- 上次评分：{user_context.get('last_rating', 0)}

请判断用户是否会取消订单？回答"是"或"否"，并简要说明原因。
"""
        return self.generate(prompt, max_tokens=200)

    def generate_analysis_report(self, result: Dict) -> str:
        """生成分析报告"""
        prompt = f"""
你是一个商业分析师。基于以下陪诊服务沙盘模拟数据，生成一份详细的分析报告。

模拟周期：{result['total_days']} 天
总 GMV：¥{result['total_gmv']:,.0f}
总订单数：{result['total_orders']:,}
完成订单数：{result['total_completed']:,}
平均完成率：{result['avg_completion_rate']:.1%}
总毛利：¥{result['total_gross_profit']:,.0f}
平均毛利率：{result['avg_margin']:.1%}

请从以下角度分析：
1. 业务健康度评估
2. 关键瓶颈识别
3. 优化建议（需求侧、供给侧、运营效率）
4. 风险提示

报告要求：
- 使用中文
- 结构清晰
- 数据驱动
- 提供可执行的建议

请生成报告：
"""
        return self.generate(prompt, max_tokens=2000)
