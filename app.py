import streamlit as st
import pandas as pd
import numpy as np
import difflib

# ----------------------------------------------------------------
# 1. 页面全局配置与全局样式注入 (实现吸顶效果与精美无边框卡片)
# ----------------------------------------------------------------
st.set_page_config(page_title="循证营养品深度评估系统", layout="centered")

st.markdown("""
<style>
    /* 强制移除Streamlit原生内边距，提升移动端紧凑感 */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    
    /* 科学循证卡片通用样式 */
    .evidence-card {
        padding: 15px; border-radius: 8px; margin-bottom: 15px;
        border-left: 5px solid #2e7d32; background-color: #f1f8e9;
    }
    .evidence-card.insufficient { border-left-color: #ef6c00; background-color: #fff3e0; }
    .evidence-card.high-dose { border-left-color: #1565c0; background-color: #e3f2fd; }
    
    /* 辟谣卡片通用样式 */
    .debunk-card {
        padding: 15px; border-radius: 8px; margin-bottom: 15px;
        border: 1px solid #ffcdd2; background-color: #ffebee;
    }
    
    /* 自定义可视化范围进度条样式 */
    .bar-container { width: 100%; background-color: #e0e0e0; border-radius: 4px; height: 12px; position: relative; margin: 15px 0; }
    .bar-fill { height: 100%; background-color: #4caf50; border-radius: 4px; }
    .bar-pointer { position: absolute; top: -4px; width: 4px; height: 20px; background-color: #212121; border-radius: 2px; }
    .zone-marker { position: absolute; height: 100%; background-color: rgba(76, 175, 80, 0.3); border-left: 1px dashed #2e7d32; border-right: 1px dashed #2e7d32; }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------
# 2. 内存数据加载模块 (基于位置解耦，锁定前 5 种核心数据)
# ----------------------------------------------------------------
@st.cache_data
def load_and_clean_data():
    try:
        df_ing = pd.read_excel("ingredients.xlsx")
        df_evi = pd.read_excel("efficacy_evidence.xlsx")
        df_deb = pd.read_excel("debunking_statements.xlsx")
        df_prod = pd.read_excel("products.xlsx")
        
        df_ing.columns = ['中文标准名', '英文标准名', '是否为化合物形态', '折算系数', '每日安全上限(UL)', '单位'][:len(df_ing.columns)]
        df_evi.columns = ['所属成分(中文名)', '学术健康效果', '临床起效量', '临床最大推荐量', '科学共识陈述(给用户的结论)'][:len(df_evi.columns)]
        df_deb.columns = ['所属成分(中文名)', '商家夸大话术/伪功效', '触发打假的关键词', '科学驳斥陈述(给用户的警示)'][:len(df_deb.columns)]
        df_prod.columns = ['品牌名', '商品官方全称', '搜索别名(逗号隔开)', '每日建议服用几粒', '包含的成分(对应表1中文名)', '单粒原料投料量'][:len(df_prod.columns)]
        
        for df in [df_ing, df_evi, df_deb, df_prod]:
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).str.strip()
        return df_ing, df_evi, df_deb, df_prod
    except Exception as e:
        st.error(f"底层数据加载异常: {str(e)}")
        return None, None, None, None

df_ing, df_evi, df_deb, df_prod = load_and_clean_data()

# ⚠️ 初始化“最高等级安全拦截占位符”（确保高危红盾无条件渲染在页面最顶部）
top_safety_placeholder = st.empty()

# ----------------------------------------------------------------
# 3. 视觉重构版：四段式算法渲染引擎
# ----------------------------------------------------------------
def execute_evaluation_engine(ing_name, raw_dose, servings):
    ing_meta = df_ing[df_ing["中文标准名"] == ing_name]
    if ing_meta.empty:
        st.error(f"未在核心事实库中找到标准名称为 【{ing_name}】 的记录。")
        return

    factor = float(ing_meta["折算系数"].values[0])
    unit = str(ing_meta["单位"].values[0])
    ul_val = ing_meta["每日安全上限(UL)"].values[0]
    upper_limit = float(ul_val) if pd.notna(ul_val) and str(ul_val) != "无" and str(ul_val) != "nan" else float('inf')

    # 核心算法计算
    daily_intake = float(raw_dose) * float(servings) * factor

    st.markdown(f"## 📊 成分循证看板：{ing_name}")
    st.markdown(f"用户每日活性物质总摄入量：`{daily_intake:.2f} {unit}`")

    # 1. 跨生命周期安全红线强拦截 (超量状态)
    if daily_intake > upper_limit:
        top_safety_placeholder.markdown(f"""
        <div style="padding:20px; border-radius:10px; background-color:#b71c1c; color:white; margin-bottom:25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h3 style="margin:0; color:white;">🚨 毒性与超量极端危险报警</h3>
            <p style="margin:10px 0 0 0; font-size:14px;">
                警告：当前每日总摄入量（{daily_intake:.2f} {unit}）已严重跨越国家卫健委及营养学会划定的最高耐受上限（UL: {upper_limit} {unit}）。
                临床循证表明，该行为具备高概率引发肝肾毒性功能损伤等不可逆的不良生理副反应，<b>请立刻停止服用并咨询医师！</b>
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # 常态下顶部展现标准免责声明
        top_safety_placeholder.markdown("""
        <div style="padding:12px; border-radius:6px; background-color:#eceff1; border-left:4px solid #607d8b; margin-bottom:20px; font-size:13px; color:#546e7a;">
            ⚠️ <b>医学免责声明：</b> 评估结果仅基于公开人类临床试验（RCT）数据，不构成临床诊断。处方药患者切勿盲目以补充剂替代药物治疗。
        </div>
        """, unsafe_allow_html=True)

    # 2. 真实功效及区间进度条渲染 (Tier 1 & Tier 2)
    evidence_rows = df_evi[df_evi["所属成分(中文名)"] == ing_name]
    st.markdown("### 🟢 临床循证·证实功效核验")
    
    if not evidence_rows.empty:
        for _, row in evidence_rows.iterrows():
            min_eff = float(row["临床起效量"])
            max_eff = float(row["临床最大推荐量"])
            goal = row["学术健康效果"]
            consensus = row["科学共识陈述(给用户的结论)"]

            # 四段式状态判定
            if daily_intake < min_eff:
                card_class = "evidence-card insufficient"
                status_title = "⚠️ 剂量不足 (难以建立起效获益)"
                pointer_percent = min(100.0, (daily_intake / min_eff) * 40.0) # 按比例缩放至坐标轴
            elif min_eff <= daily_intake <= max_eff:
                card_class = "evidence-card"
                status_title = "✅ 黄金剂量达标 (临床高学术推荐度)"
                pointer_percent = 40.0 + ((daily_intake - min_eff) / (max_eff - min_eff)) * 40.0
            else:
                card_class = "evidence-card high-dose"
                status_title = "🟡 高强度干预剂量 (日常补充不建议超标)"
                pointer_percent = 80.0 + min(20.0, ((daily_intake - max_eff) / max_eff) * 20.0)

            # 渲染自定义区间进度条 (0%-40%不足区, 40%-80%有效推荐区, 80%-100%高剂量区)
            st.markdown(f"""
            <div class="{card_class}">
                <b style="font-size:16px; color:#1a237e;">🎯 针对目标：{goal}</b><br>
                <span style="font-size:13px; font-weight:bold;">当前评估状态：{status_title}</span>
                <div class="bar-container">
                    <div class="zone-marker" style="left:40%; width:40%;"></div> <div class="bar-pointer" style="left:{pointer_percent}%;"></div> </div>
                <div style="display:flex; justify-content:space-between; font-size:11px; color:#757575; margin-top:-10px;">
                    <span>0 {unit}</span>
                    <span>起效阈值: {min_eff} {unit}</span>
                    <span>临床上限: {max_eff} {unit}</span>
                </div>
                <p style="margin-top:10px; font-size:13px; line-height:1.5; color:#212121;"><b>科学共识：</b>{consensus}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("该成分首期 facts 事实库中暂未关联 Tier 1/2 的学术获益，请等待专家补齐数据。")

    # 3. 商业夸大辟谣区渲染 (Tier 3)
    debunk_rows = df_deb[df_deb["所属成分(中文名)"] == ing_name]
    st.markdown("### 🔴 商业营销·伪功效辟谣看板")
    
    if not debunk_rows.empty:
        for _, row in debunk_rows.iterrows():
            claim = row["商家夸大话术/伪功效"]
            refutation = row["科学驳斥陈述(给用户的警示)"]
            
            st.markdown(f"""
            <div class="debunk-card">
                <span style="background-color:#d32f2f; color:white; padding:2px 6px; border-radius:3px; font-size:11px; font-weight:bold;">E 级无证据</span>
                <b style="color:#c62828; margin-left:5px; font-size:14px;">高频商业营销词：宣称能“{claim}”</b>
                <p style="margin:8px 0 0 0; font-size:13px; color:#212121; line-height:1.5;"><b>⚡ 循证逻辑驳斥：</b>{refutation}</p>
            </div>
            """, unsafe_allow_html=True)
            
        # 4. 自动化生成“一键避坑分享文案”
        st.write("---")
        st.markdown("### 🔗 科学避坑卡片分享")
        st.write("点击下方框内文本，可直接一键复制，发送给朋友进行科普避坑：")
        
        first_claim = debunk_rows.iloc[0]["商家夸大话术/伪功效"]
        share_text = f"【注意避坑！】我的朋友，针对宣称能“{first_claim}”的营养品，经循证医学数据库交叉测算，其核心成分【{ing_name}】在此功效上的科学证据评级强制为E级（属于商业纯粹夸大，缺乏临床人体RCT数据支持）。你可以点击该链接执行科学免费核验： https://nutrition-eval.streamlit.app"
        st.code(share_text, language="text")
    else:
        st.info("💡 提示：暂未发现该成分在市面上有高频、大规模的违规夸大营销话术。")

# ----------------------------------------------------------------
# 4. 前端主交互视图控制中心
# ----------------------------------------------------------------
if df_ing is not None:
    mode = st.sidebar.radio("选择查询模式", ["商品名称搜索", "手动拆解成分评估"])

    if mode == "商品名称搜索":
        st.markdown("## 🔍 智能商品检索")
        search_input = st.text_input("请输入您想查询的营养品商品全称或别名", placeholder="如: 斯维诗大蓟水飞蓟护肝片")
        
        if search_input:
            matched_rows = df_prod[
                df_prod["商品官方全称"].str.contains(search_input, case=False, na=False) |
                df_prod["搜索别名(逗号隔开)"].str.contains(search_input, case=False, na=False)
            ]
            
            if not matched_rows.empty:
                st.success(f"成功在已知库中检索到商品，正在解析复合配方...")
                for _, p_row in matched_rows.iterrows():
                    p_name = p_row["商品官方全称"]
                    brand = p_row["品牌名"]
                    daily_servings = p_row["每日建议服用几粒"]
                    ing_target = p_row["包含的成分(对应表1中文名)"]
                    raw_dose = p_row["单粒原料投料量"]
                    
                    st.markdown(f"""
                    <div style="background-color:#eceff1; padding:10px; border-radius:4px; margin-bottom:10px; font-size:14px;">
                        🏢 <b>品牌：</b>{brand} | 📦 <b>官方注册名：</b>{p_name} | 💊 <b>标准频次：</b>每日 {daily_servings} 粒
                    </div>
                    """, unsafe_allow_html=True)
                    execute_evaluation_engine(ing_target, raw_dose, daily_servings)
            else:
                st.warning("⚠️ 暂未收录该品牌商品。请通过左侧边栏切换至【手动拆解成分评估】模式进行即时计算。")

    elif mode == "手动拆解成分评估":
        st.markdown("## 🧪 手动成分反向拆解")
        selected_ing = st.selectbox("1. 请选择您要评估的活性成分", df_ing["中文标准名"].tolist())
        current_unit = df_ing[df_ing["中文标准名"] == selected_ing]["单位"].values[0]
        
        input_dose = st.number_input(f"2. 请输入单粒/单剂的【原料投料量】 (单位已自动锁定为: {current_unit})", min_value=0.0, step=1.0, value=100.0)
        input_servings = st.number_input("3. 请选择说明书推荐的【每日服用几粒/几剂】", min_value=1, max_value=100, step=1, value=2)
        
        if st.button("开始动态循证评估", type="primary"):
            execute_evaluation_engine(selected_ing, input_dose, input_servings)
