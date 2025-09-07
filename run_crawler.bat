@echo off
chcp 65001 >nul
REM 比赛信息爬虫定时任务批处理文件
REM 用于Windows任务计划程序调用

REM 设置工作目录
cd /d "E:\pachong"

REM 记录开始时间
echo [%date% %time%] 开始执行爬虫任务 >> logs\task_scheduler.log

REM 激活虚拟环境（如果使用虚拟环境）
REM call venv\Scripts\activate.bat

REM 执行爬虫任务
python scheduler.py --mode once >> logs\task_scheduler.log 2>&1

REM 记录完成时间
echo [%date% %time%] 爬虫任务执行完成 >> logs\task_scheduler.log
echo. >> logs\task_scheduler.log

REM 可选：发送完成通知（需要配置邮件或其他通知方式）
REM python send_notification.py

pause