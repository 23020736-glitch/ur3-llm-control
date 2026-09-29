import os
from glob import glob
from setuptools import setup

pkg = 'ur3_llm_control'
setup(
    name=pkg, version='0.1.0', packages=[pkg],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + pkg]),
        ('share/' + pkg, ['package.xml']),
        (os.path.join('share', pkg, 'launch'), glob('launch/*.py')),
        (os.path.join('share', pkg, 'config'), glob('config/*')),
    ],
    install_requires=['setuptools', 'pyyaml'], zip_safe=True,
    entry_points={'console_scripts': [
        'llm_planner = ur3_llm_control.llm_planner:main',
        'skill_executor = ur3_llm_control.skill_executor:main',
    ]},
)
