import os
import yaml
import cv2
from datetime import datetime, timezone
import traceback

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, JointState
from cv_bridge import CvBridge
import tf2_ros


class CameraLogger(Node):
    def __init__(self):
        super().__init__('camera_logger')

        self.declare_parameter('output_dir', os.path.expanduser('~/jetcobot_captures'))
        self.declare_parameter('world_frame', 'world')
        self.declare_parameter('camera_frame', 'camera_link')

        self.output_dir = self.get_parameter('output_dir').value
        self.world_frame = self.get_parameter('world_frame').value
        self.camera_frame = self.get_parameter('camera_frame').value
        os.makedirs(self.output_dir, exist_ok=True)

        self.bridge = CvBridge()
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.latest_joint_state = None
        self.seq = 0
        self.images_received = 0

        self.create_subscription(JointState, '/joint_states', self._joint_cb, 10)
        self.create_subscription(Image, '/camera/image_raw', self._image_cb, 10)

        self.get_logger().info(f'Saving captures to {self.output_dir}')
        self.get_logger().info(f'Subscribing to /camera/image_raw')

    def _joint_cb(self, msg: JointState):
        self.latest_joint_state = msg

    def _image_cb(self, msg: Image):
        try:
            self.images_received += 1
            if self.images_received == 1:
                self.get_logger().info(f'Received first image: {msg.width}x{msg.height}, encoding={msg.encoding}')
            
            stamp = msg.header.stamp
            sec = stamp.sec if hasattr(stamp, 'sec') else int(stamp.nanosec / 1e9)
            nsec = stamp.nanosec if hasattr(stamp, 'nanosec') else stamp.nanosec % int(1e9)
            iso_time = datetime.fromtimestamp(sec + nsec * 1e-9, tz=timezone.utc).isoformat()

            base_name = f'img_{self.seq:06d}_{sec}_{nsec:09d}'
            img_path = os.path.join(self.output_dir, base_name + '.png')
            meta_path = os.path.join(self.output_dir, base_name + '.yaml')

            # Save image
            cv_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            cv2.imwrite(img_path, cv_img)

            # Look up camera pose in world frame at this timestamp
            pose_data = None
            try:
                tf = self.tf_buffer.lookup_transform(
                    self.world_frame, self.camera_frame, stamp)
                t = tf.transform.translation
                q = tf.transform.rotation
                pose_data = {
                    'position': {'x': t.x, 'y': t.y, 'z': t.z},
                    'orientation': {'x': q.x, 'y': q.y, 'z': q.z, 'w': q.w},
                }
            except Exception as e:
                self.get_logger().debug(f'TF lookup failed for {base_name}: {e}')

            joint_data = None
            if self.latest_joint_state is not None:
                joint_data = dict(zip(
                    self.latest_joint_state.name,
                    self.latest_joint_state.position
                ))

            metadata = {
                'image_file': os.path.basename(img_path),
                'sequence': self.seq,
                'stamp': {'sec': sec, 'nanosec': nsec, 'iso': iso_time},
                'frame_id': msg.header.frame_id,
                'encoding': msg.encoding,
                'width': msg.width,
                'height': msg.height,
                'camera_pose_in_world': pose_data,
                'joint_positions': joint_data,
            }

            with open(meta_path, 'w') as f:
                yaml.safe_dump(metadata, f, sort_keys=False)

            self.seq += 1
            self.get_logger().info(f'Saved {base_name}')
        except Exception as e:
            self.get_logger().error(f'Error processing image: {e}')
            self.get_logger().error(traceback.format_exc())


def main(args=None):
    rclpy.init(args=args)
    node = CameraLogger()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()


if __name__ == '__main__':
    main()