import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

OUT = r"C:\Netease_Ai\03_document_processing\ppt\outputs\charts"
os.makedirs(OUT, exist_ok=True)

RED   = '#C00000'
GRAY  = '#AAAAAA'
DARK  = '#1A1A1A'
LGRAY = '#F0F0F0'
RED2  = '#E84040'

plt.rcParams['font.family'] = 'Microsoft YaHei'
plt.rcParams['axes.unicode_minus'] = False

# ── 图1：AI前后对比效果（第02页）柱状图 ──
fig, ax = plt.subplots(figsize=(5.5, 3.2))
fig.patch.set_facecolor('white')
metrics = ['次日留存率', 'NPC互动时长', '新手完成率', '玩家满意度']
before  = [38, 2.1, 52, 71]
after   = [51, 4.8, 73, 88]
x = np.arange(len(metrics))
w = 0.32
b1 = ax.bar(x - w/2, before, w, label='引入AI前', color=GRAY,   zorder=3)
b2 = ax.bar(x + w/2, after,  w, label='引入AI后', color=RED,    zorder=3)
ax.set_xticks(x)
ax.set_xticklabels(metrics, fontsize=11)
ax.set_ylabel('数值（%  /  分钟）', fontsize=10)
ax.set_ylim(0, 105)
ax.yaxis.grid(True, color='#EEEEEE', zorder=0)
ax.set_axisbelow(True)
ax.spines[['top','right']].set_visible(False)
for bar in b2:
    h = bar.get_height()
    ax.annotate(f'+{int(h - before[list(b2).index(bar)])}',
                xy=(bar.get_x()+bar.get_width()/2, h+1.5),
                ha='center', va='bottom', fontsize=9, color=RED, fontweight='bold')
ax.legend(fontsize=10, framealpha=0)
ax.set_title('AI 介入前后关键指标对比', fontsize=12, fontweight='bold', pad=8)
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'chart_p02_compare.png'), dpi=150, bbox_inches='tight')
plt.close()
print('chart1 done')

# ── 图2：各方向成熟度雷达图（第04/05页）──
fig, ax = plt.subplots(figsize=(4.0, 4.0), subplot_kw=dict(polar=True))
fig.patch.set_facecolor('white')
labels  = ['智能NPC对话', '动态难度', '个性化引导', '行为预测', '情感感知']
values  = [72, 85, 68, 60, 28]
values += values[:1]
angles  = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
angles += angles[:1]
ax.plot(angles, values, color=RED, linewidth=2)
ax.fill(angles, values, color=RED, alpha=0.18)
ax.set_thetagrids(np.degrees(angles[:-1]), labels, fontsize=10)
ax.set_ylim(0, 100)
ax.set_yticks([20, 40, 60, 80, 100])
ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=8, color=GRAY)
ax.grid(color='#DDDDDD')
ax.set_title('各方向行业落地成熟度（%）', fontsize=11, fontweight='bold', pad=18)
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'chart_p04_radar.png'), dpi=150, bbox_inches='tight')
plt.close()
print('chart2 done')

# ── 图3：A/B测试效果折线图（第06页）──
fig, ax = plt.subplots(figsize=(5.5, 3.0))
fig.patch.set_facecolor('white')
days    = [1, 3, 7, 14, 21, 30]
ctrl    = [100, 72, 55, 41, 34, 29]
test    = [100, 79, 65, 54, 48, 43]
ax.plot(days, ctrl, color=GRAY, marker='o', linewidth=2, markersize=5, label='统一引导（对照组）')
ax.plot(days, test, color=RED,  marker='s', linewidth=2, markersize=5, label='个性化引导（测试组）')
ax.fill_between(days, ctrl, test, alpha=0.08, color=RED)
ax.set_xlabel('天数', fontsize=10)
ax.set_ylabel('留存率（%）', fontsize=10)
ax.set_ylim(0, 115)
ax.set_xticks(days)
ax.yaxis.grid(True, color='#EEEEEE')
ax.set_axisbelow(True)
ax.spines[['top','right']].set_visible(False)
ax.annotate('+14%', xy=(30, 43), xytext=(24, 60),
            arrowprops=dict(arrowstyle='->', color=RED),
            fontsize=11, color=RED, fontweight='bold')
ax.legend(fontsize=10, framealpha=0)
ax.set_title('新手引导 A/B 测试：30日留存率对比', fontsize=11, fontweight='bold', pad=8)
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'chart_p06_ab.png'), dpi=150, bbox_inches='tight')
plt.close()
print('chart3 done')

# ── 图4：时间节省占比饼图（第08页）──
fig, ax = plt.subplots(figsize=(3.8, 3.2))
fig.patch.set_facecolor('white')
labels4  = ['AI可自动完成', '人工把关优化', '创意决策（人）']
sizes    = [45, 30, 25]
colors4  = [RED, '#F4A0A0', LGRAY]
wedges, texts, autotexts = ax.pie(
    sizes, labels=labels4, colors=colors4,
    autopct='%1.0f%%', startangle=120,
    textprops={'fontsize': 10},
    wedgeprops={'edgecolor': 'white', 'linewidth': 2})
for at in autotexts:
    at.set_fontsize(11)
    at.set_fontweight('bold')
ax.set_title('交互设计工作量拆解\n（引入AI后）', fontsize=11, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'chart_p08_pie.png'), dpi=150, bbox_inches='tight')
plt.close()
print('chart4 done')

# ── 图5：行业渗透趋势折线图（第09页）──
fig, ax = plt.subplots(figsize=(5.5, 3.0))
fig.patch.set_facecolor('white')
years = [2021, 2022, 2023, 2024, 2025, 2026]
rates = [8, 15, 27, 42, 58, 71]
ax.plot(years, rates, color=RED, marker='o', linewidth=2.5, markersize=6)
ax.fill_between(years, rates, alpha=0.10, color=RED)
for x, y in zip(years, rates):
    ax.annotate(f'{y}%', xy=(x, y), xytext=(0, 8),
                textcoords='offset points', ha='center',
                fontsize=9, color=RED, fontweight='bold')
ax.set_xlabel('年份', fontsize=10)
ax.set_ylabel('AI交互功能渗透率（%）', fontsize=10)
ax.set_ylim(0, 90)
ax.set_xticks(years)
ax.yaxis.grid(True, color='#EEEEEE')
ax.set_axisbelow(True)
ax.spines[['top','right']].set_visible(False)
ax.set_title('游戏行业 AI 交互功能渗透率趋势', fontsize=11, fontweight='bold', pad=8)
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'chart_p09_trend.png'), dpi=150, bbox_inches='tight')
plt.close()
print('chart5 done')
print('ALL CHARTS GENERATED')
