"""
Setup script for the TradingAgents package.

Note: This file is kept for backwards compatibility with older pip versions.
The primary configuration is in pyproject.toml.
"""

from setuptools import setup, find_packages

setup(
    name="tradingcrew",
    version="0.5.0",
    description="TradingCrew - Multi-Agent LLM Financial Trading Framework",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="TradingCrew Team",
    author_email="yijia.xiao@cs.ucla.edu",
    url="https://github.com/rminchev1/TradingCrew",
    packages=find_packages(exclude=["tests*", "analysis_history*"]),
    include_package_data=True,
    package_data={
        "webui": ["assets/*", "assets/**/*"],
        "cli": ["static/*"],
    },
    install_requires=[
        "typing-extensions>=4.0.0",
        "langchain>=0.1.0",
        "langchain-openai>=0.0.2",
        "langchain-experimental>=0.0.40",
        "langgraph>=0.0.20",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "praw>=7.7.0",
        "feedparser>=6.0.0",
        "stockstats>=0.5.4",
        "finnhub-python>=2.4.0",
        "parsel>=1.8.0",
        "requests>=2.28.0",
        "tqdm>=4.65.0",
        "pytz>=2023.3",
        "python-dotenv>=1.0.0",
        "rich>=13.0.0",
        "typer>=0.9.0",
        "questionary>=2.0.1",
        "plotly>=5.18.0",
        "dash>=3.0.0",
        "dash-bootstrap-components>=2.0.0",
        "flask>=3.0.0",
        "alpaca-py>=0.8.2",
        "yfinance>=0.2.40",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
        ],
        "extras": [
            "redis>=4.5.0",
            "chainlit>=0.7.0",
            "backtrader>=1.9.0",
            "chromadb>=0.4.0",
            "gradio>=4.0.0",
        ],
    },
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "tradingcrew=cli.main:main",
            "tradingcrew-web=webui:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords=[
        "trading",
        "finance",
        "llm",
        "agents",
        "alpaca",
        "stocks",
        "crypto",
        "ai",
        "langchain",
        "langgraph",
    ],
)
