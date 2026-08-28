#!/usr/bin/env python3
"""
Simple script to debug camera topic and verify Image message format
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import sys


class CameraDebugger(Node):
    def __init__(self):
        super().__init__('camera_debugger')
        self.get_logger().info('Starting camera debugger...')
        self.get_logger().info('Subscribing to /camera/image_raw')
        self.subscription = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.listener_callback,
            10)
        self.subscription  # prevent unused variable warning
        self.msg_count = 0

    def listener_callback(self, msg):
        self.msg_count += 1
        if self.msg_count == 1 or self.msg_count % 10 == 0:
            self.get_logger().info(f'Received message #{self.msg_count}:')
            self.get_logger().info(f'  Frame ID: {msg.header.frame_id}')
            self.get_logger().info(f'  Timestamp: {msg.header.stamp}')
            self.get_logger().info(f'  Width: {msg.width}, Height: {msg.height}')
            self.get_logger().info(f'  Encoding: {msg.encoding}')
            self.get_logger().info(f'  Data length: {len(msg.data)} bytes')


def main(args=None):
    rclpy.init(args=args)
    node = CameraDebugger()
    
    print("\nListening for camera messages... (Ctrl+C to stop)")
    print("Make sure gazebo.launch.py is running in another terminal!")
    print("")
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
