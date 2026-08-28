#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/int32.hpp>
#include <std_msgs/msg/float64.hpp>
#include <chrono>
#include <cmath>

// Drives the Gazebo turntable modeled in lab_world_plant3.sdf.
//
// The SDF's turntable_joint uses the JointPositionController plugin
// (gz-sim-joint-position-controller-system) on /turntable/cmd_pos
// (gz.msgs.Double, ABSOLUTE target angle in RADIANS, bridged here as
// std_msgs/Float64). Gazebo's own PID drives the joint to that target.
//
// SINGLE CONTINUOUS SPIN, not stepped: on /turntable/full_turn, this node
// commands one absolute target of +2*pi radians (360 deg) past wherever it
// currently is, then just gives Gazebo full_turn_duration_s to smoothly
// carry it there -- no intermediate step commands, no per-step settle.
// capture_node keeps grabbing frames continuously the whole time via its
// own independent timer in sequence_node.
//
// turntable_joint has no travel limits (continuous revolute), so the
// commanded angle is tracked as an UNWRAPPED, monotonically increasing
// value in radians and only wrapped to [0, 360) deg for telemetry. This
// avoids a wrap-around bug where modding the target before sending it
// (e.g. 350 deg + 45 deg -> "35 deg") could spin the table backward the
// short way instead of continuing forward.
//
// current_angle_deg during the spin is a linear INTERPOLATION between the
// start and target angle over full_turn_duration_s, not a measured value
// (this node doesn't subscribe to the joint's real gz feedback) -- good
// enough for per-frame metadata, not a precision encoder reading.
class TurntableNode : public rclcpp::Node
{
public:
  TurntableNode() : Node("turntable_node"), commanded_angle_rad_(0.0)
  {
    // How long Gazebo is given to complete one full 360 deg turn. Tune
    // this to how fast you want the physical/sim motion to look --
    // longer = smoother turn, shorter = faster scan but more risk of the
    // PID not quite catching up by the time we declare done.
    this->declare_parameter<double>("full_turn_duration_s", 8.0);
    // How often telemetry (/turntable/current_angle_deg) is published
    // during the spin.
    this->declare_parameter<double>("telemetry_interval_s", 0.2);

    this->get_parameter("full_turn_duration_s", full_turn_duration_s_);
    this->get_parameter("telemetry_interval_s", telemetry_interval_s_);

    cmd_pos_pub_ = this->create_publisher<std_msgs::msg::Float64>("/turntable/cmd_pos", 10);
    angle_pub_ = this->create_publisher<std_msgs::msg::Float64>("/turntable/current_angle_deg", 10);
    rotate_done_pub_ = this->create_publisher<std_msgs::msg::Int32>("/turntable/rotate_done", 10);

    full_turn_sub_ = this->create_subscription<std_msgs::msg::Int32>(
      "/turntable/full_turn", 10,
      std::bind(&TurntableNode::full_turn_cb, this, std::placeholders::_1));

    // Command + publish the starting position once so the joint holds at
    // 0 and capture_node has something for frame 0.
    publish_target(commanded_angle_rad_);
    publish_angle();

    RCLCPP_INFO(this->get_logger(),
      "turntable_node ready: one-shot 360 deg spin over %.1fs on /turntable/full_turn (sends radians to /turntable/cmd_pos).",
      full_turn_duration_s_);
  }

private:
  void full_turn_cb(const std_msgs::msg::Int32::SharedPtr /*msg*/)
  {
    double start_rad = commanded_angle_rad_;
    double target_rad = start_rad + 2.0 * M_PI; // exactly one full turn, in radians

    RCLCPP_INFO(this->get_logger(),
      "Commanding full 360 deg turn: %.4f rad -> %.4f rad, over %.1fs...",
      start_rad, target_rad, full_turn_duration_s_);

    publish_target(target_rad); // single absolute command, Gazebo's PID does the rest

    rclcpp::Rate rate(1.0 / telemetry_interval_s_);
    auto spin_start = this->now();
    while (rclcpp::ok()) {
      double elapsed = (this->now() - spin_start).seconds();
      if (elapsed >= full_turn_duration_s_) break;
      double frac = elapsed / full_turn_duration_s_;
      commanded_angle_rad_ = start_rad + frac * (target_rad - start_rad);
      publish_angle();
      rate.sleep();
    }

    commanded_angle_rad_ = target_rad;
    publish_angle();
    RCLCPP_INFO(this->get_logger(), "Full turn complete, now at %.1f deg (wrapped).", wrapped_deg());

    std_msgs::msg::Int32 done;
    done.data = 0;
    rotate_done_pub_->publish(done);
  }

  void publish_target(double angle_rad)
  {
    std_msgs::msg::Float64 msg;
    msg.data = angle_rad; // RADIANS -- gz-sim-joint-position-controller-system expects radians
    cmd_pos_pub_->publish(msg);
  }

  void publish_angle()
  {
    std_msgs::msg::Float64 msg;
    msg.data = wrapped_deg();
    angle_pub_->publish(msg);
  }

  double wrapped_deg() const
  {
    double deg = commanded_angle_rad_ * 180.0 / M_PI;
    double wrapped = std::fmod(deg, 360.0);
    if (wrapped < 0) wrapped += 360.0;
    return wrapped;
  }

  rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr cmd_pos_pub_;
  rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr angle_pub_;
  rclcpp::Publisher<std_msgs::msg::Int32>::SharedPtr rotate_done_pub_;
  rclcpp::Subscription<std_msgs::msg::Int32>::SharedPtr full_turn_sub_;

  double full_turn_duration_s_;
  double telemetry_interval_s_;
  double commanded_angle_rad_;
};

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<TurntableNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}