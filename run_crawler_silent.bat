@echo off
chcp 65001 >nul
REM 比赛信息爬虫定时任务批处理文件（静默模式）
REM 专用于Windows任务计划程序调用

REM 设置工作目录
cd /d "E:\pachong"

REM 创建日志目录（如果不存在）
if not exist "logs" mkdir logs

REM 记录开始时间
echo [%date% %time%] 开始执行定时爬虫任务 >> logs\task_scheduler.log

REM 执行爬虫任务
python scheduler.py --mode once >> logs\task_scheduler.log 2>&1

REM 检查执行结果
if %errorlevel% equ 0 (
    echo [%date% %time%] 爬虫任务执行成功 >> logs\task_scheduler.log
) else (
    echo [%date% %time%] 爬虫任务执行失败，错误代码: %errorlevel% >> logs\task_scheduler.log
)

echo. >> logs\task_scheduler.log