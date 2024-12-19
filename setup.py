from setuptools import setup, find_packages

setup(
    name="ssbubble",
    version="0.1.0",
    description="SSBubble Control Application",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        'PyQt6>=6.6.1',
        'pyqtgraph>=0.13.3',
        'pyserial>=3.5',
        'minimalmodbus>=2.1.1',
        'numpy>=1.26.0',
        'pandas>=2.1.0',
        'psutil>=5.9.0',
        'typing-extensions>=4.9.0'
    ],
    extras_require={
        'dev': [
            'pytest>=8.0.0',
            'pytest-qt>=4.4.0',
            'pytest-asyncio>=0.25.0',
            'pytest-cov>=6.0.0',
            'pytest-mock>=3.12.0',
            'black>=24.1.0',
            'flake8>=7.0.0',
            'mypy>=1.8.0'
        ]
    },
    entry_points={
        'console_scripts': [
            'ssbubble=main:main',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
