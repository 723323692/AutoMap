# -*- coding: utf-8 -*-
"""
YOLO模型训练脚本
在现有模型基础上微调，添加新类别并提升识别精度
"""

from ultralytics import YOLO
import os

# 配置
BASE_MODEL = '../weights/stronger.pt'  # 现有模型
DATASET_CONFIG = 'dataset.yaml'        # 数据集配置
OUTPUT_DIR = 'runs/train'              # 输出目录

# 训练参数
EPOCHS = 50          # 训练轮数（微调不需要太多）
BATCH_SIZE = 16      # 批次大小（根据显存调整，显存不够就改小）
IMG_SIZE = 640       # 图片尺寸
DEVICE = 0           # GPU设备，0表示第一块显卡，'cpu'表示用CPU

def train():
    print("=" * 50)
    print("开始训练")
    print(f"基础模型: {BASE_MODEL}")
    print(f"数据集配置: {DATASET_CONFIG}")
    print(f"训练轮数: {EPOCHS}")
    print("=" * 50)
    
    # 加载现有模型
    model = YOLO(BASE_MODEL)
    
    # 开始训练
    results = model.train(
        data=DATASET_CONFIG,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        device=DEVICE,
        project=OUTPUT_DIR,
        name='stronger_v2',
        exist_ok=True,
        # 优化参数
        patience=10,        # 早停，10轮没提升就停止
        save=True,          # 保存检查点
        save_period=10,     # 每10轮保存一次
        plots=True,         # 生成训练曲线图
        # 数据增强
        augment=True,
        mosaic=1.0,
        mixup=0.1,
    )
    
    print("=" * 50)
    print("训练完成！")
    print(f"最佳模型保存在: {OUTPUT_DIR}/stronger_v2/weights/best.pt")
    print("=" * 50)
    
    return results

if __name__ == '__main__':
    train()
