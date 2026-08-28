#include <rclcpp/rclcpp.hpp>
#include <moveit/move_group_interface/move_group_interface.hpp>
#include <std_msgs/msg/int32.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <thread>
#include <chrono>
#include <vector>
#include <atomic>

// Simplified flow, no stepping:
//   1. Move arm to a keypoint
//   2. Send turntable_node ONE /turntable/full_turn trigger (it commands
//      +2*pi radians absolute on /turntable/cmd_pos and gives Gazebo
//      full_turn_duration_s to complete it smoothly -- see turntable_node.cpp)
//   3. capture_node keeps grabbing frames on its own continuous timer
//      (started here) the whole time step 1+2 are happening
//   4. Wait for turntable_node's rotate_done ack, then move to the next
//      keypoint (if any) and repeat
//   5. Arm home, stop capturing, publish scan-complete
class SequenceNode : public rclcpp::Node
{
public:
  SequenceNode() : Node("sequence_node"), got_joint_state_(false), scan_started_(false), turntable_done_(false)
  {
    signal_pub_ = this->create_publisher<std_msgs::msg::Int32>("/capture_signal", 10);
    start_sub_ = this->create_subscription<std_msgs::msg::Int32>(
      "/capture_start", 10, std::bind(&SequenceNode::start_cb, this, std::placeholders::_1));
    joint_state_sub_ = this->create_subscription<sensor_msgs::msg::JointState>(
      "/joint_states", rclcpp::SensorDataQoS(),
      std::bind(&SequenceNode::joint_state_cb, this, std::placeholders::_1));

    full_turn_pub_ = this->create_publisher<std_msgs::msg::Int32>("/turntable/full_turn", 10);
    turntable_done_sub_ = this->create_subscription<std_msgs::msg::Int32>(
      "/turntable/rotate_done", 10, std::bind(&SequenceNode::turntable_done_cb, this, std::placeholders::_1));

    // Continuous-capture rate: a frame is requested every capture_interval_ms
    // for the whole time the arm is moving and the whole time the turntable
    // is spinning. Nothing waits on anything else.
    this->declare_parameter<int>("capture_interval_ms", 300);
    // Must exceed turntable_node's full_turn_duration_s by some margin, or
    // we'll give up waiting before the physical spin is actually done.
    this->declare_parameter<double>("full_turn_wait_timeout_s", 12.0);
  }

  bool initialize()
  {
    RCLCPP_INFO(this->get_logger(), "Waiting for joint states... (timeout: 60s)");

    auto start = std::chrono::steady_clock::now();
    while ((std::chrono::steady_clock::now() - start) < std::chrono::duration<double>(60.0)) {
      rclcpp::spin_some(this->get_node_base_interface());
      if (got_joint_state_) {
        RCLCPP_INFO(this->get_logger(), "Joint states received!");
        break;
      }
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    if (!got_joint_state_) {
      RCLCPP_ERROR(this->get_logger(), "No /joint_states received.");
      return false;
    }

    move_group_interface_ = std::make_shared<moveit::planning_interface::MoveGroupInterface>(shared_from_this(), "arm_group");
    move_group_interface_->setNumPlanningAttempts(10);
    move_group_interface_->setPlanningTime(5.0);

    RCLCPP_INFO(this->get_logger(), "========================================");
    RCLCPP_INFO(this->get_logger(), "  Robot is ready!");
    RCLCPP_INFO(this->get_logger(), "  Click 'START SCAN' in the GUI window.");
    RCLCPP_INFO(this->get_logger(), "========================================");

    scan_thread_ = std::thread(&SequenceNode::execute_scan_loop, this);
    return true;
  }

  ~SequenceNode() {
    if (scan_thread_.joinable()) scan_thread_.join();
  }

private:
  void joint_state_cb(const sensor_msgs::msg::JointState::SharedPtr /*msg*/) {
    got_joint_state_ = true;
  }

  void start_cb(const std_msgs::msg::Int32::SharedPtr /*msg*/) {
    scan_started_ = true;
    RCLCPP_INFO(this->get_logger(), "Scan triggered by GUI button!");
  }

  void turntable_done_cb(const std_msgs::msg::Int32::SharedPtr /*msg*/) {
    turntable_done_ = true;
  }

  void execute_scan_loop()
  {
    while (!scan_started_ && rclcpp::ok()) {
      std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
    if (!rclcpp::ok()) return;

    RCLCPP_INFO(this->get_logger(), "START pressed -- scan begins now, no delay.");

    // Add more keypoints here if you want multiple viewpoints, each
    // getting its own full 360 deg spin. Currently just home.
    std::vector<std::vector<double>> waypoints = {
    //{0.0, 0.0, 0.0, 0.0, 0.0, 0.0},                   // home
    //{0.0, 0.0, -1.047, 1.099, 0.0, 0.0},              // zoom on plant
    {0.0, 0.471239, -0.523599, -0.122173, 0.104720, 0.0}, // custom pose
    };
    const std::vector<double> home_joint_values = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};

    int capture_interval_ms = 300;
    this->get_parameter("capture_interval_ms", capture_interval_ms);
    double full_turn_wait_timeout_s = 12.0;
    this->get_parameter("full_turn_wait_timeout_s", full_turn_wait_timeout_s);

    RCLCPP_INFO(this->get_logger(),
      "%zu keypoint(s), one full 360 deg spin each, capturing continuously every %d ms.",
      waypoints.size(), capture_interval_ms);

    global_frame_index_ = 0;

    // ---- One continuous capture thread for the WHOLE scan ----
    // Fire-and-forget: publishes /capture_signal on a fixed timer from the
    // moment START is pressed until the scan ends, regardless of what the
    // arm or turntable are doing.
    std::atomic<bool> capturing(true);
    std::thread capture_thread([this, &capturing, capture_interval_ms]() {
      while (capturing.load() && rclcpp::ok()) {
        std_msgs::msg::Int32 signal;
        signal.data = global_frame_index_++;
        signal_pub_->publish(signal);
        std::this_thread::sleep_for(std::chrono::milliseconds(capture_interval_ms));
      }
    });

    for (size_t wp = 0; wp < waypoints.size(); ++wp) {
      if (!rclcpp::ok()) break;
      RCLCPP_INFO(this->get_logger(), "=== Keypoint %zu/%zu: moving arm ===", wp + 1, waypoints.size());

      move_group_interface_->setJointValueTarget(waypoints[wp]);
      moveit::planning_interface::MoveGroupInterface::Plan plan;
      if (move_group_interface_->plan(plan) != moveit::core::MoveItErrorCode::SUCCESS) {
        RCLCPP_ERROR(this->get_logger(), "Planning failed for keypoint %zu -- skipping its spin.", wp + 1);
        continue;
      }
      if (move_group_interface_->execute(plan) != moveit::core::MoveItErrorCode::SUCCESS) {
        RCLCPP_ERROR(this->get_logger(), "Execution failed for keypoint %zu -- skipping its spin.", wp + 1);
        continue;
      }

      RCLCPP_INFO(this->get_logger(), "Arm in position. Commanding single 360 deg turntable spin...");
      turntable_done_ = false;
      std_msgs::msg::Int32 trigger;
      trigger.data = 0;
      full_turn_pub_->publish(trigger);

      auto wait_start = std::chrono::steady_clock::now();
      while (!turntable_done_ && rclcpp::ok() &&
             (std::chrono::steady_clock::now() - wait_start) < std::chrono::duration<double>(full_turn_wait_timeout_s)) {
        // NOTE: no spin_some here -- main() already runs rclcpp::spin(node)
        // on this same node, which is what actually invokes turntable_done_cb
        // and start_cb. Calling spin_some on the same node from this thread
        // races with that and aborts with "Node has already been added to
        // an executor." Just poll the atomic flag. Capture thread keeps
        // firing the entire time.
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
      }
      if (!turntable_done_) {
        RCLCPP_ERROR(this->get_logger(), "Timed out waiting for the 360 deg spin to finish. Aborting scan.");
        capturing = false;
        capture_thread.join();
        RCLCPP_INFO(this->get_logger(), "Scan aborted! %d frames captured.", global_frame_index_.load());
        std_msgs::msg::Int32 termination_msg;
        termination_msg.data = -1;
        signal_pub_->publish(termination_msg);
        return;
      }
      RCLCPP_INFO(this->get_logger(), "Spin complete for keypoint %zu.", wp + 1);
    }

    // Arm home at the end (still capturing throughout).
    if (rclcpp::ok()) {
      RCLCPP_INFO(this->get_logger(), "Sweep complete. Returning arm to home position...");
      move_group_interface_->setJointValueTarget(home_joint_values);
      moveit::planning_interface::MoveGroupInterface::Plan home_plan;
      if (move_group_interface_->plan(home_plan) == moveit::core::MoveItErrorCode::SUCCESS) {
        move_group_interface_->execute(home_plan);
      }
    }

    capturing = false;
    capture_thread.join();

    RCLCPP_INFO(this->get_logger(), "Scan complete! %d frames captured.", global_frame_index_.load());
    std_msgs::msg::Int32 termination_msg;
    termination_msg.data = -1;
    signal_pub_->publish(termination_msg);
  }

  rclcpp::Publisher<std_msgs::msg::Int32>::SharedPtr signal_pub_;
  rclcpp::Subscription<std_msgs::msg::Int32>::SharedPtr start_sub_;
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_state_sub_;
  rclcpp::Publisher<std_msgs::msg::Int32>::SharedPtr full_turn_pub_;
  rclcpp::Subscription<std_msgs::msg::Int32>::SharedPtr turntable_done_sub_;
  std::atomic<bool> got_joint_state_;
  std::atomic<bool> scan_started_;
  std::atomic<bool> turntable_done_;
  std::atomic<int> global_frame_index_;
  std::shared_ptr<moveit::planning_interface::MoveGroupInterface> move_group_interface_;
  std::thread scan_thread_;
};

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<SequenceNode>();
  if (!node->initialize()) {
    RCLCPP_ERROR(node->get_logger(), "Initialization failed. Exiting.");
    rclcpp::shutdown();
    return 1;
  }
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}