from setuptools import setup, find_packages

setup(
    name="broadcastify",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.1",
        "beautifulsoup4>=4.9.3",
        "click>=8.0.0",
        "rich>=10.0.0",
        "numpy<2",
        "torch",
        "openai-whisper==20231117",
    ],
    entry_points={
        'console_scripts': [
            'state-scraper=scripts.state_scraper:main',
        ],
    },
)
