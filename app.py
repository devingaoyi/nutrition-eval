import streamlit as st
import pandas as pd
import numpy as np
import difflib

# ----------------------------------------------------------------
# 1. 页面全局配置与安全盾牌样式定义
# ----------------------------------------------------------------
st.set_page_config(page_title="循证营养品深度评估系统", layout="centered")

st.markdown("""
> ⚠️ **医学免责声明：** 本系统提供的数据均基于公开的临床循证医学文献（如 PubMed）提取。
> 评估结果仅供科学科普与膳食参考，**不构成任何医疗建议或疾病治疗方案**。
> 若您正在服用处方药或患有器质性疾病，请务必遵医嘱，切勿盲目停药或以营养品替代药物。
""")
st.write("---")

# ----------------------------------------------------------------
# 2. 内存数据加载模块 (位置解耦设计：彻底免疫Excel表头文字错误)
# ----------------------------------------------------------------
@st.cache_data
def load_and_clean_data():
    try:
        df_ing = pd.read_excel("ingredients.xlsx")
        df_evi = pd.read_excel("efficacy_evidence.xlsx")
        df_deb = pd.read_excel("debunking_statements.xlsx")
        df_prod = pd.read_excel("products.xlsx")
        
        # 强制基于列的物理位置进行重命名，完全忽略用户在Excel第一行填写的任何文本
        df_ing.columns = ['中文标准名', '英文标准名', '是否为化合物形态', '折算系数', '每日安全上限(UL)', '单位'][:len(df_ing.columns)]
        df_evi.columns = ['所属成分(中文名)', '学术健康效果', '临床起效量', '临床最大推荐量', '科学共识陈述(给用户的结论)'][:len(df_evi.columns)]
        df_deb.columns = ['所属成分(中文名)', '商家夸大话术/伪功效', '触发打假的关键词', '科学驳斥陈述(给用户的警示)'][:len(df_deb.columns)]
        df_prod.columns = ['品牌名', '商品官方全称', '搜索别名(逗号隔开)', '每日建议服用几粒', '包含的成分(对应表1中文名)', '单粒原料投料量'][:len(df_prod.columns)]
        
        # 统一清洗所有文本型单元格的前后隐藏空格
        for df in [df_ing, df_evi, df_deb, df_prod]:
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).str.strip()
        return df_ing, df_evi, df_deb, df_prod
    except Exception as e:
        st.error(f"底层Excel数据加载失败，请确保文件名与结构完整。错误信息: {str(e)}")
        return None, None, None, None

df_ing, df_evi, df_deb, df_prod = load_and_clean_data()

# ----------------------------------------------------------------
# 3. 核心四段式算法处理引擎
# ----------------------------------------------------------------
def execute_evaluation_engine(ing_name, raw_dose, servings):
    ing_meta = df_ing[df_ing["中文标准名"] == ing_name]
    if ing_meta.empty:
        st.error(f"成分库中未找到标准名称为 【{ing_name}】 的记录。")
        return

    factor = float(ing_meta["折算系数"].values[0])
    unit = str(ing_meta["单位"].values[0])
    ul_val = ing_meta["每日安全上限(UL)"].values[0]
    upper_limit = float(ul_val) if pd.notna(ul_val) and str(ul_val) != "无" and str(ul_val) != "nan" else float('inf')

    daily_intake = float(raw_dose) * float(servings) * factor

    st.subheader(f"📊 成分评估看板: {ing_name}")
    st.write(f"实际计算结果：每日活性物质总摄入量约为 **{daily_intake:.2f} {unit}**")

    if daily_intake > upper_limit:
        st.error(f"🚨 毒性与超量危险：当前剂量已超过国家推荐的每日最高耐受上限（UL: {upper_limit} {unit}）。长期连续服用存在明确的肝肾损伤等潜在不良副反应风险，建议立刻停止服用。")
    
    evidence_rows = df_evi[df_evi["所属成分(中文名)"] == ing_name]
    if not evidence_rows.empty:
        st.markdown("### 🟢 循证医学·真实科学功效")
        for _, row in evidence_rows.iterrows():
            min_eff = float(row["临床起效量"])
            max_eff = float(row["临床最大推荐量"])
            goal = row["学术健康效果"]
            consensus = row["科学共识陈述(给用户的结论)"]

            if daily_intake < min_eff:
                status_text = "⚠️ 剂量不足"
                status_color = "orange"
                desc = "当前服用量低于临床试验的起效阈值，可能无法达到预期健康效果。"
            elif min_eff <= daily_intake <= max_eff:
                status_text = "✅ 剂量达标"
                status_color = "green"
                desc = "当前服用量处于临床循证医学推荐的黄金有效区间，能最大化发挥其生物学效用。"
            else:
                status_text = "🟡 高剂量提示"
                status_color = "blue"
                desc = "当前剂量已超过常规膳食推荐区间，属于临床高强度干预剂量，普通人不建议长期无医嘱维持。"

            with st.expander(f"{goal} - :{status_color}[{status_text}]"):
                st.write(f"**临床推荐有效区间：** {min_eff} - {max_eff} {unit}")
                st.write(f"**状态评估：** {desc}")
                st.write(f"**科学共识：** {consensus}")

    # 读取该成分对应的打假辟谣库 (Tier 3)
    debunk_rows = df_deb[df_deb["所属成分(中文名)"] == ing_name]
    st.markdown("### 🔴 商业夸大·防坑辟谣看板")
    if not debunk_rows.empty:
        for _, row in debunk_rows.iterrows():
            claim = row["商家夸大话术/伪功效"]
            refutation = row["科学驳斥陈述(给用户的警示)"]
            
            st.markdown(f"❌ **商家宣称伪功效：** *{claim}*")
            st.markdown(f"🧬 **证据级别：** `E 级 (无人类临床证据 / 商业纯粹夸大)`")
            st.markdown(f"💡 **循证医学驳斥：** {refutation}")
            st.write("---")
    else:
        st.info("💡 提示：暂未发现该成分在市面上有高频、大规模的违规夸大营销话术。")

# ----------------------------------------------------------------
# 4. 前端交互视图控制中心
# ----------------------------------------------------------------
if df_ing is not None:
    mode = st.sidebar.radio("选择查询模式", ["商品名称搜索", "手动拆解成分评估"])

    if mode == "商品名称搜索":
        st.markdown("### 🔍 智能商品检索")
        search_input = st.text_input("请输入您想查询的营养品商品全称或别名", placeholder="如: 斯维诗大蓟水飞蓟护肝片")
        
        if search_input:
            matched_rows = df_prod[
                df_prod["商品官方全称"].str.contains(search_input, case=False, na=False) |
                df_prod["搜索别名(逗号隔开)"].str.contains(search_input, case=False, na=False)
            ]
            
            if not matched_rows.empty:
                st.success(f"成功在白名单库中检索到该商品，正在解析其配方构成...")
                for _, p_row in matched_rows.iterrows():
                    p_name = p_row["商品官方全称"]
                    brand = p_row["品牌名"]
                    daily_servings = p_row["每日建议服用几粒"]
                    ing_target = p_row["包含的成分(对应表1中文名)"]
                    raw_dose = p_row["单粒原料投料量"]
                    
                    st.info(f"🏷️ **品牌：** {brand} | **标准商品名：** {p_name} | **建议服用量：** 每日 {daily_servings} 粒/剂")
                    execute_evaluation_engine(ing_target, raw_dose, daily_servings)
            else:
                st.warning("⚠️ 暂未收录该品牌商品。请通过左侧边栏切换至【手动拆解成分评估】模式进行即时计算。")

    elif mode == "手动拆解成分评估":
        st.markdown("### 🧪 手动成分反向拆解")
        st.write("请对照您手里营养品瓶身背面的成分表（Supplement Facts）进行选择：")
        
        selected_ing = st.selectbox("1. 请选择您要评估的活性成分", df_ing["中文标准名"].tolist())
        current_unit = df_ing[df_ing["中文标准名"] == selected_ing]["单位"].values[0]
        
        input_dose = st.number_input(f"2. 请输入单粒/单剂的【原料投料量】 (单位已自动锁定为: {current_unit})", min_value=0.0, step=1.0, value=100.0)
        input_servings = st.number_input("3. 请选择说明书推荐的【每日服用几粒/几剂】", min_value=1, max_value=100, step=1, value=2)
        
        if st.button("开始动态循证评估", type="primary"):
            execute_evaluation_engine(selected_ing, input_dose, input_servings)
