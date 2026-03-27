import io
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class PDFService:
    def __init__(self):
        self.styles = getSampleStyleSheet()

    def _default_meta(self, meta=None):
        meta = dict(meta or {})
        meta.setdefault('school', '河南师范大学')
        meta.setdefault('team', 'PIONEER工作室')
        meta.setdefault('competition', '第十二届@际大学生创新大赛')
        meta.setdefault('date', datetime.now().strftime('%Y-%m-%d'))
        meta.setdefault('title', '智析实验 · 基于SHAP的可解释AI科研分析系统')
        meta.setdefault('subtitle', 'SHAP XAI Attribution & Optimization Platform')
        meta.setdefault('authors', 'PIONEER工作室团队成员')
        meta.setdefault('department', '河南师范大学化学化工学院')
        meta.setdefault('advisor', '（待填写）')
        return meta

    def _page_header_footer(self, meta, section_title=''):
        def _draw(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 9)
            canvas.setFillColor(colors.HexColor('#6b7280'))

            header_left = meta.get('title', '')
            header_right = section_title or meta.get('competition', '')
            canvas.drawString(doc.leftMargin, A4[1] - 1.2 * cm, header_left)
            canvas.drawRightString(A4[0] - doc.rightMargin, A4[1] - 1.2 * cm, header_right)

            canvas.setStrokeColor(colors.HexColor('#e5e7eb'))
            canvas.setLineWidth(0.6)
            canvas.line(doc.leftMargin, A4[1] - 1.35 * cm, A4[0] - doc.rightMargin, A4[1] - 1.35 * cm)

            footer_left = f"{meta.get('school', '')} · {meta.get('team', '')}"
            footer_right = f"Page {doc.page}"
            canvas.drawString(doc.leftMargin, 1.0 * cm, footer_left)
            canvas.drawRightString(A4[0] - doc.rightMargin, 1.0 * cm, footer_right)
            canvas.restoreState()
        return _draw

    def _cover_story(self, meta, report_id=None, sample_id=None, doc_type='报告'):
        story = []
        story.append(Spacer(1, 70))
        story.append(Paragraph(meta.get('title', ''), self.styles['Title']))
        story.append(Spacer(1, 8))
        story.append(Paragraph(meta.get('subtitle', ''), self.styles['Heading2']))
        story.append(Spacer(1, 20))

        # Author information table
        author_rows = [
            ['作者', meta.get('authors', '-')],
            ['单位', meta.get('department', '-')],
            ['指导老师', meta.get('advisor', '-')],
            ['学校', meta.get('school', '-')],
            ['团队', meta.get('team', '-')],
            ['比赛/赛道', meta.get('competition', '-')],
            ['日期', meta.get('date', '-')],
            ['文档类型', f"{doc_type}（论文版式PDF）"],
        ]
        if report_id is not None:
            author_rows.append(['报告编号', str(report_id)])
        if sample_id is not None:
            author_rows.append(['样本编号', str(sample_id)])

        t = Table(author_rows, colWidths=[3.0 * cm, 13.0 * cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8)
        ]))
        story.append(t)
        story.append(Spacer(1, 16))
        story.append(Paragraph('注：本报告由系统自动生成，内容用于竞赛展示与科研辅助，不作为最终实验结论。', self.styles['BodyText']))
        story.append(PageBreak())
        return story

    def build_report_pdf(
        self,
        report,
        sample,
        model=None,
        level_label='-',
        level_description='-',
        meta=None,
        abstract_text=None,
        conclusion_text=None,
        keywords=None,
        abstract_sections=None,
        references=None,
        keywords_en=None,
        abstract_sections_en=None,
        conclusion_en=None,
        figure_captions=None
    ):
        buffer = io.BytesIO()
        meta = self._default_meta(meta)
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=1.6 * cm,
            bottomMargin=1.6 * cm
        )

        story = []
        story.extend(self._cover_story(meta, report_id=getattr(report, 'id', None), sample_id=getattr(sample, 'sample_id', None) if sample else None, doc_type='报告'))

        # Chinese Abstract
        story.append(Paragraph('摘要（中文）', self.styles['Heading2']))
        if keywords:
            kw = '；'.join([str(x) for x in (keywords or []) if x])
            story.append(Paragraph(f'<b>关键词：</b>{kw}', self.styles['BodyText']))
            story.append(Spacer(1, 6))

        method = (abstract_sections or {}).get('method') if isinstance(abstract_sections, dict) else None
        result = (abstract_sections or {}).get('result') if isinstance(abstract_sections, dict) else None
        concl = (abstract_sections or {}).get('conclusion') if isinstance(abstract_sections, dict) else None

        if method or result or concl:
            if method:
                story.append(Paragraph('<b>方法：</b>' + self._safe_paragraph(method), self.styles['BodyText']))
            if result:
                story.append(Paragraph('<b>结果：</b>' + self._safe_paragraph(result), self.styles['BodyText']))
            if concl:
                story.append(Paragraph('<b>结论：</b>' + self._safe_paragraph(concl), self.styles['BodyText']))
        else:
            story.append(Paragraph(self._safe_paragraph(abstract_text) if abstract_text else '本报告基于实验数据与模型推断结果，生成可解释归因与优化建议，用于辅助科研决策。', self.styles['BodyText']))
        story.append(Spacer(1, 10))

        # English Abstract
        story.append(Paragraph('Abstract (English)', self.styles['Heading2']))
        if keywords_en:
            kw_en = '; '.join([str(x) for x in (keywords_en or []) if x])
            story.append(Paragraph(f'<b>Keywords:</b> {kw_en}', self.styles['BodyText']))
            story.append(Spacer(1, 6))

        method_en = (abstract_sections_en or {}).get('method') if isinstance(abstract_sections_en, dict) else None
        result_en = (abstract_sections_en or {}).get('result') if isinstance(abstract_sections_en, dict) else None
        concl_en = (abstract_sections_en or {}).get('conclusion') if isinstance(abstract_sections_en, dict) else None

        if method_en or result_en or concl_en:
            if method_en:
                story.append(Paragraph('<b>Method:</b> ' + self._safe_paragraph(method_en), self.styles['BodyText']))
            if result_en:
                story.append(Paragraph('<b>Result:</b> ' + self._safe_paragraph(result_en), self.styles['BodyText']))
            if concl_en:
                story.append(Paragraph('<b>Conclusion:</b> ' + self._safe_paragraph(concl_en), self.styles['BodyText']))
        else:
            story.append(Paragraph('This report generates explainable attribution and optimization suggestions based on experimental data and model inference, serving as a decision support tool for scientific research.', self.styles['BodyText']))
        story.append(Spacer(1, 12))

        # Conclusion section (Chinese + English)
        story.append(Paragraph('结论 / Conclusion', self.styles['Heading2']))
        story.append(Paragraph(self._safe_paragraph(conclusion_text) if conclusion_text else '综合归因结果与敏感性分析，建议围绕关键影响因子做梯度实验并持续迭代优化。', self.styles['BodyText']))
        if conclusion_en:
            story.append(Spacer(1, 6))
            story.append(Paragraph(self._safe_paragraph(conclusion_en), self.styles['BodyText']))
        story.append(Spacer(1, 12))

        header_table = Table([
            ['报告编号', str(getattr(report, 'id', '-')),
             '样本编号', getattr(sample, 'sample_id', '-') if sample else '-'],
            ['实验分组', getattr(sample, 'experiment_group', '-') if sample else '-',
             '实验轮次', str(getattr(sample, 'experiment_round', '-') if sample else '-')],
            ['归因模型', getattr(model, 'name', '-') if model else '-',
             '诊断时间', getattr(report, 'created_at', '').strftime('%Y-%m-%d %H:%M') if getattr(report, 'created_at', None) else '-']
        ], colWidths=[2.2 * cm, 5.8 * cm, 2.2 * cm, 5.8 * cm])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(header_table)
        story.append(Spacer(1, 12))

        probability = (getattr(report, 'success_probability', 0) or 0) * 100
        story.append(Paragraph(f'结果等级：<b>{level_label}</b>', self.styles['Heading2']))
        story.append(Paragraph(f'预测成功率：<b>{probability:.1f}%</b>', self.styles['BodyText']))
        story.append(Paragraph(level_description or '-', self.styles['BodyText']))
        story.append(Spacer(1, 12))

        top_features = getattr(report, 'top_features', None) or []
        if top_features:
            story.append(Paragraph('Top 特征贡献（SHAP）', self.styles['Heading2']))
            img = self._plot_top_features_bar(top_features)
            story.append(Image(img, width=16 * cm, height=8 * cm))
            story.append(Spacer(1, 10))

            rows = [['排名', '特征', '贡献值', '特征值']]
            for idx, feat in enumerate(top_features[:8], start=1):
                rows.append([
                    str(idx),
                    str(feat.get('display_name') or feat.get('feature') or '-'),
                    f"{float(feat.get('contribution', 0)):.4f}",
                    str(feat.get('formatted_value') or feat.get('value') or '-')
                ])
            t = Table(rows, colWidths=[1.2 * cm, 6.2 * cm, 2.6 * cm, 6.0 * cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eaf2ff')),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5)
            ]))
            story.append(t)
            story.append(Spacer(1, 12))

        advice = getattr(report, 'expert_advice', None) or ''
        story.append(Paragraph('优化建议摘要', self.styles['Heading2']))
        story.append(Paragraph(self._safe_paragraph(advice) if advice else '建议围绕 Top 因子进行单变量梯度扰动实验，逐步逼近最佳条件区间。', self.styles['BodyText']))

        story.append(Spacer(1, 14))
        story.append(Paragraph('参考文献（GB/T 7714）', self.styles['Heading2']))
        refs_list = [str(x).strip() for x in (references or []) if str(x).strip()]
        if refs_list:
            refs_html = '<br/>'.join([self._safe_paragraph(x) for x in refs_list[:12]])
            story.append(Paragraph(refs_html, self.styles['BodyText']))
        else:
            refs = (
                '[1] Lundberg SM, Lee SI. A unified approach to interpreting model predictions[C]//NeurIPS. 2017.<br/>'
                '[2] Molnar C. Interpretable Machine Learning[M]. 2nd ed. 2022.<br/>'
                '[3] SHAP Documentation[EB/OL]. https://shap.readthedocs.io/'
            )
            story.append(Paragraph(refs, self.styles['BodyText']))

        doc.build(
            story,
            onFirstPage=self._page_header_footer(meta, section_title='报告PDF'),
            onLaterPages=self._page_header_footer(meta, section_title='报告PDF')
        )
        buffer.seek(0)
        return buffer

    def build_case_study_pdf(
        self,
        sample,
        round_timeline,
        before_after=None,
        meta=None,
        abstract_text=None,
        conclusion_text=None,
        keywords=None,
        abstract_sections=None,
        references=None
    ):
        buffer = io.BytesIO()
        meta = self._default_meta(meta)
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=1.6 * cm,
            bottomMargin=1.6 * cm
        )

        story = []
        story.extend(self._cover_story(meta, sample_id=getattr(sample, 'sample_id', None), doc_type='案例对比'))

        story.append(Paragraph('摘要', self.styles['Heading2']))
        if keywords:
            kw = '；'.join([str(x) for x in (keywords or []) if x])
            story.append(Paragraph(f'<b>关键词：</b>{kw}', self.styles['BodyText']))
            story.append(Spacer(1, 6))

        method = (abstract_sections or {}).get('method') if isinstance(abstract_sections, dict) else None
        result = (abstract_sections or {}).get('result') if isinstance(abstract_sections, dict) else None
        concl = (abstract_sections or {}).get('conclusion') if isinstance(abstract_sections, dict) else None
        if method or result or concl:
            if method:
                story.append(Paragraph('<b>方法：</b>' + self._safe_paragraph(method), self.styles['BodyText']))
            if result:
                story.append(Paragraph('<b>结果：</b>' + self._safe_paragraph(result), self.styles['BodyText']))
            if concl:
                story.append(Paragraph('<b>结论：</b>' + self._safe_paragraph(concl), self.styles['BodyText']))
        else:
            story.append(Paragraph(self._safe_paragraph(abstract_text) if abstract_text else '本案例展示样本在多轮优化过程中的成功率提升轨迹与关键因子变化，用于证明优化闭环效果。', self.styles['BodyText']))
        story.append(Spacer(1, 10))

        story.append(Paragraph('结论', self.styles['Heading2']))
        story.append(Paragraph(self._safe_paragraph(conclusion_text) if conclusion_text else '通过多轮优化迭代，成功率显著提升，关键因素贡献结构发生调整，验证了系统对实验优化的有效支持。', self.styles['BodyText']))
        story.append(Spacer(1, 12))

        story.append(Paragraph(f'样本编号：<b>{getattr(sample, "sample_id", "-")}</b>', self.styles['BodyText']))
        story.append(Paragraph(f'实验分组：<b>{getattr(sample, "experiment_group", "-")}</b>  |  实验轮次：<b>{getattr(sample, "experiment_round", "-")}</b>', self.styles['BodyText']))
        story.append(Spacer(1, 10))

        if round_timeline:
            labels = [item.get('round_label') for item in round_timeline]
            values = [float(item.get('probability', 0)) for item in round_timeline]
            img = self._plot_line(labels, values, title='成功率随轮次变化')
            story.append(Image(img, width=16 * cm, height=8 * cm))
            story.append(Spacer(1, 10))

        if before_after:
            story.append(Paragraph('前后对比', self.styles['Heading2']))
            rows = [
                ['指标', '第1轮', f'第{len(round_timeline)}轮'],
                ['成功率(%)', str(before_after.get('first_probability', '-')), str(before_after.get('last_probability', '-'))],
                ['提升(%)', '-', str(before_after.get('improvement', '-'))]
            ]
            t = Table(rows, colWidths=[4.0 * cm, 6.0 * cm, 6.0 * cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eaf2ff')),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
            ]))
            story.append(t)
            story.append(Spacer(1, 12))

        story.append(Paragraph('轮次摘要', self.styles['Heading2']))
        rows = [['轮次', '成功率(%)', 'Top1因子', '建议摘要']]
        for item in (round_timeline or [])[:10]:
            top1 = ((item.get('top3_features') or [{}])[0] or {})
            rows.append([
                str(item.get('round_label', '-')),
                str(item.get('probability', '-')),
                str(top1.get('name', '-')),
                (item.get('advice', '') or '')[:60]
            ])
        t2 = Table(rows, colWidths=[2.2 * cm, 2.4 * cm, 4.4 * cm, 7.0 * cm])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eaf2ff')),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5)
        ]))
        story.append(t2)

        story.append(Spacer(1, 14))
        story.append(Paragraph('参考文献（GB/T 7714）', self.styles['Heading2']))
        refs_list = [str(x).strip() for x in (references or []) if str(x).strip()]
        if refs_list:
            refs_html = '<br/>'.join([self._safe_paragraph(x) for x in refs_list[:12]])
            story.append(Paragraph(refs_html, self.styles['BodyText']))
        else:
            refs = (
                '[1] Lundberg SM, Lee SI. A unified approach to interpreting model predictions[C]//NeurIPS. 2017.<br/>'
                '[2] Molnar C. Interpretable Machine Learning[M]. 2nd ed. 2022.<br/>'
                '[3] SHAP Documentation[EB/OL]. https://shap.readthedocs.io/'
            )
            story.append(Paragraph(refs, self.styles['BodyText']))

        doc.build(
            story,
            onFirstPage=self._page_header_footer(meta, section_title='案例PDF'),
            onLaterPages=self._page_header_footer(meta, section_title='案例PDF')
        )
        buffer.seek(0)
        return buffer

    def _plot_top_features_bar(self, top_features):
        labels = [str(f.get('display_name') or f.get('feature') or '-') for f in top_features[:8]]
        values = [float(f.get('contribution', 0)) for f in top_features[:8]]
        colors_list = ['#2ec4b6' if v >= 0 else '#f4a261' for v in values]

        fig, ax = plt.subplots(figsize=(9, 4.2), dpi=150)
        ax.barh(labels[::-1], values[::-1], color=colors_list[::-1])
        ax.set_xlabel('SHAP Contribution')
        ax.grid(axis='x', alpha=0.2)
        fig.tight_layout()

        img = io.BytesIO()
        fig.savefig(img, format='png', bbox_inches='tight')
        plt.close(fig)
        img.seek(0)
        return ImageReader(img)

    def _plot_line(self, labels, values, title=''):
        fig, ax = plt.subplots(figsize=(9, 4.2), dpi=150)
        ax.plot(range(1, len(values) + 1), values, marker='o', color='#4361ee')
        ax.set_xticks(range(1, len(values) + 1))
        ax.set_xticklabels(labels, rotation=0)
        ax.set_ylim(0, 100)
        ax.set_ylabel('Success Probability (%)')
        if title:
            ax.set_title(title)
        ax.grid(alpha=0.2)
        fig.tight_layout()

        img = io.BytesIO()
        fig.savefig(img, format='png', bbox_inches='tight')
        plt.close(fig)
        img.seek(0)
        return ImageReader(img)

    def _safe_paragraph(self, text):
        return (text or '').replace('\n', '<br/>')
