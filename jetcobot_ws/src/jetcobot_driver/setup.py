from setuptools import find_packages, setup
package_name = 'jetcobot_driver'
setup(
name=package_name,
version='0.0.0',
packages=find_packages(exclude=['test']),
data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
install_requires=['setuptools'],
zip_safe=True,
maintainer='jetson',
maintainer_email='jetson@todo.todo',
description='TODO: Package description',
license='TODO: License declaration',
tests_require=['pytest'],
entry_points={
'console_scripts': [
'sync_plan = jetcobot_driver.sync_plan:main',
'sync_plan_nx = jetcobot_driver.sync_plan_nx:main',
'camera_logger = jetcobot_driver.camera_logger_node:main'
        ],
    },
)