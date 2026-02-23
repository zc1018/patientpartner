"""
Streamlit Web UI - 陪诊服务沙盘模拟系统
"""
import streamlit as st
import pandas as pd
import os
from pathlib import Path

# 添加 src 到路径
import sys
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import SimulationConfig
from simulation import Simulation
from visualization import Visualizer


def main():
    st.set_page_config(
        page_title="陪诊服务沙盘模拟系统",
        page_icon="🏥",
        layout="wide"
    )

    st.title("🏥 陪诊服务沙盘模拟系统")
    st.markdown("基于滴滴生态的中老年陪诊服务商业模式验证")

    # 侧边栏：参数配置
    with st.sidebar:
        st.header("⚙️ 参数配置")

        st.subheader("时间参数")
        total_days = st.slider("模拟天数", 30, 180, 90, 10)

        st.subheader("需求侧参数")
        dau_base = st.number_input("日活基数", value=2_000_000, step=100_000)
        exposure_rate = st.slider("曝光率", 0.01, 0.20, 0.05, 0.01)
        click_rate = st.slider("点击率", 0.01, 0.10, 0.02, 0.01)
        consult_rate = st.slider("咨询转化率", 0.10, 0.50, 0.30, 0.05)
        order_rate = st.slider("下单转化率", 0.10, 0.50, 0.20, 0.05)
        price_mean = st.number_input("客单价均值（元）", value=200, step=10)
        repurchase_prob = st.slider("复购概率", 0.10, 0.50, 0.30, 0.05)

        st.subheader("供给侧参数")
        initial_escorts = st.number_input("初始陪诊员数", value=15, step=5)
        weekly_recruit = st.number_input("每周招募人数", value=5, step=1)
        training_days = st.number_input("培训周期（天）", value=7, step=1)
        daily_order_limit = st.number_input("日接单上限", value=3, step=1)
        escort_commission = st.slider("陪诊员分成比例", 0.50, 0.90, 0.70, 0.05)

        st.subheader("LLM 设置")
        enable_llm = st.checkbox("启用 LLM 功能", value=False)
        llm_provider = st.selectbox("LLM 提供商", ["anthropic", "openai"])

        # 构建配置
        config = SimulationConfig(
            total_days=total_days,
            dau_base=dau_base,
            exposure_rate=exposure_rate,
            click_rate=click_rate,
            consult_rate=consult_rate,
            order_rate=order_rate,
            price_mean=price_mean,
            repurchase_prob=repurchase_prob,
            initial_escorts=initial_escorts,
            weekly_recruit=weekly_recruit,
            training_days=training_days,
            daily_order_limit=daily_order_limit,
            escort_commission=escort_commission,
            enable_llm=enable_llm,
            llm_provider=llm_provider,
        )

    # 主区域
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📊 模拟控制")

    with col2:
        run_button = st.button("🚀 开始模拟", type="primary", use_container_width=True)

    if run_button:
        try:
            # 运行模拟
            with st.spinner("模拟运行中，请稍候..."):
                sim = Simulation(config)
                result = sim.run(verbose=False)

            # 显示结果
            st.success("✅ 模拟完成！")

            # 核心指标卡片
            st.subheader("📈 核心指标")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "总 GMV",
                    f"¥{result.total_gmv:,.0f}",
                    delta=f"{result.avg_margin:.1%} 毛利率"
                )

            with col2:
                st.metric(
                    "总订单数",
                    f"{result.total_orders:,}",
                    delta=f"{result.total_completed:,} 完成"
                )

            with col3:
                st.metric(
                    "平均完成率",
                    f"{result.avg_completion_rate:.1%}",
                )

            with col4:
                st.metric(
                    "总毛利",
                    f"¥{result.total_gross_profit:,.0f}",
                )

            # 趋势图表
            st.subheader("📊 趋势分析")

            visualizer = Visualizer(result)

            tab1, tab2, tab3, tab4 = st.tabs(["订单趋势", "供需平衡", "财务指标", "完成率"])

            with tab1:
                fig = visualizer.plot_order_trend()
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                fig = visualizer.plot_supply_demand()
                st.plotly_chart(fig, use_container_width=True)

            with tab3:
                fig = visualizer.plot_financial_metrics()
                st.plotly_chart(fig, use_container_width=True)

            with tab4:
                fig = visualizer.plot_completion_rate()
                st.plotly_chart(fig, use_container_width=True)

            # 数据表格
            st.subheader("📋 详细数据")
            df = result.to_dataframe()
            st.dataframe(df, use_container_width=True)

            # 下载按钮
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 下载 CSV 数据",
                data=csv,
                file_name="simulation_result.csv",
                mime="text/csv",
            )

            # LLM 分析报告
            if enable_llm and result.llm_report:
                st.subheader("🤖 AI 分析报告")
                st.markdown(result.llm_report)

        except Exception as e:
            st.error(f"模拟失败: {str(e)}")
            st.exception(e)

    else:
        # 显示说明
        st.info("👈 请在左侧配置参数，然后点击"开始模拟"按钮")

        st.markdown("""
        ### 系统说明

        这是一个基于滴滴生态的陪诊服务商业沙盘模拟系统，用于验证商业模式的可行性。

        **核心功能**：
        - 🎯 需求生成：基于滴滴流量漏斗模型生成用户订单
        - 👥 供给模拟：模拟陪诊员招募、培训、流失全流程
        - 🔄 匹配履约：智能订单分配与服务完成模拟
        - 📊 数据分析：实时统计业务指标和财务数据
        - 🤖 AI 智能：LLM 生成突发事件和分析报告

        **使用步骤**：
        1. 在左侧调整模拟参数
        2. 点击"开始模拟"按钮
        3. 查看结果图表和数据
        4. 下载 CSV 数据进行进一步分析

        **参数说明**：
        - **需求侧**：控制用户订单生成的漏斗转化率
        - **供给侧**：控制陪诊员的招募、培训、流失
        - **LLM**：启用后可生成突发事件和 AI 分析报告（需配置 API Key）
        """)


if __name__ == "__main__":
    main()
