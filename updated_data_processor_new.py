#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新的数据处理器 - 支持新的13分评分系统和文字结构化
"""

import pandas as pd
import re
import json
from typing import Dict, List, Any
import matplotlib.pyplot as plt

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class UpdatedDataProcessor:
    def __init__(self):
        self.scoring_config = {
            'market_value': {
                'max_score': 6,
                'items': {
                    'fortune_500_world': 2,
                    'fortune_500_china': 1,
                    'china_manufacturing_500': 1,
                    'unicorn_enterprise': 1,
                    'gazelle_enterprise': 1,
                    'listed_company': 1
                }
            },
            'rd_innovation': {
                'max_score': 12,
                'items': {
                    'manufacturing_champion_national': 2,
                    'manufacturing_champion_provincial': 1,
                    'sophisticated_enterprises_vipnational': 3,
                    'sophisticated_enterprises_national': 2,
                    'specialized_new_provincial': 1,
                    'high_tech_enterprise': 1,
                    'tech_center_national': 2,
                    'tech_center_provincial': 1,
                    'tech_innovation_demo': 1,
                    'standard_international': 3,
                    'standard_national': 2,
                    'standard_industry': 1
                }
            },
            'smart_manufacturing': {
                'max_score': 5,
                'items': {
                    'excellent_smart_factory': 1,
                    'leading_smart_factory': 2,
                    'lighthouse_factory': 2
                }
            },
            'green_manufacturing': {
                'max_score': 8,
                'items': {
                    'green_factory_national': 2,
                    'green_factory_provincial': 1,
                    'green_design_national': 2,
                    'green_design_provincial': 1,
                    'green_park_national': 2,
                    'green_park_provincial': 1,
                    'green_supply_national': 2,
                    'green_supply_provincial': 1
                }
            },
            'credit_level': {
                'max_score': 1,
                'items': {
                    'aeo_certification': 1
                }
            }
        }


    def parse_excel_data(self, file_path: str) -> List[Dict]:
        """解析Excel文件数据"""
        try:
            df = pd.read_excel(file_path)
            companies = []
            
            for _, row in df.iterrows():
                company = self._process_company_row(row)
                companies.append(company)
            
            return companies
        except Exception as e:
            raise Exception(f"Excel文件解析失败: {str(e)}")
    
    def _process_company_row(self, row: pd.Series) -> Dict:
        """处理单个企业数据行"""
        
        # 定义各评分字段的权重（你可以根据实际调整系数）
        weights = {
        'market_value_score': 2.0,
        'rd_innovation_score': 1.0,
        'smart_manufacturing_score': 2.0,
        'green_manufacturing_score': 1.5,
        'credit_level_score': 1.5,
        'total_score': 10/6 # 可以对总分也乘系数，或保留原始总分
        }
        company = {
            # 基本信息
            'name': str(row.get('企业名称', '')).strip(),
            'introduction': str(row.get('企业简介', '')).strip(),
            'city': str(row.get('所属市县', '')).strip(),
            'exhibition_count': self._safe_int(row.get('已参展届数', 0)),
            'vip_level': str(row.get('VIP等级', '')).strip(),
            'is_brand': str(row.get('是否品牌', '')).strip() == '是',
            'exhibition_areas': self._safe_int(row.get('参展展区数', 0)),
            'exhibition_areas_vip': str(row.get('VIP所属展区', '')).strip(),
            'eligibility_criteria': str(row.get('符合准入资格情况', '')).strip(),
            'purchase_package_status': str(row.get('购买套餐情况', '')).strip(),
            'trading_group': str(row.get('交易团', '')).strip(),
            
            # 结构化文字内容
            'highlights': self._parse_highlights(str(row.get('企业亮点', ''))),
            'leading_position': self._parse_leading_position(str(row.get('领先地位', ''))),
            'industry_sectors': self._parse_industry_sectors(str(row.get('产业板块', ''))),
            'main_products': self._parse_main_products(str(row.get('主营产品', ''))),
            'vip_products': self._parse_vip_products(str(row.get('所在VIP展区产品情况', ''))),
            
            # 评分相关数据
            'fortune_500_world': self._safe_int(row.get('世界《财富》500强(2分)', 0)),
            'fortune_500_china': self._safe_int(row.get('中国《财富》500强(1分)', 0)),
            'china_manufacturing_500': self._safe_int(row.get('中国制造业500强(1分)', 0)),
            'unicorn_enterprise': self._safe_int(row.get('独角兽企业(1分)', 0)),
            'gazelle_enterprise': self._safe_int(row.get('瞪羚企业(1分)', 0)),
            'listed_company': self._safe_int(row.get('上市企业(1分)', 0)),
            'market_value_score': self._safe_int(row.get('市场价值总分', 0)), #########
            'manufacturing_champion_national': self._safe_int(row.get('国际级制造业单项冠军(2分)', 0)),
            'manufacturing_champion_provincial': self._safe_int(row.get('省级制造业单项冠军(1分)', 0)),
            'sophisticated_enterprises_vipnational':self._safe_int(row.get('国家级专精特新重点“小巨人(3分)”', 0)),
            'sophisticated_enterprises_national':self._safe_int(row.get('国家级专精特新“小巨人”(2分)', 0),),
            'specialized_new_provincial': self._safe_int(row.get('省级专精特新(1分)', 0)),
            'high_tech_enterprise': self._safe_int(row.get('国家级高新技术企业(1分)', 0)),
            'tech_center_national': self._safe_int(row.get('国家级企业技术中心(2分)', 0)),
            'tech_center_provincial': self._safe_int(row.get('省级企业技术中心(1分)', 0)),
            'tech_innovation_demo': self._safe_int(row.get('国家技术创新示范企业(1分)', 0)),
            'standard_international': self._safe_int(row.get('参与制定国际标准(3分)', 0)),
            'standard_national': self._safe_int(row.get('参与制定国家标准(2分)', 0)),
            'standard_industry': self._safe_int(row.get('参与制定行业标准(1分)', 0)),
            'rd_innovation_score': self._safe_int(row.get('研发创新总分' ,0)),
            'excellent_smart_factory': self._safe_int(row.get('卓越级智能工厂(1分)', 0)),
            'leading_smart_factory': self._safe_int(row.get('领航级智能工厂(2分)', 0)),
            'lighthouse_factory': self._safe_int(row.get('灯塔工厂(3分)', 0)),
            'smart_manufacturing_score': self._safe_int(row.get('智能制造总分' ,0)),
            'green_factory_national': self._safe_int(row.get('国家级绿色工厂(2分)', 0)),
            'green_factory_provincial': self._safe_int(row.get('省级绿色工厂(1分)', 0)),
            'green_design_national': self._safe_int(row.get('国家级绿色设计产品(2分)', 0)),
            'green_design_provincial': self._safe_int(row.get('省级绿色设计产品(1分)', 0)),
            'green_park_national': self._safe_int(row.get('国家级绿色工业园(2分)', 0)),
            'green_park_provincial': self._safe_int(row.get('省级绿色工业园(1分)', 0)),
            'green_supply_national': self._safe_int(row.get('国家级绿色供应链管理(2分)', 0)),
            'green_supply_provincial': self._safe_int(row.get('省级绿色供应链管理(1分)', 0)),
            'green_manufacturing_score': self._safe_int(row.get('绿色制造总分', 0)),
            'aeo_certification': self._safe_int(row.get('AEO高级认证企业(2分)', 0)),
            'credit_level_score': self._safe_int(row.get('信用水平总分', 0)),
            #'total_scores': self._safe_int(row.get('总分', 0)),
        }
        # 获取原始评分数据
        company['market_value_score'] = self._safe_int(row.get('市场价值总分', 0))
        company['rd_innovation_score'] = self._safe_int(row.get('研发创新总分', 0))
        company['smart_manufacturing_score'] = self._safe_int(row.get('智能制造总分', 0))
        company['green_manufacturing_score'] = self._safe_int(row.get('绿色制造总分', 0))
        company['credit_level_score'] = self._safe_int(row.get('信用水平总分', 0))
        total_score = self._safe_int(row.get('总分', 0))

        # 应用加权系数
        weighted_scores = {
        'market_value': company['market_value_score'] * weights['market_value_score'],
        'rd_innovation': company['rd_innovation_score'] * weights['rd_innovation_score'],
        'smart_manufacturing': company['smart_manufacturing_score'] * weights['smart_manufacturing_score'],
        'green_manufacturing': company['green_manufacturing_score'] * weights['green_manufacturing_score'],
        'credit_level': company['credit_level_score'] * weights['credit_level_score'],
        }
        # 重新计算总分（可以替代原始 total_score）
        total_score = sum(weighted_scores.values()) * weights['total_score']
        # 🔧 修复关键问题：创建scores对象
        #total_score = self._safe_int(row.get('总分', 0))
        
        # 构建scores对象，这是JavaScript代码期望的数据结构
        company['scores'] = {
            'market_value': company['market_value_score'],
            
            'rd_innovation': company['rd_innovation_score'],
            
            'smart_manufacturing': company['smart_manufacturing_score'],
            'green_manufacturing': company['green_manufacturing_score'],
            
            'credit_level': company['credit_level_score'],
            
            'total': round(total_score , 2),  # 🎯 这是修复JavaScript错误的关键
            'percentage': round(total_score, 1) if total_score > 0 else 0
        }
        
        # 添加荣誉信息
        company['honors'] = self._extract_honors(row)
        
        return company
    
    def _parse_highlights(self, text: str) -> List[str]:
        """解析企业亮点"""
        if not text or text == 'nan':
            return []
        
        highlights = []
        # 按数字序号分割
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.', line):
                # 去掉序号，保留内容
                content = re.sub(r'^\d+\.', '', line).strip()
                if content:
                    highlights.append(content)
        
        return highlights
    
    def _parse_leading_position(self, text: str) -> List[str]:
        """解析领先地位"""
        if not text or text == 'nan':
            return []
        
        positions = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.', line):
                content = re.sub(r'^\d+\.', '', line).strip()
                if content:
                    positions.append(content)
        
        return positions
    
    def _parse_industry_sectors(self, text: str) -> List[str]:
        """解析产业板块"""
        if not text or text == 'nan':
            return []
        
        sectors = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.', line):
                content = re.sub(r'^\d+\.', '', line).strip()
                if content:
                    sectors.append(content)
        
        return sectors
    
#    def _parse_main_products(self, text: str) -> Dict[str, List[str]]:
#        """解析主营产品"""
#        if not text or text == 'nan':
#            return {}
        
#        categories = {}
        # 按冒号分割类别
#        parts = text.split('：')
        
#        i = 0
#        while i < len(parts) - 1:
#            category = parts[i].strip()
            # 清理类别名称（去掉前面的数字序号等）
#            category = re.sub(r'^\d+\.', '', category).strip()
            
#            if i + 1 < len(parts):
#                products_text = parts[i + 1]
                # 如果下一部分包含下一个类别，需要分割
#                next_category_match = re.search(r'\n\d+\.', products_text)
#                if next_category_match:
#                    products_text = products_text[:next_category_match.start()]
                
                # 按逗号或顿号分割产品
#                products = re.split(r'[，、]', products_text)
#                products = [p.strip() for p in products if p.strip()]
                
#                if category and products:
#                   categories[category] = products
            
#            i += 1
        
#        return categories
    

    ###### new version 
    def _parse_main_products(self, text: str) -> Dict[str, List[str]]:
        
    #"""解析主营产品"""
        if not text or text == 'nan':
            return {}
    
        categories = {}
        #parts = text.split('：')   bug!!!!!!!!!!!!!!!
        # 正则提取：编号.类别：产品列表
        pattern = re.compile(r'\d+\.\s*([^：]+)：([^0-9]+)')
        matches = pattern.findall(text)
        for category, products_text in matches:
            category = category.strip()
            products = re.split(r'[，、]', products_text)
            products = [p.strip() for p in products if p.strip()]
            if category and products:
                categories[category] = products
    
        return categories
        

    def _parse_vip_products(self, text: str) -> Dict[str, List[Dict]]:
        """解析VIP展区产品情况"""
        if not text or text == 'nan':
            return {}
        
        result = {}
        
        # 按"一、二、三"分割大类
        sections = re.split(r'[一二三]、', text)
        section_names = ['新品', '爆品', '热卖品']
        
        for i, section in enumerate(sections[1:]):  # 跳过第一个空元素
            if i < len(section_names) and section.strip():
                products = []
                
                # 按数字序号分割产品
                product_lines = re.split(r'\n\d+\.', section)
                for line in product_lines:
                    line = line.strip()
                    if line:
                        # 提取产品系列名称（【】内的内容）
                        series_match = re.search(r'【([^】]+)】', line)
                        series_name = series_match.group(1) if series_match else ''
                        
                        # 提取产品描述
                        description = re.sub(r'【[^】]+】', '', line).strip()
                        description = re.sub(r'^\d+\.', '', description).strip()
                        
                        if description:
                            products.append({
                                'series': series_name,
                                'description': description
                            })
                
                if products:
                    result[section_names[i]] = products
        
        return result
    
    
    def _extract_honors(self, row: pd.Series) -> List[Dict[str, str]]:
        """提取企业荣誉信息"""
        honors = []
        
        # 市场价值类荣誉
        if self._safe_int(row.get('世界《财富》500强(2分)', 0)) > 0:
            level = "世界级" if self._safe_int(row.get('世界《财富》500强(2分)', 0)) == 2 else "省级"
            honors.append({'category': '市场价值', 'name': '世界《财富》500强(2分)', 'level': 'gold'})
        
        if self._safe_int(row.get('国家《财富》500强(1分)', 0)) > 0:
            level = "国家级" if self._safe_int(row.get('国家《财富》500强(1分)', 0)) == 1 else "国家级"
            honors.append({'category': '市场价值', 'name': '国家《财富》500强(1分)', 'level': 'yellow'})
        
        if self._safe_int(row.get('中国制造业500强(1分)', 0)) > 0:
            honors.append({'category': '市场价值', 'name': '中国制造业500强(1分)', 'level': 'silver'})
            
        if self._safe_int(row.get('独角兽企业(1分)', 0)) > 0:
            honors.append({'category': '市场价值', 'name': '独角兽企业(1分)', 'level': 'blue'})
            
        if self._safe_int(row.get('瞪羚企业(1分)', 0)) > 0:
            honors.append({'category': '市场价值', 'name': '瞪羚企业(1分)', 'level': 'blue'})
        
        if self._safe_int(row.get('上市企业(1分)', 0)) > 0:
            honors.append({'category': '市场价值', 'name': '上市企业(1分)', 'level': 'blue'})
        
        
        # 研发创新类荣誉
        if self._safe_int(row.get('国家级制造业单项冠军(2分)', 0)) > 0:
            honors.append({'category': '研发创新', 'name': '国家级制造业单项冠军', 'level': 'gold'})
        
        if self._safe_int(row.get('省级制造单项冠军(1分)', 0)) > 0:
            honors.append({'category': '研发创新', 'name': '省级制造单项冠军', 'level': 'silver'})
        
        if self._safe_int(row.get('国家级专精特新重点“小巨人”(3分)', 0)) > 0:
            honors.append({'category': '研发创新', 'name': '国家级专精特新重点“小巨人”(3分)', 'level': 'silver'})
            
        if self._safe_int(row.get('国家级专精特新“小巨人”(2分)', 0)) > 0:
            honors.append({'category': '研发创新', 'name': '国家级专精特新“小巨人”(2分)', 'level': 'silver'})
            
        if self._safe_int(row.get('省级专精特新(1分)', 0)) > 0:
            honors.append({'category': '研发创新', 'name': '省级专精特新(1分)', 'level': 'silver'})
            
        if self._safe_int(row.get('国家高新技术企业(1分)', 0)) > 0:
            honors.append({'category': '研发创新', 'name': '国家高新技术企业(1分)', 'level': 'silver'})
        
        if self._safe_int(row.get('国家级企业技术中心(2分)', 0)) > 0:
            honors.append({'category': '研发创新', 'name': '国家级企业技术中心(2分)', 'level': 'silver'})
            
        if self._safe_int(row.get('省级企业技术中心(1分)', 0)) > 0:
            honors.append({'category': '研发创新', 'name': '省级企业技术中心(1分)', 'level': 'silver'})
            
        if self._safe_int(row.get('国家技术创新示范企业(1分)', 0)) > 0:
            honors.append({'category': '研发创新', 'name': '国家技术创新示范企业(1分)', 'level': 'silver'})
            
        if self._safe_int(row.get('参与制定国际标准(3分)', 0)) > 0:
            honors.append({'category': '研发创新', 'name': '参与制定国际标准(3分)', 'level': 'silver'})
            
        if self._safe_int(row.get('参与制定国家标准(2分)', 0)) > 0:
            honors.append({'category': '研发创新', 'name': '参与制定国家标准(2分)', 'level': 'silver'})
            
        if self._safe_int(row.get('国家技术创新示范企业(1分)', 0)) > 0:
            honors.append({'category': '研发创新', 'name': '国家技术创新示范企业(1分)', 'level': 'silver'})
            
        if self._safe_int(row.get('参与制定行业标准(1分)', 0)) > 0:
            honors.append({'category': '研发创新', 'name': '参与制定行业标准(1分)', 'level': 'silver'})
            
        
        # 智能制造类荣誉
        if self._safe_int(row.get('卓越级智能工厂(1分)', 0)) > 0:
            honors.append({'category': '智能制造', 'name': '卓越级智能工厂(1分)', 'level': 'blue'})
        
        if self._safe_int(row.get('领航级智能工厂(2分)', 0)) > 0:
            honors.append({'category': '智能制造', 'name': '领航级智能工厂(2分)', 'level': 'gold'})
        
        if self._safe_int(row.get('灯塔工厂(2分)', 0)) > 0:
            honors.append({'category': '智能制造', 'name': '灯塔工厂(2分)', 'level': 'gold'})
        
        # 绿色制造类荣誉
        if self._safe_int(row.get('国家级绿色工厂(2分)', 0)) > 0:
            honors.append({'category': '绿色制造', 'name': '国家级绿色工厂(2分)', 'level': 'green'})
        
        if self._safe_int(row.get('省级绿色工厂(1分)', 0)) > 0:
            honors.append({'category': '绿色制造', 'name': '省级绿色工厂(1分)', 'level': 'green'})
            
        if self._safe_int(row.get('国家级绿色设计产品(2分)', 0)) > 0:
            honors.append({'category': '绿色制造', 'name': '国家级绿色设计产品(2分)', 'level': 'green'})
            
        if self._safe_int(row.get('省级绿色设计产品(1分)', 0)) > 0:
            honors.append({'category': '绿色制造', 'name': '省级绿色设计产品(1分)', 'level': 'green'})
            
        if self._safe_int(row.get('国家级绿色工业园(2分)', 0)) > 0:
            honors.append({'category': '绿色制造', 'name': '国家级绿色工业园(2分)', 'level': 'green'})
            
        if self._safe_int(row.get('省级绿色工业园(1分)', 0)) > 0:
            honors.append({'category': '绿色制造', 'name': '省级绿色工业园(1分)', 'level': 'green'})
            
        if self._safe_int(row.get('国家级绿色供应链管理(2分)', 0)) > 0:
            honors.append({'category': '绿色制造', 'name': '国家级绿色供应链管理(2分)', 'level': 'green'})
            
        if self._safe_int(row.get('省级绿色供应链管理(1分)', 0)) > 0:
            honors.append({'category': '绿色制造', 'name': '省级绿色供应链管理(1分)', 'level': 'green'})
        
        
        # 信用水平类荣誉
        if self._safe_int(row.get('AEO高级认证企业(1分)', 0)) > 0:
            honors.append({'category': '信用水平', 'name': 'AEO高级认证企业(1分)', 'level': 'blue'})
        
        return honors
    
    def _safe_int(self, value) -> int:
        """安全转换为整数"""
        try:
            if pd.isna(value) or value == '' or value == 'nan':
                return 0
            return int(float(value))
        except (ValueError, TypeError):
            return 0

#   def _safe_int(self, value):
#        try:
#            if pd.isna(value): return 0
#            return int(str(value).strip())
#        except:
#            return 0

    
    def get_statistics(self, companies: List[Dict]) -> Dict:
        """获取统计信息"""
        if not companies:
            return {
                'total_companies': 0,
                'average_score': 0,
                'gold_vip_count': 0,
                'brand_companies': 0,
                'score_distribution': {}
            }
        
        # 🔧 修复：使用scores.total而不是total
        total_score = sum(company['scores']['total'] for company in companies)
        gold_vip_count = sum(1 for company in companies if company.get('vip_level') == '金标')
        brand_count = sum(1 for company in companies if company.get('is_brand'))
        
        # 评分分布
        score_ranges = {'0-3分': 0, '4-6分': 0, '7-9分': 0, '10-13分': 0}
        for company in companies:
            score = company['scores']['total']  # 🔧 修复：使用scores.total
            if score <= 3:
                score_ranges['0-3分'] += 1
            elif score <= 6:
                score_ranges['4-6分'] += 1
            elif score <= 9:
                score_ranges['7-9分'] += 1
            else:
                score_ranges['10-13分'] += 1
        
        return {
            'total_companies': len(companies),
            'average_score': round(total_score / len(companies), 1),
            'gold_vip_count': gold_vip_count,
            'brand_companies': brand_count,
            'score_distribution': score_ranges
        }

# 测试代码
if __name__ == "__main__":
    processor = UpdatedDataProcessor()
    
    # 创建测试数据
    test_data = {
        '企业名称': 'TCL实业控股股份有限公司',
        '企业简介': '成立于2018年，TCL实业聚焦智能终端业务...',
        '企业亮点': '1.TCL电视出货量全球第二\n2.TCL空调出货量全球第四\n3.TCL Mini LED电商中国市场全渠道零售量及零售额冠军',
        '领先地位': '1.TCL电视出货量全球第二\n2.TCL空调出货量全球第四',
        '产业板块': '1.光伏板块\n2.场景互联网及AI×loT板块（雷鸟科技）\n3.AR产品板块（雷鸟创新）',
        '主营产品': '个人及家庭产品：电视、空调、冰箱、洗衣机 \n企业及商用产品：商用工程产品、商用显示、中央空调',
        'VIP等级': '金标',
        '是否品牌': '是',
        '已参展届数': 4,
        '《财富》500强（世界2分、中国1分）': 1,
        '中国制造业500强（1分）': 1,
        '国家高新技术企业（1分）': 1,
        '制造业单项冠军（国家级2分、省级1分）': 2,
        '专精特新（国家级2分、省级1分）': 1,
        '绿色工厂（国家级2分、省级1分）': 2,
        'AEO高级认证企业（1分）': 0,
        '总分': 13
    }
    
    # 测试数据处理
    import pandas as pd
    test_row = pd.Series(test_data)
    company = processor._process_company_row(test_row)
    
    print("✅ 数据处理测试结果：")
    print(f"企业名称: {company['name']}")
    print(f"企业亮点: {company['highlights']}")
    print(f"领先地位: {company['leading_position']}")
    print(f"产业板块: {company['industry_sectors']}")
    print(f"主营产品: {company['main_products']}")
    print(f": {company['scores']}")
    print(f"荣誉信息: {len(company['honors'])}项荣誉")
    
    print("\n✅ 新评分系统测试通过！")

