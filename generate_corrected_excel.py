import pandas as pd
import numpy as np
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

xls = pd.ExcelFile('fund_screening_20260624_201806.xlsx')

all_funds = pd.read_excel(xls, sheet_name='01_全市场排行')
all_funds.columns = ['序号', '基金代码', '基金简称', '日期', '单位净值', '累计净值',
                    '日涨跌幅', '近1周', '近1月', '近3月', '近6月', '近1年', '近2年', '近3年',
                    '今年来', '成立以来', '成立以来收益', '费率']

for col in ['近1年', '近6月', '近3月', '近1月', '近1周', '日涨跌幅', '近3年', '近2年', '今年来']:
    all_funds[col] = pd.to_numeric(all_funds[col], errors='coerce')

my_codes = ['004597','013477','008702','022015','017437','024725','008888','025720','005164','013279','004503','012349','000216','009033','023729','011610','100032','161133','003095','010421']
candidates = all_funds[~all_funds['基金代码'].astype(str).str.zfill(6).isin(my_codes)].copy()

def classify_fund(row):
    r1y = row['近1年'] if pd.notna(row['近1年']) else -999
    r6m = row['近6月'] if pd.notna(row['近6月']) else -999
    if r1y > 80 or r6m > 50:
        return 'A_过热型(不推荐追)'
    elif r1y > 30 and r6m > 10:
        return 'B_成长型(等回调定投)'
    elif r1y > 5 and r6m > -5:
        return 'C_稳健型(可定投)'
    elif r1y >= -5 and r6m >= -10:
        return 'D_防守型(推荐定投)'
    else:
        return 'E_弱势型(暂不推荐)'

def classify_theme(name):
    name = str(name)
    theme_rules = [
        ('AI/人工智能', ['人工智能', 'AI应用', '智能']),
        ('半导体/芯片', ['半导体', '芯片', '设备']),
        ('新能源', ['新能源', '碳中和', '光伏', '储能', '新能源车', '锂电', '清洁能源']),
        ('医药/医疗', ['医药', '医疗', '健康', '生物', '创新药', '制药']),
        ('消费', ['消费', '白酒', '食品', '饮料', '家电', '汽车']),
        ('红利/低波', ['红利', '低波', '高股息', '分红']),
        ('银行', ['银行']),
        ('债券/固收', ['债券', '纯债', '中短债', '同业存单', '固收']),
        ('黄金', ['黄金', '贵金属', '金ETF']),
        ('QDII/海外', ['QDII', '纳斯达克', '标普', '全球', '美国', '海外']),
        ('数据中心/云计算', ['数据中心', 'IDC', '云计算', '服务器']),
        ('软件/信创', ['软件', '信创', '操作系统', '数据库', '网络安全', '信息安全']),
        ('光模块/通信', ['光模块', '光通信', '光纤', '通信']),
    ]
    for theme, keywords in theme_rules:
        for kw in keywords:
            if kw in name:
                return theme
    return '其他'

candidates['主题分类'] = candidates['基金简称'].apply(classify_theme)
candidates['风险分类'] = candidates.apply(classify_fund, axis=1)

candidates['综合得分'] = (
    candidates['近1年'].fillna(0) * 0.25 +
    candidates['近6月'].fillna(0) * 0.25 +
    candidates['近3月'].fillna(0) * 0.2 +
    candidates['近1月'].fillna(0) * 0.2
)

output_file = 'fund_screening_corrected_20260624.xlsx'

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # Sheet 1-5: 按风险分类
    defensive = candidates[candidates['风险分类'] == 'D_防守型(推荐定投)'].sort_values('综合得分', ascending=False)
    defensive.to_excel(writer, sheet_name='1-防守型(推荐定投)', index=False)

    steady = candidates[candidates['风险分类'] == 'C_稳健型(可定投)'].sort_values('综合得分', ascending=False)
    steady.to_excel(writer, sheet_name='2-稳健型(可定投)', index=False)

    growth = candidates[candidates['风险分类'] == 'B_成长型(等回调定投)'].sort_values('综合得分', ascending=False)
    growth.to_excel(writer, sheet_name='3-成长型(等回调)', index=False)

    hot = candidates[candidates['风险分类'] == 'A_过热型(不推荐追)'].sort_values('综合得分', ascending=False)
    hot.to_excel(writer, sheet_name='4-过热型(不买)', index=False)

    weak = candidates[candidates['风险分类'] == 'E_弱势型(暂不推荐)'].sort_values('综合得分', ascending=False)
    weak.to_excel(writer, sheet_name='5-弱势型(暂不买)', index=False)

    # Sheet 6: 你的组合缺口
    gap_themes = ['医药/医疗', '消费', '新能源', '数据中心/云计算', '软件/信创', '红利/低波']
    gap_data = candidates[candidates['主题分类'].isin(gap_themes)].sort_values(['主题分类', '综合得分'], ascending=[True, False])
    gap_data.to_excel(writer, sheet_name='6-你的组合缺口', index=False)

    # Sheet 7: AI 相关
    ai_all = candidates[candidates['主题分类'] == 'AI/人工智能'].sort_values('综合得分', ascending=False)
    ai_all.to_excel(writer, sheet_name='7-AI相关全景', index=False)

    # Sheet 8: 全市场 TOP50
    top50 = candidates.sort_values('综合得分', ascending=False).head(50)
    top50.to_excel(writer, sheet_name='8-全市场TOP50', index=False)

    # Sheet 9: 你的持仓
    my_holdings = all_funds[all_funds['基金代码'].astype(str).str.zfill(6).isin(my_codes)].copy()
    my_holdings['主题分类'] = my_holdings['基金简称'].apply(classify_theme)
    for col in ['近1年', '近6月', '近3月', '近1月']:
        my_holdings[col] = pd.to_numeric(my_holdings[col], errors='coerce')
    my_holdings.to_excel(writer, sheet_name='9-你的持仓', index=False)

    # Sheet 10: 定投计划
    plan_data = {
        '定投日': ['周一', '周一', '周一', '周一', '周二', '周二', '周三', '周三', '周四'],
        '基金名称': ['南方创业板人工智能ETF联接A', '华宝纳斯达克精选(QDII)C', '华夏科创50ETF联接A', '富国中证红利指数增强A',
                     '华夏中证金融科技ETF联接C', '鹏华中证银行指数(LOF)C', '中欧医疗健康混合A', '华泰柏瑞中证1000ETF联接A', '华夏国证半导体芯片ETF联接C'],
        '基金代码': ['024725', '017437', '11612', '100032', '013477', '004597', '003095', '16630', '008888'],
        '定投金额': [150, 100, 50, 100, '190~195', 70, 50, 50, 50],
        '类型': ['固定', '固定', '固定', '固定', '智能', '固定', '固定', '固定', '固定'],
        '分类': ['成长型', '稳健型', '稳健型', '防守型', '成长型', '防守型', '防守型', '稳健型', '成长型'],
    }
    plan_df = pd.DataFrame(plan_data)
    plan_df.to_excel(writer, sheet_name='10-修正后定投计划', index=False)

    # Sheet 11: 代码勘误表
    error_data = {
        '原推荐代码': ['161133', '011610', '010421', '17854'],
        '原假设名称': ['易方达中证1000ETF联接A', '华夏科创50ETF联接A', '华夏消费龙头混合A', '某数据中心基金'],
        '实际名称': ['摩根恒生科技ETF(FOF-LOF)A', '华夏科技创新50ETF联接A', '通财新能源精选A', '代码不存在'],
        '正确代码': ['16630', '11612', '未找到(可能为LOF)', '008021(华富AI产业)'],
    }
    error_df = pd.DataFrame(error_data)
    error_df.to_excel(writer, sheet_name='11-代码勘误表', index=False)

print(f'修正版 Excel 已生成: {output_file}')
print()
print('11 个 Sheet:')
print('  1-防守型(推荐定投) - 安全边际最高')
print('  2-稳健型(可定投) - 趋势向好')
print('  3-成长型(等回调) - 波动大需耐心')
print('  4-过热型(不买) - 短期涨幅过大')
print('  5-弱势型(暂不买) - 走势不佳')
print('  6-你的组合缺口 - 医药/消费/新能源等')
print('  7-AI相关全景 - 所有AI基金')
print('  8-全市场TOP50 - 综合评分最高')
print('  9-你的持仓 - 当前持仓明细')
print('  10-修正后定投计划 - 9只基金')
print('  11-代码勘误表 - 4处错误对照')
