#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VIP企业信息数据看板系统 - 最终更新版本
支持新的13分评分系统和优化的文字内容结构化展现
"""

from flask import Flask, render_template_string, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import re
import json
import io
import base64
import warnings
import os
warnings.filterwarnings('ignore')


# 导入数据处理器
import sys
sys.path.append('/home/ubuntu')
from updated_data_processor_new import UpdatedDataProcessor
#from honor_statistics_generator import HonorStatisticsGenerator


# 图表生成相关导入
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import seaborn as sns
    import numpy as np
    CHARTS_AVAILABLE = True
    
    # 配置中文字体
    chinese_fonts = ['Hiragino Sans GB', 'STHeiti', 'Hei', 'Microsoft YaHei', 'Arial Unicode MS']
    font_found = False
    
    for font_name in chinese_fonts:
        try:
            plt.rcParams['font.sans-serif'] = [font_name]
            plt.rcParams['axes.unicode_minus'] = False
            # 测试字体
            fig, ax = plt.subplots(figsize=(1, 1))
            ax.text(0.5, 0.5, '测试', fontsize=12)
            plt.close(fig)
            font_found = True
            print(f"✅ 成功配置中文字体: {font_name}")
            break
        except:
            continue
    
    if not font_found:
        print("⚠️ 未找到合适的中文字体，将使用英文显示")
        USE_CHINESE = False
    else:
        USE_CHINESE = True

except ImportError:
    CHARTS_AVAILABLE = False
    USE_CHINESE = False
    print("⚠️ 图表库未安装，图表功能将不可用")

app = Flask(__name__)
CORS(app)


# 全局变量存储企业数据
companies_data = []
data_processor = UpdatedDataProcessor()

# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#3b82f6">
    <title>VIP企业信息数据看板</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }

        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 1rem 2rem;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 1000;
        }

        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            font-size: 1.8rem;
            font-weight: bold;
            background: linear-gradient(45deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .header-actions {
            display: flex;
            gap: 1rem;
        }

        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn-primary {
            background: linear-gradient(45deg, #3b82f6, #1d4ed8);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(59, 130, 246, 0.3);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.9);
            color: #374151;
            border: 1px solid #d1d5db;
        }

        .btn-secondary:hover {
            background: white;
            transform: translateY(-1px);
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }

        .upload-area {
            background: rgba(255, 255, 255, 0.95);
            border: 2px dashed #3b82f6;
            border-radius: 12px;
            padding: 3rem;
            text-align: center;
            margin-bottom: 2rem;
            transition: all 0.3s ease;
        }

        .upload-area:hover {
            border-color: #1d4ed8;
            background: white;
        }

        .upload-area.dragover {
            border-color: #10b981;
            background: rgba(16, 185, 129, 0.05);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            border-left: 5px solid #3B82F6;
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-card.gold {
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border-left-color: #F59E0B;
        }
        
        .stat-card.green {
            background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
            border-left-color: #10B981;
        }
        
        .stat-card.purple {
            background: linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%);
            border-left-color: #8B5CF6;
        }

        .stat-icon {
            font-size: 2rem;
            margin-bottom: 10px;
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #3b82f6;
            margin-bottom: 0.5rem;
        }

        .stat-label {
            color: #6b7280;
            font-size: 0.9rem;
        }
        .stat-number {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        .stat-card .stat-number {
            color: #1E3A8A;
        }
        
        .stat-card.gold .stat-number {
            color: #D97706;
        }
        
        .stat-card.green .stat-number {
            color: #059669;
        }
        
        .stat-card.purple .stat-number {
            color: #7C3AED;
        }
        
        .stat-label {
            color: #6b7280;
            font-size: 1rem;
            font-weight: 500;
        }

        .detail-header {
            background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
            color: white;
            padding: 30px;
            position: relative;
        }

        .detail-company-name {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .detail-subtitle {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .detail-vip-badge {
            position: absolute;
            top: 30px;
            right: 30px;
            padding: 10px 20px;
            border-radius: 25px;
            font-size: 1rem;
            font-weight: 700;
            background: rgba(245, 158, 11, 0.9);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .companies-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .company-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }

        .company-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        }

        .company-card.selected {
            border: 2px solid #3b82f6;
            box-shadow: 0 8px 30px rgba(59, 130, 246, 0.3);
        }

        .vip-badge {
            position: absolute;
            top: 1rem;
            right: 1rem;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: bold;
        }

        .vip-gold {
            background: linear-gradient(45deg, #fbbf24, #f59e0b);
            color: white;
        }

        .vip-silver {
            background: linear-gradient(45deg, #e5e7eb, #9ca3af);
            color: #374151;
        }

        .company-name {
            font-size: 1.2rem;
            font-weight: bold;
            color: #1f2937;
        }

        .company-info {
            flex: 1;
            display: flex;
            justify-content: space-between;
            flex-direction: column;
            gap: 0.5rem;
        }

        .score-info {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .score-circle {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: white;
            background: linear-gradient(45deg, #3b82f6, #1d4ed8);
        }

        .progress-bar {
            flex: 1;
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin-left: 2rem;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(45deg, #10b981, #059669);
            border-radius: 4px;
            transition: width 0.5s ease;
        }

        .company-details {
            display: flex;
            gap: 1rem;
            font-size: 0.9rem;
            color: #6b7280;
            background: white;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            margin-top: 2rem;
        }

        .tabs {
            display: flex;
            border-bottom: 2px solid #e5e7eb;
            margin-bottom: 2rem;
        }

        .tab {
            padding: 1rem 2rem;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.3s ease;
            font-weight: 600;
        }

        .tab.active {
            color: #3b82f6;
            border-bottom-color: #3b82f6;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .info-card {
            background: #f8fafc;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
        }

        .info-title {
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .info-content {
            color: #6b7280;
            line-height: 1.6;
        }

        .highlights-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .highlight-card {
            background: linear-gradient(45deg, #f0f9ff, #e0f2fe);
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #0ea5e9;
        }

        .highlight-card .icon {
            font-size: 1.2rem;
            margin-bottom: 0.5rem;
        }

        .tags-container {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 1rem;
        }

        .tag {
            padding: 0.25rem 0.75rem;
            background: linear-gradient(45deg, #3b82f6, #1d4ed8);
            color: white;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }

        .products-section {
            margin-bottom: 2rem;
        }

        .products-category {
            background: #f8fafc;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }

        .category-title {
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .products-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        .product-tag {
            padding: 0.25rem 0.75rem;
            background: #e0f2fe;
            color: #0369a1;
            border-radius: 15px;
            font-size: 0.8rem;
        }

        .vip-products-section {
            margin-bottom: 2rem;
        }

        .vip-category {
            background: #f8fafc;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            border-left: 4px solid #10b981;
        }

        .vip-category.new-products {
            border-left-color: #3b82f6;
        }

        .vip-category.hot-products {
            border-left-color: #f59e0b;
        }

        .vip-category.bestsellers {
            border-left-color: #ef4444;
        }

        .exhibition-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .exhibition-card {
            background: linear-gradient(45deg, #f0f9ff, #e0f2fe);
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .exhibition-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(45deg, #3b82f6, #1d4ed8);
        }

        .exhibition-value {
            font-size: 2rem;
            font-weight: bold;
            color: #3b82f6;
            margin-bottom: 0.5rem;
        }

        .exhibition-label {
            color: #6b7280;
            font-size: 0.9rem;
        }

        .honors-section {
            margin-bottom: 2rem;
        }

        .honors-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }

        .honor-badge {
            padding: 0.75rem 1rem;
            border-radius: 8px;
            text-align: center;
            font-weight: 600;
            font-size: 0.9rem;
        }

        .honor-gold {
            background: linear-gradient(45deg, #fbbf24, #f59e0b);
            color: white;
            padding: 1rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        }

        .honor-silver {
            background: linear-gradient(45deg, #e5e7eb, #9ca3af);
            color: #374151;
            padding: 1rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        }
        
        .honor-blue {
            background: linear-gradient(45deg, #60a5fa, #2563eb);
            color: white;
            padding: 1rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        }

        .honor-green {
            background: linear-gradient(45deg, #10b981, #059669);
            color: white;
            padding: 1rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        }
        
        .honor-yellow {
            background: linear-gradient(45deg, #fde047, #facc15);
            color: white;
            padding: 1rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        }

        .charts-section {
            margin-bottom: 2rem;
        }

        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
        }

        .chart-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        

        .chart-title {
            font-weight: bold;
            margin-bottom: 1rem;
            color: #1f2937;
        }

        .chart-placeholder {
            text-align: center;
            padding: 2rem;
            color: #6b7280;
            background: #f9fafb;
            border-radius: 8px;
            border: 2px dashed #d1d5db;
        }

        .chart-placeholder .icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }

        .score-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }

        .score-table th,
        .score-table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }

        .score-table th {
            background: #f8fafc;
            font-weight: 600;
            color: #374151;
        }

        .score-excellent {
            color: #059669;
            font-weight: bold;
        }

        .score-good {
            color: #0369a1;
            font-weight: bold;
        }

        .score-average {
            color: #d97706;
            font-weight: bold;
        }

        .score-poor {
            color: #dc2626;
            font-weight: bold;
        }

        .loading {
            text-align: center;
            padding: 2rem;
            color: #6b7280;
        }

        .error {
            background: #fef2f2;
            color: #dc2626;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }

        .success {
            background: #f0fdf4;
            color: #059669;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            .header-content {
                flex-direction: column;
                gap: 1rem;
            }

            .companies-grid {
                grid-template-columns: 1fr;
            }

            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }    
        /* 排行榜样式 */
        .ranking-section {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border-radius: 20px;
            padding: 2.5rem;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
            margin-bottom: 2rem;
            border: 1px solid rgba(59, 130, 246, 0.1);
            position: relative;
            overflow: hidden;
        }

        .ranking-section::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6, #06b6d4);
        }

        .ranking-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 3px solid #f3f4f6;
            position: relative;
        }

        .ranking-header::after {
            content: '';
            position: absolute;
            bottom: -3px;
            left: 0;
            width: 100px;
            height: 3px;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6);
            border-radius: 2px;
        }

        .ranking-controls {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            align-items: flex-end;
        }

        .search-box {
            position: relative;
            display: flex;
            align-items: center;
        }

        .search-box input {
            padding: 0.75rem 3rem 0.75rem 1.5rem;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            font-size: 1rem;
            width: 280px;
            transition: all 0.3s ease;
            background: white;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }

        .search-box input:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15), 0 4px 15px rgba(59, 130, 246, 0.1);
            transform: translateY(-1px);
        }

        .search-box input::placeholder {
            color: #9ca3af;
            font-style: italic;
        }

        .clear-btn {
            position: absolute;
            right: 0.5rem;
            background: none;
            border: none;
            color: #6b7280;
            cursor: pointer;
            padding: 0.25rem;
            border-radius: 4px;
            transition: all 0.3s ease;
        }

        .clear-btn:hover {
            background: #f3f4f6;
            color: #374151;
        }
        
        .ranking-title {
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #1e293b, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .ranking-filters {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .filter-btn {
            padding: 0.75rem 1.5rem;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            background: white;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9rem;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            position: relative;
            overflow: hidden;
        }

        .filter-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            transition: left 0.5s ease;
        }

        .filter-btn:hover::before {
            left: 100%;
        }

        .filter-btn.active {
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            color: white;
            border-color: #3b82f6;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
            transform: translateY(-2px);
        }

        .filter-btn:hover {
            border-color: #3b82f6;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.2);
        }

            .ranking-list {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .ranking-item {
            display: flex;
            align-items: center;
            padding: 2rem;
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border-radius: 16px;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
            border: 2px solid transparent;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        }

        .ranking-item::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6);
            transform: scaleX(0);
            transition: transform 0.3s ease;
        }

        .ranking-item:hover::before {
            transform: scaleX(1);
        }

        .ranking-item:hover {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-color: #3b82f6;
            transform: translateY(-4px) scale(1.02);
            box-shadow: 0 12px 40px rgba(59, 130, 246, 0.2);
        }

        .ranking-item.highlighted {
            background: #fef3c7;
            border-color: #f59e0b;
            animation: highlight 2s ease-in-out;
        }

        @keyframes highlight {
            0%, 100% { background: #fef3c7; }
            50% { background: #fde68a; }
        }

        .rank-number {
            width: 70px;
            height: 70px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.8rem;
            font-weight: 800;
            margin-right: 2rem;
            color: white;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            position: relative;
            overflow: hidden;
        }

        .rank-number::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, transparent 30%, rgba(255, 255, 255, 0.2) 50%, transparent 70%);
            transform: translateX(-100%);
            transition: transform 0.6s ease;
        }

        .rank-number:hover::before {
            transform: translateX(100%);
        }

        .rank-1 { 
            background: linear-gradient(135deg, #ffd700, #fbbf24, #f59e0b); 
            color: #92400e; 
            box-shadow: 0 8px 25px rgba(255, 215, 0, 0.4);
            animation: goldGlow 2s ease-in-out infinite alternate;
        }
        .rank-2 { 
            background: linear-gradient(135deg, #c0c0c0, #e5e7eb, #9ca3af); 
            color: #374151; 
            box-shadow: 0 8px 25px rgba(192, 192, 192, 0.4);
        }
        .rank-3 { 
            background: linear-gradient(135deg, #cd7f32, #d97706, #b45309); 
            color: white; 
            box-shadow: 0 8px 25px rgba(205, 127, 50, 0.4);
        }
        .rank-other { 
            background: linear-gradient(135deg, #6b7280, #9ca3af, #6b7280); 
            color: white;
            box-shadow: 0 4px 15px rgba(107, 114, 128, 0.3);
        }

        @keyframes goldGlow {
            0% { box-shadow: 0 8px 25px rgba(255, 215, 0, 0.4); }
            100% { box-shadow: 0 12px 35px rgba(255, 215, 0, 0.6); }
        }

        .company-info {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .company-name {
            font-size: 1.2rem;
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 0.5rem;
        }

        .company-details {
            display: flex;
            gap: 1rem;
            font-size: 0.9rem;
            color: #6b7280;
            flex-wrap: wrap;
        }

        .company-detail-item {
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }

        .score-section {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
            margin-left: 1rem;
            min-width: 120px;
        }

        .total-score {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #1e293b, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            animation: scorePulse 2s ease-in-out infinite;
        }

        @keyframes scorePulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        .score-label {
            font-size: 0.8rem;
            color: #6b7280;
            text-align: center;
            font-weight: 500;
        }

        .score-breakdown {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }

        .score-item {
            background: white;
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
            font-size: 0.8rem;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .ranking-vip-badge {
            padding: 0.5rem 1rem;
            border-radius: 25px;
            font-size: 0.9rem;
            font-weight: 700;
            color: white;
            margin-left: 1.5rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }

        .vip-badge::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            transition: left 0.5s ease;
        }

        .vip-badge:hover::before {
            left: 100%;
        }

        .vip-badge:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
        }

        .vip-badge.金标 {
            color: white;
            background: linear-gradient(45deg, #f59e0b, #d97706);
        }

        .vip-badge.银标 {
            color: white;
            background: linear-gradient(45deg, #6b7280, #9ca3af);
        }

        .vip-badge.铜标 {
            color: white;
            background: linear-gradient(45deg, #92400e, #b45309);
        }

        /* 统计信息 */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }

        .stat-icon {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #1f2937;
        }

        .stat-label {
            color: #6b7280;
            font-size: 0.9rem;
        }

        /* 响应式设计 */
        @media (max-width: 768px) {
            .ranking-header {
                flex-direction: column;
                gap: 1rem;
                align-items: flex-start;
            }

            .ranking-filters {
                flex-wrap: wrap;
            }

            .ranking-item {
                flex-direction: column;
                text-align: center;
                gap: 1rem;
            }

            .rank-number {
                margin-right: 0;
            }

            .score-section {
                margin-left: 0;
            }

            .company-details {
                justify-content: center;
                flex-wrap: wrap;
            }
        }

        /* 加载动画 */
        .loading {
            display: none;
            text-align: center;
            padding: 2rem;
            color: #6b7280;
        }

        .loading.show {
            display: block;
        }

        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #f3f4f6;
            border-top: 4px solid #3b82f6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* 空状态 */
        .empty-state {
            text-align: center;
            padding: 3rem;
            color: #6b7280;
            display: none;
        }

        .empty-state.show {
            display: block;
        }

        .empty-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }

        /* 排行榜统计信息 */
        .ranking-stats {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
            border-left: 5px solid #3b82f6;
            box-shadow: 0 8px 25px rgba(59, 130, 246, 0.1);
            position: relative;
            overflow: hidden;
        }

        .ranking-stats::before {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            width: 100px;
            height: 100px;
            background: radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%);
            border-radius: 50%;
            transform: translate(30px, -30px);
        }

        .stats-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1.5rem;
        }

        .stat-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        }

        .stat-item .stat-label {
            font-size: 0.9rem;
            color: #6b7280;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }

        .stat-item .stat-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #1f2937;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="logo">🏆 VIP企业信息数据看板</div>
            <div class="header-actions">
                <input type="file" id="fileInput" accept=".xlsx,.xls,.csv" style="display: none;">
                <button class="btn btn-secondary" onclick="document.getElementById('fileInput').click()">
                    📁 导入Excel
                </button>
                <button class="btn btn-primary" onclick="exportPDF()" id="exportBtn" style="display: none;">
                    📄 导出PDF报告
                </button>
            </div>
        </div>
    </div>

    <div class="container">
        <div id="uploadSection" class="upload-area">
            <div style="font-size: 3rem; margin-bottom: 1rem;">📊</div>
            <h2>VIP企业信息数据看板</h2>
            <p style="margin: 1rem 0; color: #6b7280;">支持新100分评分系统和优化的文字内容结构化展现</p>
            <div style="margin-top: 2rem;">
                <button class="btn btn-primary" onclick="document.getElementById('fileInput').click()">
                    选择Excel文件
                </button>
                <button class="btn btn-secondary" onclick="loadDemoData()" style="margin-left: 1rem;">
                    使用演示数据
                </button>
            </div>
            <p style="margin-top: 1rem; font-size: 0.9rem; color: #6b7280;">
                支持 .xlsx、.xls 格式文件，或拖拽文件到此区域
            </p>
        </div>

        <div id="dashboardSection" style="display: none;">
            <div class="stats-grid" id="statsGrid">
                <!-- 统计卡片将在这里动态生成 -->
            </div>

            <div class="companies-grid" id="companiesGrid">
                <!-- 企业卡片将在这里动态生成 -->
            </div>

            <div id="companyDetails" class="company-details">
                <!-- 企业详情将在这里显示 -->
            </div>
        </div>

        <div id="loadingSection" class="loading" style="display: none;">
            <div style="font-size: 2rem; margin-bottom: 1rem;">⏳</div>
            <p>正在处理数据，请稍候...</p>
        </div>
    </div>

    <script>
        let companiesData = [];
        let selectedCompany = null;

        // 文件上传处理
        document.getElementById('fileInput').addEventListener('change', handleFileUpload);

        // 拖拽上传
        const uploadArea = document.querySelector('.upload-area');
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileUpload({ target: { files: files } });
            }
        });

        function handleFileUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            showLoading();

            fetch('/api/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.success) {
                    companiesData = data.companies;
                    showDashboard();
                    showSuccess('数据上传成功！');
                } else {
                    showError(data.error || '文件上传失败');
                }
            })
            .catch(error => {
                hideLoading();
                showError('上传过程中发生错误：' + error.message);
            });
        }

        function loadDemoData() {
            showLoading();
            
            fetch('/api/demo-data')
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.success) {
                    companiesData = data.companies;
                    showDashboard();
                    showSuccess('演示数据加载成功！');
                } else {
                    showError(data.error || '演示数据加载失败');
                }
            })
            .catch(error => {
                hideLoading();
                showError('加载演示数据时发生错误：' + error.message);
            });
        }

        function showDashboard() {
            document.getElementById('uploadSection').style.display = 'none';
            document.getElementById('dashboardSection').style.display = 'block';
            document.getElementById('exportBtn').style.display = 'inline-flex';
            
            renderStats();
            renderCompanies();
        }

        function renderStats() {
            const stats = calculateStats();
            const statsGrid = document.getElementById('statsGrid');
            
            statsGrid.innerHTML = `
                <div class="stat-card">
                    <div class="stat-icon">🏢</div>
                    <div class="stat-number">${stats.totalCompanies}</div>
                    <div class="stat-label">企业总数</div>
                </div>
                <div class="stat-card green">
                    <div class="stat-icon">📊</div>
                    <div class="stat-number">${stats.averageScore}</div>
                    <div class="stat-label">平均评分</div>
                </div>
                <div class="stat-card gold">
                    <div class="stat-icon">🏆</div>
                    <div class="stat-number">${stats.goldVipCount}</div>
                    <div class="stat-label">金标企业</div>
                </div>
                <div class="stat-card purple">
                    <div class="stat-icon">⭐</div>
                    <div class="stat-number">${stats.brandCompanies}</div>
                    <div class="stat-label">品牌企业</div>
                </div>
            `;
        }

        function calculateStats() {
            const totalCompanies = companiesData.length;
            const totalScore = companiesData.reduce((sum, company) => sum + company.scores.total, 0);
            const averageScore = totalCompanies > 0 ? (totalScore / totalCompanies).toFixed(1) : 0;
            const goldVipCount = companiesData.filter(company => company.vip_level === '金标').length;
            const brandCompanies = companiesData.filter(company => company.is_brand).length;
            
            return {
                totalCompanies,
                averageScore,
                goldVipCount,
                brandCompanies
            };
        }

        function renderCompanies() {
            const companiesGrid = document.getElementById('companiesGrid');
            
            companiesGrid.innerHTML = companiesData.map(company => `
                <div class="company-card" onclick="selectCompany('${company.name}')">
                    <div class="vip-badge ${company.vip_level === '金标' ? 'vip-gold' : 'vip-silver'}">
                        ${company.vip_level}
                    </div>
                    <div class="company-name">${company.name}</div>
                    <div class="company-info">
                        <div class="score-info">
                            <div class="score-circle">${company.scores.total}</div>
                            <div style="margin-left: 0.5rem;">
                                <div style="font-weight: bold;">${company.scores.total}/100分</div>
                                <div style="font-size: 0.8rem; color: #6b7280;">📊评分完成度 ${company.scores.percentage}%</div>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${company.scores.percentage}%"></div>
                            </div>
                        </div>
                    </div>
                    <div style="margin-top: 1rem; display: flex; justify-content: space-between; font-size: 0.9rem; color: #6b7280;">
                        <span>🏛️参展${company.exhibition_count}届</span>
                        <span>${company.is_brand ? '🎖️品牌企业' : '🔖 非品牌企业'}</span>
                        <span>📍${company.exhibition_areas}个展区</span>
                        <span>👨‍💼${company.trading_group}交易团</span>
                    </div>
                    <button class="btn btn-primary" style="width: 100%; margin-top: 1rem;" onclick="event.stopPropagation(); selectCompany('${company.name}')">
                        查看详情
                    </button>
                </div>
            `).join('');
        }

        function selectCompany(companyName) {
            selectedCompany = companiesData.find(company => company.name === companyName);
            if (!selectedCompany) return;

            // 更新选中状态
            document.querySelectorAll('.company-card').forEach(card => {
                card.classList.remove('selected');
            });
            event.currentTarget.classList.add('selected');

            // 显示详情
            showCompanyDetails();
            
            // 滚动到详情区域
            document.getElementById('companyDetails').scrollIntoView({ 
                behavior: 'smooth',
                block: 'start'
            });
        }

        function showCompanyDetails() {
            const detailsContainer = document.getElementById('companyDetails');
            detailsContainer.style.display = 'block';
            
            detailsContainer.innerHTML = `
                <div class="detail-header">
                    <div class="detail-company-name" id="detailCompanyName">${selectedCompany.name}</div>
                    <div class="detail-subtitle" id="detailSubtitle">已参展${selectedCompany.exhibition_count}届</div>
                    <div class="detail-vip-badge" id="detailVipBadge">
                        🏆 <span>${selectedCompany.vip_level || ''}</span>
                    </div>
                </div>
                
                <div class="tabs">
                    <div class="tab active" onclick="switchTab('overview')">🏢 企业概览</div>
                    <div class="tab" onclick="switchTab('exhibition')">🗂️ 参展信息</div>
                    <div class="tab" onclick="switchTab('analysis')">📈 评分分析</div>
                    <div class="tab" onclick="switchTab('ranking')">📊 评分排行榜</div>
                </div>

                <div id="overview" class="tab-content active">
                    ${renderOverviewTab()}
                </div>

                <div id="exhibition" class="tab-content">
                    ${renderExhibitionTab()}
                </div>

                <div id="analysis" class="tab-content">
                    ${renderAnalysisTab()}
                </div>
                
                <div id="ranking" class="tab-content">
                    ${renderRankingTab()}
                <div>
            `;
        }

        function renderOverviewTab() {
            return `
                <div class="info-grid">
                    <div class="info-card">
                        <div class="info-title">📋 企业简介</div>
                        <div class="info-content">${selectedCompany.introduction || '暂无信息'}</div>
                    </div>
                    <div class="info-card">
                        <div class="info-title">🏙️ 所在城市</div>
                        <div class="info-content">${selectedCompany.city || '暂无信息'}</div>
                    </div>
                </div>

                <div class="highlights-grid">
                    <h3 style="grid-column: 1 / -1; margin-bottom: 1rem; color: #1f2937;">✨ 企业亮点</h3>
                    ${selectedCompany.highlights.map(highlight => `
                        <div class="highlight-card">
                            <div class="icon">⭐</div>
                            <div>${highlight}</div>
                        </div>
                    `).join('')}
                </div>

                <div class="highlights-grid">
                    <h3 style="grid-column: 1 / -1; margin-bottom: 1rem; color: #1f2937;">🏆 领先地位</h3>
                    ${selectedCompany.leading_position.map(position => `
                        <div class="highlight-card">
                            <div class="icon">🥇</div>
                            <div>${position}</div>
                        </div>
                    `).join('')}
                </div>

                <div class="products-section">
                    <h3 style="margin-bottom: 1rem; color: #1f2937;">🏭 产业板块</h3>
                    <div class="tags-container">
                        ${selectedCompany.industry_sectors.map(sector => `
                            <div class="tag">${sector}</div>
                        `).join('')}
                    </div>
                </div>

                <div class="products-section">
                    <h3 style="margin-bottom: 1rem; color: #1f2937;">📦 主营产品</h3>
                    ${Object.entries(selectedCompany.main_products).map(([category, products]) => `
                        <div class="products-category">
                            <div class="category-title">
                                <span>📋</span>
                                ${category}
                            </div>
                            <div class="products-list">
                                ${products.map(product => `
                                    <div class="product-tag">${product}</div>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>

            `;
        }

        function renderExhibitionTab() {
            return `
                <div class="exhibition-stats">
                    <div class="exhibition-card">
                        <div class="exhibition-value">${selectedCompany.exhibition_count}</div>
                        <div class="exhibition-label">已参展届数</div>
                    </div>
                    <div class="exhibition-card">
                        <div class="exhibition-value">${selectedCompany.vip_level}</div>
                        <div class="exhibition-label">VIP等级</div>
                    </div>
                    <div class="exhibition-card">
                        <div class="exhibition-value">${selectedCompany.is_brand ? '是' : '否'}</div>
                        <div class="exhibition-label">品牌企业</div>
                    </div>
                </div>

                <div class="info-grid">
                    <div class="info-card">
                        <div class="info-title">🎞️ 参展历程</div>
                        <div class="info-content">
                            该企业已连续参展${selectedCompany.exhibition_count}届广交会，
                            ${selectedCompany.vip_level === '金标' ? '是金标VIP企业，' : ''}
                            ${selectedCompany.is_brand ? '是品牌企业' : ''}
                        </div>
                    </div>
                    <div class="info-card">
                        <div class="info-title">🏷️ 企业标识</div>
                        <div class="info-content">
                            <div class="tags-container">
                                <div class="tag">${selectedCompany.vip_level}</div>
                                ${selectedCompany.is_brand ? '<div class="tag">品牌企业</div>' : '<div class="tag">一般企业</div>'}
                                <div class="tag">参展${selectedCompany.exhibition_count}届</div>
                                <div class="tag">VIP展区:${selectedCompany.exhibition_areas_vip}</div>
                                <div class="tag">准入资格:${selectedCompany.eligibility_criteria}</div>
                                <div class="tag">${selectedCompany.purchase_package_status}套餐</div>
                            </div>
                        </div>
                    </div>
                </div>

                ${Object.keys(selectedCompany.vip_products).length > 0 ? `
                    <div class="vip-products-section">
                        <h3 style="margin-bottom: 1rem; color: #1f2937;">🌟 VIP展区产品情况</h3>
                        ${Object.entries(selectedCompany.vip_products).map(([category, products]) => `
                            <div class="vip-category ${category === '新品' ? 'new-products' : category === '爆品' ? 'hot-products' : 'bestsellers'}">
                                <div class="category-title">
                                    <span>${category === '新品' ? '🆕' : category === '爆品' ? '💥' : '🔥'}</span>
                                    ${category}
                                </div>
                                ${products.map(product => `
                                    <div style="margin-bottom: 0.5rem;">
                                        ${product.series ? `<strong>【${product.series}】</strong>` : ''}
                                        ${product.description}
                                    </div>
                                `).join('')}
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            `;
        }

        function renderAnalysisTab() {
            return `
                <div class="honors-section">
                    <h3 style="margin-bottom: 1rem; color: #1f2937;">🏆 企业荣誉</h3>
                    <div class="honors-grid">
                        ${selectedCompany.honors.map(honor => `
                            <div class="honor-badge honor-${honor.level}">
                                ${honor.name}
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div class="charts-section">
                    <h3 style="margin-bottom: 1rem; color: #1f2937;">📊 评分可视化</h3>
                    <div class="charts-grid">
                        <div class="chart-card">
                            <div id="radarChart">
                                <div class="chart-placeholder">
                                    <div class="icon">📊</div>
                                    <div>五大类别评分的可视化对比</div>
                                    <div style="font-size: 0.9rem; margin-top: 0.5rem;">清晰展示企业在各个维度的表现</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="info-card">
                    <div class="info-title">📋 评分详情</div>
                    <table class="score-table">
                        <thead>
                            <tr style="background: #e5e7eb;">
                                <th style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">评分类别</th>
                                <th style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">当前得分</th>
                                <th style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">满分</th>
                                <th style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">完成度</th>
                                <th style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">评价</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td style="padding: 0.75rem; border: 1px solid #d1d5db;">市场价值</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">${Math.round(selectedCompany.scores.market_value * 2 * 10/6)}</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">20</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">${Math.round(selectedCompany.scores.market_value / 6 * 100)}%</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;" class="${getScoreClass(selectedCompany.scores.market_value / 6)}">${getScoreLabel(selectedCompany.scores.market_value / 6)}</td>
                            </tr>
                            <tr>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">研发创新</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">${selectedCompany.scores.rd_innovation}</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">20</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">${Math.round(selectedCompany.scores.rd_innovation / 12 * 100)}%</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;" class="${getScoreClass(selectedCompany.scores.rd_innovation / 12)}">${getScoreLabel(selectedCompany.scores.rd_innovation / 12)}</td>
                            </tr>
                            <tr>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">智能制造</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">${Math.round(selectedCompany.scores.smart_manufacturing * 2 * 10/6)}</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">20</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">${Math.round(selectedCompany.scores.smart_manufacturing / 6 * 100)}%</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;" class="${getScoreClass(selectedCompany.scores.smart_manufacturing / 6)}">${getScoreLabel(selectedCompany.scores.smart_manufacturing / 6)}</td>
                            </tr>
                            <tr>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">绿色制造</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">${Math.round(selectedCompany.scores.green_manufacturing * 1.5 * 10/6)}</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">20</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">${Math.round(selectedCompany.scores.green_manufacturing / 8 * 100)}%</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;" class="${getScoreClass(selectedCompany.scores.green_manufacturing / 8)}">${getScoreLabel(selectedCompany.scores.green_manufacturing / 8)}</td>
                            </tr>
                            <tr>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">信用水平</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">${Math.round(selectedCompany.scores.credit_level * 1.5 * 10/6)}</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">20</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">${Math.round(selectedCompany.scores.credit_level / 4 * 100)}%</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;" class="${getScoreClass(selectedCompany.scores.credit_level / 4)}">${getScoreLabel(selectedCompany.scores.credit_level / 4)}</td>
                            </tr>
                            <tr style="background: #f8fafc; font-weight: bold;">
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">总计</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">${selectedCompany.scores.total}</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">100</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;">${selectedCompany.scores.percentage}%</td>
                                <td style="padding: 0.75rem; text-align: center; border: 1px solid #d1d5db;" class="${getScoreClass(selectedCompany.scores.total / 100)}">${getScoreLabel(selectedCompany.scores.total / 100)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            `;
        }

        function getScoreClass(ratio) {
            if (ratio >= 0.8) return 'score-excellent';
            if (ratio >= 0.6) return 'score-good';
            if (ratio >= 0.4) return 'score-average';
            return 'score-poor';
        }

        function getScoreLabel(ratio) {
            if (ratio >= 0.8) return '优秀';
            if (ratio >= 0.6) return '良好';
            if (ratio >= 0.4) return '一般';
            return '待提升';
        }

        function switchTab(tabName) {
            // 更新标签状态
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.target.classList.add('active');

            // 更新内容显示
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabName).classList.add('active');

            // 如果是分析标签页，加载图表
            if (tabName === 'analysis') {
                loadCharts();
            }
            
            // 如果是排行榜标签页，加载排行榜数据
            if (tabName === 'ranking') {
                loadRankingData();
            }
        }

        function loadCharts() {
            if (!selectedCompany) return;

            // 加载雷达图
            fetch('/api/generate-radar-chart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(selectedCompany)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('radarChart').innerHTML = `<img src="data:image/png;base64,${data.chart}" style="max-width: 100%; height: auto;">`;
                }
            })
            .catch(error => console.error('雷达图加载失败:', error));

            // 加载评分分解图
            fetch('/api/generate-score-chart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(selectedCompany)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('scoreChart').innerHTML = `<img src="data:image/png;base64,${data.chart}" style="max-width: 100%; height: auto;">`;
                }
            })
            .catch(error => console.error('评分图加载失败:', error));

            // 加载环形图
            fetch('/api/generate-donut-chart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(selectedCompany)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('donutChart').innerHTML = `<img src="data:image/png;base64,${data.chart}" style="max-width: 100%; height: auto;">`;
                }
            })
            .catch(error => console.error('环形图加载失败:', error));
        }
        
        function renderRankingTab() {
            return `
                <!-- 排行榜 -->
                <div class="ranking-section">
                    <div class="ranking-header">
                        <div class="ranking-title">
                            📈 企业排行榜
                        </div>
                        <div class="ranking-controls">
                            <div class="search-box">
                                <input type="text" id="rankingSearch" placeholder="搜索企业名称..." onkeyup="searchInRanking()">
                                <button onclick="clearRankingSearch()" class="clear-btn">✕</button>
                            </div>
                            <div class="ranking-filters">
                                <button class="filter-btn active" data-filter="all" onclick="filterRanking('all')">全部企业</button>
                                <button class="filter-btn" data-filter="gold" onclick="filterRanking('gold')">金标企业</button>
                                <button class="filter-btn" data-filter="silver" onclick="filterRanking('silver')">银标企业</button>
                                <button class="filter-btn" data-filter="brand" onclick="filterRanking('brand')">品牌企业</button>
                                <button class="filter-btn" data-filter="top10" onclick="filterRanking('top10')">前10名</button>
                                <button class="filter-btn" data-filter="high_score" onclick="filterRanking('high_score')">高分企业(≥80分)</button>
                            </div>
                        </div>
                    </div>

                    <div class="ranking-stats" id="rankingStats" style="display: none;">
                        <div class="stats-row">
                            <div class="stat-item">
                                <span class="stat-label">企业总数</span>
                                <span class="stat-value" id="totalCompanies">0</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">平均分数</span>
                                <span class="stat-value" id="avgScore">0</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">最高分数</span>
                                <span class="stat-value" id="maxScore">0</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">金标企业</span>
                                <span class="stat-value" id="goldCount">0</span>
                            </div>
                        </div>
                    </div>

                    <div class="loading" id="rankingLoading" style="display: none;">
                        <div class="spinner"></div>
                        <div>正在加载排行榜数据...</div>
                    </div>

                    <div class="empty-state" id="rankingEmptyState" style="display: none;">
                        <div class="empty-icon">📋</div>
                        <div>暂无企业数据</div>
                        <div style="font-size: 0.9rem; margin-top: 0.5rem;">请先导入企业数据</div>
                    </div>
                    
                    <div class="ranking-list" id="rankingList"></div>
                </div>
            `;
        }

        // 排行榜相关函数
        let currentRankingFilter = 'all';
        let rankingData = [];

        function loadRankingData() {
            if (!companiesData || companiesData.length === 0) {
                document.getElementById('rankingEmptyState').style.display = 'block';
                document.getElementById('rankingList').innerHTML = '';
                return;
            }

            document.getElementById('rankingLoading').style.display = 'block';
            document.getElementById('rankingEmptyState').style.display = 'none';
            document.getElementById('rankingList').innerHTML = '';

            // 处理排行榜数据
            setTimeout(() => {
                processRankingData();
                document.getElementById('rankingLoading').style.display = 'none';
            }, 500);
        }

        function processRankingData() {
            // 按总分排序
            rankingData = [...companiesData].sort((a, b) => b.scores.total - a.scores.total);
            
            // 添加排名
            rankingData.forEach((company, index) => {
                company.rank = index + 1;
            });

            updateRankingStats();
            renderRankingList();
        }

        function updateRankingStats() {
            if (!rankingData || rankingData.length === 0) {
                document.getElementById('rankingStats').style.display = 'none';
                return;
            }

            const totalCompanies = rankingData.length;
            const scores = rankingData.map(c => c.scores.total);
            const avgScore = scores.reduce((sum, score) => sum + score, 0) / totalCompanies;
            const maxScore = Math.max(...scores);
            const goldCount = rankingData.filter(c => c.vip_level === '金标').length;

            document.getElementById('totalCompanies').textContent = totalCompanies;
            document.getElementById('avgScore').textContent = avgScore.toFixed(1);
            document.getElementById('maxScore').textContent = maxScore;
            document.getElementById('goldCount').textContent = goldCount;

            document.getElementById('rankingStats').style.display = 'block';
        }

        function filterRanking(filterType) {
            currentRankingFilter = filterType;
            
            // 更新按钮状态
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');

            // 应用筛选
            let filteredData = [...rankingData];
            
            switch (filterType) {
                case 'gold':
                    filteredData = rankingData.filter(company => company.vip_level === '金标');
                    break;
                case 'silver':
                    filteredData = rankingData.filter(company => company.vip_level === '银标');
                    break;
                case 'brand':
                    filteredData = rankingData.filter(company => company.is_brand);
                    break;
                case 'top10':
                    filteredData = rankingData.slice(0, 10);
                    break;
                case 'high_score':
                    filteredData = rankingData.filter(company => company.scores.total >= 80);
                    break;
                default:
                    // 'all' - 显示所有企业
                    break;
            }

            renderRankingList(filteredData);
        }

        function renderRankingList(data = rankingData) {
            const rankingList = document.getElementById('rankingList');
            
            if (!data || data.length === 0) {
                rankingList.innerHTML = `
                    <div style="text-align: center; padding: 2rem; color: #6b7280;">
                        <div style="font-size: 2rem; margin-bottom: 1rem;">📊</div>
                        <div>暂无符合条件的企业数据</div>
                    </div>
                `;
                return;
            }

            rankingList.innerHTML = data.map((company, index) => {
                const rankClass = company.rank <= 3 ? `rank-${company.rank}` : 'rank-other';
                const vipClass = company.vip_level === '金标' ? '金标' : company.vip_level === '银标' ? '银标' : '铜标';
                
                return `
                    <div class="ranking-item" onclick="selectCompanyFromRanking('${company.name}')">
                        <div class="rank-number ${rankClass}">
                            ${company.rank}
                        </div>
                        <div class="company-info">
                            <div class="company-name">${company.name}</div>
                            <div class="company-details">
                                <div class="company-detail-item">
                                    <span>🏛️</span>
                                    <span>参展${company.exhibition_count}届</span>
                                </div>
                                <div class="company-detail-item">
                                    <span>📍</span>
                                    <span>${company.city || '未知城市'}</span>
                                </div>
                                <div class="company-detail-item">
                                    <span>${company.is_brand ? '🎖️' : '🔖'}</span>
                                    <span>${company.is_brand ? '品牌企业' : '一般企业'}</span>
                                </div>
                                <div class="company-detail-item">
                                    <span>👨‍💼</span>
                                    <span>${company.trading_group}交易团</span>
                                </div>
                            </div>
                        </div>
                        <div class="score-section">
                            <div class="total-score">${company.scores.total}</div>
                            <div class="score-label">总分</div>
                            <div class="score-breakdown">
                                <div class="score-item">市场:${Math.round(company.scores.market_value / 6 * 100)}%</div>
                                <div class="score-item">研发:${Math.round(company.scores.rd_innovation / 12 * 100)}%</div>
                                <div class="score-item">制造:${Math.round(company.scores.smart_manufacturing / 6 * 100)}%</div>
                                <div class="score-item">绿色:${Math.round(company.scores.green_manufacturing / 8 * 100)}%</div>
                                <div class="score-item">信用:${Math.round(company.scores.credit_level / 4 * 100)}%</div>
                            </div>
                        </div>
                        <div class="vip-badge ${vipClass}">
                            ${company.vip_level}
                        </div>
                    </div>
                `;
            }).join('');
        }

        function selectCompanyFromRanking(companyName) {
            // 高亮选中的企业
            document.querySelectorAll('.ranking-item').forEach(item => {
                item.classList.remove('highlighted');
            });
            event.currentTarget.classList.add('highlighted');

            // 选择企业并显示详情
            selectCompany(companyName);
        }

        // 搜索功能
        let searchTimeout;
        let currentSearchQuery = '';

        function searchInRanking() {
            const searchInput = document.getElementById('rankingSearch');
            const query = searchInput.value.trim().toLowerCase();
            
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentSearchQuery = query;
                applySearchAndFilter();
            }, 300);
        }

        function clearRankingSearch() {
            const searchInput = document.getElementById('rankingSearch');
            searchInput.value = '';
            currentSearchQuery = '';
            applySearchAndFilter();
        }

        function applySearchAndFilter() {
            let filteredData = [...rankingData];
            
            // 应用当前筛选
            switch (currentRankingFilter) {
                case 'gold':
                    filteredData = rankingData.filter(company => company.vip_level === '金标');
                    break;
                case 'silver':
                    filteredData = rankingData.filter(company => company.vip_level === '银标');
                    break;
                case 'brand':
                    filteredData = rankingData.filter(company => company.is_brand);
                    break;
                case 'top10':
                    filteredData = rankingData.slice(0, 10);
                    break;
                case 'high_score':
                    filteredData = rankingData.filter(company => company.scores.total >= 80);
                    break;
                default:
                    // 'all' - 显示所有企业
                    break;
            }
            
            // 应用搜索
            if (currentSearchQuery) {
                filteredData = filteredData.filter(company => 
                    company.name.toLowerCase().includes(currentSearchQuery) ||
                    (company.city && company.city.toLowerCase().includes(currentSearchQuery)) ||
                    (company.introduction && company.introduction.toLowerCase().includes(currentSearchQuery))
                );
            }
            
            renderRankingList(filteredData);
        }

        // 修改filterRanking函数以支持搜索
        function filterRanking(filterType) {
            currentRankingFilter = filterType;
            
            // 更新按钮状态
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');

            applySearchAndFilter();
        }

        function exportPDF() {
            if (!selectedCompany) {
                showError('请先选择一个企业');
                return;
            }

            showLoading();

            fetch('/api/generate-pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(selectedCompany)
            })
            .then(response => {
                if (response.ok) {
                    return response.blob();
                }
                throw new Error('PDF生成失败');
            })
            .then(blob => {
                hideLoading();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `${selectedCompany.name}_VIP报告_${new Date().toISOString().slice(0, 10)}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                showSuccess('PDF报告生成成功！');
            })
            .catch(error => {
                hideLoading();
                showError('PDF生成失败：' + error.message);
            });
        }

        function showLoading() {
            document.getElementById('loadingSection').style.display = 'block';
        }

        function hideLoading() {
            document.getElementById('loadingSection').style.display = 'none';
        }

        function showError(message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = message;
            document.body.appendChild(errorDiv);
            setTimeout(() => {
                document.body.removeChild(errorDiv);
            }, 5000);
        }

        function showSuccess(message) {
            const successDiv = document.createElement('div');
            successDiv.className = 'success';
            successDiv.textContent = message;
            document.body.appendChild(successDiv);
            setTimeout(() => {
                document.body.removeChild(successDiv);
            }, 3000);
        }
    </script>
</body>
</html>
'''

# API路由
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '没有选择文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': '没有选择文件'})
        
        # 读取文件内容
        file_content = file.read()
        
        # 根据文件扩展名处理
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(file_content))
        
        # 处理数据
        global companies_data
        companies_data = []
        
        for _, row in df.iterrows():
            company = data_processor._process_company_row(row)
            companies_data.append(company)
        
        return jsonify({
            'success': True,
            'companies': companies_data,
            'message': f'成功处理 {len(companies_data)} 家企业数据'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'文件处理失败: {str(e)}'})

@app.route('/api/demo-data')
def get_demo_data():
    try:
        # 创建演示数据
        demo_data = {
            '企业名称': 'TCL实业控股股份有限公司',
            '企业简介': '成立于2018年，TCL实业聚焦智能终端业务，主要涵盖显示、智能家电、创新业务及家庭互联网等全品类智能消费电子产品及服务。',
            '企业亮点': '1.TCL电视出货量全球第二\n2.TCL空调出货量全球第四\n3.TCL Mini LED电商中国市场全渠道零售量及零售额冠军\n4.雷鸟智能眼镜国内消费级市场AR产品排名第一\n5.近六年研发投入超过600亿元',
            '领先地位': '1.TCL电视出货量全球第二\n2.TCL空调出货量全球第四\n3.TCL移动路由器全球出货量第三\n4.TCL Mini LED电商中国市场全渠道零售量及零售额冠军\n5.雷鸟智能眼镜国内消费级市场AR产品排名第一',
            '产业板块': '1.光伏板块\n2.场景互联网及AI×loT板块（雷鸟科技）\n3.AR产品板块（雷鸟创新）',
            '主营产品': '1.个人及家庭产品：电视、空调、冰箱、洗衣机、智能门锁、灵悉套系家电、智能穿戴\n2.企业及商用产品：电视、冰箱、空调、洗衣机、商用显示、中央空调',
            '所在VIP展区产品情况': '一、\n1.【QM8K MiniLED 系列电视（5月）】：搭载WHVA面板、配备可播放杜比全景声的上置扬声器\n2.【X11K 超大尺寸电视】：采用14k区Halo Control和B&O音频技术\n二、\n1.【Q9L Pro/Q10L Pro 系列】：京东家电品牌榜、天猫大家电成交榜榜首\n2.【T7L 系列】：首销期在电商平台销量稳居 TOP3\n三、\n1.【TCL 智屏】：2024年一季度，TCL 电视国际市场出货量同比增长21.2%\n2.【新风空调】：表现强劲，市场份额逐步扩大',
            '所属市县': '惠州市',
            'VIP等级': '金标',
            '是否品牌': '是',
            '已参展届数': 5,
            '参展展区数': 1,
            '《财富》500强（世界2分、中国1分）': 1,
            '中国制造业500强（1分）': 1,
            '独角兽企业（1分）': 0,
            '瞪羚企业（1分）': 0,
            '上市企业（1分）': 1,
            '制造业单项冠军（国家级2分、省级1分）': 2,
            '专精特新（国家级2分、省级1分）': 1,
            '国家高新技术企业（1分）': 1,
            '企业技术中心（国家级2分、省级1分）': 2,
            '国家技术创新示范企业（1分）': 0,
            '参与制定标准（国际3分、国家2分、行业1分）': 2,
            '卓越级智能工厂（1分）': 0,
            '领航级智能工厂（2分）': 0,
            '灯塔工厂（2分）': 0,
            '绿色工厂（国家级2分、省级1分）': 2,
            '绿色设计产品（国家级2分、省级1分）': 0,
            '绿色工业园区（国家级2分、省级1分）': 0,
            '绿色供应链管理（国家级2分、省级1分）': 0,
            'AEO高级认证企业（1分）': 0,
            '总分': 13
        }
        
        # 处理演示数据
        import pandas as pd
        demo_row = pd.Series(demo_data)
        company = data_processor._process_company_row(demo_row)
        
        global companies_data
        companies_data = [company]
        
        return jsonify({
            'success': True,
            'companies': companies_data,
            'message': '演示数据加载成功'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'演示数据加载失败: {str(e)}'})

@app.route('/api/generate-radar-chart', methods=['POST'])
def generate_radar_chart():
    if not CHARTS_AVAILABLE:
        return jsonify({'success': False, 'error': '图表功能不可用'})
    
    try:
        company = request.json
        
        # 创建雷达图
        categories = ['市场价值', '研发创新', '智能制造', '绿色制造', '信用水平'] if USE_CHINESE else ['Market Value', 'R&D Innovation', 'Smart Mfg', 'Green Mfg', 'Credit Level']
        values = [
            company['scores']['market_value'] / 6 * 100,
            company['scores']['rd_innovation'] / 12 * 100,
            company['scores']['smart_manufacturing'] / 6 * 100,
            company['scores']['green_manufacturing'] / 8 * 100,
            company['scores']['credit_level'] / 4  * 100
        ]
        
        # 闭合雷达图
        values += values[:1]
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]
        
        fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(projection='polar'))
        ax.plot(angles, values, 'o-', linewidth=2, color='#3b82f6')
        ax.fill(angles, values, alpha=0.25, color='#3b82f6')
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'])
        ax.grid(True)
        
        title = f"{company['name']} - 五维度评分雷达图" if USE_CHINESE else f"{company['name']} - Five-Dimension Radar Chart"
        plt.title(title, size=12, weight='bold', pad=20)
        
        # 转换为base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        chart_data = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return jsonify({'success': True, 'chart': chart_data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'雷达图生成失败: {str(e)}'})

@app.route('/api/generate-score-chart', methods=['POST'])
def generate_score_chart():
    if not CHARTS_AVAILABLE:
        return jsonify({'success': False, 'error': '图表功能不可用'})
    
    try:
        company = request.json
        
        categories = ['市场价值', '研发创新', '智能制造', '绿色制造', '信用水平'] if USE_CHINESE else ['Market Value', 'R&D Innovation', 'Smart Mfg', 'Green Mfg', 'Credit Level']
        current_scores = [
            company['scores']['market_value'],
            company['scores']['rd_innovation'],
            company['scores']['smart_manufacturing'],
            company['scores']['green_manufacturing'],
            company['scores']['credit_level']
        ]
        max_scores = [6, 12, 6, 8, 4]
        
        x = np.arange(len(categories))
        width = 0.45
        
        fig, ax = plt.subplots(figsize=(5, 3))
        bars1 = ax.bar(x - width/2, current_scores, width, label='当前得分' if USE_CHINESE else 'Current Score', color='#3b82f6')
        bars2 = ax.bar(x + width/2, max_scores, width, label='满分' if USE_CHINESE else 'Max Score', color='#e5e7eb')
        
        ax.set_xlabel('评分类别' if USE_CHINESE else 'Score Categories')
        ax.set_ylabel('分数' if USE_CHINESE else 'Score')
        ax.set_title(f"{company['name']} - 总分完成度" if USE_CHINESE else f"{company['name']} - Score Breakdown Chart")
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # 转换为base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        chart_data = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return jsonify({'success': True, 'chart': chart_data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'评分图生成失败: {str(e)}'})

@app.route('/api/generate-donut-chart', methods=['POST'])
def generate_donut_chart():
    if not CHARTS_AVAILABLE:
        return jsonify({'success': False, 'error': '图表功能不可用'})
    
    try:
        company = request.json
        
        total_score = company['scores']['total']
        max_total = 36  # 6+12+6+8+6
        percentage = total_score / max_total * 100
        
        sizes = [percentage, 100 - percentage]
        labels = ['已完成', '未完成'] if USE_CHINESE else ['Completed', 'Remaining']
        colors = ['#3b82f6', '#e5e7eb']
        
        fig, ax = plt.subplots(figsize=(4, 4))
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                        startangle=90, pctdistance=0.85)
        
        # 创建环形图
        centre_circle = plt.Circle((0,0), 0.70, fc='white')
        fig.gca().add_artist(centre_circle)
        
        # 在中心添加总分
        ax.text(0, 0, f'{total_score}/{max_total}', ha='center', va='center', 
                fontsize=20, weight='bold', color='#1f2937')
        
        title = f"{company['name']} - 总分完成度" if USE_CHINESE else f"{company['name']} - Total Score Completion"
        plt.title(title, size=12, weight='bold', pad=20)
        
        # 转换为base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        chart_data = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return jsonify({'success': True, 'chart': chart_data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'环形图生成失败: {str(e)}'})



#@app.route('/api/honor-charts', methods=['POST'])
#def generate_honor_charts():
#    try:
#        data = request.get_json()
#        companies = data.get('companies', [])
        
#        if not companies:
#            return jsonify({'success': False, 'error': '没有企业数据'})
        
        # 创建临时目录存储图表
#        temp_dir = tempfile.mkdtemp()
        
        # 生成荣誉统计图
#        result = honor_generator.generate_comprehensive_dashboard(companies, temp_dir)
        
#        return jsonify({
#            'success': True,
#            'charts': result['charts'],
#            'statistics': result['statistics']
#        })
        
#    except Exception as e:
#        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/chart-image')
def get_chart_image():
    try:
        chart_path = request.args.get('path')
        if not chart_path or not os.path.exists(chart_path):
            return "图表文件不存在", 404
        
        return send_file(chart_path, mimetype='image/png')
        
    except Exception as e:
        return f"获取图表失败: {str(e)}", 500


##########################################################
@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        company = request.json
        
        # 简化的PDF生成（使用reportlab）
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        from datetime import datetime
        
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # 封面页
        p.setFont("Helvetica-Bold", 24)
        p.drawCentredString(width/2, height-100, f"{company['name']}")
        
        p.setFont("Helvetica", 16)
        p.drawCentredString(width/2, height-150, "VIP Enterprise Information Report")
        
        p.setFont("Helvetica", 12)
        p.drawCentredString(width/2, height-200, f"VIP Level: {company['vip_level']}")
        p.drawCentredString(width/2, height-220, f"Total Score: {company['scores']['total']}/25")
        p.drawCentredString(width/2, height-240, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 基本信息
        y_position = height - 300
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y_position, "Basic Information")
        
        y_position -= 30
        p.setFont("Helvetica", 10)
        info_lines = [
            f"Company Name: {company['name']}",
            f"City: {company.get('city')}",
            f"Exhibition Count: {company.get(['exhibition_count'])}",
            f"Brand Status: {'Yes' if company.get('is_brand') else 'No'}",
            f"VIP Level: {company['vip_level']}"
        ]
        
        for line in info_lines:
            p.drawString(50, y_position, line)
            y_position -= 20
        
        # 评分详情
        y_position -= 30
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y_position, "Score Details")
        
        y_position -= 30
        p.setFont("Helvetica", 10)
        score_lines = [
            f"Market Value: {company['scores']['market_value']}/5",
            f"R&D Innovation: {company['scores']['rd_innovation']}/12",
            f"Smart Manufacturing: {company['scores']['smart_manufacturing']}/5",
            f"Green Manufacturing: {company['scores']['green_manufacturing']}/8",
            f"Credit Level: {company['scores']['credit_level']}/1",
            f"Total Score: {company['scores']['total']}/36 ({company['scores']['percentage']}%)"
        ]
        
        for line in score_lines:
            p.drawString(50, y_position, line)
            y_position -= 20
        
        # 企业亮点
        if company.get('highlights'):
            y_position -= 30
            p.setFont("Helvetica-Bold", 14)
            p.drawString(50, y_position, "Company Highlights")
            
            y_position -= 20
            p.setFont("Helvetica", 10)
            for i, highlight in enumerate(company['highlights'][:5], 1):
                if y_position < 100:
                    p.showPage()
                    y_position = height - 50
                p.drawString(50, y_position, f"{i}. {highlight[:80]}...")
                y_position -= 20
        
        p.save()
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{company['name']}_VIP_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'PDF生成失败: {str(e)}'})

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'charts_available': CHARTS_AVAILABLE,
        'chinese_font': USE_CHINESE,
        'companies_loaded': len(companies_data)
    })

# 排行榜相关API路由
@app.route('/api/ranking', methods=['GET'])
def get_ranking():
    """获取企业排行榜"""
    try:
        filter_type = request.args.get('filter', 'all')
        sort_by = request.args.get('sort', 'total_score')
        
        if not companies_data:
            return jsonify({
                'success': False,
                'message': '暂无企业数据',
                'data': []
            })
        
        # 按总分排序
        sorted_companies = sorted(companies_data, key=lambda x: x['scores']['total'], reverse=True)
        
        # 添加排名
        for i, company in enumerate(sorted_companies):
            company['rank'] = i + 1
        
        # 应用筛选
        if filter_type == 'gold':
            filtered_companies = [c for c in sorted_companies if c.get('vip_level') == '金标']
        elif filter_type == 'silver':
            filtered_companies = [c for c in sorted_companies if c.get('vip_level') == '银标']
        elif filter_type == 'brand':
            filtered_companies = [c for c in sorted_companies if c.get('is_brand')]
        elif filter_type == 'top10':
            filtered_companies = sorted_companies[:10]
        elif filter_type == 'high_score':
            filtered_companies = [c for c in sorted_companies if c['scores']['total'] >= 80]
        else:
            filtered_companies = sorted_companies
        
        return jsonify({
            'success': True,
            'message': '获取排行榜成功',
            'data': {
                'companies': filtered_companies,
                'total': len(filtered_companies),
                'filter': filter_type
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取排行榜失败: {str(e)}',
            'data': None
        }), 500

@app.route('/api/search-companies', methods=['GET'])
def search_companies():
    """搜索企业"""
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))
        
        if not query:
            return jsonify({
                'success': False,
                'message': '搜索关键词不能为空',
                'data': []
            }), 400
        
        if not companies_data:
            return jsonify({
                'success': False,
                'message': '暂无企业数据',
                'data': []
            })
        
        # 简单搜索实现
        results = []
        query_lower = query.lower()
        
        for company in companies_data:
            if (query_lower in company['name'].lower() or 
                query_lower in company.get('city', '').lower() or
                query_lower in company.get('introduction', '').lower()):
                results.append(company)
        
        # 按总分排序
        results.sort(key=lambda x: x['scores']['total'], reverse=True)
        results = results[:limit]
        
        return jsonify({
            'success': True,
            'message': '搜索成功',
            'data': {
                'companies': results,
                'total': len(results),
                'query': query
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'搜索失败: {str(e)}',
            'data': None
        }), 500

@app.route('/api/ranking-statistics', methods=['GET'])
def get_ranking_statistics():
    """获取排行榜统计信息"""
    try:
        if not companies_data:
            return jsonify({
                'success': False,
                'message': '暂无企业数据',
                'data': {}
            })
        
        # 计算统计信息
        total_companies = len(companies_data)
        gold_vip_count = len([c for c in companies_data if c.get('vip_level') == '金标'])
        silver_vip_count = len([c for c in companies_data if c.get('vip_level') == '银标'])
        brand_companies = len([c for c in companies_data if c.get('is_brand')])
        
        # 分数统计
        scores = [c['scores']['total'] for c in companies_data]
        avg_score = sum(scores) / len(scores) if scores else 0
        max_score = max(scores) if scores else 0
        min_score = min(scores) if scores else 0
        
        # 分数段统计
        high_score_count = len([s for s in scores if s >= 80])
        medium_score_count = len([s for s in scores if 60 <= s < 80])
        low_score_count = len([s for s in scores if s < 60])
        
        return jsonify({
            'success': True,
            'message': '获取统计信息成功',
            'data': {
                'total_companies': total_companies,
                'gold_vip_count': gold_vip_count,
                'silver_vip_count': silver_vip_count,
                'brand_companies': brand_companies,
                'avg_score': round(avg_score, 1),
                'max_score': max_score,
                'min_score': min_score,
                'high_score_count': high_score_count,
                'medium_score_count': medium_score_count,
                'low_score_count': low_score_count
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取统计信息失败: {str(e)}',
            'data': None
        }), 500

@app.route('/api/company/<company_name>', methods=['GET'])
def get_company_details(company_name):
    """获取企业详细信息"""
    try:
        if not companies_data:
            return jsonify({
                'success': False,
                'message': '暂无企业数据',
                'data': None
            }), 404
        
        # 查找企业
        company = None
        for c in companies_data:
            if c['name'] == company_name:
                company = c
                break
        
        if not company:
            return jsonify({
                'success': False,
                'message': f'未找到企业: {company_name}',
                'data': None
            }), 404
        
        return jsonify({
            'success': True,
            'message': '获取企业信息成功',
            'data': company
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取企业信息失败: {str(e)}',
            'data': None
        }), 500

if __name__ == '__main__':
    print("🚀 VIP企业信息数据看板启动中...")
    print("📊 支持新的13分评分系统")
    print("🎨 优化的文字内容结构化展现")
    print("🌐 访问地址: http://localhost:5001")
    if CHARTS_AVAILABLE:
        print("✅ 图表功能可用")
        if USE_CHINESE:
            print("✅ 中文字体配置成功")
        else:
            print("⚠️ 使用英文字体显示")
    else:
        print("⚠️ 图表功能不可用，请安装matplotlib和seaborn")
    
    # 获取端口（Heroku会提供PORT环境变量）
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)

