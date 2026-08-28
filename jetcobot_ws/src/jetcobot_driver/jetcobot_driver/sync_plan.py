#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from pymycobot.mycobot import MyCobot

class MycobotReceiver(Node):
    def __init__(self):
        super().__init__("mycobot_receiver")
        
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baud', 1000000)
        port = self.get_parameter('port').value
        baud = self.get_parameter('baud').value

        self.mc = MyCobot(port, baud)
        self.get_logger().info(f"Connected to MyCobot at {port}, baud: {baud}")
        self.subscription = self.create_subscription(JointState,'joint_states',self.callback,10)

    def callback(self, msg):
        self.get_logger().info(f"******: {msg.position}")
        data_list = []

        for index, value in enumerate(msg.position):
            data_list.append(value)
        index_1 = data_list[1]   #0.4
        index_2 = data_list[2]   #0.6
        index_3 = data_list[3]   #0.2

        data_list[1] = index_3
        data_list[2] = index_1
        data_list[3] = index_2

        data_list[5] = data_list[5] - 0.7853981633974483
        
        self.mc.send_radians(data_list, 80)
        self.get_logger().info(f"Received joints: {data_list}")

def main(args=None):
    rclpy.init(args=args)
    node = MycobotReceiver()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
