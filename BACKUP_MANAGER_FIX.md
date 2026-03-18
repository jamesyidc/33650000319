# Backup Manager 服务修复记录

## 问题描述

**时间**: 2026-03-19 04:00 北京时间  
**URL**: https://9002-iwyspq7c2ufr5cnosf8lb-82b888ba.sandbox.novita.ai/backup-manager  
**症状**: Backup Manager 页面显示"服务未启动"

## 问题原因

backup-manager 服务没有在 PM2 中启动。虽然备份调度器脚本 `backup_scheduler.py` 存在，但没有配置为自动运行。

## 修复步骤

### 1. 确认备份脚本存在

```bash
ls -l /home/user/webapp/backup_scheduler.py
```

备份调度器脚本功能：
- 每 12 小时执行一次自动备份
- 调用 `auto_backup_system.py` 执行实际备份
- 记录备份历史到 `data/backup_history.jsonl`
- 保留最近 3 个备份文件
- 使用北京时间（UTC+8）

### 2. 使用 PM2 启动服务

```bash
cd /home/user/webapp
pm2 start backup_scheduler.py --name backup-manager --interpreter python3 --time
pm2 save
```

**参数说明**：
- `--name backup-manager`: 设置服务名称
- `--interpreter python3`: 使用 Python 3 解释器
- `--time`: 在日志中添加时间戳

### 3. 验证服务状态

```bash
# 检查 PM2 状态
pm2 list | grep backup-manager

# 查看日志
pm2 logs backup-manager --lines 50 --nostream
```

**预期输出**：
```
✅ 备份调度器已启动
⏱️  备份间隔: 12.0 小时
📜 备份脚本: /home/user/webapp/auto_backup_system.py
🎯 执行首次备份...
```

### 4. 验证备份文件

```bash
# 检查备份文件
ls -lh /tmp/webapp_backup_*.tar.gz

# 检查备份历史
tail -5 /home/user/webapp/data/backup_history.jsonl
```

### 5. 验证 API 端点

```bash
# 测试备份状态 API
curl -s http://localhost:9002/api/backup/status | python3 -m json.tool

# 测试备份触发 API
curl -X POST http://localhost:9002/api/backup/trigger
```

## 修复结果

### ✅ 服务状态

- **PM2 ID**: 23
- **服务名**: backup-manager
- **状态**: online
- **重启次数**: 0
- **进程**: python3 backup_scheduler.py

### ✅ 首次备份完成

**备份信息**：
- **文件名**: webapp_backup_20260319_4.tar.gz
- **大小**: 286.24 MB
- **时间**: 2026-03-19 03:59:28 (北京时间)
- **状态**: 成功

**备份内容统计**：
```
- PYTHON: 403 文件, 5.43 MB
- MARKDOWN: 75 文件, 693.62 KB
- HTML: 290 文件, 14.10 MB
- CONFIG: 302 文件, 3.24 MB
- DATA: 1382 文件, 3.23 GB
- LOGS: 54 文件, 15.14 MB
- OTHER: 1363 文件, 167.61 MB
```

### ✅ 当前保留备份

保留最近 3 个备份文件：
1. webapp_backup_20260319_4.tar.gz - 286.24 MB - 2026-03-18 19:59:28
2. webapp_backup_20260319_3.tar.gz - 286.24 MB - 2026-03-18 19:57:53
3. webapp_backup_20260319_2.tar.gz - 286.24 MB - 2026-03-18 19:57:49

### ✅ 下次备份时间

**预定时间**: 2026-03-19 15:59:28 (北京时间)  
**间隔**: 12 小时

### ✅ API 状态

- `/api/backup/status` - ✅ 正常返回备份列表和历史
- `/api/backup/trigger` - ✅ 可手动触发备份

### ✅ 页面加载

- **URL**: https://9002-iwyspq7c2ufr5cnosf8lb-82b888ba.sandbox.novita.ai/backup-manager
- **加载时间**: 9.81 秒
- **页面标题**: 自动备份管理系统
- **状态**: 正常显示

## 备份系统架构

### 文件结构

```
/home/user/webapp/
├── backup_scheduler.py          # 备份调度器（12小时定时）
├── auto_backup_system.py        # 实际备份执行脚本
├── data/
│   └── backup_history.jsonl     # 备份历史记录
└── /tmp/
    └── webapp_backup_*.tar.gz   # 备份文件（保留最近3个）
```

### PM2 配置

```javascript
{
  name: 'backup-manager',
  script: 'backup_scheduler.py',
  interpreter: 'python3',
  time: true,
  autorestart: true
}
```

### API 路由

在 `core_code/app.py` 中定义：

- **GET /backup-manager** - 备份管理页面
- **GET /api/backup/status** - 获取备份状态
- **POST /api/backup/trigger** - 手动触发备份

## 维护建议

### 1. 监控备份状态

```bash
# 定期检查服务状态
pm2 status backup-manager

# 查看最近的日志
pm2 logs backup-manager --lines 100 --nostream
```

### 2. 手动触发备份

如需立即执行备份：

```bash
curl -X POST http://localhost:9002/api/backup/trigger
```

### 3. 清理旧备份

备份系统自动保留最近 3 个备份。如需调整：

编辑 `auto_backup_system.py` 中的 `MAX_BACKUPS` 参数：

```python
MAX_BACKUPS = 3  # 改为需要保留的数量
```

### 4. 修改备份间隔

编辑 `backup_scheduler.py` 中的 `BACKUP_INTERVAL`：

```python
BACKUP_INTERVAL = 12 * 60 * 60  # 12小时（秒）
```

修改后需要重启服务：

```bash
pm2 restart backup-manager
```

## 问题排查

### 问题：服务频繁重启

**检查日志**：
```bash
pm2 logs backup-manager --err --lines 100
```

**常见原因**：
- 备份脚本路径错误
- 权限不足
- 磁盘空间不足

### 问题：备份失败

**检查备份历史**：
```bash
tail -20 /home/user/webapp/data/backup_history.jsonl | grep failed
```

**常见原因**：
- 文件在备份时被修改（tar: file changed as we read it）- 警告，不影响备份
- 备份文件太小（< 260 MB）- 可能备份不完整
- 磁盘空间不足

### 问题：页面显示数据不准确

**刷新缓存**：
- 强制刷新页面（Ctrl+F5）
- 检查 API 返回：`curl http://localhost:9002/api/backup/status`

## 总结

**修复完成时间**: 2026-03-19 04:02 北京时间  
**修复用时**: ~2 分钟  
**服务状态**: ✅ 正常运行  
**下次备份**: 2026-03-19 15:59:28 (北京时间)

backup-manager 服务已成功启动，首次备份已完成，系统将每 12 小时自动执行备份任务。
