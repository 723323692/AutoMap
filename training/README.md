# 模型训练指南

## 1. 准备数据集

### 目录结构
```
dataset/
├── images/
│   ├── train/    # 训练图片（80%）
│   └── val/      # 验证图片（20%）
├── labels/
│   ├── train/    # 训练标注（YOLO格式txt）
│   └── val/      # 验证标注
```

### 标注工具
```bash
pip install labelimg
labelimg dataset/images/train dataset/classes.txt
```

### 标注格式（YOLO格式）
每张图片对应一个同名的txt文件，每行一个目标：
```
类别ID 中心x 中心y 宽度 高度
```
坐标都是相对值（0-1之间）

### 类别ID对照
- 0: boss
- 1: card
- 2: continue
- 3: door（重点标注，提升精度）
- 4: gold
- 5: hero
- 6: loot
- 7: menu
- 8: monster
- 9: elite-monster
- 10: shop
- 11: shop-mystery
- 12: sss
- 13: door-boss
- 14: obstacle（障碍物）

## 2. 修改配置

编辑 `dataset.yaml`：
- 修改 `path` 为数据集实际路径
- 修改类别14的名称为你的新类别

## 3. 开始训练

```bash
cd training
python train.py
```

## 4. 训练完成

最佳模型保存在：`runs/train/stronger_v2/weights/best.pt`

复制到weights目录替换原模型：
```bash
copy runs\train\stronger_v2\weights\best.pt ..\weights\stronger.pt
```

## 5. 注意事项

- 显存不够：减小 BATCH_SIZE（改成8或4）
- 训练太慢：减少 EPOCHS
- 效果不好：增加数据量，检查标注质量
