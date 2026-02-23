"""
可视化模块
"""
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import List

from .modules.analytics import SimulationResult, DailyMetrics


class Visualizer:
    """可视化工具"""

    def __init__(self, result: SimulationResult):
        self.result = result
        self.df = result.to_dataframe()

    def plot_order_trend(self, save_path: str = None):
        """订单趋势图"""
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=self.df['day'],
            y=self.df['total_orders'],
            mode='lines+markers',
            name='总订单',
            line=dict(color='blue', width=2)
        ))

        fig.add_trace(go.Scatter(
            x=self.df['day'],
            y=self.df['completed_orders'],
            mode='lines+markers',
            name='完成订单',
            line=dict(color='green', width=2)
        ))

        fig.update_layout(
            title='订单趋势',
            xaxis_title='天数',
            yaxis_title='订单数',
            hovermode='x unified',
            template='plotly_white'
        )

        if save_path:
            fig.write_html(save_path)

        return fig

    def plot_supply_demand(self, save_path: str = None):
        """供需平衡图"""
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Scatter(
                x=self.df['day'],
                y=self.df['total_orders'],
                mode='lines',
                name='需求（订单数）',
                line=dict(color='orange', width=2)
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=self.df['day'],
                y=self.df['available_escorts'],
                mode='lines',
                name='供给（可用陪诊员）',
                line=dict(color='purple', width=2)
            ),
            secondary_y=True,
        )

        fig.update_xaxes(title_text="天数")
        fig.update_yaxes(title_text="订单数", secondary_y=False)
        fig.update_yaxes(title_text="陪诊员数", secondary_y=True)

        fig.update_layout(
            title='供需平衡',
            hovermode='x unified',
            template='plotly_white'
        )

        if save_path:
            fig.write_html(save_path)

        return fig

    def plot_financial_metrics(self, save_path: str = None):
        """财务指标趋势"""
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('GMV 趋势', '毛利率趋势'),
            vertical_spacing=0.15
        )

        # GMV
        fig.add_trace(
            go.Scatter(
                x=self.df['day'],
                y=self.df['gmv'],
                mode='lines',
                name='GMV',
                line=dict(color='green', width=2),
                fill='tozeroy'
            ),
            row=1, col=1
        )

        # 毛利率
        fig.add_trace(
            go.Scatter(
                x=self.df['day'],
                y=self.df['margin_rate'] * 100,
                mode='lines',
                name='毛利率 (%)',
                line=dict(color='blue', width=2)
            ),
            row=2, col=1
        )

        fig.update_xaxes(title_text="天数", row=2, col=1)
        fig.update_yaxes(title_text="GMV (元)", row=1, col=1)
        fig.update_yaxes(title_text="毛利率 (%)", row=2, col=1)

        fig.update_layout(
            height=600,
            showlegend=True,
            template='plotly_white'
        )

        if save_path:
            fig.write_html(save_path)

        return fig

    def plot_completion_rate(self, save_path: str = None):
        """完成率趋势"""
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=self.df['day'],
            y=self.df['completion_rate'] * 100,
            mode='lines+markers',
            name='完成率',
            line=dict(color='teal', width=2)
        ))

        fig.add_hline(
            y=self.result.avg_completion_rate * 100,
            line_dash="dash",
            line_color="red",
            annotation_text=f"平均: {self.result.avg_completion_rate:.1%}"
        )

        fig.update_layout(
            title='订单完成率趋势',
            xaxis_title='天数',
            yaxis_title='完成率 (%)',
            hovermode='x unified',
            template='plotly_white'
        )

        if save_path:
            fig.write_html(save_path)

        return fig

    def generate_all_charts(self, output_dir: str = "output"):
        """生成所有图表"""
        import os
        os.makedirs(output_dir, exist_ok=True)

        charts = {
            "order_trend": self.plot_order_trend(f"{output_dir}/order_trend.html"),
            "supply_demand": self.plot_supply_demand(f"{output_dir}/supply_demand.html"),
            "financial": self.plot_financial_metrics(f"{output_dir}/financial.html"),
            "completion": self.plot_completion_rate(f"{output_dir}/completion_rate.html"),
        }

        return charts
