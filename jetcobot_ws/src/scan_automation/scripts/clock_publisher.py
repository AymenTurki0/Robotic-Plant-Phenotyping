#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rosgraph_msgs.msg import Clock
from builtin_interfaces.msg import Time
import time

class ClockPublisher(Node):
    def __init__(self):
        super().__init__('clock_publisher')
        self.pub = self.create_publisher(Clock, '/clock', 10)
        self.timer = self.create_timer(0.01, self.publish_clock)  # 100 Hz

    def publish_clock(self):
        now = time.time()
        sec = int(now)
        nanosec = int((now - sec) * 1e9)
        msg = Clock()
        msg.clock.sec = sec
        msg.clock.nanosec = nanosec
        self.pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = ClockPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()