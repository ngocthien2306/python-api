# Email Reminder System Setup Guide

## Tổng quan
Hệ thống email reminder tự động gửi email nhắc nhở người dùng về các task dựa trên reminder documents đã có sẵn trong database.

## Các thành phần chính

### 1. Email Service (`app/services/email_service.py`)
- Xử lý việc gửi email thông qua Gmail SMTP
- Có template HTML chuyên dụng cho reminder emails
- Method: `send_task_reminder_notification_email()`

### 2. Reminder Email Service (`app/services/reminder_email_service.py`)
- **Chức năng chính**: `process_due_reminders()` - quét và gửi email cho reminder đã đến hạn
- Tìm các reminder có `status: "pending"` và `triggerTime <= now`
- Gửi email và mark reminder thành `"sent"`
- Có thêm `send_test_reminder_email()` để test

### 3. Scheduler Service (`app/services/scheduler_service.py`)
- **Chạy liên tục**: Check reminder mỗi 60 giây
- Tự động start khi app khởi động và stop khi app shutdown
- Sử dụng asyncio để chạy background task

### 4. Reminder Update Service (`app/services/reminder_update_service.py`)
- **Tự động update reminders**: Khi task thay đổi thời gian due_date/due_time
- Tính toán lại `triggerTime` dựa trên `beforeDue` (ví dụ: "15m", "1h", "2d")
- Support nhiều format: "15m", "1h30m", "2d", etc.

### 5. API Routes (`app/api/routes/reminders.py`)
- `POST /api/v1/reminders` - Tạo reminder mới
- `GET /api/v1/reminders/upcoming` - Lấy danh sách reminder sắp tới
- `POST /api/v1/reminders/process` - Trigger xử lý reminder manually
- `POST /api/v1/reminders/test/{user_id}` - Gửi test email

## Cách hoạt động

### 1. Tự động chạy liên tục
```python
# Scheduler tự động start khi app khởi động
# Check reminder mỗi 60 giây
# Logic mới: Tính toán thời gian due của task từ due_date + due_time
# Check xem hiện tại có nằm trong khoảng beforeDue không
# Ví dụ: Task due 15:00, beforeDue "15m" → gửi reminder từ 14:45 đến 15:00
# Gửi email và mark là "sent" (chỉ gửi 1 lần)
```

### 2. Khi người dùng update task
```python
# Trong API update task, nếu due_date hoặc due_time thay đổi:
# 1. Update task thành công
# 2. Tự động tìm tất cả pending reminders của task đó
# 3. Tính lại triggerTime dựa trên beforeDue
# 4. Update các reminders với triggerTime mới
```

### 3. Logic tính toán reminder window (Mới)
```python
# Ví dụ: Task due "2024-01-15 14:00", reminder beforeDue "15m"
# Reminder window: từ 13:45 đến 14:00
# Nếu thời gian hiện tại nằm trong window này → gửi email

# Support formats beforeDue:
# "15m" = 15 phút trước
# "1h" = 1 giờ trước  
# "1h30m" = 1 giờ 30 phút trước
# "2d" = 2 ngày trước
# "1d2h30m" = 1 ngày 2 giờ 30 phút trước

# Ưu điểm logic mới:
# - Không phụ thuộc vào triggerTime trong DB
# - Tính toán real-time từ task due_date/due_time
# - Chỉ gửi 1 lần trong window thời gian
# - Tự động sync khi task time thay đổi
```

### 4. Xóa task tự động xóa reminders
```python
# Khi xóa task, API sẽ tự động:
# 1. Tìm tất cả reminders có taskId = task_id
# 2. Xóa tất cả reminders đó
# 3. Xóa task
# 4. Return số lượng reminders đã xóa
```

## Setup Instructions

### 1. Cấu hình SMTP trong .env
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=taskmanagement.agent@gmail.com
SMTP_PASSWORD=ugqu xoiw wout iotf
SMTP_FROM_EMAIL=taskmanagement.agent@gmail.com
SMTP_FROM_NAME=Task Management System
FRONTEND_URL=http://localhost:5173
```

### 2. Khởi động server
```bash
cd python-api
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Scheduler sẽ tự động chạy
- Khi server start, scheduler sẽ tự động bắt đầu
- Check reminder mỗi 60 giây
- Log sẽ hiển thị: "Scheduler service started"

### 4. Test hệ thống

#### Test manual processing:
```bash
curl -X POST "http://localhost:8000/api/v1/reminders/process" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Test gửi email thử:
```bash
curl -X POST "http://localhost:8000/api/v1/reminders/test/USER_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Tạo reminder mới:
```bash
curl -X POST "http://localhost:8000/api/v1/reminders" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "task_id": "TASK_ID",
    "before_due": "15m",
    "message": "Nhắc nhở: Task sắp hết hạn!"
  }'
```

## Cấu trúc Reminder Document

```json
{
  "_id": "ObjectId",
  "userId": "string",
  "taskId": "ObjectId", 
  "type": "time",
  "triggerTime": "ISODate",
  "beforeDue": "15m",
  "message": "Reminder: Task title due in 15m",
  "channel": "notification",
  "status": "pending", // hoặc "sent"
  "priority": "medium",
  "scheduleType": "",
  "slotIndex": 0,
  "ruleIndex": 0,
  "createdAt": "ISODate",
  "updatedAt": "ISODate"
}
```

## Log Files để theo dõi

Hệ thống tạo 2 file log chính trong thư mục `logs/`:

### 1. `logs/reminder_system.log` - Hoạt động gửi email
```bash
# Ví dụ logs:
2024-01-15 14:30:00 - reminder_system - INFO - 🔍 [2024-01-15 14:30:00] Starting reminder check cycle...
2024-01-15 14:30:00 - reminder_system - INFO - Found 3 due reminders to process:
2024-01-15 14:30:00 - reminder_system - INFO -   1. Reminder 507f1f... - User: ngocthien - Trigger: 2024-01-15 14:29:30
2024-01-15 14:30:00 - reminder_system - INFO -   2. Reminder 507f1g... - User: john123 - Trigger: 2024-01-15 14:25:00
2024-01-15 14:30:01 - reminder_system - INFO - ✅ Reminder 507f1f... sent successfully for task: Complete Project Report
2024-01-15 14:30:02 - reminder_system - INFO - ✅ Reminder 507f1g... sent successfully for task: Team Meeting
2024-01-15 14:30:03 - reminder_system - INFO - ✅ [2024-01-15 14:30:03] Processed 3 reminders: 2 sent successfully, 1 failed
```

### 2. `logs/reminder_updates.log` - Cập nhật reminders khi task thay đổi
```bash
# Ví dụ logs:
2024-01-15 15:45:00 - reminder_updates - INFO - 🔄 [2024-01-15 15:45:00] Updating reminders for task 507f1f77...
2024-01-15 15:45:00 - reminder_updates - INFO - 📅 [2024-01-15 15:45:00] Task new due date: 2024-01-16 16:00:00, due time: 16:00
2024-01-15 15:45:00 - reminder_updates - INFO - 📋 [2024-01-15 15:45:00] Found 2 pending reminders to update:
2024-01-15 15:45:00 - reminder_updates - INFO -    1. Reminder 507f1f... - beforeDue: 15m - Current trigger: 2024-01-16 15:45:00
2024-01-15 15:45:00 - reminder_updates - INFO -    2. Reminder 507f1g... - beforeDue: 1h - Current trigger: 2024-01-16 15:00:00
2024-01-15 15:45:01 - reminder_updates - INFO - ✅ Updated reminder 507f1f... with new trigger time: 2024-01-16 15:45:00
2024-01-15 15:45:01 - reminder_updates - INFO - ✅ Updated reminder 507f1g... with new trigger time: 2024-01-16 15:00:00
2024-01-15 15:45:01 - reminder_updates - INFO - 🏁 [2024-01-15 15:45:01] Updated 2/2 reminders for task 507f1f77...
```

### Logs quan trọng để check:
- 🔍 "Starting reminder check cycle" - Bắt đầu check chu kỳ 60 giây
- 📧 "Found X due reminders to process" - Tìm thấy reminder cần gửi
- ✅ "Reminder sent successfully" - Email đã gửi thành công  
- ❌ "Failed to send reminder" - Email gửi thất bại
- 🔄 "Updating reminders for task" - Đang update reminder khi task thay đổi
- 📅 "Task new due date" - Thông tin due date/time mới của task
- 🏁 "Updated X/Y reminders" - Kết quả update reminders

### Theo dõi logs real-time:
```bash
# Theo dõi reminder system logs:
tail -f logs/reminder_system.log

# Theo dõi reminder updates logs:
tail -f logs/reminder_updates.log

# Theo dõi cả 2 logs cùng lúc:
tail -f logs/reminder_system.log logs/reminder_updates.log

# Grep tìm kiếm logs cụ thể:
grep "Starting reminder check cycle" logs/reminder_system.log
grep "sent successfully" logs/reminder_system.log
grep "Updating reminders for task" logs/reminder_updates.log
```

## Xử lý lỗi thường gặp

### 1. Scheduler không chạy
- Check logs có "Scheduler service started" không
- Kiểm tra database connection
- Restart server

### 2. Email không gửi được
- Kiểm tra SMTP credentials trong .env
- Check Gmail app password còn valid không
- Verify network connection

### 3. Reminder không update khi task thay đổi
- Check task update API có gọi reminder service không
- Verify task_id và reminder mapping
- Check logs có "Updated X reminders" không

## Performance Notes

- Scheduler check mỗi 60 giây (có thể adjust trong `scheduler_service.py`)
- Có delay 0.5 giây giữa mỗi email để tránh spam
- Reminder chỉ xử lý khi `status: "pending"`
- Sau khi gửi thành công sẽ mark `status: "sent"`