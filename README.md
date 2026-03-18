# 诗词学习助手（Poetry Expert System）

一个基于 **Python + Streamlit** 开发的古诗词学习系统，支持诗词浏览、语音朗读、录音识别、背诵检测、练习闯关、积分与错题本等功能。

---

## 一、项目简介

本项目旨在构建一个面向古诗词学习场景的智能学习助手，帮助用户通过“阅读 + 朗读 + 跟读 + 练习”的方式提升古诗词学习兴趣和记忆效果。

### 主要功能

- 诗词浏览与学习
- 诗词朗读（TTS 语音合成）
- 录音跟读（语音识别）
- 背诵检测
- 练习模式 / 闯关模式
- 学习积分与连击系统
- 错题本与成就记录

---

## 二、项目结构

请确保项目目录结构如下：

```bash
Poetry expert system/
├── poem_app_v3.py         # 主程序入口
├── poems_v2.json          # 诗词数据文件
├── requirements.txt       # 依赖文件
├── start_app.bat          # 一键启动脚本（Windows）
└── README.md              # 项目说明文档
```

## 三、快速运行与部署

### 1. 克隆项目
```bash
git clone https://github.com/Karterlar/Poetry-learning-app.git
cd Poetry-learning-app、
```
### 2. 安装依赖
```bash
pip install -r requirements.txt
```
### 3. 启动应用
```bash
streamlit run app.py
```
