.PHONY: help install dev test clean docker-build docker-up docker-down init-db check

help:
	@echo "可用命令:"
	@echo "  make install      - 安装依赖"
	@echo "  make dev          - 启动开发服务器"
	@echo "  make test         - 运行测试"
	@echo "  make clean        - 清理临时文件"
	@echo "  make docker-build - 构建Docker镜像"
	@echo "  make docker-up    - 启动Docker服务"
	@echo "  make docker-down  - 停止Docker服务"
	@echo "  make init-db      - 初始化数据库"
	@echo "  make sample-data  - 生成示例数据"
	@echo "  make check        - 系统检查"
	@echo "  make init-sample  - 初始化示例系统"

install:
	pip install -r requirements.txt

dev:
	python run.py

test:
	pytest -v

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

init-db:
	python init_db.py

sample-data:
	python scripts/sample_data_generator.py

check:
	python scripts/check_system.py

init-sample:
	python scripts/init_sample_system.py
