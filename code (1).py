# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

@st.cache_data
def load_data():
    df = pd.read_csv("seoul_temperature.csv")
    df["날짜"] = df["날짜"].astype(str).str.strip()
    df["날짜"] = df["날짜"].str.lstrip("\t")
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    df["연도"] = df["날짜"].dt.year
    df["월"] = df["날짜"].dt.month
    for col in ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["날짜", "연도"])
    df["일교차"] = df["최고기온(℃)"] - df["최저기온(℃)"]
    return df


def main():
    st.set_page_config(page_title="서울 기온 분석", layout="wide")
    st.title("📊 서울 연도별 기온 분석 (1907~)")

    df = load_data()

    yearly = df.groupby("연도").agg(
        평균기온=("평균기온(℃)", "mean"),
        최저기온=("최저기온(℃)", "mean"),
        최고기온=("최고기온(℃)", "mean"),
        평균일교차=("일교차", "mean"),
    ).reset_index()
    yearly["평균_5년이동평균"] = yearly["평균기온"].rolling(window=5, min_periods=1).mean()

    min_year = int(yearly["연도"].min())
    max_year = int(yearly["연도"].max())

    st.sidebar.header("📅 연도 범위 설정")
    selected_range = st.sidebar.slider(
        "분석할 연도 범위",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        step=1,
    )
    start_year, end_year = selected_range

    tab1, tab2, tab3 = st.tabs(["연도별 기온 추이", "월별 히트맵", "최고·최저 기온 & 일교차"])

    with tab1:
        mask = (yearly["연도"] >= start_year) & (yearly["연도"] <= end_year)
        subset = yearly[mask]

        col1, col2, col3 = st.columns(3)
        col1.metric("선택 구간 평균기온", f"{subset['평균기온'].mean():.2f} ℃")
        col2.metric("선택 구간 최고기온", f"{subset['최고기온'].max():.2f} ℃")
        col3.metric("선택 구간 최저기온", f"{subset['최저기온'].min():.2f} ℃")

        fig1 = make_subplots(specs=[[{"secondary_y": False}]])
        fig1.add_trace(
            go.Scatter(
                x=subset["연도"],
                y=subset["평균기온"],
                mode="lines+markers",
                name="연도별 평균기온",
                line=dict(color="#1f77b4", width=2),
                marker=dict(size=5),
            )
        )
        fig1.add_trace(
            go.Scatter(
                x=subset["연도"],
                y=subset["평균_5년이동평균"],
                mode="lines",
                name="5년 이동평균",
                line=dict(color="#ff7f0e", width=3, dash="dash"),
            )
        )
        fig1.update_layout(
            title=f"서울 연도별 평균기온 ({start_year} ~ {end_year})",
            xaxis_title="연도",
            yaxis_title="평균기온 (℃)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            template="plotly_white",
            height=450,
        )
        fig1.update_xaxes(tickformat="d", dtick=5)
        st.plotly_chart(fig1, use_container_width=True)

        fig_diff = go.Figure()
        fig_diff.add_trace(
            go.Scatter(
                x=subset["연도"],
                y=subset["평균일교차"],
                mode="lines+markers",
                name="연도별 평균 일교차",
                line=dict(color="#2ca02c", width=2),
                marker=dict(size=5),
            )
        )
        fig_diff.update_layout(
            title=f"서울 연도별 평균 일교차 ({start_year} ~ {end_year})",
            xaxis_title="연도",
            yaxis_title="일교차 (℃)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            template="plotly_white",
            height=350,
        )
        fig_diff.update_xaxes(tickformat="d", dtick=5)
        st.plotly_chart(fig_diff, use_container_width=True)

    with tab2:
        heatmap_df = df[(df["연도"] >= start_year) & (df["연도"] <= end_year)]
        heatmap_data = heatmap_df.groupby(["연도", "월"])["평균기온(℃)"].mean().unstack(fill_value=None)

        all_years = sorted(heatmap_data.index.tolist())
        all_months = list(range(1, 13))

        z_data = []
        y_labels = []
        for y in all_years:
            row = []
            for m in all_months:
                val = heatmap_data.loc[y, m] if m in heatmap_data.columns and pd.notna(heatmap_data.loc[y, m]) else None
                row.append(val)
            z_data.append(row)
            y_labels.append(str(y))

        fig_heat = go.Figure(data=go.Heatmap(
            z=z_data,
            x=all_months,
            y=y_labels,
            colorscale="RdYlBu_r",
            hoverongaps=False,
            colorbar=dict(title="평균기온 (℃)"),
        ))
        fig_heat.update_layout(
            title=f"월별 평균기온 히트맵 ({start_year} ~ {end_year})",
            xaxis_title="월",
            yaxis_title="연도",
            xaxis=dict(tickmode="array", tickvals=all_months, ticktext=[f"{m}월" for m in all_months]),
            yaxis=dict(autorange="reversed"),
            height=max(400, len(all_years) * 22),
            margin=dict(l=60, r=40, t=60, b=60),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    with tab3:
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("🔥 최고기온 상위 10일")
            top10 = df.nlargest(10, "최고기온(℃)")[["날짜", "지점", "최고기온(℃)"]].reset_index(drop=True)
            top10["날짜"] = top10["날짜"].dt.strftime("%Y-%m-%d")
            st.dataframe(top10, use_container_width=True, hide_index=True)

        with col_b:
            st.subheader("🥶 최저기온 하위 10일")
            bottom10 = df.nsmallest(10, "최저기온(℃)")[["날짜", "지점", "최저기온(℃)"]].reset_index(drop=True)
            bottom10["날짜"] = bottom10["날짜"].dt.strftime("%Y-%m-%d")
            st.dataframe(bottom10, use_container_width=True, hide_index=True)

        st.divider()

        mask = (yearly["연도"] >= start_year) & (yearly["연도"] <= end_year)
        subset = yearly[mask]

        fig_range = go.Figure()
        fig_range.add_trace(
            go.Scatter(
                x=subset["연도"],
                y=subset["평균일교차"],
                mode="lines+markers",
                name="연도별 평균 일교차",
                line=dict(color="#2ca02c", width=2),
                marker=dict(size=5),
            )
        )
        fig_range.update_layout(
            title=f"연도별 평균 일교차 ({start_year} ~ {end_year})",
            xaxis_title="연도",
            yaxis_title="일교차 (℃)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            template="plotly_white",
            height=350,
        )
        fig_range.update_xaxes(tickformat="d", dtick=5)
        st.plotly_chart(fig_range, use_container_width=True)

        st.caption(f"데이터 기간: {min_year}년 ~ {max_year}년 | 분석 구간: {start_year}년 ~ {end_year}년")
        st.caption("출처: seoul_temperature.csv")


if __name__ == "__main__":
    main()
